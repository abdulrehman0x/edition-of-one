from __future__ import annotations

import json
import os

import pytest

from pdf_generator.render import build_html, count_pages, render_pdf


REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SAMPLE = os.path.join(REPO_ROOT, "frontend", "public", "sample-edition.json")


def _load_sample() -> dict:
    with open(SAMPLE, "r", encoding="utf-8") as f:
        return json.load(f)


def _clone(base: dict) -> dict:
    return json.loads(json.dumps(base))


@pytest.fixture(autouse=True)
def _fast_offline(monkeypatch):
    """Keep tests network-free and fast."""
    monkeypatch.setenv("PDF_HTTP_TIMEOUT", "1")
    monkeypatch.setenv("PDF_IMG_BUDGET", "3")
    yield


@pytest.fixture(scope="module")
def base_edition() -> dict:
    return _load_sample()


@pytest.fixture
def tmp_pdf(tmp_path):
    return str(tmp_path / "out.pdf")


def _assert_pdf(path: str) -> None:
    with open(path, "rb") as f:
        head = f.read(4)
    assert head == b"%PDF"


def test_render_sample(tmp_pdf, base_edition):
    render_pdf(base_edition, tmp_pdf)
    _assert_pdf(tmp_pdf)
    assert os.path.getsize(tmp_pdf) > 1000
    assert count_pages(base_edition) >= 3


def test_build_html_is_str(base_edition):
    html = build_html(base_edition)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Edition of One" in html


def test_broken_images(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    bad = "http://10.255.255.1/nope.jpg"

    def _break(art):
        if isinstance(art, dict):
            art["image_url"] = bad
            art["image"] = bad

    _break(ed.get("lead"))
    for a in ed.get("secondary") or []:
        _break(a)
    for sec in ed.get("sections") or []:
        _break(sec.get("feature"))
        for a in sec.get("items") or []:
            _break(a)

    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_empty_sections(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["sections"] = []
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_missing_back_page(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed.pop("back_page", None)
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_press_gallery_present(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["press_gallery"] = {
        "topic_label": "Test topic",
        "rows": [
            {
                "source": "Outlet A",
                "headline": "Headline from A",
                "url": "https://a.example/x",
                "emphasis": "angle A",
            },
            {
                "source": "Outlet B",
                "headline": "Headline from B",
                "url": "https://b.example/x",
                "emphasis": "angle B",
            },
            {
                "source": "Outlet C",
                "headline": "Headline from C",
                "url": "https://c.example/x",
                "emphasis": "angle C",
            },
        ],
        "agreed_facts": ["Fact one.", "Fact two."],
        "open_question": "What happens next?",
    }
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_200_character_headline(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    if isinstance(ed.get("lead"), dict):
        ed["lead"]["headline"] = "X" * 200
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_body_with_html_and_unicode(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    if isinstance(ed.get("lead"), dict):
        ed["lead"]["body"] = (
            "A body with <script>alert(1)</script> & < > \"quotes\" "
            "and unicode \u2713 \u00fcn\u00efc\u00f6d\u00e9 \u2014 and a \u2018curly\u2019 apostrophe."
        )
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_lead_only(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["sections"] = []
    ed["secondary"] = []
    ed["briefs"] = []
    ed["front_briefs"] = []
    ed["secondary_stories"] = []
    ed.pop("back_page", None)
    ed.pop("press_gallery", None)
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)
