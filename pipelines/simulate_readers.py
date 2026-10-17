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
