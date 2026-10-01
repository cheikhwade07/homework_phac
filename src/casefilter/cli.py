"""Command-line interface.

Examples:
    casefilter "Filter the cases related to leukemia." --n 30
    casefilter "Filter the cases associated with e-scooter injuries." --keyword scooter
    casefilter "Filter the cases related to infectious disease." --n 20 --show-text
"""

from __future__ import annotations

import argparse
import sys
import textwrap

from casefilter.data import load_cases
from casefilter.pipeline import DEFAULT_PROMPT, build_classifier, run_filter, select_cases
from casefilter.prompts import PROMPTS_DIR

RULE = "-" * 110


def _snippet(text: str, width: int = 86) -> str:
    return textwrap.shorten(" ".join(text.split()), width=width, placeholder="...")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="casefilter",
        description="Filter MultiCaRe clinical cases by a criterion written in plain language.",
    )
    parser.add_argument("request", help="the filtering request, in quotes")
    parser.add_argument("--n", type=int, default=20, help="number of cases to classify")
    parser.add_argument("--seed", type=int, default=0, help="random seed for the case sample")
    parser.add_argument(
        "--keyword", help="only consider cases whose text contains this word (cheap pre-filter)"
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT, help="prompt version in prompts/")
    parser.add_argument("--show-text", action="store_true", help="print relevant cases in full")
    args = parser.parse_args(argv)

    if not args.request.strip():
        parser.error("the request is empty")
    if args.n < 1:
        parser.error("--n must be at least 1")
    available = sorted(p.stem for p in PROMPTS_DIR.glob("classify.*.toml"))
    if args.prompt not in available:
        parser.error(f"unknown prompt '{args.prompt}'; choose from: {', '.join(available)}")

    try:
        classifier = build_classifier(args.prompt)
    except Exception as exc:  # most often a missing API key
        print(f"Could not start the LLM client: {exc}", file=sys.stderr)
        print("Set GEMINI_API_KEY in a .env file (see .env.example).", file=sys.stderr)
        return 2

    cases = select_cases(load_cases(), args.n, args.seed, args.keyword)
    if not cases:
        print(f"No cases contain the keyword '{args.keyword}'.", file=sys.stderr)
        return 1
    scope = f" containing '{args.keyword}'" if args.keyword else ""
    print(f"Request:    {args.request}")
    print(f"Classifier: {classifier.name}")
    print(f"Cases:      {len(cases)}{scope}")
    try:
        definition = classifier.definition_for(args.request)
    except Exception as exc:
        print(f"Could not interpret the request: {exc}", file=sys.stderr)
        return 2
    if definition is not None:
        print()
        print("Request interpreted as")
        print(textwrap.indent(definition.to_text(), "  "))
    print()

    results = run_filter(args.request, cases, classifier)

    print("Result for each case")
    print(RULE)
    for case, prediction in results:
        print(f"{prediction.label:<6}{case.case_id:<18}{_snippet(case.case_text)}")

    relevant = [(c, p) for c, p in results if p.label == "YES"]
    errors = [p for _, p in results if p.label == "ERROR"]
    failed = f"  ({len(errors)} could not be classified)" if errors else ""
    print()
    print(f"Relevant cases: {len(relevant)} of {len(results)}{failed}")
    print(RULE)
    for case, prediction in relevant:
        print(case.case_id)
        if prediction.evidence:
            flag = "" if prediction.evidence_found else "  [quote not found in case text]"
            print(f'  evidence: "{prediction.evidence}"{flag}')
        elif prediction.evidence_found is False:
            print("  evidence: [none given]")
        if prediction.reason:
            print(f"  reason:   {prediction.reason}")
        if args.show_text:
            print(textwrap.indent(textwrap.fill(case.case_text, 100), "  | "))
        print()
    for prediction in errors:
        print(f"ERROR {prediction.case_id}: {prediction.error}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
