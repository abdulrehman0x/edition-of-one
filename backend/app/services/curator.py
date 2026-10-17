from __future__ import annotations

import asyncio
import json
from typing import List, Optional

from ..core.config import get_settings
from ..core.store import get_store
from ..models.schemas import (
    ArticleRecord,
    Edition,
    Profile,
    Weather,
)
from .fallback_editor import build_edition
from .widgets import weather_for


async def _gather_articles() -> List[ArticleRecord]:
    store = get_store()
    out: List[ArticleRecord] = []
    for k in store.list("articles/"):
        data = store.get(k)
        if not data:
            continue
        try:
            out.append(ArticleRecord(**data))
        except Exception:
            continue
    return out


def _load_fallback() -> List[ArticleRecord]:
    s = get_settings()
    try:
        with open(s.fallback_articles_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [ArticleRecord(**a) for a in raw]
    except Exception:
        return []


async def build_edition_async(reader_id: str, date_str: str) -> Optional[Edition]:
    store = get_store()
    profile_data = store.get(f"profiles/{reader_id}")
    if not profile_data:
        return None
    try:
        profile = Profile(**profile_data)
    except Exception:
        return None

    articles = await _gather_articles()
    if not articles:
        articles = _load_fallback()
    if not articles:
        return None

    s = get_settings()
    city = profile.location or s.demo_city
    weather = await asyncio.to_thread(weather_for, city)

    try:
        edition = await asyncio.wait_for(
            asyncio.to_thread(build_edition, reader_id, date_str, articles, profile),
            timeout=20.0,
        )
    except Exception:
        edition = build_edition(reader_id, date_str, articles, profile)

    edition.front.weather = Weather(**weather) if weather else None
    edition.dateline = f"{city} \u2014 {date_str}"
    return edition


async def curate(reader_id: str, date_str: str) -> Optional[Edition]:
    return await build_edition_async(reader_id, date_str)
