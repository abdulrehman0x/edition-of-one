import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pdf_generator"))

from render import build_html  # noqa: E402


def _sample():
    return {
        "id": "ed-test-2025-01-01",
        "reader_id": "test-reader",
        "date": "2025-01-01",
        "nameplate": "Edition of One",
        "dateline": "Islamabad \u2014 2025-01-01",
        "front": {
            "lead": {
                "id": "a1",
                "title": "A lead story <b>unsafe</b>",
                "source": "Test Wire",
                "topics": ["world"],
                "body": {"short": "Short.", "medium": "Medium body.", "long": "Long body."},
            },
            "secondary": [],
            "briefs": [],
            "weather": {"city": "Islamabad", "temp_c": 30, "high_c": 33, "low_c": 22, "condition": ""},
            "quote": "A quote for the front page.",
        },
        "sections": [],
        "outside_bubble": [],
    }


def test_build_html_renders():
    html = build_html(_sample())
    assert "Edition of One" in html
    assert "A lead story" in html


def test_article_markup_is_escaped():
    html = build_html(_sample())
    assert "<b>unsafe</b>" not in html
    assert "&lt;b&gt;unsafe" in html
