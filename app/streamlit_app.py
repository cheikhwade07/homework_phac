"""Web interface: enter a request, classify cases, review the relevant ones.

Run with:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from casefilter.data import load_cases
from casefilter.pipeline import DEFAULT_PROMPT, build_classifier, run_filter, select_cases
from casefilter.prompts import PROMPTS_DIR

EXAMPLES = [
    "Filter the cases related to cardiovascular disease.",
    "Filter the cases associated with e-scooter injuries.",
    "Filter the cases related to leukemia.",
    "Filter the cases related to infectious disease.",
]
OWN = "(write your own)"

st.set_page_config(page_title="Clinical Case Filter", layout="wide")
st.title("Clinical Case Filter")
st.caption(
    "Describe the cases you want in plain language. Each case is read by an LLM, "
    "which answers YES or NO."
)


@st.cache_resource(show_spinner="Loading the MultiCaRe dataset (the first run downloads it)...")
def cases_table() -> pd.DataFrame:
    return load_cases()


@st.cache_resource
def classifier_for(prompt_version: str):
    return build_classifier(prompt_version)


with st.sidebar:
    st.header("Cases to classify")
    n_cases = st.slider("Number of cases", min_value=5, max_value=200, value=30, step=5)
    keyword = st.text_input(
        "Keyword pre-filter (optional)",
        help="Only cases containing this word are considered. Useful for rare concepts "
        "such as 'scooter', where a random sample would contain no matches.",
    )
    seed = st.number_input("Random seed", min_value=0, value=0, step=1)
    versions = sorted(p.stem for p in PROMPTS_DIR.glob("classify.*.toml"))
    prompt_version = st.selectbox("Prompt version", versions, index=versions.index(DEFAULT_PROMPT))

example = st.selectbox("Example requests", [OWN, *EXAMPLES])
request = st.text_input("Filtering request", value="" if example == OWN else example)

if st.button("Run classification", type="primary", disabled=not request.strip()):
    cases = select_cases(cases_table(), n_cases, int(seed), keyword)
    if not cases:
        st.warning("No cases contain that keyword.")
        st.stop()
    try:
        classifier = classifier_for(prompt_version)
        definition = classifier.definition_for(request)
    except Exception as exc:
        st.error(f"Could not start: {exc}. Check that GEMINI_API_KEY is set in .env.")
        st.stop()
    with st.spinner(f"Classifying {len(cases)} cases..."):
        results = run_filter(request, cases, classifier)
    st.session_state["results"] = results
    st.session_state["run"] = {
        "request": request,
        "classifier": classifier.name,
        "definition": definition.to_text() if definition else None,
    }

if "results" in st.session_state:
    results = st.session_state["results"]
    run = st.session_state["run"]
    relevant = [(c, p) for c, p in results if p.label == "YES"]
    errors = [p for _, p in results if p.label == "ERROR"]

    st.subheader(f"Request: {run['request']}")
    st.caption(f"Classifier: {run['classifier']}")
    if run["definition"]:
        with st.expander("How the request was interpreted"):
            st.text(run["definition"])
    left, middle, right = st.columns(3)
    left.metric("Cases classified", len(results))
    middle.metric("Relevant (YES)", len(relevant))
    right.metric("Could not classify", len(errors))

    tab_relevant, tab_all = st.tabs(["Relevant cases", "Result for each case"])

    with tab_relevant:
        if not relevant:
            st.info("No relevant cases in this sample. Try more cases or a keyword pre-filter.")
        for case, prediction in relevant:
            with st.expander(f"{case.case_id}: {prediction.reason or 'YES'}"):
                if prediction.evidence:
                    st.markdown(f"**Evidence:** “{prediction.evidence}”")
                    if prediction.evidence_found is False:
                        st.warning("This quote was not found in the case text.")
                st.write(case.case_text)

    with tab_all:
        table = pd.DataFrame(
            {
                "case_id": [c.case_id for c, _ in results],
                "result": [p.label for _, p in results],
                "reason": [p.reason or p.error or "" for _, p in results],
                "evidence": [p.evidence or "" for _, p in results],
                "case_text": [c.case_text for c, _ in results],
            }
        )
        st.dataframe(table, width="stretch", hide_index=True)
        st.download_button(
            "Download results as CSV",
            table.to_csv(index=False).encode("utf-8"),
            file_name="case_filter_results.csv",
            mime="text/csv",
        )
