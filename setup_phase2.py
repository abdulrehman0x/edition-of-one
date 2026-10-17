#!/usr/bin/env python3
"""setup_phase2.py - Edition of One: Phase 2 generator.

Adds the learning loop (events -> weights -> tomorrow's edition), the
reader simulation, the Next.js frontend, and the audio / press-gallery /
back-page extras. Run it AFTER setup_phase1.py:

    python setup_phase2.py            (keeps files that already exist)
    python setup_phase2.py --force    (overwrites them)

A handful of Phase 1 files are always upgraded in place (marked "upd"):
the API routers, the schemas, the curator, the Makefile, requirements.txt.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORCE = "--force" in sys.argv


def D(s: str) -> str:
    return textwrap.dedent(s)


def write(rel: str, content: str, upgrade: bool = False) -> None:
    p = ROOT / rel
    if p.exists() and not (FORCE or upgrade):
        print(f"  keep  {rel} (exists; use --force to overwrite)")
        return
    verb = "upd  " if p.exists() else "wrote"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.lstrip("\n"), encoding="utf-8")
    print(f"  {verb} {rel}")


def patch(rel: str, old: str, new: str) -> None:
    """Idempotent in-place edit of a Phase 1 file."""
    p = ROOT / rel
    if not p.exists():
        print(f"  WARN  {rel} missing - run setup_phase1.py first")
        return
    s = p.read_text(encoding="utf-8")
    if new in s:
        print(f"  ok    {rel} (already patched)")
        return
    if old not in s:
        print(f"  WARN  {rel}: expected text not found, patch skipped")
        return
    p.write_text(s.replace(old, new, 1), encoding="utf-8")
    print(f"  patch {rel}")


def append_lines(rel: str, lines: list) -> None:
    p = ROOT / rel
    if not p.exists():
        print(f"  WARN  {rel} missing - run setup_phase1.py first")
        return
    s = p.read_text(encoding="utf-8")
    have = {ln.strip() for ln in s.splitlines()}
    todo = [ln for ln in lines if ln.strip() not in have]
    if not todo:
        print(f"  ok    {rel} (nothing to add)")
        return
    if not s.endswith("\n"):
        s += "\n"
    p.write_text(s + "\n".join(todo) + "\n", encoding="utf-8")
    print(f"  patch {rel} (+{len(todo)} lines)")


print("Phase 2: generating files...")
if not (ROOT / "backend/app/models/schemas.py").exists():
    print("  backend/app/models/schemas.py not found - run setup_phase1.py first.")
    raise SystemExit(1)

# ----------------------------------------------------------------------
# Phase 1 files patched in place
# ----------------------------------------------------------------------

# Edition / Profile gain the fields the learning loop and extras write.
patch(
    "backend/app/models/schemas.py",
    "from typing import Literal, Optional, List, Dict\n",
    "from typing import Any, Literal, Optional, List, Dict\n",
)
patch(
    "backend/app/models/schemas.py",
    "    outside_bubble: List[ArticleRecord] = Field(default_factory=list)\n",
    "    outside_bubble: List[ArticleRecord] = Field(default_factory=list)\n"
    "    weight_snapshot: Dict[str, float] = Field(default_factory=dict)\n"
    "    why_text: str = \"\"\n"
    "    broadcast: Optional[Dict[str, Any]] = None\n",
)
patch(
    "backend/app/models/schemas.py",
    "    outside_bubble_ratio: float = 0.15\n",
    "    outside_bubble_ratio: float = 0.15\n"
    "    reading_time_pref: str = \"medium\"\n"
    "    topic_stats: Dict[str, Dict[str, float]] = Field(default_factory=dict)\n"
    "    weight_deltas: Dict[str, float] = Field(default_factory=dict)\n",
)

# New editions get gallery / back page / broadcast script as they are built.
patch(
    "backend/app/services/curator.py",
    "from .widgets import weather_for\n",
    "from .extras import enrich_edition\nfrom .widgets import weather_for\n",
)
patch(
    "backend/app/services/curator.py",
    "    return edition\n\n\nasync def curate",
    "    return enrich_edition(edition)\n\n\nasync def curate",
)

append_lines("backend/requirements.txt", [
    "mutagen",
    "# optional: matplotlib  (chart written by pipelines/simulate_readers.py)",
])
append_lines(".gitignore", ["data/cache/audio/", "frontend/.next/"])
patch(
    "Makefile",
    ".PHONY: setup snapshot seed verify api test demo pdf pdfcheck",
    ".PHONY: setup snapshot seed verify api test demo pdf pdfcheck learn simulate extras web-install web",
)
append_lines("Makefile", [
    "",
    "learn:",
    "\t$(PYTHON) pipelines/learn.py",
    "",
    "simulate:",
    "\t$(PYTHON) pipelines/simulate_readers.py",
    "",
    "extras:",
    "\t$(PYTHON) pipelines/build_extras.py",
    "",
    "web-install:",
    "\tcd frontend && npm install",
    "",
    "web:",
    "\tcd frontend && npm run dev",
])
append_lines("docs/CONTRACT.md", [
    "",
    "## Phase 2 additions",
    "",
    "- `Edition` gains `weight_snapshot`, `why_text`, `broadcast`.",
    "- `Profile` gains `reading_time_pref`, `topic_stats`, `weight_deltas`.",
    "- `POST /profile/{reader_id}/advance` — learn from events, build tomorrow's edition.",
    "- `GET  /profile/{reader_id}/history` — weight snapshots.",
    "- `DELETE /profile/{reader_id}/topics/{topic}` — drop a topic.",
    "- `POST /edition/{reader_id}/enrich?date=&audio=` — rebuild gallery/back page/broadcast.",
    "- `GET  /audio/{reader_id}/{date}` — broadcast MP3 (only when audio was generated).",
    "- Events are stored with a millisecond `ts`; learning state lives under `learning/<reader>/`.",
])

# ----------------------------------------------------------------------
# Backend: services, API, prompts
# ----------------------------------------------------------------------
write(
    "backend/app/api/main.py",
    D(
        r"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from . import archive, audio, dev, edition, events, onboarding, profile

app = FastAPI(title="Edition of One", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    from ..core.store import get_store
    get_store()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
app.include_router(edition.router, prefix="/edition", tags=["edition"])
app.include_router(archive.router, prefix="/archive", tags=["archive"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
app.include_router(audio.router, prefix="/audio", tags=["audio"])
# /dev/reset wipes the store; keep it off outside local development.
if get_settings().enable_dev:
    app.include_router(dev.router, prefix="/dev", tags=["dev"])
"""
    ), upgrade=True,
)
write(
    "backend/app/api/profile.py",
    D(
        r"""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..core.store import get_store
from ..models.schemas import Profile
from ..services.learning import LearningEngine

router = APIRouter()


@router.get("/{reader_id}")
async def get_profile(reader_id: str):
    p = get_store().get(f"profiles/{reader_id}")
    if p is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p


@router.post("/{reader_id}/advance")
async def advance(reader_id: str):
    # Demo hook for "a night passes": learn from events, build tomorrow's edition.
    store = get_store()
    if store.get(f"profiles/{reader_id}") is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await asyncio.to_thread(LearningEngine(store).advance, reader_id)


@router.get("/{reader_id}/history")
async def history(reader_id: str):
    return LearningEngine(get_store()).weight_history(reader_id)


@router.delete("/{reader_id}/topics/{topic}")
async def remove_topic(reader_id: str, topic: str):
    store = get_store()
    data = store.get(f"profiles/{reader_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = Profile(**data)
    profile.topics = [t for t in profile.topics if t != topic]
    profile.weights = {k: v for k, v in profile.weights.items() if k != topic}
    store.put(f"profiles/{reader_id}", profile.model_dump())
    return profile.model_dump()
"""
    ), upgrade=True,
)
write(
    "backend/app/api/events.py",
    D(
        r"""
from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..core.store import get_store
from ..models.schemas import EventType

router = APIRouter()


class EventIn(BaseModel):
    reader_id: str
    article_id: Optional[str] = None
    event_type: EventType
    value: float = 1.0


@router.post("")
async def record(ev: EventIn):
    ns = time.time_ns()
    payload = ev.model_dump()
    # The learning engine selects events by this millisecond timestamp;
    # without it every event looks like it happened at time 0 and is ignored.
    payload["ts"] = ns // 1_000_000
    get_store().put(f"events/{ev.reader_id}/{ns}_{ev.event_type}", payload)
    return {"ok": True}
"""
    ), upgrade=True,
)
write(
    "backend/app/api/edition.py",
    D(
        r"""
from __future__ import annotations

import asyncio
from datetime import date as _date

from fastapi import APIRouter, HTTPException

from ..services.edition_service import get_or_build_edition
from ..services.extras import enrich_stored

router = APIRouter()


def _day(date: str) -> str:
    return _date.today().isoformat() if date == "today" else date


@router.get("/{reader_id}")
async def get_edition(reader_id: str, date: str = "today"):
    ed = await get_or_build_edition(reader_id, _day(date))
    if ed is None:
        raise HTTPException(status_code=404, detail="No edition available")
    return ed.model_dump() if hasattr(ed, "model_dump") else ed


@router.post("/{reader_id}/enrich")
async def enrich(reader_id: str, date: str = "today", audio: bool = False):
    # Rebuilds the gallery/back page/broadcast for a stored edition;
    # audio=true also synthesises the MP3 (needs network and edge-tts).
    d = _day(date)
    await get_or_build_edition(reader_id, d)
    res = await asyncio.to_thread(enrich_stored, reader_id, d, audio)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("reason", "failed"))
    return res
"""
    ), upgrade=True,
)
write(
    "backend/app/api/onboarding.py",
    D(
        r"""
from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.store import get_store
from ..services.profile_service import create_profile

router = APIRouter()


class OnboardingRequest(BaseModel):
    reader_id: str
    name: str = ""
    interests: List[str] = Field(default_factory=list)
    loves: List[str] = Field(default_factory=list)
    reading_time: str = "medium"
    location: str = ""
    tone: str = "neutral"


@router.post("")
async def onboard(req: OnboardingRequest):
    profile = create_profile(req)
    # "Loved" topics start at full weight, merely "liked" ones a little lower,
    # so the first edition already reflects the strength of the choice.
    base = 0.7 if req.loves else 1.0
    for t in profile.topics:
        profile.weights[t] = 1.0 if t in req.loves else base
    if req.reading_time in ("short", "medium", "long"):
        profile.reading_time_pref = req.reading_time
    get_store().put(f"profiles/{profile.reader_id}", profile.model_dump())
    return profile.model_dump()
"""
    ), upgrade=True,
)
write(
    "backend/app/services/learning.py",
    D(
        r"""
from __future__ import annotations

import json
import time
from datetime import date, timedelta
from functools import lru_cache
from typing import Any, Dict, List, Optional

from ..core.config import get_settings
from ..core.store import get_store
from ..models.schemas import ArticleRecord, Profile
from .extras import finish_edition
from .fallback_editor import build_edition

EVENT_WEIGHTS: Dict[str, float] = {
    "thumb_up": 2.0,
    "save": 2.0,
    "dwell": 1.5,
    "click": 1.0,
    "pdf_open": 0.5,
    "impression": 0.0,
    "skip": -0.3,
    "thumb_down": -2.0,
}

WEIGHT_DECAY = 0.97      # applied once per learning night
STEP = 0.08              # weight change per unit of event weight
NEW_TOPIC_START = 0.5    # weight given to a topic the reader never picked
PROMOTE_AT = 0.65        # learned weight at which a topic joins profile.topics
DROP_BELOW = 0.05        # weight below which a topic leaves profile.topics
MAX_TOPICS = 12


def _normalize(weights: Dict[str, float]) -> Dict[str, float]:
    return {k: max(0.0, min(1.0, float(v))) for k, v in weights.items()}


def _topics_from_weights(current: List[str], weights: Dict[str, float]) -> List[str]:
    # build_edition() decides "in bubble" from profile.topics, not from weights,
    # so learned interest has to be reflected there or it never changes the paper.
    keep = [t for t in current if weights.get(t, 1.0) >= DROP_BELOW]
    for t, w in sorted(weights.items(), key=lambda kv: kv[1], reverse=True):
        if w >= PROMOTE_AT and t not in keep:
            keep.append(t)
    return keep[:MAX_TOPICS]


@lru_cache(maxsize=4)
def _fallback_by_id(path: str) -> Dict[str, dict]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return {a["id"]: a for a in json.load(fh)}
    except Exception:
        return {}


def _fallback_articles() -> List[ArticleRecord]:
    out: List[ArticleRecord] = []
    for a in _fallback_by_id(get_settings().fallback_articles_path).values():
        try:
            out.append(ArticleRecord(**a))
        except Exception:
            continue
    return out


class LearningEngine:
    def __init__(self, store: Optional[Any] = None) -> None:
        self.store = store or get_store()

    # Learning state lives under learning/<reader>/..., NOT under profiles/,
    # so listing profiles/ only ever returns real profiles.
    @staticmethod
    def _k(reader_id: str, name: str) -> str:
        return f"learning/{reader_id}/{name}"

    # ------------------------------------------------------------------
    def _collect_events(self, reader_id: str, since_ms: int) -> List[dict]:
        events: List[dict] = []
        for k in self.store.list(f"events/{reader_id}/"):
            data = self.store.get(k)
            if not data:
                continue
            try:
                ts = int(data.get("ts") or 0)
            except (TypeError, ValueError):
                ts = 0
            if ts > since_ms:
                events.append(data)
        events.sort(key=lambda d: int(d.get("ts") or 0))
        return events

    def _article(self, article_id: str) -> Optional[dict]:
        art = self.store.get(f"articles/{article_id}")
        if art:
            return art
        return _fallback_by_id(get_settings().fallback_articles_path).get(article_id)

    def _article_topics(self, article_id: str) -> List[str]:
        art = self._article(article_id)
        return list(art.get("topics", [])) if art else []

    def _update_centroid(self, reader_id: str, article_id: str, direction: float) -> None:
        # Running mean of liked (and, negatively, disliked) article embeddings.
        # Stored for later ranking work; the Phase 2 editor does not read it yet.
        try:
            from ..core.embeddings import embed_one
        except Exception:
            return
        art = self._article(article_id)
        if not art:
            return
        text = (art.get("title", "") or "") + " " + ((art.get("body") or {}).get("short", "") or "")
        if not text.strip():
            return
        try:
            emb = embed_one(text)
        except Exception:
            return
        if not emb:
            return
        key = self._k(reader_id, "centroid")
        current = self.store.get(key) or {}
        vec = current.get("vec") or [0.0] * len(emb)
        n = float(current.get("n", 0.0))
        if len(vec) != len(emb):
            vec, n = [0.0] * len(emb), 0.0
        new_n = n + abs(direction)
        new_vec = [(v * n + e * direction) / new_n for v, e in zip(vec, emb)]
        self.store.put(key, {"vec": new_vec, "n": new_n})

    @staticmethod
    def _infer_reading_time(events: List[dict], current: str) -> str:
        dwells = [float(e.get("value") or 0.0) for e in events if e.get("event_type") == "dwell"]
        if not dwells:
            return current or "medium"
        avg = sum(dwells) / len(dwells)
        if avg >= 60.0:
            return "long"
        if avg >= 25.0:
            return "medium"
        return "short"

    # ------------------------------------------------------------------
    def process_events(self, reader_id: str, events: List[dict]) -> Dict[str, Dict[str, float]]:
        data = self.store.get(f"profiles/{reader_id}")
        if not data:
            return {"weights": {}, "deltas": {}}
        profile = Profile(**data)

        weights = {k: float(v) * WEIGHT_DECAY for k, v in profile.weights.items()}
        stats = {t: dict(s) for t, s in profile.topic_stats.items()}
        deltas: Dict[str, float] = {}

        for ev in events:
            et = ev.get("event_type", "")
            ew = EVENT_WEIGHTS.get(et, 0.0)
            aid = ev.get("article_id")
            if ew == 0.0 or not aid:
                continue
            topics = self._article_topics(aid)
            if not topics:
                continue
            for t in topics:
                bump = ew * STEP
                weights[t] = weights.get(t, NEW_TOPIC_START) + bump
                deltas[t] = deltas.get(t, 0.0) + bump
                st = stats.setdefault(t, {"alpha": 1.0, "beta": 1.0})
                side = "alpha" if ew > 0 else "beta"
                st[side] = float(st.get(side, 1.0)) + abs(ew) * 0.25
            if et in ("thumb_up", "save", "click"):
                self._update_centroid(reader_id, aid, 1.0)
            elif et in ("thumb_down", "skip"):
                self._update_centroid(reader_id, aid, -0.5)

        weights = _normalize(weights)
        profile.weights = weights
        profile.topics = _topics_from_weights(list(profile.topics), weights)
        profile.topic_stats = stats
        # Event-driven change only, so the nightly decay doesn't show up as "taste".
        profile.weight_deltas = {t: round(d, 3) for t, d in deltas.items()}
        profile.reading_time_pref = self._infer_reading_time(events, profile.reading_time_pref)
        self.store.put(f"profiles/{reader_id}", profile.model_dump())
        self.store.put(
            self._k(reader_id, f"snapshots/{time.time_ns()}"),
            {
                "weights": weights,
                "topic_stats": stats,
                "reading_time_pref": profile.reading_time_pref,
            },
        )
        return {"weights": weights, "deltas": profile.weight_deltas}

    # ------------------------------------------------------------------
    @staticmethod
    def _delta_explanation(deltas: Dict[str, float]) -> str:
        moves = [(k, v) for k, v in deltas.items() if abs(v) > 0.01]
        if not moves:
            return "No meaningful preference changes tonight."
        moves.sort(key=lambda kv: abs(kv[1]), reverse=True)
        parts = [f"{k.replace('_', ' ')} {v:+.2f}" for k, v in moves[:4]]
        return "You leaned " + ", ".join(parts) + " after tonight's reading."

    def _load_articles(self) -> List[ArticleRecord]:
        articles: List[ArticleRecord] = []
        for k in self.store.list("articles/"):
            d = self.store.get(k)
            if not d:
                continue
            try:
                articles.append(ArticleRecord(**d))
            except Exception:
                continue
        return articles or _fallback_articles()

    def advance(self, reader_id: str, with_widgets: bool = True) -> Dict[str, Any]:
        data = self.store.get(f"profiles/{reader_id}")
        if not data:
            return {"reader_id": reader_id, "error": "no profile"}

        last_key = self._k(reader_id, "last")
        since_ms = int((self.store.get(last_key) or {}).get("ts", 0))
        events = self._collect_events(reader_id, since_ms)

        deltas: Dict[str, float] = {}
        if events:
            deltas = self.process_events(reader_id, events)["deltas"]
            # Advance the cursor to the newest event we consumed (not "now"),
            # so an event that lands mid-run is picked up next time.
            self.store.put(last_key, {"ts": max(int(e.get("ts") or 0) for e in events)})

        profile = Profile(**self.store.get(f"profiles/{reader_id}"))
        explanation = self._delta_explanation(deltas)
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        articles = self._load_articles()
        if articles:
            edition = build_edition(reader_id, tomorrow, articles, profile)
            edition = finish_edition(edition, profile, with_widgets=with_widgets)
            edition.weight_snapshot = dict(profile.weights)
            edition.why_text = explanation
            self.store.put(f"editions/{reader_id}/{tomorrow}", edition.model_dump())

        return {
            "reader_id": reader_id,
            "date": tomorrow,
            "events_processed": len(events),
            "deltas": deltas,
            "explanation": explanation,
        }

    def weight_history(self, reader_id: str) -> List[dict]:
        out: List[dict] = []
        for k in self.store.list(self._k(reader_id, "snapshots/")):
            d = self.store.get(k) or {}
            out.append({"key": k, "weights": d.get("weights", {})})
        return out
"""
    ),
)
write(
    "backend/app/services/extras.py",
    D(
        r"""
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
"""
    ),
)
write(
    "backend/app/services/broadcast.py",
    D(
        r"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..core.config import get_settings
from ..models.schemas import Edition

WORDS_PER_SECOND = 2.6   # used to estimate the timeline when there is no audio


def audio_file(reader_id: str, date_str: str) -> Path:
    # Ids come from URLs, so keep them to a safe character set.
    safe_reader = re.sub(r"[^A-Za-z0-9_-]", "_", reader_id)
    safe_date = re.sub(r"[^0-9-]", "_", date_str)
    return Path(get_settings().cache_dir) / "audio" / safe_reader / f"{safe_date}.mp3"


def _script_from_edition(edition: Edition) -> Dict[str, Any]:
    lead = edition.front.lead
    if lead:
        intro = f"Good morning. It's {edition.date}. We lead with: {lead.title}."
    else:
        intro = f"Good morning. It's {edition.date}, and this is your edition of one."
    chapters: List[Dict[str, str]] = []
    if lead:
        chapters.append({"title": lead.title, "script": lead.body.medium or lead.body.short})
    for a in edition.front.secondary:
        chapters.append({"title": a.title, "script": a.body.short})
    for sec in edition.sections:
        for a in sec.articles[:1]:
            chapters.append({"title": a.title, "script": a.body.short})
    outro = "That's your morning. Have a thoughtful day."
    return {"intro": intro, "chapters": chapters, "outro": outro}


def _estimate(text: str) -> float:
    return len((text or "").split()) / WORDS_PER_SECOND


def _try_edge_tts(text: str, out_path: Path) -> bool:
    try:
        import asyncio
        import edge_tts  # type: ignore
    except Exception:
        return False
    try:
        async def _run() -> None:
            await edge_tts.Communicate(text, voice="en-GB-RyanNeural").save(str(out_path))

        asyncio.run(_run())
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def _duration(path: Path, fallback: float) -> float:
    try:
        from mutagen.mp3 import MP3  # type: ignore
        return float(MP3(str(path)).info.length)
    except Exception:
        return fallback


def build_broadcast(edition: Edition, with_audio: bool = False) -> Dict[str, Any]:
    script = _script_from_edition(edition)
    texts = [script["intro"]] + [c["script"] for c in script["chapters"]] + [script["outro"]]
    estimates = [_estimate(t) for t in texts]

    def timeline(durations: List[float]) -> List[Dict[str, Any]]:
        t = durations[0]  # chapters start after the intro
        out = []
        for c, d in zip(script["chapters"], durations[1:-1]):
            out.append({"title": c["title"], "start": round(t, 1), "duration": round(d, 1)})
            t += d
        return out

    result: Dict[str, Any] = {
        "mode": "script-only",
        "audio_url": None,
        "script": script,
        "chapters": timeline(estimates),
        "duration": round(sum(estimates), 1),
    }

    # edge-tts needs the network, so it is skipped when running offline.
    if not with_audio or get_settings().llm_offline == 1:
        return result

    combined = audio_file(edition.reader_id, edition.date)
    combined.parent.mkdir(parents=True, exist_ok=True)
    parts: List[Path] = []
    for i, text in enumerate(texts):
        seg = combined.with_name(f"{combined.stem}_{i}.mp3")
        if not _try_edge_tts(text, seg):
            for p in parts:
                p.unlink(missing_ok=True)
            return result
        parts.append(seg)

    # MP3 frames can simply be concatenated; no ffmpeg needed.
    with combined.open("wb") as out:
        for p in parts:
            out.write(p.read_bytes())
    durations = [_duration(p, e) for p, e in zip(parts, estimates)]
    for p in parts:
        p.unlink(missing_ok=True)

    result.update(
        mode="audio",
        audio_url=f"/audio/{edition.reader_id}/{edition.date}",
        chapters=timeline(durations),
        duration=round(sum(durations), 1),
    )
    return result
"""
    ),
)
write(
    "backend/app/services/press_gallery.py",
    D(
        r"""
from __future__ import annotations

from typing import Dict, List

from ..models.schemas import ArticleRecord, GalleryRow, PressGallery


def _cluster_by_topic(articles: List[ArticleRecord]) -> Dict[str, List[ArticleRecord]]:
    clusters: Dict[str, List[ArticleRecord]] = {}
    for a in articles:
        for t in a.topics:
            clusters.setdefault(t, []).append(a)
    return clusters


def _agreed_facts(cluster: List[ArticleRecord]) -> List[str]:
    seen: Dict[str, int] = {}
    for a in cluster:
        for sent in (a.body.short or "").split(". "):
            sent = sent.strip().rstrip(".")
            if len(sent) >= 20:
                seen[sent] = seen.get(sent, 0) + 1
    agreed = [k for k, v in seen.items() if v >= 2]
    if not agreed and seen:
        agreed = [next(iter(seen))]
    return agreed[:3]


def _framing_differences(cluster: List[ArticleRecord]) -> List[str]:
    return [f"{a.source}: {a.title}" for a in cluster[:3]]


def build_gallery(articles: List[ArticleRecord]) -> PressGallery:
    # Topic clusters stand in for "same story" until real story clustering
    # (embeddings) lands; only clusters with 2+ articles are shown.
    clusters = _cluster_by_topic(articles)
    rows: List[GalleryRow] = []
    ranked = sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]
    for topic, cluster in ranked:
        if len(cluster) < 2:
            continue
        agreed = _agreed_facts(cluster)
        framing = _framing_differences(cluster)
        caption = f"Outlets agree: {agreed[0] if agreed else '…'}. Framings: " + " | ".join(framing)
        rows.append(
            GalleryRow(title=topic.replace("_", " ").title(), url="", caption=caption)
        )
    return PressGallery(rows=rows)
"""
    ),
)
write(
    "backend/app/services/back_page.py",
    D(
        r"""
from __future__ import annotations

import random
from typing import List, Optional

from ..models.schemas import ArticleRecord, BackPage, OnThisDay, QuizQ, WordSearch

# Fixed "from history" items. They are not matched to today's date.
_HISTORICAL = [
    (1947, "Pakistan gains independence."),
    (1969, "Apollo 11 lands the first humans on the Moon."),
    (1989, "The World Wide Web is proposed at CERN."),
    (2008, "The global financial crisis deepens."),
    (2015, "The Paris climate agreement is adopted."),
    (2020, "WHO declares COVID-19 a pandemic."),
]

_DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)]


