from app.core.llm import repair_json


def test_plain_json():
    assert repair_json('{"a": 1}') == {"a": 1}


def test_code_fence():
    assert repair_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_prose_wrapped():
    got = repair_json('Sure! Here you go: {"a": 2, "b": [1,2,3]}')
    assert isinstance(got, dict) and got.get("a") == 2


def test_prose_wrapped_list():
    got = repair_json('Result: [{"a": 1}, {"a": 2}] hope that helps')
    assert isinstance(got, list) and len(got) == 2


def test_broken_json_returns_dict():
    got = repair_json('{a: 1,')
    assert isinstance(got, (dict, list))
