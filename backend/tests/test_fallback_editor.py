from __future__ import annotations

import datetime as dt

import pytest

from app.models.schemas import ArticleRecord, Edition, Profile
from app.services.fallback_editor import build_edition


def _article(
    article_id: str,
    title: str,
    topic: str = "world",
    body: str = "One sentence here. Another sentence follows. A third sentence closes the note.",
    importance: float = 0.5,
) -> ArticleRecord:
    return ArticleRecord(
        id=article_id,
        url=f"https://example.org/{article_id}",
        title=title,
        body=body,
        source="Test Wire",
        topic=topic,
        importance=importance,
    )


def _profile(**kwargs) -> Profile:
    data = {"reader_id": "reader-test", "display_name": "Tester", "topic_weights": {"world": 0.5}}
    data.update(kwargs)
    return Profile(**data)


def _all_ids(edition: Edition) -> list[str]:
    ids = [edition.front.lead.id]
    ids.extend(article.id for article in edition.front.secondary)
    ids.extend(article.id for article in edition.front.briefs)
    for section in edition.sections:
        ids.extend(article.id for article in section.items)
    return ids


def test_zero_weights() -> None:
    profile = _profile(topic_weights={})
    articles = [_article(f"a{i}", f"Story number {i}") for i in range(10)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id


def test_three_articles() -> None:
    profile = _profile()
    articles = [_article(f"a{i}", f"Three story {i}") for i in range(3)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id
    assert len(_all_ids(edition)) >= 3


def test_empty_bodies() -> None:
    profile = _profile()
    articles = [
        ArticleRecord(
            id=f"empty{i}",
            url=f"https://example.org/empty{i}",
            title=f"Empty body story {i}",
            body="",
            brief="",
            source="Test Wire",
            topic="world",
        )
        for i in range(6)
    ]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id


def test_no_articles_raises() -> None:
    profile = _profile()
    with pytest.raises(ValueError, match="no articles"):
        build_edition(profile, [], dt.date(2024, 1, 1), 1)


def test_near_duplicates_removed() -> None:
    profile = _profile()
    articles = [
        _article("a1", "This is a very similar title about the same topic"),
        _article("a2", "This is a very similar title about the same topic"),
        _article("a3", "Completely different story about something else entirely"),
        _article("a4", "Another story about cats and their daily habits"),
    ]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    ids = _all_ids(edition)
    assert "a1" in ids
    assert "a2" not in ids


def test_output_validates_against_edition() -> None:
    profile = _profile()
    articles = [_article(f"v{i}", f"Validation story {i}") for i in range(6)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    Edition.model_validate(edition.model_dump())
