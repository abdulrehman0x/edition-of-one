from __future__ import annotations

import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.models.schemas import ArticleRecord, Profile, Weather  # noqa: E402
from app.services.fallback_editor import build_edition  # noqa: E402
from app.services.widgets import weather_for  # noqa: E402

PROFILE_SPECS = [
    {
        "reader_id": "demo-ayesha",
        "name": "Ayesha",
        "topics": ["pakistan", "politics", "education", "world"],
        "weights": {"pakistan": 1.0, "politics": 0.9, "education": 0.8, "world": 0.6},
        "location": "Islamabad",
    },
    {
        "reader_id": "demo-bilal",
        "name": "Bilal",
        "topics": ["business", "markets", "technology", "startups", "ai"],
        "weights": {"business": 1.0, "markets": 0.9, "technology": 0.8,
                     "startups": 0.7, "ai": 0.7},
        "location": "Karachi",
    },
    {
        "reader_id": "demo-sara",
        "name": "Sara",
        "topics": ["cricket", "sport", "culture", "film_music", "science", "space"],
        "weights": {"cricket": 1.0, "sport": 0.8, "culture": 0.7,
                     "film_music": 0.7, "science": 0.6, "space": 0.6},
        "location": "Lahore",
    },
]

SAMPLE_SIZE = 20


def _finish(edition, profile, weather: dict, date_str: str) -> None:
    edition.front.weather = Weather(**weather)
    edition.dateline = f"{profile.location} \u2014 {date_str}"


def main() -> None:
    store = get_store()
    fb_path = ROOT / "data/fallback_articles.json"
    raw = json.loads(fb_path.read_text(encoding="utf-8"))
    articles = [ArticleRecord(**a) for a in raw]

    random.seed(42)

    for spec in PROFILE_SPECS:
        profile = Profile(tone="neutral", outside_bubble_ratio=0.15, **spec)
        store.put(f"profiles/{profile.reader_id}", profile.model_dump())
        weather = weather_for(profile.location)  # one lookup per reader (cached)
        for i in range(14):
            d = (date.today() - timedelta(days=i)).isoformat()
            sample = random.sample(articles, k=min(len(articles), SAMPLE_SIZE))
            edition = build_edition(profile.reader_id, d, sample, profile)
            _finish(edition, profile, weather, d)
            store.put(f"editions/{profile.reader_id}/{d}", edition.model_dump())
        print(f"  seeded {profile.reader_id}: 14 editions")

    sample_profile = Profile(tone="neutral", outside_bubble_ratio=0.15, **PROFILE_SPECS[0])
    sample_date = date.today().isoformat()
    sample = random.sample(articles, k=min(len(articles), SAMPLE_SIZE))
    sample_ed = build_edition(sample_profile.reader_id, sample_date, sample, sample_profile)
    _finish(sample_ed, sample_profile, weather_for(sample_profile.location), sample_date)

    out_dir = ROOT / "frontend/public"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "sample-edition.json").write_text(
        json.dumps(sample_ed.model_dump(), indent=2, default=str),
        encoding="utf-8",
    )
    print("  wrote frontend/public/sample-edition.json")


if __name__ == "__main__":
    main()
