from __future__ import annotations

import re
from typing import Any, List

from ..core.store import get_store
from ..models.schemas import Profile

KEYWORDS = {
    "world": ["world", "global", "international", "geopolitics"],
    "pakistan": ["pakistan", "karachi", "lahore", "islamabad", "punjab", "sindh"],
    "politics": ["politics", "election", "parliament", "government", "policy"],
    "business": ["business", "company", "industry", "economy"],
    "markets": ["markets", "stocks", "finance", "trading", "index"],
    "technology": ["technology", "tech", "software", "gadget", "internet"],
    "ai": ["ai", "artificial intelligence", "machine learning", "llm", "neural"],
    "science": ["science", "research", "study", "discovery"],
    "space": ["space", "nasa", "rocket", "satellite", "astronomy"],
    "health": ["health", "medicine", "hospital", "disease", "vaccine"],
    "sport": ["sport", "sports", "athlete", "olympics"],
    "cricket": ["cricket", "batting", "bowling", "wicket"],
    "football": ["football", "soccer", "goal", "premier league"],
    "culture": ["culture", "art", "books", "theatre"],
    "film_music": ["film", "movie", "music", "cinema", "album"],
    "education": ["education", "school", "university", "students"],
    "climate": ["climate", "environment", "emissions", "sustainability"],
    "startups": ["startups", "founders", "vc", "venture", "entrepreneur"],
    "opinion": ["opinion", "analysis", "column", "editorial"],
}


def _has_word(text: str, word: str) -> bool:
    # Word-boundary match so "ai" doesn't fire on "email" or "maintain".
    return re.search(r"\b" + re.escape(word) + r"\b", text) is not None


def _keywords_to_topics(text: str) -> List[str]:
    t = text.lower()
    return [
        topic for topic, words in KEYWORDS.items()
        if any(_has_word(t, w) for w in words)
    ]


def create_profile(req: Any) -> Profile:
    interests = list(getattr(req, "interests", []) or [])
    location = getattr(req, "location", "") or ""
    text = " ".join(interests) + " " + location
    found = _keywords_to_topics(text)

    topics: List[str] = []
    for t in list(interests) + found:
        if t in KEYWORDS and t not in topics:
            topics.append(t)
    if not topics:
        topics = ["world", "pakistan", "technology", "business", "sport"]
    topics = topics[:10]

    weights = {t: 1.0 for t in topics}
    return Profile(
        reader_id=getattr(req, "reader_id"),
        name=getattr(req, "name", "") or getattr(req, "reader_id"),
        topics=topics,
        weights=weights,
        location=location,
        tone=getattr(req, "tone", "neutral") or "neutral",
        outside_bubble_ratio=0.15,
    )


def persist_profile(profile: Profile) -> None:
    get_store().put(f"profiles/{profile.reader_id}", profile.model_dump())