def make_word_search(words: List[str], size: int = 12, seed: int = 42) -> WordSearch:
    rng = random.Random(seed)
    grid: List[List[str]] = [["" for _ in range(size)] for _ in range(size)]
    placed: List[str] = []

    for raw in words:
        word = raw.upper().replace(" ", "").replace("-", "").replace("_", "")
        if not word or len(word) > size:
            continue
        for _ in range(200):
            dr, dc = rng.choice(_DIRECTIONS)
            r = rng.randint(0, size - 1)
            c = rng.randint(0, size - 1)
            end_r = r + dr * (len(word) - 1)
            end_c = c + dc * (len(word) - 1)
            if not (0 <= end_r < size and 0 <= end_c < size):
                continue
            cells = [(r + dr * i, c + dc * i) for i in range(len(word))]
            if any(grid[rr][cc] and grid[rr][cc] != ch for (rr, cc), ch in zip(cells, word)):
                continue
            for (rr, cc), ch in zip(cells, word):
                grid[rr][cc] = ch
            placed.append(word)
            break

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(size):
        for c in range(size):
            if not grid[r][c]:
                grid[r][c] = rng.choice(letters)

    return WordSearch(grid=["".join(row) for row in grid], words=placed)


def _quiz_from_articles(articles: List[ArticleRecord]) -> List[QuizQ]:
    out: List[QuizQ] = []
    for a in articles[:5]:
        opts = [a.title]
        for b in articles:
            if len(opts) >= 4:
                break
            if b.id != a.id and b.title not in opts:
                opts.append(b.title)
        while len(opts) < 4:
            opts.append(f"None of the above ({len(opts)})")
        random.Random(sum(ord(c) for c in a.id)).shuffle(opts)
        topic = a.topics[0].replace("_", " ") if a.topics else "today's news"
        out.append(
            QuizQ(
                question=f"Which of these headlines ran under {topic}?",
                options=opts,
                answer=opts.index(a.title),
            )
        )
    return out


