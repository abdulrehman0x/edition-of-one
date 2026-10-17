from types import SimpleNamespace

from app.services.profile_service import _keywords_to_topics, create_profile


def test_ai_keyword_needs_word_boundary():
    assert "ai" not in _keywords_to_topics("please maintain my email")
    assert "ai" in _keywords_to_topics("I follow AI and tech")


def test_create_profile_defaults():
    req = SimpleNamespace(reader_id="r", name="", interests=[], location="", tone="")
    p = create_profile(req)
    assert p.topics and p.name == "r"
