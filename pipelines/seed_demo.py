from __future__ import annotations

import datetime as dt
import json
import random
from pathlib import Path

from app.core.store import get_store
from app.models.schemas import ArticleRecord, Profile
from app.services.fallback_editor import build_edition

DEMO_READERS = [
    {
        "reader_id": "demo-ayesha",
        "display_name": "Ayesha",
        "topic_weights": {"ai": 0.9, "technology": 0.8, "startups": 0.6, "science": 0.4, "pakistan": 0.5},
        "reading_minutes": 15,
        "region_bias": 0.5,
    },
    {
        "reader_id": "demo-bilal",
        "display_name": "Bilal",
        "topic_weights": {"cricket": 0.9, "sport": 0.7, "pakistan": 0.9, "politics": 0.6, "business": 0.4},
        "reading_minutes": 15,
        "region_bias": 0.8,
    },
    {
        "reader_id": "demo-sara",
        "display_name": "Sara",
        "topic_weights": {"climate": 0.9, "science": 0.8, "health": 0.6, "world": 0.6, "culture": 0.5},
        "reading_minutes": 30,
        "region_bias": 0.5,
    },
]


def _load_articles() -> list[ArticleRecord]:
    cache_path = Path("data/cache/articles.json")
    fallback_path = Path("data/fallback_articles.json")
    paths = [cache_path, fallback_path]
    for path in paths:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            articles = [ArticleRecord.model_validate(row) for row in data]
            if articles:
                return articles
        except Exception:
            continue
    raise RuntimeError("no articles available in cache or fallback")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    articles = _load_articles()
    store = get_store()
    today = dt.date.today()
    start = today - dt.timedelta(days=13)
    latest_ayesha = None

    for config in DEMO_READERS:
        profile = Profile(
            reader_id=config["reader_id"],
            display_name=config["display_name"],
            topic_weights=config["topic_weights"],
            reading_minutes=config["reading_minutes"],
            region_bias=config["region_bias"],
        )
        store.save_profile(profile)

        for offset in range(14):
            edition_date = start + dt.timedelta(days=offset)
            issue_no = offset + 1
            rng = random.Random(edition_date.toordinal())
            sample_size = max(1, int(round(len(articles) * 0.7)))
            sample_size = min(sample_size, len(articles))
            sample = rng.sample(articles, sample_size)
            edition = build_edition(profile, sample, edition_date, issue_no)
            edition.meta = {"fallback": True, "demo_seed": True}
            store.save_edition(edition)
            if profile.reader_id == "demo-ayesha" and edition_date == today:
                latest_ayesha = edition

    if latest_ayesha is None:
        raise RuntimeError("latest demo-ayesha edition was not built")

    payload = latest_ayesha.model_dump(mode="json")
    _write_json(Path("frontend/public/sample-edition.json"), payload)
    _write_json(Path("docs/samples/sample-edition.json"), payload)
    print("Seeded 3 readers x 14 editions")


if __name__ == "__main__":
    main()