def build_back_page(
    articles: List[ArticleRecord],
    words: Optional[List[str]] = None,
    seed: int = 42,
) -> BackPage:
    if words is None:
        firsts = [a.topics[0] for a in articles[:12] if a.topics]
        words = list(dict.fromkeys(firsts))[:8]
    return BackPage(
        quiz=_quiz_from_articles(articles),
        word_search=make_word_search(words, seed=seed) if words else None,
        on_this_day=[OnThisDay(year=y, text=t) for y, t in _HISTORICAL[:4]],
    )
"""
    ),
)
write(
    "backend/app/api/audio.py",
    D(
        r"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..services.broadcast import audio_file

router = APIRouter()


@router.get("/{reader_id}/{date}")
async def get_audio(reader_id: str, date: str):
    path = audio_file(reader_id, date)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No audio for this edition")
    return FileResponse(str(path), media_type="audio/mpeg")
"""
    ),
)
write(
    "backend/prompts/broadcast.md",
    D(
        r"""
You are the anchor for "The Morning Broadcast", a 4-minute personalised
news audio segment.

Reader: {{reader_id}}
Date: {{date}}
Top stories: {{titles}}

Write a warm, grounded script. Return JSON ONLY:
{
  "intro": "<= 40 words",
  "chapters": [
    {"title": "story title", "script": "<= 90 words"}
  ],
  "outro": "<= 25 words"
}

No invented facts.
"""
    ),
)
write(
    "backend/prompts/gallery.md",
    D(
        r"""
You are comparing how multiple outlets covered the same story.

Coverage: {{coverage_json}}

Return JSON ONLY:
{
  "agreed_facts": ["..."],
  "framing_differences": ["..."],
  "neutral_questions": ["..."]
}
"""
    ),
)
write(
    "backend/prompts/quiz.md",
    D(
        r"""
Generate 5 multiple-choice news quiz questions grounded in the articles below.

Articles: {{articles_json}}

Return JSON ONLY:
[
  {"question": "...", "options": ["A", "B", "C", "D"], "answer": 0}
]
"""
    ),
)

# ----------------------------------------------------------------------
# Pipelines
# ----------------------------------------------------------------------
write(
    "pipelines/learn.py",
    D(
        r"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.services.learning import LearningEngine  # noqa: E402


def main() -> None:
    store = get_store()
    engine = LearningEngine(store=store)
    readers = sorted({k.split("/")[-1] for k in store.list("profiles/")})
    if not readers:
        print("No profiles found. Run `make seed` first.")
        return

    for rid in readers:
        result = engine.advance(rid)
        if "error" in result:
            print(f"  [skip] {rid}: {result['error']}")
            continue
        pretty = {k: v for k, v in result["deltas"].items() if abs(v) > 0.005}
        print(f"  {rid}: {result['events_processed']} events processed")
        print(f"    edition: {result['date']}")
        if pretty:
            print(f"    deltas: {json.dumps(pretty)}")
        print(f"    why: {result['explanation']}")


if __name__ == "__main__":
    main()
"""
    ),
)
write(
    "pipelines/simulate_readers.py",
    D(
        r"""
from __future__ import annotations

import csv
import random
import sys
import time
from pathlib import Path
from typing import Dict, List

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import get_settings  # noqa: E402
from app.core.store import get_store  # noqa: E402
from app.models.schemas import Profile  # noqa: E402
from app.services.fallback_editor import build_edition  # noqa: E402
from app.services.learning import LearningEngine, _fallback_articles  # noqa: E402

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore

DAYS = 7

# Every simulated reader starts from the same generic guess (a cold start)
# and has hidden "true" interests that they react to. Learning works if the
# front page drifts towards the true topics over the week.
COLD_TOPICS = ["world", "technology", "business", "sport"]

PERSONAS: List[Dict] = [
    {"reader_id": "sim-pakistan", "name": "Sim Pakistan",
     "true_topics": ["pakistan", "politics", "education"]},
    {"reader_id": "sim-business", "name": "Sim Business",
     "true_topics": ["business", "markets", "startups"]},
    {"reader_id": "sim-sport", "name": "Sim Sport",
     "true_topics": ["cricket", "football", "sport"]},
]


def _front_articles(edition: dict) -> List[dict]:
    front = edition.get("front") or {}
    picked: List[dict] = []
    if front.get("lead"):
        picked.append(front["lead"])
    picked.extend(front.get("secondary") or [])
    picked.extend(front.get("briefs") or [])
    return picked


def _match_pct(edition: dict, true_topics: List[str]) -> float:
    picked = _front_articles(edition)
    if not picked:
        return 0.0
    hits = sum(1 for a in picked if any(t in true_topics for t in a.get("topics", [])))
    return round(100.0 * hits / len(picked), 2)


def _reset(store, rid: str) -> None:
    # Re-running must start from scratch, otherwise old events/learning
    # state leak into the new run.
    for prefix in (f"events/{rid}/", f"learning/{rid}/", f"editions/{rid}/"):
        for k in store.list(prefix):
            store.delete(k)
    store.delete(f"profiles/{rid}")


def _read_edition(store, rng: random.Random, rid: str, edition: dict,
                  true_topics: List[str]) -> int:
    last = int((store.get(f"learning/{rid}/last") or {}).get("ts", 0))
    ts = max(last + 1, int(time.time() * 1000))
    arts = _front_articles(edition)
    for sec in edition.get("sections") or []:
        arts.extend(sec.get("articles") or [])

    n = 0
    for a in arts:
        relevant = any(t in true_topics for t in a.get("topics", []))
        if relevant:
            kind = "thumb_up" if rng.random() < 0.8 else "click"
        else:
            kind = "thumb_down" if rng.random() < 0.25 else "skip"
        ts += 1
        store.put(
            f"events/{rid}/{ts}_{kind}_{a['id']}",
            {"reader_id": rid, "article_id": a["id"], "event_type": kind,
             "value": 1.0, "ts": ts},
        )
        n += 1
    return n


def main() -> None:
    store = get_store()
    engine = LearningEngine(store=store)
    articles = _fallback_articles()
    if not articles:
        print(f"No articles at {get_settings().fallback_articles_path}; run setup_phase1.py.")
        return

    out_dir = ROOT / "docs/samples"
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    rows: List[dict] = []
    trend: Dict[str, List[float]] = {}

    for persona in PERSONAS:
        rid = persona["reader_id"]
        _reset(store, rid)
        profile = Profile(
            reader_id=rid,
            name=persona["name"],
            topics=list(COLD_TOPICS),
            weights={t: 0.5 for t in COLD_TOPICS},
            location="Islamabad",
            outside_bubble_ratio=0.15,
        )
        store.put(f"profiles/{rid}", profile.model_dump())
        edition = build_edition(rid, "day-0", articles, profile).model_dump()
        trend[rid] = []

        for day in range(1, DAYS + 1):
            match = _match_pct(edition, persona["true_topics"])
            trend[rid].append(match)
            n_events = _read_edition(store, rng, rid, edition, persona["true_topics"])
            rows.append({"day": day, "reader_id": rid, "reader_name": persona["name"],
                         "match_pct": match, "events": n_events})
            result = engine.advance(rid, with_widgets=False)
            edition = store.get(f"editions/{rid}/{result['date']}") or edition

        print(f"  {rid}: match {trend[rid][0]:.0f}% -> {trend[rid][-1]:.0f}%")

    csv_path = out_dir / "simulation.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=["day", "reader_id", "reader_name", "match_pct", "events"]
        )
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {csv_path}")

    if plt is None:
        print("  matplotlib not installed; skipped simulation.png")
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    for persona in PERSONAS:
        ax.plot(range(1, DAYS + 1), trend[persona["reader_id"]], marker="o", label=persona["name"])
    ax.set_xlabel("Day")
    ax.set_ylabel("Front-page match %")
    ax.set_title("Edition of One - reader match over 7 days")
    ax.legend()
    ax.grid(True, alpha=0.3)
    png_path = out_dir / "simulation.png"
    fig.tight_layout()
    fig.savefig(png_path, dpi=120)
    plt.close(fig)
    print(f"  wrote {png_path}")


if __name__ == "__main__":
    main()
"""
    ),
)
write(
    "pipelines/build_extras.py",
    D(
        r"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.services.extras import enrich_stored  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Add gallery, back page and broadcast to stored editions.")
    ap.add_argument("--audio", action="store_true",
                    help="also synthesise MP3s (needs network, edge-tts, LLM_OFFLINE=0)")
    ap.add_argument("--last", type=int, default=3,
                    help="only the newest N editions per reader (default 3)")
    args = ap.parse_args()

    store = get_store()
    by_reader: dict = {}
    for k in store.list("editions/"):
        parts = k.split("/")
        if len(parts) == 3:  # editions/<reader>/<date>
            by_reader.setdefault(parts[1], []).append(parts[2])

    total = 0
    for reader, dates in sorted(by_reader.items()):
        for d in sorted(dates, reverse=True)[: args.last]:
            res = enrich_stored(reader, d, with_audio=args.audio)
            status = res.get("broadcast_mode") if res.get("ok") else res.get("reason")
            print(f"  {reader} {d}: {status}")
            total += 1
    print(f"Enriched {total} editions.")


if __name__ == "__main__":
    main()
"""
    ),
)

