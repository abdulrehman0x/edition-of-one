from __future__ import annotations

import datetime as dt
import os
import re
import urllib.parse

from app.models.schemas import ArticleRecord, Art, Body, Edition, Front, Profile, Section

_WORD_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _dedupe(articles: list[ArticleRecord]) -> list[ArticleRecord]:
    kept: list[ArticleRecord] = []
    kept_tokens: list[set[str]] = []
    for article in articles:
        tokens = _tokenize(article.title)
        if any(_jaccard(tokens, other) > 0.6 for other in kept_tokens):
            continue
        kept.append(article)
        kept_tokens.append(tokens)
    return kept


def _topic_weight(profile: Profile, topic: str, default: float = 0.15) -> float:
    return float(profile.topic_weights.get(topic, default))


def _freshness(article: ArticleRecord, index: int, total: int, for_date: dt.date) -> float:
    if article.published_at is not None:
        published = article.published_at
        if published.tzinfo is None:
            published = published.replace(tzinfo=dt.timezone.utc)
        anchor = dt.datetime.combine(for_date, dt.time.min, tzinfo=dt.timezone.utc)
        days = max(0.0, (anchor - published).total_seconds() / 86400.0)
        return 1.0 / (1.0 + days / 7.0)
    if total <= 1:
        return 1.0
    return max(0.0, 1.0 - index / (total - 1))


def _score(article: ArticleRecord, index: int, total: int, profile: Profile, for_date: dt.date) -> float:
    return (
        0.5 * _topic_weight(profile, article.topic)
        + 0.3 * float(article.importance)
        + 0.2 * _freshness(article, index, total, for_date)
    )


def _trim_headline(title: str) -> str:
    words = title.split()
    if not words:
        return "Untitled"
    return " ".join(words[:14])


def _extract(text: str, target: int) -> str:
    source = (text or "").strip()
    if not source:
        return ""
    sentences = [sentence.strip() for sentence in _SENTENCE_RE.split(source) if sentence.strip()]
    if not sentences:
        sentences = [source]
    selected: list[str] = []
    count = 0
    for sentence in sentences:
        words = sentence.split()
        if selected and count + len(words) > target:
            break
        if not selected and len(words) > target:
            selected.append(" ".join(words[:target]))
            count = target
            break
        selected.append(sentence)
        count += len(words)
        if count >= target:
            break
    result = " ".join(selected).strip()
    return result or source


def _body(article: ArticleRecord) -> Body:
    source = article.body.strip() or article.brief.strip() or article.title.strip() or "No text available."
    return Body(
        short=_extract(source, 35) or source,
        medium=_extract(source, 60) or source,
        long=_extract(source, 90) or source,
    )


def _tracked_url(reader_id: str, article: ArticleRecord) -> str:
    base = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    quoted = urllib.parse.quote(article.url)
    return f"{base}/r/{article.id}?reader_id={reader_id}&to={quoted}"


def _make_art(article: ArticleRecord, profile: Profile, slot: str, why: str) -> Art:
    return Art(
        id=article.id,
        headline=_trim_headline(article.title),
        deck=article.brief.strip(),
        body=_body(article),
        source=article.source,
        url=article.url,
        tracked_url=_tracked_url(profile.reader_id, article),
        image=article.image_url,
        topic=article.topic,
        slot=slot,
        why=why,
        outside_bubble=False,
        importance=article.importance,
        cluster_id=article.cluster_id,
        published_at=article.published_at,
        qr_svg=None,
    )


def _top_topics(profile: Profile, articles: list[ArticleRecord]) -> list[str]:
    if profile.topic_weights:
        ranked = sorted(profile.topic_weights.items(), key=lambda item: (-item[1], item[0]))
        return [topic for topic, _ in ranked[:2]]
    counts: dict[str, int] = {}
    for article in articles:
        counts[article.topic] = counts.get(article.topic, 0) + 1
    ranked_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return [topic for topic, _ in ranked_counts[:2]]


def _editors_note(profile: Profile, articles: list[ArticleRecord]) -> str:
    topics = _top_topics(profile, articles)
    if len(topics) >= 2:
        return f"Today's edition leads with {topics[0]} and {topics[1]}, chosen from your reading signals."
    if len(topics) == 1:
        return f"Today's edition focuses on {topics[0]}, chosen from your reading signals."
    return "Today's edition is a balanced selection from the available stories."


def _sections(remaining: list[ArticleRecord], profile: Profile, reading_minutes: int) -> list[Section]:
    if not remaining:
        return []
    grouped: dict[str, list[ArticleRecord]] = {}
    for article in remaining:
        grouped.setdefault(article.topic, []).append(article)
    section_count = 2 if reading_minutes <= 5 else 3 if reading_minutes <= 15 else 5
    topics = sorted(grouped.keys(), key=lambda topic: (-_topic_weight(profile, topic), topic))[:section_count]
    sections: list[Section] = []
    for topic in topics:
        items: list[Art] = []
        for index, article in enumerate(grouped[topic][:4]):
            slot = "feature" if index == 0 else "standard"
            items.append(_make_art(article, profile, slot, f"Because you follow {topic}"))
        sections.append(Section(name=topic.replace("_", " ").title(), items=items))
    return sections


def _mark_outside(edition: Edition, profile: Profile, score_by_id: dict[str, float]) -> None:
    arts: list[Art] = [edition.front.lead] + edition.front.secondary + edition.front.briefs
    for section in edition.sections:
        arts.extend(section.items)
    candidates = [art for art in arts if _topic_weight(profile, art.topic) < 0.3]
    if not candidates:
        candidates = arts
    if not candidates:
        return
    best = max(candidates, key=lambda art: score_by_id.get(art.id, 0.0))
    best.outside_bubble = True
    best.why = "Outside your usual reading"


def build_edition(
    profile: Profile,
    articles: list[ArticleRecord],
    for_date: dt.date,
    issue_no: int,
) -> Edition:
    if not articles:
        raise ValueError("no articles")
    deduped = _dedupe(list(articles))
    if not deduped:
        raise ValueError("no articles")
    total = len(deduped)
    scored: list[tuple[float, int, ArticleRecord]] = []
    for index, article in enumerate(deduped):
        scored.append((_score(article, index, total, profile, for_date), index, article))
    scored.sort(key=lambda item: (-item[0], item[1]))
    ordered = [article for _, _, article in scored]
    score_by_id = {article.id: score for score, _, article in scored}

    lead_article = ordered[0]
    secondary_articles = ordered[1:5]
    brief_articles = ordered[5:8]
    remaining_articles = ordered[8:]

    lead = _make_art(lead_article, profile, "lead", "Top story of the day")
    secondary = [
        _make_art(article, profile, "secondary", f"Because you follow {article.topic}")
        for article in secondary_articles
    ]
    briefs = [
        _make_art(article, profile, "brief", f"Because you follow {article.topic}")
        for article in brief_articles
    ]

    edition = Edition(
        date=for_date,
        issue_no=issue_no,
        reader_id=profile.reader_id,
        reader_name=profile.display_name or profile.reader_id,
        tagline=f"Printed for {profile.display_name}",
        editors_note=_editors_note(profile, deduped),
        front=Front(lead=lead, secondary=secondary, briefs=briefs),
        sections=_sections(remaining_articles, profile, profile.reading_minutes),
        meta={"fallback": True},
    )
    _mark_outside(edition, profile, score_by_id)
    return edition
