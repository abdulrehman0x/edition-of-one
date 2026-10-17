from __future__ import annotations

from typing import Any, Dict, List

from ..core.config import get_settings
from ..core.store import get_store
from ..models.schemas import ArticleRecord, Edition, Profile, Weather
from .back_page import build_back_page
from .broadcast import build_broadcast
from .press_gallery import build_gallery
from .widgets import weather_for


def edition_articles(edition: Edition) -> List[ArticleRecord]:
    arts: List[ArticleRecord] = []
    if edition.front.lead:
        arts.append(edition.front.lead)
    arts.extend(edition.front.secondary)
    arts.extend(edition.front.briefs)
    for sec in edition.sections:
        arts.extend(sec.articles)
    arts.extend(edition.outside_bubble)
    seen, out = set(), []
    for a in arts:
        if a.id not in seen:
            seen.add(a.id)
            out.append(a)
    return out


def enrich_edition(edition: Edition, with_audio: bool = False) -> Edition:
    # Fills the fields the frontend actually reads: press_gallery, back_page
    # and broadcast. Every step is best-effort; a failure leaves it unset.
    arts = edition_articles(edition)
    try:
        edition.press_gallery = build_gallery(arts)
    except Exception:
        pass
    try:
        seed = sum(ord(c) for c in edition.date)
        edition.back_page = build_back_page(arts, seed=seed)
    except Exception:
        pass
    try:
        edition.broadcast = build_broadcast(edition, with_audio=with_audio)
    except Exception:
        pass
    return edition


def finish_edition(
    edition: Edition,
    profile: Profile,
    with_widgets: bool = True,
    with_audio: bool = False,
) -> Edition:
    city = profile.location or get_settings().demo_city
    if with_widgets:
        try:
            edition.front.weather = Weather(**weather_for(city))
        except Exception:
            pass
    edition.dateline = f"{city} \u2014 {edition.date}"
    return enrich_edition(edition, with_audio=with_audio)


def enrich_stored(reader_id: str, date_str: str, with_audio: bool = True) -> Dict[str, Any]:
    store = get_store()
    key = f"editions/{reader_id}/{date_str}"
    payload = store.get(key)
    if not payload:
        return {"ok": False, "reason": "no edition"}
    try:
        edition = Edition(**payload)
    except Exception:
        return {"ok": False, "reason": "bad edition"}
    edition = enrich_edition(edition, with_audio=with_audio)
    store.put(key, edition.model_dump())
    mode = (edition.broadcast or {}).get("mode", "unavailable")
    return {"ok": True, "broadcast_mode": mode}