# ----------------------------------------------------------------------
# Tests
# ----------------------------------------------------------------------
write(
    "backend/tests/test_learning.py",
    D(
        r"""
import time

from app.core.store import FileStore
from app.models.schemas import Profile
from app.services.learning import LearningEngine


def _setup(tmp_path):
    store = FileStore(tmp_path)
    for i, (title, topics) in enumerate(
        [("Cricket final tonight", ["cricket", "sport"]), ("Budget debate", ["politics"])]
    ):
        store.put(
            f"articles/a{i}",
            {"id": f"a{i}", "title": title, "topics": topics, "body": {"short": title}},
        )
    profile = Profile(reader_id="r", topics=["politics"], weights={"politics": 0.6})
    store.put("profiles/r", profile.model_dump())
    return store


def _event(store, aid, kind, ts):
    store.put(
        f"events/r/{ts}_{kind}",
        {"reader_id": "r", "article_id": aid, "event_type": kind, "value": 1.0, "ts": ts},
    )


def test_likes_raise_weight_and_promote_topic(tmp_path):
    store = _setup(tmp_path)
    now = int(time.time() * 1000)
    for i in range(3):
        _event(store, "a0", "thumb_up", now + i)
    result = LearningEngine(store=store).advance("r", with_widgets=False)

    assert result["events_processed"] == 3
    assert result["deltas"]["cricket"] > 0.4
    profile = store.get("profiles/r")
    assert profile["weights"]["cricket"] > 0.65
    assert "cricket" in profile["topics"]          # promoted into the bubble
    assert "cricket" in result["explanation"]


def test_events_are_consumed_once(tmp_path):
    store = _setup(tmp_path)
    _event(store, "a0", "thumb_up", int(time.time() * 1000))
    engine = LearningEngine(store=store)
    assert engine.advance("r", with_widgets=False)["events_processed"] == 1
    assert engine.advance("r", with_widgets=False)["events_processed"] == 0


def test_dislikes_lower_weight_and_aux_keys_are_not_profiles(tmp_path):
    store = _setup(tmp_path)
    _event(store, "a1", "thumb_down", int(time.time() * 1000))
    LearningEngine(store=store).advance("r", with_widgets=False)

    assert store.get("profiles/r")["weights"]["politics"] < 0.6
    assert store.list("profiles/") == ["profiles/r"]


def test_advance_without_profile_reports_error(tmp_path):
    assert "error" in LearningEngine(store=FileStore(tmp_path)).advance("ghost")
"""
    ),
)
write(
    "backend/tests/test_back_page.py",
    D(
        r"""
from app.models.schemas import ArticleRecord, Body
from app.services.back_page import build_back_page, make_word_search
from app.services.press_gallery import build_gallery


def _art(i, topics):
    return ArticleRecord(
        id=f"a{i}", title=f"Headline {i}", topics=topics, source=f"Src{i}",
        body=Body(short=f"Short body number {i} with enough words."),
    )


def test_word_search_places_words_inside_grid():
    ws = make_word_search(["pakistan", "cricket", "climate"], size=12, seed=1)
    assert len(ws.grid) == 12 and all(len(r) == 12 for r in ws.grid)
    assert ws.words


def test_quiz_answer_points_at_the_real_headline():
    arts = [_art(i, ["world"]) for i in range(6)]
    bp = build_back_page(arts)
    assert len(bp.quiz) == 5
    for q, a in zip(bp.quiz, arts):
        assert q.options[q.answer] == a.title


def test_back_page_is_deterministic_per_seed():
    arts = [_art(i, ["world", "sport"][i % 2:i % 2 + 1]) for i in range(8)]
    assert build_back_page(arts, seed=3).word_search == build_back_page(arts, seed=3).word_search


def test_gallery_needs_two_articles_per_topic():
    rows = build_gallery([_art(1, ["world"]), _art(2, ["world"]), _art(3, ["sport"])]).rows
    assert [r.title for r in rows] == ["World"]
"""
    ),
)
write(
    "backend/tests/test_broadcast.py",
    D(
        r"""
import os

os.environ["LLM_OFFLINE"] = "1"

from app.models.schemas import ArticleRecord, Body, Edition, Front
from app.services.broadcast import audio_file, build_broadcast


def _edition():
    lead = ArticleRecord(id="a1", title="Lead", body=Body(short="Short lead.", medium="Medium lead text."))
    return Edition(id="e", reader_id="r", date="2026-01-01", front=Front(lead=lead))


def test_offline_broadcast_is_script_only_with_timeline():
    b = build_broadcast(_edition(), with_audio=True)
    assert b["mode"] == "script-only" and b["audio_url"] is None
    assert b["chapters"][0]["title"] == "Lead"
    assert b["chapters"][0]["start"] > 0
    assert b["duration"] > 0


def test_audio_path_is_sanitised():
    p = audio_file("../../etc", "2026-01-01")
    assert ".." not in p.parts
"""
    ),
)

