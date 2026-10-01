from casefilter.llm import ResponseCache


def test_cache_round_trip(tmp_path):
    cache = ResponseCache(tmp_path / "c.sqlite")
    key = ResponseCache.key(model="m", user="u")
    assert cache.get(key) is None
    cache.put(key, {"text": "{}", "model": "m"})
    assert cache.get(key) == {"text": "{}", "model": "m"}


def test_cache_key_changes_with_any_input():
    base = ResponseCache.key(model="m", system="s", user="u", schema={"a": 1})
    assert base == ResponseCache.key(user="u", schema={"a": 1}, system="s", model="m")
    assert base != ResponseCache.key(model="m2", system="s", user="u", schema={"a": 1})
    assert base != ResponseCache.key(model="m", system="s", user="u2", schema={"a": 1})
