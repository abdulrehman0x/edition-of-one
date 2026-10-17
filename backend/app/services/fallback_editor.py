from __future__ import annotations

import re
from typing import Dict, List

from ..models.schemas import ArticleRecord, Body, Edition, Front, Profile, Section

STOPWORDS = set(
    '''a an the and or but if while of to in on for with by at from as is are was
    were be been being has have had do does did this that these those it its i you
    we they he she them us our your their my me'''.split()
)


def _tokens(text: str) -> set:
    return {
        w.lower()
        for w in re.findall(r"[A-Za-z0-9']+", text or "")
        if w.lower() not in STOPWORDS
    }


def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def dedupe(articles: List[ArticleRecord], threshold: float = 0.6) -> List[ArticleRecord]:
    kept: List[ArticleRecord] = []
    kept_tokens: List[set] = []
    for art in articles:
        toks = _tokens(art.title)
        if any(jaccard(toks, t) > threshold for t in kept_tokens):
            continue
        kept.append(art)
        kept_tokens.append(toks)
    return kept


def score(article: ArticleRecord, profile: Profile, freshness: float = 1.0) -> float:
    topic_w = 0.5
    if profile.weights:
        topic_w = max((profile.weights.get(t, 0.0) for t in article.topics), default=0.5)
    imp = article.importance
    loc = 1.0
    if profile.location:
        hay = (article.title + " " + article.body.short).lower()
        if profile.location.lower() in hay:
            loc = 1.1
    return (0.5 * topic_w + 0.3 * imp + 0.2 * freshness) * loc


def extract_summary(text: str, max_words: int) -> str:
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    out: List[str] = []
    count = 0
    for s in parts:
        words = s.split()
        if count + len(words) > max_words and out:
            break
        out.append(s)
        count += len(words)
        if count >= max_words:
            break
    return " ".join(out).strip()


def build_body(raw_text: str) -> Body:
    return Body(
        short=extract_summary(raw_text, 35),
        medium=extract_summary(raw_text, 60),
        long=extract_summary(raw_text, 90),
    )


def build_edition(
    reader_id: str,
    date: str,
    articles: List[ArticleRecord],
    profile: Profile,
) -> Edition:
    items = dedupe(articles, threshold=0.6)

    for a in items:
        if not a.body.long and a.body.medium:
            a.body.long = extract_summary(a.body.medium, 90)
        if not a.body.medium and a.body.short:
            a.body.medium = extract_summary(a.body.short, 60)
        if not a.body.short and a.title:
            a.body.short = a.title

    items.sort(key=lambda a: score(a, profile), reverse=True)

    in_bubble = [a for a in items if any(t in profile.topics for t in a.topics)]
    outside = [a for a in items if not any(t in profile.topics for t in a.topics)]

    lead = in_bubble[0] if in_bubble else (items[0] if items else None)
    # Every story appears exactly once: lead, secondary, briefs, sections.
    rest = [a for a in in_bubble if lead is None or a.id != lead.id]
    secondary = rest[:3]
    briefs = rest[3:7]
    remaining = rest[7:]

    outside_ratio = max(0.0, min(0.5, profile.outside_bubble_ratio))
    n_outside = int(round(len(items) * outside_ratio))
    if outside_ratio > 0 and n_outside == 0 and outside:
        n_outside = 1
    outside_pick = [a for a in outside if lead is None or a.id != lead.id][:n_outside]

    front = Front(
        lead=lead,
        secondary=secondary,
        briefs=briefs,
        weather=None,
        quote=(lead.title if lead else "The world, edited for one."),
    )

    by_topic: Dict[str, List[ArticleRecord]] = {}
    for a in remaining:
        t = next(
            (t for t in a.topics if t in profile.topics),
            a.topics[0] if a.topics else "world",
        )
        by_topic.setdefault(t, []).append(a)

    sections: List[Section] = []
    for t, arts in list(by_topic.items())[:6]:
        sections.append(
            Section(name=t.replace("_", " ").title(), slug=t, articles=arts[:6])
        )

    return Edition(
        id=f"ed-{reader_id}-{date}",
        reader_id=reader_id,
        date=date,
        front=front,
        sections=sections,
        outside_bubble=outside_pick,
    )