# ----------------------------------------------------------------------
# Frontend (Next.js 14, App Router)
# ----------------------------------------------------------------------
write(
    "frontend/package.json",
    D(
        r"""
{
  "name": "edition-of-one-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "next": "14.2.5",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/node": "^20.11.30",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "typescript": "^5.4.5",
    "eslint": "^8.57.0",
    "eslint-config-next": "14.2.5"
  }
}
"""
    ),
)
write(
    "frontend/next.config.mjs",
    D(
        r"""
/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    unoptimized: true,
  },
};
export default nextConfig;
"""
    ),
)
write(
    "frontend/tsconfig.json",
    D(
        r"""
{
  "compilerOptions": {
    "target": "es2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./*"] }
  },
  "include": [
    "next-env.d.ts",
    "**/*.ts",
    "**/*.tsx",
    ".next/types/**/*.ts"
  ],
  "exclude": ["node_modules"]
}
"""
    ),
)
write(
    "frontend/next-env.d.ts",
    D(
        r"""
/// <reference types="next" />
/// <reference types="next/image-types/global" />

// NOTE: This file should not be edited
"""
    ),
)
write(
    "frontend/README.md",
    D(
        r"""
# Edition of One — Frontend

Next.js 14 App Router web client.

## Quickstart

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

The app expects the API at `http://localhost:8000`. When the API is unreachable,
the client loads `/sample-edition.json` as a fallback and shows an offline banner.

## Structure

- `app/` — routes (onboarding, today, edition/[date], archive, profile)
- `components/` — newspapers UI components
- `components/extras/` — audio, press gallery, back page
- `lib/` — types, api wrappers, reader id, tracker

## Learning loop

Feedback buttons and reading time are sent to `POST /events`. The profile page's
"Advance one night" button calls `POST /profile/{id}/advance`, which re-weights
topics and builds tomorrow's edition (see `backend/app/services/learning.py`).
"""
    ),
)
write(
    "frontend/lib/types.ts",
    D(
        r"""
export type Topic =
 | "world"
 | "pakistan"
 | "politics"
 | "business"
 | "markets"
 | "technology"
 | "ai"
 | "science"
 | "space"
 | "health"
 | "sport"
 | "cricket"
 | "football"
 | "culture"
 | "film_music"
 | "education"
 | "climate"
 | "startups"
 | "opinion";

export type Slot = "lead" | "secondary" | "feature" | "standard" | "brief";

export type EventType =
 | "impression"
 | "click"
 | "skip"
 | "dwell"
 | "thumb_up"
 | "thumb_down"
 | "save"
 | "pdf_open";

export interface Art {
 kind: "image" | "svg" | "none";
 url?: string | null;
 caption?: string | null;
    alt?: string | null;
}

export interface Body {
  short: string;
  medium: string;
  long: string;
}

export interface ArticleRecord {
  id: string;
  title: string;
  url: string;
  source: string;
  source_id: string;
  topics: Topic[];
  published_at?: string | null;
  body: Body;
  art: Art;
  importance: number;
}

export interface Weather {
  city: string;
  temp_c?: number | null;
  condition: string;
  high_c?: number | null;
  low_c?: number | null;
}

export interface Section {
  name: string;
  slug: string;
  articles: ArticleRecord[];
}

export interface QuizQ {
  question: string;
  options: string[];
  answer: number;
}

export interface WordSearch {
 grid: string[];
    words: string[];
}

export interface MarketRow {
  symbol: string;
  price?: number | null;
  change_pct?: number | null;
}

export interface OnThisDay {
  year?: number | null;
  text: string;
}

export interface BackPage {
  quiz: QuizQ[];
  word_search?: WordSearch | null;
  on_this_day: OnThisDay[];
}

export interface GalleryRow {
  title: string;
  url: string;
  caption: string;
}

export interface PressGallery {
  rows: GalleryRow[];
}

export interface Front {
  lead?: ArticleRecord | null;
  secondary: ArticleRecord[];
  briefs: ArticleRecord[];
  weather?: Weather | null;
  quote: string;
}

export interface Chapter {
  title: string;
  articles: ArticleRecord[];
  slot: Slot;
}
export interface Edition {
  id: string;
  reader_id: string;
  date: string;
  nameplate: string;
  dateline: string;
  front: Front;
  sections: Section[];
  back_page: BackPage;
  press_gallery?: PressGallery | null;
  chapters: Chapter[];
  outside_bubble: ArticleRecord[];
  weight_snapshot?: Record<string, number>;
  why_text?: string;
  broadcast?: Broadcast | null;
}

export interface Profile {
  reader_id: string;
  name: string;
  topics: Topic[];
  weights: Record<string, number>;
  location: string;
  tone: string;
  outside_bubble_ratio: number;
  weight_deltas?: Record<string, number>;
  topic_stats?: Record<string, { alpha: number; beta: number }>;
  reading_time_pref?: string;
}

export interface Event {
  reader_id: string;
  article_id?: string | null;
  event_type: EventType;
  value: number;
  ts?: string | null;
}
export interface BroadcastChapter {
  title: string;
  start: number;
  duration: number;
}

export interface Broadcast {
  mode: "audio" | "script-only" | "unavailable";
  audio_url?: string | null;
  duration?: number;
  chapters: BroadcastChapter[];
  script?: {
    intro: string;
    chapters: { title: string; script: string }[];
    outro: string;
  };
}
"""
    ),
)
write(
    "frontend/lib/api.ts",
    D(
        r"""
import type { Edition, Event, Profile } from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

const TIMEOUT_MS = 6000;

async function timedFetch(input: string, init?: RequestInit): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function safeJson<T>(res: Response): Promise<T | null> {
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

let sampleCache: Edition | null = null;

async function loadSample(): Promise<Edition | null> {
  if (sampleCache) return sampleCache;
  try {
    const res = await fetch("/sample-edition.json");
    if (!res.ok) return null;
    const data = (await res.json()) as Edition;
    sampleCache = data;
    return data;
  } catch {
    return null;
  }
}

export interface EditionResult {
  edition: Edition | null;
  offline: boolean;
}

export async function getEdition(
  readerId: string,
  date: string
): Promise<EditionResult> {
  try {
    const res = await timedFetch(
      `${API_BASE}/edition/${encodeURIComponent(readerId)}?date=${encodeURIComponent(date)}`,
      { cache: "no-store" }
    );
    if (!res.ok) throw new Error(`status ${res.status}`);
    const data = await safeJson<Edition>(res);
    if (data) return { edition: data, offline: false };
  } catch {
    /* fall through to the bundled sample */
  }
  const sample = await loadSample();
  return { edition: sample, offline: true };
}

export async function getProfile(readerId: string): Promise<Profile | null> {
  try {
    const res = await timedFetch(
      `${API_BASE}/profile/${encodeURIComponent(readerId)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export async function getArchive(
  readerId: string
): Promise<{ dates: string[] }> {
  try {
    const res = await timedFetch(
      `${API_BASE}/archive/${encodeURIComponent(readerId)}`,
      { cache: "no-store" }
    );
    if (!res.ok) return { dates: [] };
    const data = await safeJson<{ dates: string[] }>(res);
    return data || { dates: [] };
  } catch {
    return { dates: [] };
  }
}

export async function postOnboarding(payload: {
  reader_id: string;
  name: string;
  interests: string[];
  loves?: string[];
  reading_time?: string;
  location: string;
  tone: string;
}): Promise<Profile | null> {
  try {
    const res = await timedFetch(`${API_BASE}/onboarding`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export async function postEvent(ev: Event): Promise<void> {
  try {
    await timedFetch(`${API_BASE}/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ev),
      keepalive: true,
    });
  } catch {
    /* tracking must never break reading */
  }
}

export async function advanceNight(readerId: string): Promise<boolean> {
  try {
    // Learning plus an edition rebuild can take a few seconds.
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 30000);
    try {
      const res = await fetch(
        `${API_BASE}/profile/${encodeURIComponent(readerId)}/advance`,
        { method: "POST", signal: ctrl.signal }
      );
      return res.ok;
    } finally {
      clearTimeout(timer);
    }
  } catch {
    return false;
  }
}

export async function removeTopic(
  readerId: string,
  topic: string
): Promise<Profile | null> {
  try {
    const res = await timedFetch(
      `${API_BASE}/profile/${encodeURIComponent(readerId)}/topics/${encodeURIComponent(topic)}`,
      { method: "DELETE" }
    );
    if (!res.ok) return null;
    return await safeJson<Profile>(res);
  } catch {
    return null;
  }
}

export { API_BASE };
"""
    ),
)
write(
    "frontend/lib/reader.ts",
    D(
        r"""
"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "eoo.reader_id";

function generateId(): string {
  return "reader-" + Math.random().toString(36).slice(2, 10);
}

export function getReaderId(): string {
 if (typeof window === "undefined") return "";
 const existing = window.localStorage.getItem(STORAGE_KEY);
 if (existing) return existing;
    const fresh = generateId();
    window.localStorage.setItem(STORAGE_KEY, fresh);
    return fresh;
}

export function setReaderId(id: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, id);
}

export function clearReaderId(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}

export function useReader(): [string, (id: string) => void] {
  const [id, setId] = useState<string>("");
  useEffect(() => {
    setId(getReaderId());
  }, []);
  const update = useCallback((next: string) => {
    setReaderId(next);
    setId(next);
  }, []);
  return [id, update];
}
"""
    ),
)
write(
    "frontend/lib/tracker.ts",
    D(
        r"""
"use client";

import { useEffect, useRef, type RefObject } from "react";
import { postEvent } from "./api";
import { getReaderId } from "./reader";
import type { Event, EventType } from "./types";

class Tracker {
 private queue: Event[] = [];
 private flushing = false;
 private batchSize = 5;

    track(
      event_type: EventType,
      article_id?: string | null,
      value = 1.0
    ): void {
      const ev: Event = {
        reader_id: getReaderId(),
        article_id: article_id || null,
        event_type,
        value,
      };
      this.queue.push(ev);
      if (this.queue.length >= this.batchSize) {
        void this.flush();
      }
    }

    async flush(): Promise<void> {
      if (this.flushing || this.queue.length === 0) return;
      this.flushing = true;
      const batch = this.queue.splice(0, this.queue.length);
      try {
        for (const ev of batch) {
          await postEvent(ev);
        }
      } catch {
        this.queue.push(...batch);
      } finally {
        this.flushing = false;
      }
    }
}

export const tracker = new Tracker();
if (typeof window !== "undefined") {
  window.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "hidden") {
      void tracker.flush();
    }
  });
  window.addEventListener("beforeunload", () => {
    void tracker.flush();
  });
}

export function useImpression(
  ref: RefObject<HTMLElement>,
  articleId: string
): void {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") return;
    const obs = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            tracker.track("impression", articleId, 1.0);
            obs.disconnect();
            break;
          }
        }
      },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [ref, articleId]);
}

export function useDwell(articleId: string | null, minSeconds = 1.5): void {
 const startRef = useRef<number | null>(null);
 useEffect(() => {
  if (!articleId) return;
  startRef.current = Date.now();
  const id = articleId;
  return () => {
   if (startRef.current === null) return;
   const seconds = (Date.now() - startRef.current) / 1000;
        if (seconds >= minSeconds) {
          tracker.track("dwell", id, Math.min(seconds, 300));
        }
      };
    }, [articleId, minSeconds]);
}
"""
    ),
)
write(
    "frontend/app/globals.css",
    D(
        r"""
:root {
  --paper: #f5efe0;
  --ink: #111111;
  --ink-soft: #444444;
  --ink-faint: #6c6c6c;
  --oxblood: #8b1a1a;
  --rule: #b9a98a;
  --shade: #e9e1cb;
  --serif: var(--font-caslon), "Libre Caslon Text", Georgia, serif;
  --blackletter: var(--font-fraktur), "UnifrakturCook", serif;
  --display: var(--font-playfair), "Playfair Display", serif;
}

*{
  box-sizing: border-box;
}

html,
body {
 margin: 0;
 padding: 0;
 background: var(--paper);
 color: var(--ink);
    font-family: var(--serif);
    line-height: 1.5;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
}

a{
  color: var(--oxblood);
  text-decoration: none;
}

a:hover {
  text-decoration: underline;
}

.topnav {
  display: flex;
  gap: 24px;
  align-items: center;
  padding: 12px 32px;
  border-bottom: 1px solid var(--rule);
  background: var(--paper);
  font-family: var(--serif);
  font-size: 13px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}

.topnav .brand {
  font-family: var(--blackletter);
  font-size: 26px;
  letter-spacing: 0.02em;
  text-transform: none;
  color: var(--ink);
}

.topnav a {
  color: var(--ink);
}

.topnav a:hover {
  color: var(--oxblood);
  text-decoration: none;
}
.page {
  max-width: 1400px;
  margin: 0 auto;
  padding: 32px;
}

.drop-cap::first-letter {
  font-family: var(--display);
  float: left;
  font-size: 68px;
  line-height: 0.82;
  padding: 6px 10px 0 0;
  color: var(--oxblood);
  font-weight: 700;
}

.rule-double {
  border-top: 3px double var(--ink);
  border-bottom: 1px solid var(--ink);
  padding: 6px 0;
}

.rule-single {
  border-top: 1px solid var(--ink);
}

.column-rule {
  column-rule: 1px solid var(--rule);
}

button {
  font-family: var(--serif);
  cursor: pointer;
}

button:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

input,
textarea,
select {
    font-family: var(--serif);
    background: var(--paper);
    border: 1px solid var(--ink);
    padding: 8px 10px;
    color: var(--ink);
}

input:focus,
textarea:focus,
select:focus {
  outline: 2px solid var(--oxblood);
  outline-offset: 1px;
}

@keyframes skeleton-pulse {
  0% { opacity: 0.4; }
  50% { opacity: 0.8; }
  100% { opacity: 0.4; }
}

.skeleton {
  background: var(--shade);
  animation: skeleton-pulse 1.4s ease-in-out infinite;
}

@media print {
  .topnav {
    display: none;
  }
}
"""
    ),
)
write(
    "frontend/app/layout.tsx",
    D(
        r"""
import type { Metadata } from "next";
import Link from "next/link";
import {
  Libre_Caslon_Text,
  Playfair_Display,
  UnifrakturCook,
} from "next/font/google";
import "./globals.css";

const caslon = Libre_Caslon_Text({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--font-caslon",
});

const playfair = Playfair_Display({
  subsets: ["latin"],
  weight: ["400", "700", "900"],
  variable: "--font-playfair",
});

const fraktur = UnifrakturCook({
  subsets: ["latin"],
  weight: "700",
  variable: "--font-fraktur",
});

export const metadata: Metadata = {
  title: "Edition of One",
  description: "A personalised daily broadsheet.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
     lang="en"
     className={`${caslon.variable} ${playfair.variable} ${fraktur.variable}`}
    >
     <body>
        <nav className="topnav">
          <Link href="/" className="brand">
           Edition of One
          </Link>
          <Link href="/today">Today</Link>
          <Link href="/archive">Archive</Link>
          <Link href="/profile">Profile</Link>
        </nav>
        <main>{children}</main>
       </body>
      </html>
    );
}
"""
    ),
)
write(
    "frontend/app/page.tsx",
    D(
        r"""
"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { postOnboarding } from "../lib/api";
import { getReaderId, setReaderId } from "../lib/reader";
import type { Topic } from "../lib/types";

const TOPICS: { id: Topic; label: string }[] = [
 { id: "world", label: "World" },
 { id: "pakistan", label: "Pakistan" },
 { id: "politics", label: "Politics" },
 { id: "business", label: "Business" },
 { id: "markets", label: "Markets" },
 { id: "technology", label: "Technology" },
 { id: "ai", label: "AI" },
  { id: "science", label: "Science" },
  { id: "space", label: "Space" },
  { id: "health", label: "Health" },
  { id: "sport", label: "Sport" },
  { id: "cricket", label: "Cricket" },
  { id: "football", label: "Football" },
  { id: "culture", label: "Culture" },
  { id: "film_music", label: "Film & Music" },
  { id: "education", label: "Education" },
  { id: "climate", label: "Climate" },
  { id: "startups", label: "Startups" },
  { id: "opinion", label: "Opinion" },
];

type LikeLevel = 1 | 2;

export default function OnboardingPage() {
 const router = useRouter();
 const [readerId, setLocalReaderId] = useState("");
 const [likes, setLikes] = useState<Record<string, LikeLevel>>({});
 const [freeText, setFreeText] = useState("");
 const [readingTime, setReadingTime] = useState<"short" | "medium" | "long">("medium");
 const [tone, setTone] = useState<"neutral" | "warm" | "analytical">("neutral");
  const [loading, setLoading] = useState(false);

 useEffect(() => {
   setLocalReaderId(getReaderId());
 }, []);

 function toggleTopic(topic: string, level: LikeLevel) {
   setLikes((prev) => {
     const current = prev[topic];
     if (current === level) {
       const next = { ...prev };
       delete next[topic];
       return next;
     }
     return { ...prev, [topic]: level };
   });
 }

 async function handleSubmit() {
  setLoading(true);
    const loves = Object.keys(likes).filter((k) => likes[k] === 2);
    const interests = [
      ...Object.keys(likes),
      ...(freeText.trim() ? [freeText.trim()] : []),
    ];
    const payload = {
      reader_id: readerId || getReaderId(),
      name: "Reader",
      interests,
      loves,
      reading_time: readingTime,
      location: "Islamabad",
      tone,
    };
    try {
      await postOnboarding(payload);
    } catch {
      /* continue offline */
    }
    setReaderId(payload.reader_id);
    setTimeout(() => router.push("/today"), 400);
}

return (
 <div className="page" style={{ maxWidth: 1100 }}>
   <header style={{ textAlign: "center", marginBottom: 28 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 64, margin: 0 }}>
     Edition of One
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
       color: "var(--ink-faint)",
       marginTop: 4,
     }}
    >
     Onboard your daily broadsheet
    </p>
   </header>

     <section style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 20, marginBottom: 4 }}>Pick what you read</h2>
      <p style={{ color: "var(--ink-soft)", marginTop: 0, fontSize: 13 }}>
       Tap once to like · tap again to love · tap a third time to clear.
      </p>
      <div
       style={{
        display: "grid",
       gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
       gap: 8,
       marginTop: 12,
     }}
    >
     {TOPICS.map((t) => {
       const level = likes[t.id];
       return (
         <button
          key={t.id}
          type="button"
          onClick={() => toggleTopic(t.id, level === 1 ? 2 : 1)}
          style={{
            border: "1px solid var(--ink)",
            background:
              level === 2
                ? "var(--oxblood)"
                : level === 1
                ? "var(--shade)"
                : "var(--paper)",
            color: level === 2 ? "var(--paper)" : "var(--ink)",
            padding: "10px 8px",
            fontSize: 13,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            fontWeight: level ? 700 : 400,
            transition: "all 120ms ease",
          }}
         >
          {t.label}
         </button>
       );
     })}
    </div>
   </section>

   <section style={{ marginBottom: 24 }}>
    <label style={{ display: "block", fontSize: 12, letterSpacing: "0.2em", textTransform:
"uppercase" }}>
      Free-text preferences
    </label>
    <textarea
      value={freeText}
      onChange={(e) => setFreeText(e.target.value)}
  rows={3}
  placeholder="e.g. Pakistani politics, cricket, AI and startups"
  style={{ width: "100%", marginTop: 6 }}
 />
</section>

<section style={{ marginBottom: 24 }}>
 <div style={{ fontSize: 12, letterSpacing: "0.2em", textTransform: "uppercase" }}>
  Reading time
 </div>
 <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
  {(["short", "medium", "long"] as const).map((t) => (
    <button
      key={t}
      type="button"
      onClick={() => setReadingTime(t)}
      style={{
        border: "1px solid var(--ink)",
        background: readingTime === t ? "var(--ink)" : "var(--paper)",
        color: readingTime === t ? "var(--paper)" : "var(--ink)",
        padding: "8px 16px",
        fontSize: 12,
        letterSpacing: "0.15em",
        textTransform: "uppercase",
      }}
    >
      {t}
    </button>
  ))}
 </div>
</section>

<section style={{ marginBottom: 24 }}>
 <div style={{ fontSize: 12, letterSpacing: "0.2em", textTransform: "uppercase" }}>
  Tone
 </div>
 <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
  {(["neutral", "warm", "analytical"] as const).map((t) => (
    <label
     key={t}
     style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13 }}
    >
     <input
       type="radio"
        name="tone"
        checked={tone === t}
        onChange={() => setTone(t)}
      />
      {t}
    </label>
  ))}
 </div>
</section>

<div style={{ textAlign: "center" }}>
 <button
  type="button"
  onClick={handleSubmit}
  disabled={loading}
  style={{
    padding: "14px 40px",
    border: "1px solid var(--ink)",
    background: "var(--ink)",
    color: "var(--paper)",
    fontSize: 13,
    letterSpacing: "0.3em",
    textTransform: "uppercase",
  }}
 >
  {loading ? "Setting the presses…" : "Set the presses"}
 </button>
       </div>

       {loading && (
         <div
          style={{
            textAlign: "center",
            marginTop: 24,
            fontSize: 12,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
            color: "var(--ink-faint)",
          }}
         >
          Warming the ink…
         </div>
       )}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/app/today/page.tsx",
    D(
        r"""
"use client";

import { useEffect, useState } from "react";
import EditionView from "../../components/EditionView";
import SkeletonEdition from "../../components/SkeletonEdition";
import OfflineBanner from "../../components/OfflineBanner";
import { getEdition, type EditionResult } from "../../lib/api";
import { useReader } from "../../lib/reader";

export default function TodayPage() {
    const [readerId] = useReader();
    const [result, setResult] = useState<EditionResult | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
      if (!readerId) return;
      let mounted = true;
      (async () => {
        const res = await getEdition(readerId, "today");
        if (!mounted) return;
        setResult(res);
        setLoading(false);
      })();
      return () => {
        mounted = false;
      };
    }, [readerId]);

    if (loading) return <SkeletonEdition />;
    if (!result || !result.edition) {
      return (
        <div className="page">
          <p>No edition available yet. Onboard first to set the presses.</p>
        </div>
      );
    }

    return (
      <>
       {result.offline && <OfflineBanner />}
       <EditionView edition={result.edition} />
      </>
    );
}
"""
    ),
)
write(
    "frontend/app/edition/[date]/page.tsx",
    D(
        r"""
