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
