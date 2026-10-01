# Clinical Case Filter

Filter clinical cases from the [MultiCaRe](https://huggingface.co/datasets/OpenMed/multicare-cases)
dataset using a criterion written in plain language, for example:

> Filter the cases related to cardiovascular disease.

> Filter the cases associated with e-scooter injuries.

For each case, an LLM decides whether `case_text` is relevant (**YES**) or not (**NO**).
The criterion comes from the user at runtime; nothing is hard-coded per concept.

> Work in progress. Setup, usage, evaluation results and design notes will be added as the
> components land.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux
pip install -e ".[dev]"
copy .env.example .env          # then add your API key
```

## Repository layout

```
prompts/          versioned prompt templates
src/casefilter/   core library (data, LLM client, classifiers, pipeline)
app/              user interface
eval/             labeling guidelines, test sets, evaluation runner, results
tests/            unit tests (LLM mocked)
```