"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import EditionView from "../../../components/EditionView";
import SkeletonEdition from "../../../components/SkeletonEdition";
import OfflineBanner from "../../../components/OfflineBanner";
import { getEdition, type EditionResult } from "../../../lib/api";
import { useReader } from "../../../lib/reader";

export default function EditionByDatePage() {
 const params = useParams<{ date: string }>();
 const [readerId] = useReader();
 const [result, setResult] = useState<EditionResult | null>(null);
 const [loading, setLoading] = useState(true);

 useEffect(() => {
   if (!readerId || !params?.date) return;
   let mounted = true;
   (async () => {
     const res = await getEdition(readerId, params.date);
     if (!mounted) return;
     setResult(res);
     setLoading(false);
   })();
   return () => {
     mounted = false;
   };
 }, [readerId, params?.date]);

 if (loading) return <SkeletonEdition />;
 if (!result || !result.edition) {
   return (
     <div className="page">
       <p>No edition found for {params?.date}.</p>
     </div>
   );
    }

    return (
      <>
       {result.offline && <OfflineBanner />}
       <EditionView edition={result.edition} />
      </>
    );
}
"""
    ),
)
write(
    "frontend/app/archive/page.tsx",
    D(
        r"""
"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { getArchive, getEdition } from "../../lib/api";
import { useReader } from "../../lib/reader";
import type { Edition } from "../../lib/types";

interface ArchiveEntry {
  date: string;
  headline: string;
}

export default function ArchivePage() {
 const [readerId] = useReader();
 const [entries, setEntries] = useState<ArchiveEntry[]>([]);
 const [query, setQuery] = useState("");
 const [loading, setLoading] = useState(true);

    useEffect(() => {
  if (!readerId) return;
  let mounted = true;
  (async () => {
    const { dates } = await getArchive(readerId);
    const sliced = dates.slice(0, 30);
    const rich: ArchiveEntry[] = [];
    for (const d of sliced) {
      const res = await getEdition(readerId, d);
      const ed: Edition | null = res.edition;
      rich.push({
        date: d,
        headline: ed?.front?.lead?.title || "Untitled edition",
      });
    }
    if (mounted) {
      setEntries(rich);
      setLoading(false);
    }
  })();
  return () => {
    mounted = false;
  };
}, [readerId]);

const filtered = useMemo(() => {
  const q = query.trim().toLowerCase();
  if (!q) return entries;
  return entries.filter(
    (e) =>
      e.headline.toLowerCase().includes(q) || e.date.includes(q)
  );
}, [entries, query]);

return (
 <div className="page">
   <header style={{ textAlign: "center", marginBottom: 24 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 48, margin: 0 }}>
     Archive
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
    color: "var(--ink-faint)",
  }}
 >
  Last 30 editions
 </p>
</header>

<div style={{ marginBottom: 20, maxWidth: 400, margin: "0 auto 24px" }}>
 <input
  placeholder="Search headlines or dates"
  value={query}
  onChange={(e) => setQuery(e.target.value)}
  style={{ width: "100%" }}
 />
</div>

