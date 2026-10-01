import numpy as np

from casefilter.embedding import normalise, split_long_text


def test_short_text_is_not_split():
    assert split_long_text("short", max_chars=10, overlap=2) == ["short"]


def test_long_text_is_fully_covered_with_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = split_long_text(text, max_chars=10, overlap=2)
    assert all(len(chunk) <= 10 for chunk in chunks)
    assert chunks[0] == text[:10] and chunks[-1].endswith("z")
    for left, right in zip(chunks, chunks[1:], strict=False):
        assert left[-2:] == right[:2]
    assert set("".join(chunks)) == set(text)


def test_normalise_gives_unit_length():
    assert np.isclose(np.linalg.norm(normalise(np.array([3.0, 4.0]))), 1.0)
    assert not normalise(np.zeros(3)).any()
