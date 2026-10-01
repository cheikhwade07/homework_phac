import pytest

from casefilter.prompts import PROMPTS_DIR, load_prompt


def test_every_prompt_file_loads():
    for path in PROMPTS_DIR.glob("*.toml"):
        assert load_prompt(path.stem).schema["type"] == "OBJECT"


def test_render_inserts_values_verbatim():
    _, user = load_prompt("classify.v1").render(
        classification_criteria="leukemia", case_text="Value with {braces}."
    )
    assert "leukemia" in user and "Value with {braces}." in user


def test_render_requires_every_placeholder():
    with pytest.raises(KeyError):
        load_prompt("classify.v1").render(classification_criteria="leukemia")


def test_version_must_match_file_name(tmp_path):
    (tmp_path / "x.v1.toml").write_text(
        'version = "other"\nuser = "u"\n[schema]\ntype = "OBJECT"\n'
    )
    with pytest.raises(ValueError):
        load_prompt("x.v1", directory=tmp_path)