{loading ? (
  <p style={{ textAlign: "center" }}>Scanning the back issues…</p>
):(
  <div
   style={{
     display: "grid",
     gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
     gap: 12,
   }}
  >
   {filtered.map((e) => (
     <Link
       key={e.date}
       href={`/edition/${e.date}`}
       style={{
         border: "1px solid var(--ink)",
         padding: 14,
         background: "var(--paper)",
         color: "var(--ink)",
       }}
     >
       <div
         style={{
           fontSize: 11,
           letterSpacing: "0.2em",
           textTransform: "uppercase",
           color: "var(--ink-faint)",
         }}
              >
                {e.date}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-playfair)",
                  fontSize: 18,
                  marginTop: 6,
                  lineHeight: 1.2,
                }}
              >
                {e.headline}
              </div>
            </Link>
          ))}
          {filtered.length === 0 && (
            <p style={{ textAlign: "center" }}>No editions match your search.</p>
          )}
         </div>
       )}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/app/profile/page.tsx",
    D(
        r"""
"use client";

import { useEffect, useState } from "react";
import { advanceNight, getProfile, removeTopic as removeTopicApi } from "../../lib/api";
import { useReader } from "../../lib/reader";
import type { Profile } from "../../lib/types";
export default function ProfilePage() {
 const [readerId] = useReader();
 const [profile, setProfile] = useState<Profile | null>(null);
 const [busy, setBusy] = useState(false);
 const [message, setMessage] = useState("");

 async function load() {
   if (!readerId) return;
   const p = await getProfile(readerId);
   setProfile(p);
 }

 useEffect(() => {
   void load();
   // eslint-disable-next-line react-hooks/exhaustive-deps
 }, [readerId]);

 async function handleAdvance() {
   if (!readerId) return;
   setBusy(true);
   setMessage("");
   const ok = await advanceNight(readerId);
   setBusy(false);
   setMessage(
     ok
       ? "Weights re-tuned for tomorrow. Reload the edition to see the changes."
       : "Backend offline — learning is queued locally."
   );
   await load();
 }

 async function removeTopic(topic: string) {
   if (!profile || !readerId) return;
   const updated = await removeTopicApi(readerId, topic);
   if (updated) setProfile(updated);
   else setMessage("Could not reach the backend; topic not removed.");
 }

 if (!profile) {
   return (
     <div className="page">
       <p>No profile yet. Complete onboarding first.</p>
      </div>
    );
}

const topics = Object.entries(profile.weights)
 .map(([k, v]) => [k, v] as [string, number])
 .sort((a, b) => b[1] - a[1]);

return (
 <div className="page">
   <header style={{ textAlign: "center", marginBottom: 24 }}>
    <h1 style={{ fontFamily: "var(--font-fraktur)", fontSize: 48, margin: 0 }}>
     Reader Profile
    </h1>
    <p
     style={{
       fontSize: 12,
       letterSpacing: "0.3em",
       textTransform: "uppercase",
       color: "var(--ink-faint)",
     }}
    >
     {profile.reader_id}
    </p>
   </header>

     <section style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 20 }}>Topic weights</h2>
      <div style={{ display: "grid", gap: 6, marginTop: 8 }}>
       {topics.map(([topic, weight]) => {
         const delta = profile.weight_deltas?.[topic] ?? 0;
         const arrow = delta > 0.01 ? "▲" : delta < -0.01 ? "▼" : "·";
         const color =
          delta > 0.01 ? "#1a6b1a" : delta < -0.01 ? "var(--oxblood)" : "var(--ink-faint)";
         return (
          <div
            key={topic}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              borderBottom: "1px solid var(--rule)",
              paddingBottom: 4,
            }}
      >
       <div style={{ flex: 1, textTransform: "capitalize" }}>
        {topic.replace(/_/g, " ")}
       </div>
       <div style={{ width: 200, background: "var(--shade)", height: 8 }}>
        <div
          style={{
            width: `${Math.round(weight * 100)}%`,
            background: "var(--ink)",
            height: 8,
          }}
        />
       </div>
       <div style={{ width: 60, textAlign: "right", fontSize: 12 }}>
        {weight.toFixed(2)}
       </div>
       <div style={{ width: 50, textAlign: "right", color, fontSize: 12 }}>
        {arrow} {delta !== 0 ? delta.toFixed(2) : ""}
       </div>
       <button
        type="button"
        onClick={() => removeTopic(topic)}
        style={{
          border: "1px solid var(--ink)",
          background: "var(--paper)",
          fontSize: 11,
          padding: "2px 6px",
        }}
       >
        remove
       </button>
      </div>
    );
  })}
 </div>
</section>

<section style={{ textAlign: "center", marginTop: 32 }}>
 <button
  type="button"
  onClick={handleAdvance}
  disabled={busy}
  style={{
    padding: "12px 30px",
            border: "1px solid var(--ink)",
            background: "var(--oxblood)",
            color: "var(--paper)",
            fontSize: 12,
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          {busy ? "Running overnight…" : "Advance one night (demo)"}
        </button>
        {message && (
          <p style={{ marginTop: 12, fontSize: 12, color: "var(--ink-soft)" }}>
            {message}
          </p>
        )}
       </section>
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/EditionView.tsx",
    D(
        r"""
"use client";

import { useState } from "react";
import type { Edition, ArticleRecord } from "../lib/types";
import Masthead from "./Masthead";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import BriefsList from "./BriefsList";
import SectionHeader from "./SectionHeader";
import ReadingPanel from "./ReadingPanel";
import AudioPlayer from "./extras/AudioPlayer";
import PressGallery from "./extras/PressGallery";
import BackPage from "./extras/BackPage";
import WhyChip from "./WhyChip";

export default function EditionView({ edition }: { edition: Edition }) {
 const [open, setOpen] = useState<ArticleRecord | null>(null);

 return (
  <div className="page">
    <Masthead edition={edition} />
    {edition.why_text && (
      <div style={{ margin: "8px 0 20px", textAlign: "center" }}>
       <WhyChip text={edition.why_text} />
      </div>
    )}

   <section
    style={{
      display: "grid",
      gridTemplateColumns: "3fr 1fr",
      gap: 24,
      borderBottom: "1px solid var(--ink)",
      paddingBottom: 24,
    }}
   >
    <div>
      {edition.front.lead && (
        <LeadStory
         article={edition.front.lead}
         onOpen={() => setOpen(edition.front.lead || null)}
        />
      )}
    </div>
    <aside style={{ borderLeft: "1px solid var(--rule)", paddingLeft: 18 }}>
      {edition.front.weather && (
        <div style={{ border: "1px solid var(--ink)", padding: 12, textAlign: "center",
marginBottom: 12 }}>
         <div style={{ fontSize: 11, letterSpacing: "0.2em", textTransform: "uppercase" }}>
           {edition.front.weather.city}
         </div>
         <div style={{ fontFamily: "var(--font-playfair)", fontSize: 36, lineHeight: 1 }}>
           {edition.front.weather.temp_c ?? "--"}°
         </div>
     <div style={{ fontSize: 11, color: "var(--ink-faint)" }}>
       H {edition.front.weather.high_c ?? "--"}° / L {edition.front.weather.low_c ?? "--"}°
     </div>
    </div>
  )}
  {edition.front.quote && (
    <blockquote
     style={{
       fontStyle: "italic",
       borderTop: "1px solid var(--ink)",
       borderBottom: "1px solid var(--ink)",
       padding: "12px 0",
       margin: 0,
     }}
    >
     {edition.front.quote}
    </blockquote>
  )}
  {edition.weight_snapshot && (
    <div style={{ marginTop: 16, fontSize: 11, color: "var(--ink-faint)" }}>
     Tonight's weights:{" "}
     {Object.entries(edition.weight_snapshot)
       .slice(0, 4)
       .map(([k, v]) => `${k} ${v.toFixed(2)}`)
       .join(" · ")}
    </div>
  )}
 </aside>
</section>

{edition.front.secondary.length > 0 && (
  <section
   style={{
     display: "grid",
     gridTemplateColumns: "repeat(3, 1fr)",
     gap: 20,
     marginTop: 24,
   }}
  >
   {edition.front.secondary.map((a) => (
     <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} />
   ))}
  </section>
)}
{edition.front.briefs.length > 0 && (
  <section style={{ marginTop: 24 }}>
   <BriefsList briefs={edition.front.briefs} onOpen={setOpen} />
  </section>
)}

{edition.sections.map((sec) => (
  <section key={sec.slug} style={{ marginTop: 32 }}>
    <SectionHeader name={sec.name} />
    <div
     style={{
       display: "grid",
       gridTemplateColumns: "repeat(3, 1fr)",
       gap: 20,
     }}
    >
     {sec.articles.map((a) => (
       <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} />
     ))}
    </div>
  </section>
))}

{edition.outside_bubble.length > 0 && (
  <section style={{ marginTop: 32 }}>
   <SectionHeader name="Outside Your Bubble" />
   <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
    {edition.outside_bubble.map((a) => (
      <StoryCard key={a.id} article={a} onOpen={() => setOpen(a)} compact />
    ))}
   </div>
  </section>
)}

<section style={{ marginTop: 32 }}>
 <AudioPlayer edition={edition} />
</section>

{edition.press_gallery && edition.press_gallery.rows.length > 0 && (
  <section style={{ marginTop: 24 }}>
   <PressGallery gallery={edition.press_gallery} />
  </section>
)}
       {edition.back_page && (
         <section style={{ marginTop: 24 }}>
          <BackPage backPage={edition.back_page} />
         </section>
       )}

       <ReadingPanel article={open} onClose={() => setOpen(null)} />
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/Masthead.tsx",
    D(
        r"""
"use client";

import type { Edition } from "../lib/types";

export default function Masthead({ edition }: { edition: Edition }) {
 return (
  <header
    style={{
      textAlign: "center",
      borderBottom: "3px double var(--ink)",
      borderTop: "1px solid var(--ink)",
      padding: "10px 0 12px",
      marginBottom: 20,
    }}
  >
    <h1
      style={{
       fontFamily: "var(--font-fraktur)",
          fontSize: 72,
          margin: 0,
          lineHeight: 1,
          letterSpacing: "0.01em",
        }}
       >
        {edition.nameplate || "Edition of One"}
       </h1>
       <div
        style={{
          fontSize: 11,
          letterSpacing: "0.35em",
          textTransform: "uppercase",
          color: "var(--ink-faint)",
          marginTop: 4,
        }}
       >
        {edition.dateline || edition.date}
       </div>
      </header>
    );
}
"""
    ),
)
write(
    "frontend/components/LeadStory.tsx",
    D(
        r"""
"use client";

import { useRef } from "react";
import type { ArticleRecord } from "../lib/types";
import FeedbackBar from "./FeedbackBar";
import { useImpression } from "../lib/tracker";
interface Props {
  article: ArticleRecord;
  onOpen: () => void;
}

export default function LeadStory({ article, onOpen }: Props) {
 const ref = useRef<HTMLElement>(null);
 useImpression(ref as React.RefObject<HTMLElement>, article.id);
 const body = article.body.long || article.body.medium || article.body.short;

 return (
  <article ref={ref} id={`story-${article.id}`}>
    <h1
     style={{
       fontFamily: "var(--font-playfair)",
       fontSize: 42,
       lineHeight: 1.02,
       margin: "0 0 14px",
       letterSpacing: "-0.01em",
     }}
    >
     <button
       type="button"
       onClick={onOpen}
       style={{
         background: "none",
         border: "none",
         padding: 0,
         textAlign: "left",
         color: "inherit",
         font: "inherit",
         cursor: "pointer",
       }}
     >
       {article.title}
     </button>
    </h1>
    <p
     className="drop-cap"
     style={{
       fontFamily: "var(--font-caslon)",
       fontSize: 15,
       columnCount: 3,
       columnGap: 20,
          columnRule: "1px solid var(--rule)",
          marginTop: 0,
        }}
       >
        {body}
       </p>
       <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 8,
          fontSize: 11,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--ink-faint)",
        }}
       >
        <span>{article.source}</span>
        <FeedbackBar articleId={article.id} />
       </div>
      </article>
    );
}
"""
    ),
)
write(
    "frontend/components/StoryCard.tsx",
    D(
        r"""
"use client";

import { useRef } from "react";
import type { ArticleRecord } from "../lib/types";
import FeedbackBar from "./FeedbackBar";
import { useImpression } from "../lib/tracker";

interface Props {
  article: ArticleRecord;
  onOpen: () => void;
  compact?: boolean;
}

export default function StoryCard({ article, onOpen, compact }: Props) {
 const ref = useRef<HTMLElement>(null);
 useImpression(ref as React.RefObject<HTMLElement>, article.id);
 const body = compact
  ? article.body.short
  : article.body.medium || article.body.short;

 return (
  <article
    ref={ref}
    id={`story-${article.id}`}
    style={{ borderTop: "1px solid var(--ink)", paddingTop: 8 }}
  >
    <h3
      style={{
        fontFamily: "var(--font-playfair)",
        fontSize: compact ? 15 : 20,
        margin: "4px 0 6px",
        lineHeight: 1.2,
      }}
    >
      <button
        type="button"
        onClick={onOpen}
        style={{
          background: "none",
          border: "none",
          padding: 0,
          textAlign: "left",
          color: "inherit",
          font: "inherit",
          cursor: "pointer",
        }}
      >
        {article.title}
      </button>
       </h3>
       <p style={{ fontSize: compact ? 12 : 13, color: "var(--ink-soft)", margin: 0 }}>
        {body}
       </p>
       <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 6,
          fontSize: 10,
          letterSpacing: "0.2em",
          textTransform: "uppercase",
          color: "var(--ink-faint)",
        }}
       >
        <span>{article.source}</span>
        <FeedbackBar articleId={article.id} />
       </div>
      </article>
    );
}
"""
    ),
)
write(
    "frontend/components/BriefsList.tsx",
    D(
        r"""
"use client";

import type { ArticleRecord } from "../lib/types";

interface Props {
  briefs: ArticleRecord[];
  onOpen: (a: ArticleRecord) => void;
}

export default function BriefsList({ briefs, onOpen }: Props) {
 return (
  <div
    style={{
      borderTop: "3px double var(--ink)",
      borderBottom: "1px solid var(--ink)",
      padding: "12px 0",
      columnCount: 4,
      columnGap: 18,
      columnRule: "1px solid var(--rule)",
    }}
  >
    {briefs.map((a) => (
      <div
       key={a.id}
       style={{
         breakInside: "avoid",
         marginBottom: 12,
         paddingBottom: 6,
       }}
       id={`story-${a.id}`}
      >
       <h4
         style={{
           fontFamily: "var(--font-playfair)",
           fontSize: 13,
           margin: "0 0 4px",
         }}
       >
         <button
           type="button"
           onClick={() => onOpen(a)}
           style={{
             background: "none",
             border: "none",
             padding: 0,
             textAlign: "left",
             color: "inherit",
             font: "inherit",
             cursor: "pointer",
           }}
         >
             {a.title}
            </button>
           </h4>
           <p style={{ fontSize: 11, color: "var(--ink-soft)", margin: 0 }}>
            {a.body.short}
           </p>
         </div>
       ))}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/SectionHeader.tsx",
    D(
        r"""
"use client";

export default function SectionHeader({ name }: { name: string }) {
 return (
   <h2
    style={{
      fontFamily: "var(--font-playfair)",
      fontSize: 24,
      letterSpacing: "0.2em",
      textTransform: "uppercase",
      borderBottom: "2px solid var(--ink)",
      paddingBottom: 4,
      margin: "0 0 12px",
    }}
   >
    {name}
   </h2>
 );
}
"""
    ),
)
write(
    "frontend/components/FeedbackBar.tsx",
    D(
        r"""
"use client";

import { useState } from "react";
import { tracker } from "../lib/tracker";

export default function FeedbackBar({ articleId }: { articleId: string }) {
 const [choice, setChoice] = useState<"up" | "down" | "save" | null>(null);

    function handle(kind: "up" | "down" | "save") {
      if (choice === kind) {
        setChoice(null);
        return;
      }
      setChoice(kind);
      if (kind === "up") tracker.track("thumb_up", articleId, 1.0);
      else if (kind === "down") tracker.track("thumb_down", articleId, 1.0);
      else tracker.track("save", articleId, 1.0);
    }

    const btn = (label: string, kind: "up" | "down" | "save") => (
     <button
      key={kind}
      type="button"
      onClick={() => handle(kind)}
      style={{
        border: "1px solid var(--rule)",
        background: choice === kind ? "var(--ink)" : "var(--paper)",
        color: choice === kind ? "var(--paper)" : "var(--ink-soft)",
         fontSize: 10,
         padding: "2px 6px",
         letterSpacing: "0.1em",
         textTransform: "uppercase",
       }}
      >
       {label}
      </button>
    );

    return (
      <div style={{ display: "flex", gap: 4 }}>
       {btn("▲", "up")}
       {btn("▼", "down")}
       {btn("save", "save")}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/WhyChip.tsx",
    D(
        r"""
"use client";

export default function WhyChip({ text }: { text: string }) {
 return (
  <span
    style={{
     display: "inline-block",
     border: "1px dashed var(--oxblood)",
     color: "var(--oxblood)",
     fontSize: 11,
     padding: "4px 10px",
         letterSpacing: "0.1em",
         fontStyle: "italic",
       }}
      >
       Why: {text}
      </span>
    );
}
"""
    ),
)
write(
    "frontend/components/ReadingPanel.tsx",
    D(
        r"""
"use client";

import { useEffect } from "react";
import type { ArticleRecord } from "../lib/types";
import { useDwell } from "../lib/tracker";

interface Props {
  article: ArticleRecord | null;
  onClose: () => void;
}

export default function ReadingPanel({ article, onClose }: Props) {
 useDwell(article?.id ?? null);

    useEffect(() => {
     if (!article) return;
     function onKey(ev: KeyboardEvent) {
       if (ev.key === "Escape") onClose();
     }
     window.addEventListener("keydown", onKey);
     return () => window.removeEventListener("keydown", onKey);
}, [article, onClose]);

if (!article) return null;

return (
 <div
   role="dialog"
   aria-modal="true"
   onClick={(e) => {
     if (e.target === e.currentTarget) onClose();
   }}
   style={{
     position: "fixed",
     inset: 0,
     background: "rgba(0,0,0,0.35)",
     display: "flex",
     justifyContent: "flex-end",
     zIndex: 100,
   }}
 >
   <div
     style={{
       background: "var(--paper)",
       width: "min(640px, 100%)",
       height: "100%",
       overflowY: "auto",
       padding: 32,
       borderLeft: "3px double var(--ink)",
     }}
   >
     <div
       style={{
         display: "flex",
         justifyContent: "space-between",
         alignItems: "center",
         marginBottom: 16,
       }}
     >
       <span
         style={{
           fontSize: 11,
           letterSpacing: "0.3em",
           textTransform: "uppercase",
           color: "var(--ink-faint)",
    }}
  >
    {article.source}
  </span>
  <button
    type="button"
    onClick={onClose}
    style={{
      border: "1px solid var(--ink)",
      background: "var(--paper)",
      fontSize: 11,
      padding: "2px 8px",
    }}
  >
    Esc
  </button>
</div>
<h2 style={{ fontFamily: "var(--font-playfair)", fontSize: 28, lineHeight: 1.15 }}>
  {article.title}
</h2>
<div
  style={{
    fontFamily: "var(--font-caslon)",
    fontSize: 15,
    lineHeight: 1.6,
  }}
>
  {(article.body.long || article.body.medium || article.body.short)
    .split(/\n\n+/)
    .map((p, i) => (
      <p key={i}>{p}</p>
    ))}
</div>
{article.url && (
  <p style={{ marginTop: 20, fontSize: 12 }}>
    Source:{" "}
    <a href={article.url} target="_blank" rel="noreferrer">
      {article.url}
    </a>
  </p>
)}
<p style={{ marginTop: 24, fontSize: 11, color: "var(--ink-faint)" }}>
  Press <kbd>Esc</kbd> to close
        </p>
       </div>
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/OfflineBanner.tsx",
    D(
        r"""
"use client";

export default function OfflineBanner() {
  return (
    <div
      style={{
        background: "var(--oxblood)",
        color: "var(--paper)",
        textAlign: "center",
        fontSize: 11,
        letterSpacing: "0.3em",
        textTransform: "uppercase",
        padding: "6px 0",
      }}
    >
      Offline — showing cached sample edition
    </div>
  );
}
"""
    ),
)
write(
    "frontend/components/SkeletonEdition.tsx",
    D(
        r"""
"use client";

export default function SkeletonEdition() {
  return (
    <div className="page">
      <div
       className="skeleton"
       style={{ height: 80, marginBottom: 24, borderRadius: 2 }}
      />
      <div style={{ display: "grid", gridTemplateColumns: "3fr 1fr", gap: 24 }}>
       <div>
         <div className="skeleton" style={{ height: 44, marginBottom: 12 }} />
         <div className="skeleton" style={{ height: 240 }} />
       </div>
       <div>
         <div className="skeleton" style={{ height: 100, marginBottom: 12 }} />
         <div className="skeleton" style={{ height: 100 }} />
       </div>
      </div>
      <div style={{ marginTop: 32 }}>
       <div className="skeleton" style={{ height: 20, width: 200, marginBottom: 12 }} />
       <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
         <div className="skeleton" style={{ height: 120 }} />
         <div className="skeleton" style={{ height: 120 }} />
         <div className="skeleton" style={{ height: 120 }} />
       </div>
      </div>
    </div>
  );
}
"""
    ),
)
write(
    "frontend/components/Toast.tsx",
    D(
        r"""
"use client";

import { useEffect, useState } from "react";

interface Props {
  message: string;
  onDone?: () => void;
  durationMs?: number;
}

export default function Toast({ message, onDone, durationMs = 2400 }: Props) {
 const [visible, setVisible] = useState(true);
 useEffect(() => {
   const t = setTimeout(() => {
     setVisible(false);
     onDone?.();
   }, durationMs);
   return () => clearTimeout(t);
 }, [onDone, durationMs]);

 if (!visible) return null;

 return (
  <div
    style={{
     position: "fixed",
     bottom: 24,
     left: "50%",
     transform: "translateX(-50%)",
     background: "var(--ink)",
     color: "var(--paper)",
     padding: "10px 20px",
         fontSize: 12,
         letterSpacing: "0.1em",
         zIndex: 200,
       }}
      >
       {message}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/extras/AudioPlayer.tsx",
    D(
        r"""
"use client";

import { useEffect, useRef, useState } from "react";
import { API_BASE } from "../../lib/api";
import type { Edition } from "../../lib/types";

export default function AudioPlayer({ edition }: { edition: Edition }) {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [playing, setPlaying] = useState(false);
  const [audioFailed, setAudioFailed] = useState(false);

  const bc = edition.broadcast;
  const audioUrl = bc?.audio_url ? `${API_BASE}${bc.audio_url}` : null;
  const speechMode = !audioUrl || audioFailed;
  const chapters = bc?.chapters ?? [];
  const total = Math.round(bc?.duration ?? 0);

  // Stop any speech when the edition changes or the player unmounts.
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, [edition.id]);

  function speak(): boolean {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
    const lead = edition.front.lead;
    const parts: string[] = bc?.script
      ? [
          bc.script.intro,
          ...bc.script.chapters.map((c) => `${c.title}. ${c.script}`),
          bc.script.outro,
        ]
      : lead
      ? [`${lead.title}. ${lead.body.short}`]
      : [];
    if (parts.length === 0) return false;
    window.speechSynthesis.cancel();
    parts.forEach((text, i) => {
      const utter = new SpeechSynthesisUtterance(text);
      if (i === parts.length - 1) utter.onend = () => setPlaying(false);
      window.speechSynthesis.speak(utter);
    });
    return true;
  }

  function toggle() {
    if (playing) {
      if (speechMode) window.speechSynthesis?.cancel();
      else audioRef.current?.pause();
      setPlaying(false);
      return;
    }
    if (speechMode) {
      if (speak()) setPlaying(true);
      return;
    }
    audioRef.current
      ?.play()
      .then(() => setPlaying(true))
      .catch(() => {
        setAudioFailed(true);
        if (speak()) setPlaying(true);
      });
  }

  function seek(start: number) {
    const el = audioRef.current;
    if (!el || speechMode) return;
    el.currentTime = start;
    void el.play().then(() => setPlaying(true));
  }

  function jumpTo(id: string) {
    const el = document.getElementById(`story-${id}`);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const stories = [
    ...(edition.front.lead ? [edition.front.lead] : []),
    ...edition.front.secondary,
  ];

  return (
    <div style={{ border: "1px solid var(--ink)", padding: 12, background: "var(--paper)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: 8,
        }}
      >
        <div style={{ fontSize: 12, letterSpacing: "0.25em", textTransform: "uppercase" }}>
          The Morning Broadcast
        </div>
        <button
          type="button"
          onClick={toggle}
          style={{
            border: "1px solid var(--ink)",
            background: "var(--ink)",
            color: "var(--paper)",
            padding: "4px 14px",
            fontSize: 11,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
          }}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
      </div>
      <div style={{ fontSize: 11, color: "var(--ink-faint)" }}>
        {speechMode
          ? "Read aloud by your browser's speech synthesis."
          : `${total}s · ${chapters.length} chapters`}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
        {stories.map((a, i) => (
          <button
            key={a.id}
            type="button"
            onClick={() => (speechMode || !chapters[i] ? jumpTo(a.id) : seek(chapters[i].start))}
            style={{
              border: "1px solid var(--rule)",
              background: "transparent",
              fontSize: 10,
              padding: "2px 8px",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
            }}
          >
            → {a.title.length > 28 ? a.title.slice(0, 28) + "…" : a.title}
          </button>
        ))}
      </div>
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="none"
          style={{ display: "none" }}
          onEnded={() => setPlaying(false)}
          onError={() => setAudioFailed(true)}
        />
      )}
    </div>
  );
}
"""
    ),
)
write(
    "frontend/components/extras/PressGallery.tsx",
    D(
        r"""
"use client";

import { useState } from "react";
import type { PressGallery as PG } from "../../lib/types";

export default function PressGallery({ gallery }: { gallery: PG }) {
 const [open, setOpen] = useState(false);

 return (
  <div style={{ borderTop: "1px solid var(--ink)", paddingTop: 12 }}>
    <button
     type="button"
     onClick={() => setOpen(!open)}
     style={{
       width: "100%",
       background: "transparent",
       border: "none",
       padding: 0,
       textAlign: "left",
       display: "flex",
       justifyContent: "space-between",
       alignItems: "baseline",
     }}
    >
     <h3
       style={{
         fontFamily: "var(--font-playfair)",
         fontSize: 20,
         letterSpacing: "0.2em",
         textTransform: "uppercase",
         margin: 0,
       }}
     >
       Press Gallery
     </h3>
     <span style={{ fontSize: 12, color: "var(--ink-faint)" }}>
       {open ? "▲ close" : "▼ open"}
     </span>
    </button>

    {open && (
     <div style={{ marginTop: 12 }}>
      <p style={{ fontSize: 12, color: "var(--ink-faint)", marginTop: 0 }}>
       Same story, different outlets.
      </p>
      <div style={{ display: "grid", gap: 8 }}>
       {gallery.rows.map((row, idx) => (
             <div
               key={idx}
               style={{
                 border: "1px solid var(--rule)",
                 padding: 12,
                 background: "var(--paper)",
               }}
             >
               <div
                 style={{
                   fontSize: 11,
                   letterSpacing: "0.2em",
                   textTransform: "uppercase",
                   color: "var(--ink-faint)",
                   marginBottom: 4,
                 }}
               >
                 {row.title}
               </div>
               <div style={{ fontSize: 13 }}>{row.caption}</div>
             </div>
           ))}
          </div>
         </div>
       )}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/components/extras/BackPage.tsx",
    D(
        r"""
"use client";
import { useState } from "react";
import type { BackPage as BP } from "../../lib/types";

export default function BackPage({ backPage }: { backPage: BP }) {
 const [answers, setAnswers] = useState<Record<number, number>>({});
 const [struck, setStruck] = useState<Record<string, boolean>>({});

 function selectAnswer(qIdx: number, optIdx: number) {
   setAnswers((prev) => ({ ...prev, [qIdx]: optIdx }));
 }

 const score = Object.entries(answers).filter(([q, a]) => {
   const idx = Number(q);
   return backPage.quiz[idx]?.answer === a;
 }).length;

 function toggleWord(word: string) {
   setStruck((prev) => ({ ...prev, [word]: !prev[word] }));
 }

 return (
  <div style={{ borderTop: "3px double var(--ink)", paddingTop: 20 }}>
    <h2
     style={{
       fontFamily: "var(--font-fraktur)",
       fontSize: 36,
       margin: "0 0 16px",
     }}
    >
     The Back Page
    </h2>

   {backPage.quiz.length > 0 && (
    <section style={{ marginBottom: 32 }}>
     <h3
      style={{
        fontFamily: "var(--font-playfair)",
        fontSize: 20,
        letterSpacing: "0.2em",
        textTransform: "uppercase",
      }}
     >
      News Quiz · {score} / {backPage.quiz.length}
</h3>
<ol style={{ paddingLeft: 0, listStyle: "none" }}>
 {backPage.quiz.map((q, qi) => (
  <li
    key={qi}
    style={{
      borderTop: "1px solid var(--rule)",
      padding: "10px 0",
    }}
  >
    <div style={{ fontFamily: "var(--font-playfair)", fontSize: 16 }}>
      {qi + 1}. {q.question}
    </div>
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 6 }}>
      {q.options.map((opt, oi) => {
        const chosen = answers[qi] === oi;
        const correct = q.answer === oi;
        const reveal = answers[qi] !== undefined;
        return (
          <button
           key={oi}
           type="button"
           onClick={() => selectAnswer(qi, oi)}
           style={{
             border: "1px solid var(--ink)",
             padding: "4px 10px",
             fontSize: 12,
             background: chosen
              ? reveal && correct
                ? "#1a6b1a"
                : reveal
                ? "var(--oxblood)"
                : "var(--ink)"
              : reveal && correct
              ? "#d6e6d6"
              : "var(--paper)",
             color: chosen ? "var(--paper)" : "var(--ink)",
           }}
          >
           {opt}
          </button>
        );
      })}
    </div>
      </li>
    ))}
   </ol>
  </section>
)}

{backPage.word_search && (
 <section style={{ marginBottom: 32 }}>
  <h3
   style={{
     fontFamily: "var(--font-playfair)",
     fontSize: 20,
     letterSpacing: "0.2em",
     textTransform: "uppercase",
   }}
  >
   Word Search
  </h3>
  <div
   style={{
     display: "grid",
     gridTemplateColumns: `repeat(${backPage.word_search.grid[0]?.length || 12}, 1fr)`,
     fontFamily: "monospace",
     fontSize: 12,
     gap: 2,
     maxWidth: 360,
   }}
  >
   {backPage.word_search.grid.flatMap((row, ri) =>
     row.split("").map((ch, ci) => (
       <div
        key={`${ri}-${ci}`}
        style={{
          border: "1px solid var(--rule)",
          textAlign: "center",
          padding: "4px 0",
        }}
       >
        {ch}
       </div>
     ))
   )}
  </div>
  <div style={{ marginTop: 10, display: "flex", gap: 6, flexWrap: "wrap" }}>
    {backPage.word_search.words.map((w) => (
      <button
        key={w}
        type="button"
        onClick={() => toggleWord(w)}
        style={{
          border: "1px solid var(--rule)",
          background: "transparent",
          textDecoration: struck[w] ? "line-through" : "none",
          fontSize: 11,
          padding: "2px 8px",
        }}
      >
        {w}
      </button>
    ))}
   </div>
  </section>
)}

{backPage.on_this_day.length > 0 && (
 <section>
  <h3
   style={{
     fontFamily: "var(--font-playfair)",
     fontSize: 20,
     letterSpacing: "0.2em",
     textTransform: "uppercase",
   }}
  >
   From History
  </h3>
  <ul style={{ listStyle: "none", padding: 0 }}>
   {backPage.on_this_day.map((item, i) => (
     <li
       key={i}
       style={{
         borderTop: "1px solid var(--rule)",
         padding: "8px 0",
         fontSize: 13,
       }}
     >
       <strong style={{ color: "var(--oxblood)" }}>{item.year ?? "—"}</strong>{" "}
       — {item.text}
             </li>
           ))}
          </ul>
         </section>
       )}
      </div>
    );
}
"""
    ),
)
write(
    "frontend/.eslintrc.json",
    D(
        r"""
{
  "extends": "next/core-web-vitals"
}
"""
    ),
)

print()
print("=" * 68)
print("Phase 2 scaffold created.")
print("Next steps:")
print()
print("  make seed       # Phase 1 demo data (if you haven't)")
print("  make extras     # gallery, back page, broadcast for stored editions")
print("  make simulate   # 7-day reader simulation -> docs/samples/")
print("  make learn      # one learning pass over all readers")
print("  make test")
print("  make web-install && make api   # then, in another shell: make web")
print("=" * 68)
