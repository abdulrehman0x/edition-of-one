#!/usr/bin/env python3
"""Generate the full 'Edition of One' monorepo scaffold in the current directory.

Run:  python generate_scaffold.py
Creates every file listed in the hackathon brief. Idempotent (safe to re-run).
"""
from __future__ import annotations

from pathlib import Path


DIRS: list[str] = [
    "pdf_generator",
    "data/cache",
    "frontend/public",
    "docs/samples",
]

MAKEFILE = (
    "export PYTHONPATH=backend:.\n"
    "\n"
    ".PHONY: setup snapshot seed verify api test demo\n"
    "\n"
    "setup:\n"
    "\tpip install -r backend/requirements.txt\n"
    "\n"
    "snapshot:\n"
    "\tpython -m pipelines.snapshot_feeds\n"
    "\n"
    "seed:\n"
    "\tpython -m pipelines.seed_demo\n"
    "\n"
    "verify:\n"
    "\tpython -m pipelines.verify_cache\n"
    "\n"
    "api:\n"
    "\tuvicorn app.main:app --app-dir backend --reload --port 8000\n"
    "\n"
    "test:\n"
    "\tpytest backend/tests -q\n"
    "\n"
    "demo: seed verify api\n"
)

FILES: dict[str, str] = {
    # ---- 1. skeleton ----
    ".gitignore": r""".env
.env.*
!.env.example
node_modules/
__pycache__/
*.py[cod]
.next/
out/
.venv/
.pytest_cache/
.DS_Store
*.log
""",

    # ---- 2. Makefile ----
    "Makefile": MAKEFILE,

    # ---- 3. docker ----
    "docker-compose.yml": r"""services:
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./data:/app/data
      - ./pdf_generator:/app/pdf_generator

  # web:
  #   image: node:20
  #   working_dir: /app/frontend
  #   command: npm run dev
  #   ports:
  #     - "3000:3000"
  #   depends_on:
  #     - api
""",

    "backend/Dockerfile": r"""FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir -r backend/requirements.txt

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--app-dir", "backend", "--host", "0.0.0.0", "--port", "8000"]
""",

    # ---- 4. requirements ----
    "backend/requirements.txt": r"""fastapi
uvicorn[standard]
pydantic>=2
httpx
feedparser
trafilatura
json-repair
qrcode[pil]
pillow
weasyprint
jinja2
numpy
scikit-learn
edge-tts
pydub
supabase
python-dotenv
pytest
pyyaml
""",

    # ---- 5. env example ----
    ".env.example": r"""LLM_OFFLINE=1
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
STORE=file
SUPABASE_URL=
SUPABASE_KEY=
PUBLIC_BASE_URL=http://localhost:8000
DEMO_CITY=Islamabad
DEMO_LAT=33.68
DEMO_LON=73.05
""",

    # ---- 6. supabase migration ----
    "supabase/migrations/001_init.sql": r"""create extension if not exists vector;

create table if not exists readers (
    id uuid primary key default gen_random_uuid(),
    display_name text not null default '',
    interests_text text not null default '',
    topic_weights jsonb not null default '{}'::jsonb,
    topic_stats jsonb not null default '{}'::jsonb,
    reading_minutes int not null default 15,
    region_bias real not null default 0.5,
    tone text not null default 'brief',
    watch_entities jsonb not null default '[]'::jsonb,
    centroid vector(384),
    created_at timestamptz not null default now()
);

create table if not exists sources (
    id serial primary key,
    name text not null,
    feed_url text not null unique,
    topic text not null default 'world',
    enabled boolean not null default true
);

create table if not exists articles (
    id text primary key,
    source_id integer references sources(id),
    url text not null unique,
    title text not null default '',
    body text not null default '',
    image_url text,
    published_at timestamptz,
    topic text not null default 'world',
    importance real not null default 0.5,
    brief text not null default '',
    cluster_id text,
    embedding vector(384),
    fetched_at timestamptz not null default now()
);

create table if not exists editions (
    id uuid primary key default gen_random_uuid(),
    reader_id uuid not null references readers(id) on delete cascade,
    edition_date date not null,
    doc jsonb not null,
    pdf_url text,
    audio_url text,
    unique (reader_id, edition_date)
);

create table if not exists events (
    id bigserial primary key,
    reader_id uuid not null references readers(id) on delete cascade,
    article_id text,
    edition_date date,
    type text not null check (type in ('impression','click','skip','dwell','thumb_up','thumb_down','save','pdf_open')),
    value real not null default 0.0,
    slot text not null default '',
    created_at timestamptz not null default now()
);

create index if not exists articles_embedding_ivfflat_idx
    on articles using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create index if not exists events_reader_created_idx
    on events (reader_id, created_at);
""",

    # ---- 7. contract ----
    "docs/CONTRACT.md": r"""# schemas.py
```python
from __future__ import annotations
import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field

Topic = Literal['world','pakistan','politics','business','markets','technology','ai','science','space','health','sport','cricket','football','culture','film_music','education','climate','startups','opinion']
Slot = Literal['lead','secondary','feature','standard','brief']
EventType = Literal['impression','click','skip','dwell','thumb_up','thumb_down','save','pdf_open']

class ArticleRecord(BaseModel):
    id: str; url: str; title: str; body: str = ''; source: str
    topic: Topic = 'world'; image_url: Optional[str] = None
    published_at: Optional[dt.datetime] = None; importance: float = 0.5
    cluster_id: Optional[str] = None; brief: str = ''

class Body(BaseModel):
    short: str; medium: str; long: str

class Art(BaseModel):
    id: str; headline: str; deck: str = ''; body: Body
    source: str; url: str; tracked_url: str = ''
    image: Optional[str] = None; topic: Topic; slot: Slot
    why: str = ''; outside_bubble: bool = False
    importance: float = 0.5; cluster_id: Optional[str] = None
    published_at: Optional[dt.datetime] = None; qr_svg: Optional[str] = None

class Weather(BaseModel):
    city: str; hi: int; lo: int; sky: str
class Section(BaseModel):
    name: str; items: list[Art] = Field(default_factory=list)
class Front(BaseModel):
    lead: Art; secondary: list[Art] = Field(default_factory=list); briefs: list[Art] = Field(default_factory=list)
class QuizQ(BaseModel):
    q: str; options: list[str]; answer_index: int; explain: str = ''
class WordSearch(BaseModel):
    size: int; grid: list[str]; words: list[str]
class MarketRow(BaseModel):
    label: str; value: str; change_pct: Optional[float] = None
class OnThisDay(BaseModel):
    year: int; text: str
class BackPage(BaseModel):
    quiz: list[QuizQ] = Field(default_factory=list); word_search: Optional[WordSearch] = None
    markets: list[MarketRow] = Field(default_factory=list); on_this_day: list[OnThisDay] = Field(default_factory=list)
class GalleryRow(BaseModel):
    source: str; url: str; headline: str; emphasis: str = ''
class PressGallery(BaseModel):
    topic_label: str; agreed_facts: list[str] = Field(default_factory=list)
    rows: list[GalleryRow] = Field(default_factory=list)
    only_in_one: list[dict] = Field(default_factory=list); open_question: str = ''
class Chapter(BaseModel):
    story_id: str; title: str; start_sec: float

class Edition(BaseModel):
    date: dt.date; issue_no: int; reader_id: str; reader_name: str; tagline: str = ''
    weather: Optional[Weather] = None; editors_note: str = ''
    front: Front; sections: list[Section] = Field(default_factory=list)
    back_page: BackPage = Field(default_factory=BackPage)
    press_gallery: Optional[PressGallery] = None
    audio_url: Optional[str] = None; audio_script: str = ''; chapters: list[Chapter] = Field(default_factory=list)
    pdf_url: Optional[str] = None; meta: dict = Field(default_factory=dict)

class Profile(BaseModel):
    reader_id: str; display_name: str = ''; interests_text: str = ''
    topic_weights: dict[str, float] = Field(default_factory=dict)
    topic_stats: dict[str, dict[str, float]] = Field(default_factory=dict)
    reading_minutes: int = 15; region_bias: float = 0.5
    tone: Literal['brief','deep'] = 'brief'; watch_entities: list[str] = Field(default_factory=list)
    centroid: list[float] = Field(default_factory=list)

class Event(BaseModel):
    reader_id: str; type: EventType; article_id: Optional[str] = None
    edition_date: Optional[dt.date] = None; value: float = 0.0; slot: str = ''
    ts: Optional[dt.datetime] = None
```

# REST contract

| Method | Path | Body / Query | Returns |
|---|---|---|---|
| POST | `/onboarding` | `{display_name, interests_text, tiles:list[str], reading_minutes, tone, region_bias}` | `{reader_id, profile}` |
| GET | `/edition/today?reader_id=` | query `reader_id` | `Edition` (build if missing; never fail: fall back to newest cached edition) |
| GET | `/edition/{date}?reader_id=` | query `reader_id` | `Edition` |
| GET | `/archive?reader_id=&q=` | query `reader_id`, `q` | `[{date, issue_no, lead_headline}]` newest first, `q` filters headlines |
| GET | `/edition/{date}/pdf?reader_id=` | query `reader_id` | `application/pdf` |
| GET | `/edition/{date}/audio?reader_id=` | query `reader_id` | `audio/mpeg` |
| POST | `/events` | `{events:list[Event]}` | `{accepted:int}` |
| GET | `/profile?reader_id=` | query `reader_id` | `{profile, deltas:{topic:float}}` |
| PATCH | `/profile` | `{reader_id, forget_topics:list[str]}` | `profile` |
| GET | `/r/{article_id}?reader_id=&to=` | query `reader_id`, `to` | `302` to `to`, logs a click |
| POST | `/dev/advance-day?reader_id=` | query `reader_id` | `{new_edition_date}` |
| GET | `/health` | none | `{status:'ok', offline:bool}` |
""",

    # ---- 8. Pydantic models ----
    "backend/app/models/schemas.py": r"""from __future__ import annotations
import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field

Topic = Literal['world','pakistan','politics','business','markets','technology','ai','science','space','health','sport','cricket','football','culture','film_music','education','climate','startups','opinion']
Slot = Literal['lead','secondary','feature','standard','brief']
EventType = Literal['impression','click','skip','dwell','thumb_up','thumb_down','save','pdf_open']

class ArticleRecord(BaseModel):
    id: str; url: str; title: str; body: str = ''; source: str
    topic: Topic = 'world'; image_url: Optional[str] = None
    published_at: Optional[dt.datetime] = None; importance: float = 0.5
    cluster_id: Optional[str] = None; brief: str = ''

class Body(BaseModel):
    short: str; medium: str; long: str

class Art(BaseModel):
    id: str; headline: str; deck: str = ''; body: Body
    source: str; url: str; tracked_url: str = ''
    image: Optional[str] = None; topic: Topic; slot: Slot
    why: str = ''; outside_bubble: bool = False
    importance: float = 0.5; cluster_id: Optional[str] = None
    published_at: Optional[dt.datetime] = None; qr_svg: Optional[str] = None

class Weather(BaseModel):
    city: str; hi: int; lo: int; sky: str
class Section(BaseModel):
    name: str; items: list[Art] = Field(default_factory=list)
class Front(BaseModel):
    lead: Art; secondary: list[Art] = Field(default_factory=list); briefs: list[Art] = Field(default_factory=list)
class QuizQ(BaseModel):
    q: str; options: list[str]; answer_index: int; explain: str = ''
class WordSearch(BaseModel):
    size: int; grid: list[str]; words: list[str]
class MarketRow(BaseModel):
    label: str; value: str; change_pct: Optional[float] = None
class OnThisDay(BaseModel):
    year: int; text: str
class BackPage(BaseModel):
    quiz: list[QuizQ] = Field(default_factory=list); word_search: Optional[WordSearch] = None
    markets: list[MarketRow] = Field(default_factory=list); on_this_day: list[OnThisDay] = Field(default_factory=list)
class GalleryRow(BaseModel):
    source: str; url: str; headline: str; emphasis: str = ''
class PressGallery(BaseModel):
    topic_label: str; agreed_facts: list[str] = Field(default_factory=list)
    rows: list[GalleryRow] = Field(default_factory=list)
    only_in_one: list[dict] = Field(default_factory=list); open_question: str = ''
class Chapter(BaseModel):
    story_id: str; title: str; start_sec: float

class Edition(BaseModel):
    date: dt.date; issue_no: int; reader_id: str; reader_name: str; tagline: str = ''
    weather: Optional[Weather] = None; editors_note: str = ''
    front: Front; sections: list[Section] = Field(default_factory=list)
    back_page: BackPage = Field(default_factory=BackPage)
    press_gallery: Optional[PressGallery] = None
    audio_url: Optional[str] = None; audio_script: str = ''; chapters: list[Chapter] = Field(default_factory=list)
    pdf_url: Optional[str] = None; meta: dict = Field(default_factory=dict)

class Profile(BaseModel):
    reader_id: str; display_name: str = ''; interests_text: str = ''
    topic_weights: dict[str, float] = Field(default_factory=dict)
    topic_stats: dict[str, dict[str, float]] = Field(default_factory=dict)
    reading_minutes: int = 15; region_bias: float = 0.5
    tone: Literal['brief','deep'] = 'brief'; watch_entities: list[str] = Field(default_factory=list)
    centroid: list[float] = Field(default_factory=list)

class Event(BaseModel):
    reader_id: str; type: EventType; article_id: Optional[str] = None
    edition_date: Optional[dt.date] = None; value: float = 0.0; slot: str = ''
    ts: Optional[dt.datetime] = None
""",

    # ---- 9. store ----
    "backend/app/core/store.py": r"""from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Optional, Protocol

from app.models.schemas import ArticleRecord, Edition, Event, Profile


def _as_aware(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


class Store(Protocol):
    def list_articles(self) -> list[ArticleRecord]:
        raise NotImplementedError

    def save_articles(self, articles: list[ArticleRecord]) -> None:
        raise NotImplementedError

    def get_profile(self, reader_id: str) -> Optional[Profile]:
        raise NotImplementedError

    def save_profile(self, profile: Profile) -> None:
        raise NotImplementedError

    def list_profiles(self) -> list[Profile]:
        raise NotImplementedError

    def get_edition(self, reader_id: str, edition_date: dt.date) -> Optional[Edition]:
        raise NotImplementedError

    def save_edition(self, edition: Edition) -> None:
        raise NotImplementedError

    def list_editions(self, reader_id: str) -> list[Edition]:
        raise NotImplementedError

    def add_events(self, events: list[Event]) -> None:
        raise NotImplementedError

    def list_events(self, reader_id: str, since: Optional[dt.datetime] = None) -> list[Event]:
        raise NotImplementedError


class FileStore:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or os.getenv("DATA_CACHE_DIR", "data/cache"))

    def _articles_path(self) -> Path:
        return self.root / "articles.json"

    def _profiles_dir(self) -> Path:
        return self.root / "profiles"

    def _profile_path(self, reader_id: str) -> Path:
        return self._profiles_dir() / f"{reader_id}.json"

    def _editions_dir(self, reader_id: str) -> Path:
        return self.root / "editions" / reader_id

    def _edition_path(self, reader_id: str, edition_date: dt.date) -> Path:
        return self._editions_dir(reader_id) / f"{edition_date.isoformat()}.json"

    def _events_path(self, reader_id: str) -> Path:
        return self.root / "events" / f"{reader_id}.jsonl"

    def _read_json(self, path: Path):
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_json(self, path: Path, data) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_articles(self) -> list[ArticleRecord]:
        data = self._read_json(self._articles_path())
        if not isinstance(data, list):
            return []
        articles: list[ArticleRecord] = []
        for row in data:
            try:
                articles.append(ArticleRecord.model_validate(row))
            except Exception:
                continue
        return articles

    def save_articles(self, articles: list[ArticleRecord]) -> None:
        self._write_json(
            self._articles_path(),
            [article.model_dump(mode="json") for article in articles],
        )

    def get_profile(self, reader_id: str) -> Optional[Profile]:
        data = self._read_json(self._profile_path(reader_id))
        if not isinstance(data, dict):
            return None
        try:
            return Profile.model_validate(data)
        except Exception:
            return None

    def save_profile(self, profile: Profile) -> None:
        self._write_json(self._profile_path(profile.reader_id), profile.model_dump(mode="json"))

    def list_profiles(self) -> list[Profile]:
        profiles: list[Profile] = []
        directory = self._profiles_dir()
        if not directory.exists():
            return profiles
        for path in sorted(directory.glob("*.json")):
            data = self._read_json(path)
            if not isinstance(data, dict):
                continue
            try:
                profiles.append(Profile.model_validate(data))
            except Exception:
                continue
        return profiles

    def get_edition(self, reader_id: str, edition_date: dt.date) -> Optional[Edition]:
        data = self._read_json(self._edition_path(reader_id, edition_date))
        if not isinstance(data, dict):
            return None
        try:
            return Edition.model_validate(data)
        except Exception:
            return None

    def save_edition(self, edition: Edition) -> None:
        self._write_json(
            self._edition_path(edition.reader_id, edition.date),
            edition.model_dump(mode="json"),
        )

    def list_editions(self, reader_id: str) -> list[Edition]:
        editions: list[Edition] = []
        directory = self._editions_dir(reader_id)
        if not directory.exists():
            return editions
        for path in directory.glob("*.json"):
            data = self._read_json(path)
            if not isinstance(data, dict):
                continue
            try:
                editions.append(Edition.model_validate(data))
            except Exception:
                continue
        editions.sort(key=lambda edition: edition.date, reverse=True)
        return editions

    def add_events(self, events: list[Event]) -> None:
        for event in events:
            path = self._events_path(event.reader_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def list_events(self, reader_id: str, since: Optional[dt.datetime] = None) -> list[Event]:
        path = self._events_path(reader_id)
        if not path.exists():
            return []
        events: list[Event] = []
        since_aware = _as_aware(since) if since is not None else None
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = Event.model_validate(json.loads(line))
            except Exception:
                continue
            if since_aware is not None:
                if event.ts is None:
                    continue
                if _as_aware(event.ts) < since_aware:
                    continue
            events.append(event)
        return events


class SupabaseStore:
    def __init__(self, url: str, key: str) -> None:
        from supabase import create_client

        self.client = create_client(url, key)
        self.fallback = FileStore()

    def _profile_from_row(self, row: dict) -> Profile:
        return Profile(
            reader_id=str(row["id"]),
            display_name=row.get("display_name", "") or "",
            interests_text=row.get("interests_text", "") or "",
            topic_weights=row.get("topic_weights") or {},
            topic_stats=row.get("topic_stats") or {},
            reading_minutes=int(row.get("reading_minutes", 15) or 15),
            region_bias=float(row.get("region_bias", 0.5) or 0.5),
            tone=row.get("tone", "brief") or "brief",
            watch_entities=row.get("watch_entities") or [],
            centroid=row.get("centroid") or [],
        )

    def list_articles(self) -> list[ArticleRecord]:
        try:
            response = self.client.table("articles").select("*").execute()
            articles: list[ArticleRecord] = []
            for row in response.data or []:
                articles.append(
                    ArticleRecord(
                        id=str(row["id"]),
                        url=row["url"],
                        title=row.get("title", "") or "",
                        body=row.get("body", "") or "",
                        source=row.get("source", "Supabase") or "Supabase",
                        topic=row.get("topic", "world") or "world",
                        image_url=row.get("image_url"),
                        published_at=row.get("published_at"),
                        importance=float(row.get("importance", 0.5) or 0.5),
                        cluster_id=row.get("cluster_id"),
                        brief=row.get("brief", "") or "",
                    )
                )
            return articles
        except Exception:
            return self.fallback.list_articles()

    def save_articles(self, articles: list[ArticleRecord]) -> None:
        try:
            rows = [
                {
                    "id": article.id,
                    "url": article.url,
                    "title": article.title,
                    "body": article.body,
                    "image_url": article.image_url,
                    "published_at": article.published_at.isoformat() if article.published_at else None,
                    "topic": article.topic,
                    "importance": article.importance,
                    "brief": article.brief,
                    "cluster_id": article.cluster_id,
                }
                for article in articles
            ]
            self.client.table("articles").upsert(rows).execute()
        except Exception:
            self.fallback.save_articles(articles)

    def get_profile(self, reader_id: str) -> Optional[Profile]:
        try:
            response = self.client.table("readers").select("*").eq("id", reader_id).limit(1).execute()
            rows = response.data or []
            if not rows:
                return None
            return self._profile_from_row(rows[0])
        except Exception:
            return self.fallback.get_profile(reader_id)

    def save_profile(self, profile: Profile) -> None:
        try:
            row = {
                "id": profile.reader_id,
                "display_name": profile.display_name,
                "interests_text": profile.interests_text,
                "topic_weights": profile.topic_weights,
                "topic_stats": profile.topic_stats,
                "reading_minutes": profile.reading_minutes,
                "region_bias": profile.region_bias,
                "tone": profile.tone,
                "watch_entities": profile.watch_entities,
                "centroid": profile.centroid,
            }
            self.client.table("readers").upsert(row).execute()
        except Exception:
            self.fallback.save_profile(profile)

    def list_profiles(self) -> list[Profile]:
        try:
            response = self.client.table("readers").select("*").execute()
            return [self._profile_from_row(row) for row in response.data or []]
        except Exception:
            return self.fallback.list_profiles()

    def get_edition(self, reader_id: str, edition_date: dt.date) -> Optional[Edition]:
        try:
            response = (
                self.client.table("editions")
                .select("*")
                .eq("reader_id", reader_id)
                .eq("edition_date", edition_date.isoformat())
                .limit(1)
                .execute()
            )
            rows = response.data or []
            if not rows:
                return None
            return Edition.model_validate(rows[0]["doc"])
        except Exception:
            return self.fallback.get_edition(reader_id, edition_date)

    def save_edition(self, edition: Edition) -> None:
        try:
            row = {
                "reader_id": edition.reader_id,
                "edition_date": edition.date.isoformat(),
                "doc": edition.model_dump(mode="json"),
                "pdf_url": edition.pdf_url,
                "audio_url": edition.audio_url,
            }
            self.client.table("editions").upsert(row, on_conflict="reader_id,edition_date").execute()
        except Exception:
            self.fallback.save_edition(edition)

    def list_editions(self, reader_id: str) -> list[Edition]:
        try:
            response = (
                self.client.table("editions")
                .select("doc")
                .eq("reader_id", reader_id)
                .order("edition_date", desc=True)
                .execute()
            )
            return [Edition.model_validate(row["doc"]) for row in response.data or []]
        except Exception:
            return self.fallback.list_editions(reader_id)

    def add_events(self, events: list[Event]) -> None:
        if not events:
            return
        try:
            rows = [
                {
                    "reader_id": event.reader_id,
                    "article_id": event.article_id,
                    "edition_date": event.edition_date.isoformat() if event.edition_date else None,
                    "type": event.type,
                    "value": event.value,
                    "slot": event.slot,
                }
                for event in events
            ]
            self.client.table("events").insert(rows).execute()
        except Exception:
            self.fallback.add_events(events)

    def list_events(self, reader_id: str, since: Optional[dt.datetime] = None) -> list[Event]:
        try:
            query = self.client.table("events").select("*").eq("reader_id", reader_id)
            if since is not None:
                query = query.gte("created_at", _as_aware(since).isoformat())
            response = query.order("created_at").execute()
            events: list[Event] = []
            for row in response.data or []:
                events.append(
                    Event(
                        reader_id=str(row["reader_id"]),
                        type=row["type"],
                        article_id=row.get("article_id"),
                        edition_date=row.get("edition_date"),
                        value=float(row.get("value", 0.0) or 0.0),
                        slot=row.get("slot", "") or "",
                        ts=row.get("created_at"),
                    )
                )
            return events
        except Exception:
            return self.fallback.list_events(reader_id, since)


def get_store() -> Store:
    if os.getenv("STORE", "file").lower() == "supabase":
        try:
            url = os.getenv("SUPABASE_URL", "")
            key = os.getenv("SUPABASE_KEY", "")
            if url and key:
                return SupabaseStore(url, key)
        except Exception:
            pass
    return FileStore()
""",

    # ---- 10. fallback editor ----
    "backend/app/services/fallback_editor.py": r"""from __future__ import annotations

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
""",

    # ---- 11. feeds ----
    "pipelines/feeds.yaml": r"""feeds:
  - name: BBC World
    url: https://feeds.bbci.co.uk/news/world/rss.xml
    topic: world
  - name: BBC Technology
    url: https://feeds.bbci.co.uk/news/technology/rss.xml
    topic: technology
  - name: BBC Science
    url: https://feeds.bbci.co.uk/news/science_and_environment/rss.xml
    topic: science
  - name: BBC Business
    url: https://feeds.bbci.co.uk/news/business/rss.xml
    topic: business
  - name: BBC Health
    url: https://feeds.bbci.co.uk/news/health/rss.xml
    topic: health
  - name: BBC Sport
    url: https://feeds.bbci.co.uk/sport/rss.xml
    topic: sport
  - name: Al Jazeera
    url: https://www.aljazeera.com/xml/rss/all.xml
    topic: world
  - name: Dawn
    url: https://www.dawn.com/feeds/home
    topic: pakistan
  - name: Express Tribune
    url: https://tribune.com.pk/feed/home
    topic: pakistan
  - name: Ars Technica
    url: https://feeds.arstechnica.com/arstechnica/index
    topic: technology
  - name: Hacker News
    url: https://hnrss.org/frontpage
    topic: technology
  - name: TechCrunch
    url: https://techcrunch.com/feed/
    topic: startups
  - name: MIT Technology Review
    url: https://www.technologyreview.com/feed/
    topic: ai
  - name: NASA
    url: https://www.nasa.gov/rss/dyn/breaking_news.rss
    topic: space
  - name: ESPNcricinfo
    url: https://www.espncricinfo.com/rss/content/story/feeds/0.xml
    topic: cricket
  - name: Guardian Culture
    url: https://www.theguardian.com/culture/rss
    topic: culture
  - name: Guardian Climate
    url: https://www.theguardian.com/environment/climate-crisis/rss
    topic: climate
""",

    # ---- 12. snapshot script ----
    "pipelines/snapshot_feeds.py": r"""from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import html
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import feedparser
import httpx
import trafilatura
import yaml

from app.models.schemas import ArticleRecord

USER_AGENT = "EditionOfOneBot/1.0 (offline hackathon snapshot; contact: local)"
TIMEOUT_SECONDS = 10.0
HOST_DELAY_SECONDS = 0.5


def _clean_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _summary_text(entry: Any) -> str:
    return _clean_html(entry.get("summary") or entry.get("description") or "")


def _entry_image(entry: Any, article_html: str) -> str | None:
    for key in ("media_content", "media_thumbnail"):
        for item in entry.get(key, []) or []:
            if isinstance(item, dict) and item.get("url"):
                return str(item["url"])
    for enclosure in entry.get("enclosures", []) or []:
        href = enclosure.get("href")
        if href and "image" in (enclosure.get("type") or ""):
            return str(href)
    for link in entry.get("links", []) or []:
        href = link.get("href")
        if href and link.get("rel") == "enclosure" and "image" in (link.get("type") or ""):
            return str(href)
    summary = entry.get("summary") or entry.get("description") or ""
    match = re.search(r"<img[^>]+src=[\"']([^\"']+)", summary, re.IGNORECASE)
    if match:
        return html.unescape(match.group(1))
    match = re.search(
        r"<meta[^>]+property=[\"']og:image[\"'][^>]+content=[\"']([^\"']+)",
        article_html or "",
        re.IGNORECASE,
    )
    if match:
        return html.unescape(match.group(1))
    return None


def _published_at(entry: Any) -> dt.datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        return dt.datetime(*parsed[:6], tzinfo=dt.timezone.utc)
    except Exception:
        return None


def _article_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]


async def _polite_get(client: httpx.AsyncClient, url: str, last_by_host: dict[str, float]) -> httpx.Response:
    host = urlparse(url).netloc
    now = time.monotonic()
    elapsed = now - last_by_host.get(host, 0.0)
    if elapsed < HOST_DELAY_SECONDS:
        await asyncio.sleep(HOST_DELAY_SECONDS - elapsed)
    response = await client.get(url)
    last_by_host[host] = time.monotonic()
    return response


def _extract_body(article_html: str, summary: str) -> str:
    extracted = trafilatura.extract(article_html, include_comments=False, include_tables=False) or ""
    extracted = extracted.strip()
    if len(extracted.split()) < 80 and summary:
        return summary.strip()
    return extracted


async def _process_feed(
    client: httpx.AsyncClient,
    feed: dict[str, str],
    last_by_host: dict[str, float],
) -> tuple[str, str, int, int, str, list[ArticleRecord]]:
    name = feed["name"]
    url = feed["url"]
    topic = feed["topic"]
    articles: list[ArticleRecord] = []
    try:
        response = await _polite_get(client, url, last_by_host)
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        entries = list(parsed.entries)[:8]
        for entry in entries:
            link = entry.get("link")
            if not link:
                continue
            try:
                article_response = await _polite_get(client, link, last_by_host)
                article_response.raise_for_status()
                article_html = article_response.text
            except Exception:
                article_html = ""
            summary = _summary_text(entry)
            body = _extract_body(article_html, summary)
            image_url = _entry_image(entry, article_html)
            words = len(body.split())
            importance = 0.4 + 0.1 * (1 if image_url else 0) + 0.1 * (1 if words > 300 else 0)
            articles.append(
                ArticleRecord(
                    id=_article_id(link),
                    url=link,
                    title=_clean_html(entry.get("title") or ""),
                    body=body,
                    source=name,
                    topic=topic,
                    image_url=image_url,
                    published_at=_published_at(entry),
                    importance=min(1.0, max(0.0, importance)),
                    brief=summary[:400],
                )
            )
        return name, topic, len(entries), len(articles), "ok", articles
    except Exception as exc:
        return name, topic, 0, 0, f"failed: {exc}", articles


async def _main() -> None:
    cache_path = Path("data/cache/articles.json")
    fallback_path = Path("data/fallback_articles.json")
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(Path("pipelines/feeds.yaml").read_text(encoding="utf-8"))
    feeds = config.get("feeds", [])
    last_by_host: dict[str, float] = {}
    all_articles: list[ArticleRecord] = []
    rows: list[tuple[str, str, int, int, str]] = []

    async with httpx.AsyncClient(
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    ) as client:
        for feed in feeds:
            name, topic, entry_count, article_count, status, articles = await _process_feed(client, feed, last_by_host)
            rows.append((name, topic, entry_count, article_count, status))
            all_articles.extend(articles)

    print(f"{'feed':26} {'topic':12} {'entries':>8} {'articles':>9} status")
    print("-" * 78)
    for name, topic, entry_count, article_count, status in rows:
        print(f"{name[:26]:26} {topic[:12]:12} {entry_count:8d} {article_count:9d} {status}")

    if len(all_articles) < 20:
        print("WARNING: fewer than 20 live articles; copying synthetic fallback pool into data/cache/articles.json")
        shutil.copyfile(fallback_path, cache_path)
        return

    cache_path.write_text(
        json.dumps([article.model_dump(mode="json") for article in all_articles], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(all_articles)} articles to {cache_path}")


if __name__ == "__main__":
    asyncio.run(_main())
""",

    # ---- 13. synthetic fallback pool ----
    "data/fallback_articles.json": r"""[
  {"id":"demo-0001","url":"https://example.org/demo/1","title":"[Demo] A community group shares a general update","body":"A community group shared a general update about everyday routines and local cooperation. The note described small changes in schedules, shared resources, and the value of clear communication. It did not report a specific event or name any person. Readers were invited to consider how ordinary systems support daily life and how careful planning can help people adapt.","source":"Demo Wire","topic":"world","image_url":null,"published_at":"2024-01-01T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A generic synthetic update about routines, cooperation, and planning."},
  {"id":"demo-0002","url":"https://example.org/demo/2","title":"[Demo] Local planning note describes shared resources","body":"A local planning note described shared resources and simple coordination. The text focused on routine choices, clear schedules, and practical communication. It avoided specific claims and did not identify any organization. The note suggested that small improvements can make daily systems easier to understand. It also encouraged readers to think about how ordinary decisions affect groups over time.","source":"Demo Wire","topic":"pakistan","image_url":null,"published_at":"2024-01-02T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic planning note about coordination and shared resources."},
  {"id":"demo-0003","url":"https://example.org/demo/3","title":"[Demo] Discussion guide outlines ordinary civic habits","body":"A discussion guide outlined ordinary civic habits and respectful conversation. The material described listening, asking clear questions, and checking assumptions. It did not mention a real campaign or public figure. Instead, it offered general examples of how groups can compare views and make room for disagreement. The guide ended with a simple prompt about improving everyday communication.","source":"Demo Wire","topic":"politics","image_url":"https://example.org/demo/image/3.jpg","published_at":"2024-01-03T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic guide about listening and civic conversation habits."},
  {"id":"demo-0004","url":"https://example.org/demo/4","title":"[Demo] Small business note emphasizes clear records","body":"A small business note emphasized clear records and steady routines. It described generic practices such as reviewing schedules, tracking simple costs, and keeping communication direct. No real company or market result was mentioned. The note suggested that reliable habits can reduce confusion during busy periods. It closed with a reminder to review assumptions before making changes.","source":"Demo Wire","topic":"business","image_url":null,"published_at":"2024-01-04T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic business note about records and routines."},
  {"id":"demo-0005","url":"https://example.org/demo/5","title":"[Demo] Tool review describes everyday digital hygiene","body":"A tool review described everyday digital hygiene in general terms. It covered password habits, backup routines, and the value of reading settings carefully. The review did not evaluate a real product. It used simple examples to explain why consistency matters more than complexity. Readers were encouraged to test changes on a small scale before relying on them.","source":"Demo Wire","topic":"technology","image_url":"https://example.org/demo/image/5.jpg","published_at":"2024-01-05T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic technology note about basic digital hygiene."},
  {"id":"demo-0006","url":"https://example.org/demo/6","title":"[Demo] AI primer explains checking outputs","body":"An AI primer explained the importance of checking outputs and asking clear questions. The text described general patterns in automated tools without naming a real system. It recommended comparing results, reviewing assumptions, and keeping human judgment in the loop. The primer also noted that simple explanations can help teams discuss tradeoffs before adopting new workflows.","source":"Demo Wire","topic":"ai","image_url":null,"published_at":"2024-01-06T00:00:00Z","importance":0.7,"cluster_id":null,"brief":"A synthetic AI primer about outputs, assumptions, and review."},
  {"id":"demo-0007","url":"https://example.org/demo/7","title":"[Demo] Science explainer describes careful observation","body":"A science explainer described careful observation and repeatable steps. It used a generic example of comparing notes and recording small changes. No real experiment or finding was reported. The explainer emphasized patience, clear language, and the difference between a guess and a tested claim. It ended by suggesting that good questions often matter as much as answers.","source":"Demo Wire","topic":"science","image_url":null,"published_at":"2024-01-07T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic science explainer about observation and repeatability."},
  {"id":"demo-0008","url":"https://example.org/demo/8","title":"[Demo] Space club note describes night-sky routines","body":"A space club note described night-sky routines and simple observation habits. It mentioned checking weather, letting eyes adjust, and keeping a small log. No real mission or celestial event was named. The note focused on patience and shared learning. It also suggested that beginner groups benefit from clear checklists and a comfortable pace.","source":"Demo Wire","topic":"space","image_url":"https://example.org/demo/image/8.jpg","published_at":"2024-01-08T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic space club note about observation routines."},
  {"id":"demo-0009","url":"https://example.org/demo/9","title":"[Demo] Health desk shares general rest checklist","body":"A health desk shared a general rest checklist for everyday routines. The list mentioned breaks, hydration, and consistent sleep habits. It did not offer medical advice or describe a real study. The note encouraged readers to notice patterns and consult qualified professionals for personal concerns. It stressed simple language and realistic expectations.","source":"Demo Wire","topic":"health","image_url":null,"published_at":"2024-01-09T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic health checklist about rest and everyday habits."},
  {"id":"demo-0010","url":"https://example.org/demo/10","title":"[Demo] Sports club outlines practice planning","body":"A sports club outlined practice planning in general terms. The note described warmups, clear goals, and balanced schedules. It did not report a match or name a team. Coaches were encouraged to keep instructions short and to review progress over time. The club also emphasized safety, rest, and inclusive participation for different experience levels.","source":"Demo Wire","topic":"sport","image_url":"https://example.org/demo/image/10.jpg","published_at":"2024-01-10T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic sports note about practice planning and safety."},
  {"id":"demo-0011","url":"https://example.org/demo/11","title":"[Demo] Cricket practice note focuses on basics","body":"A cricket practice note focused on basics and steady improvement. It described warmups, repeated drills, and clear communication between players. No real player or result was mentioned. The note suggested that simple routines help groups stay organized. It also reminded readers to balance effort with rest and to keep sessions inclusive.","source":"Demo Wire","topic":"cricket","image_url":null,"published_at":"2024-01-11T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic cricket note about drills, communication, and rest."},
  {"id":"demo-0012","url":"https://example.org/demo/12","title":"[Demo] Culture notebook describes shared reading","body":"A culture notebook described shared reading and small discussion groups. The note mentioned choosing a theme, keeping sessions short, and inviting different interpretations. It did not review a real book or exhibition. The aim was to show how culture can support conversation and careful listening. It ended with a simple prompt for future gatherings.","source":"Demo Wire","topic":"culture","image_url":"https://example.org/demo/image/12.jpg","published_at":"2024-01-12T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic culture note about shared reading and discussion."},
  {"id":"demo-0013","url":"https://example.org/demo/13","title":"[Demo] Climate guide describes everyday adaptation","body":"A climate guide described everyday adaptation in general terms. It covered planning for changing routines, reducing waste, and checking local resources. No real policy or event was named. The guide encouraged readers to start with small steps and review what works. It also noted that clear communication helps groups respond to uncertainty together.","source":"Demo Wire","topic":"climate","image_url":null,"published_at":"2024-01-13T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic climate guide about small adaptation steps."},
  {"id":"demo-0014","url":"https://example.org/demo/14","title":"[Demo] Startup diary outlines early experiments","body":"A startup diary outlined early experiments and simple validation. The note described asking users clear questions, testing a small feature, and reviewing results. It did not mention a real company or funding event. The diary emphasized learning quickly and writing down assumptions. It also encouraged founders to keep scope small and communication direct.","source":"Demo Wire","topic":"startups","image_url":null,"published_at":"2024-01-14T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic startup note about experiments and validation."},
  {"id":"demo-0015","url":"https://example.org/demo/15","title":"[Demo] World desk shares a general context note","body":"A world desk shared a general context note about everyday cooperation. The text described clear communication, shared schedules, and respect for different viewpoints. It did not report a real event or location. The note encouraged readers to separate observation from assumption. It closed with a reminder that context can change how people understand the same situation.","source":"Demo Wire","topic":"world","image_url":null,"published_at":"2024-01-15T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic world note about context and cooperation."},
  {"id":"demo-0016","url":"https://example.org/demo/16","title":"[Demo] Product team note describes usability checks","body":"A product team note described usability checks and simple feedback loops. It mentioned observing routine tasks, asking open questions, and noting confusion points. No real product was named. The note suggested that small tests can reveal more than large assumptions. It encouraged teams to document findings and share them in plain language.","source":"Demo Wire","topic":"technology","image_url":"https://example.org/demo/image/16.jpg","published_at":"2024-01-16T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic product note about usability and feedback."},
  {"id":"demo-0017","url":"https://example.org/demo/17","title":"[Demo] Research circle explains note keeping","body":"A research circle explained note keeping and careful comparison. The note described writing down steps, checking assumptions, and reviewing differences. It did not describe a real study or result. The circle emphasized clear records and humble language. It also suggested that small, repeatable checks can help groups avoid jumping to conclusions.","source":"Demo Wire","topic":"science","image_url":null,"published_at":"2024-01-17T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic research note about records and comparison."},
  {"id":"demo-0018","url":"https://example.org/demo/18","title":"[Demo] Wellness desk shares a general routine note","body":"A wellness desk shared a general routine note about pacing and balance. It mentioned breaks, movement, and clear daily priorities. It did not give medical advice or describe a real condition. The note encouraged readers to notice small changes and seek qualified guidance when needed. It used plain language and avoided promises.","source":"Demo Wire","topic":"health","image_url":null,"published_at":"2024-01-18T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic wellness note about pacing and balance."},
  {"id":"demo-0019","url":"https://example.org/demo/19","title":"[Demo] Market notebook describes careful comparison","body":"A market notebook described careful comparison and basic record keeping. It mentioned reviewing categories, checking dates, and writing down assumptions. No real price or company was named. The note focused on habits that support clear thinking. It also suggested that readers ask what a number measures before drawing conclusions.","source":"Demo Wire","topic":"business","image_url":null,"published_at":"2024-01-19T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic market note about comparison and record keeping."},
  {"id":"demo-0020","url":"https://example.org/demo/20","title":"[Demo] Arts desk describes a simple workshop plan","body":"An arts desk described a simple workshop plan for small groups. The note mentioned warmup exercises, shared materials, and short reflection breaks. It did not review a real artist or performance. The plan emphasized participation and clear instructions. It ended with a suggestion to keep the first session small and adjust based on feedback.","source":"Demo Wire","topic":"culture","image_url":"https://example.org/demo/image/20.jpg","published_at":"2024-01-20T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic arts note about a small workshop plan."},
  {"id":"demo-0021","url":"https://example.org/demo/21","title":"[Demo] AI notebook describes prompt review habits","body":"An AI notebook described prompt review habits and clear expectations. It mentioned checking instructions, comparing outputs, and noting uncertainty. No real model or service was named. The note encouraged users to keep examples simple and to review results before sharing them. It also suggested documenting what worked and what needed correction.","source":"Demo Wire","topic":"ai","image_url":null,"published_at":"2024-01-21T00:00:00Z","importance":0.6,"cluster_id":null,"brief":"A synthetic AI note about prompt review and uncertainty."},
  {"id":"demo-0022","url":"https://example.org/demo/22","title":"[Demo] Climate notebook describes local checklists","body":"A climate notebook described local checklists and small planning steps. It mentioned reviewing seasonal routines, sharing resources, and keeping messages clear. No real event or policy was named. The notebook encouraged groups to start with practical actions and review them over time. It also noted that trust grows through consistent communication.","source":"Demo Wire","topic":"climate","image_url":null,"published_at":"2024-01-22T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic climate note about local checklists and planning."},
  {"id":"demo-0023","url":"https://example.org/demo/23","title":"[Demo] City desk shares a general coordination note","body":"A city desk shared a general coordination note about everyday services and communication. It described clear schedules, shared information, and simple feedback. It did not report a real municipal event. The note encouraged readers to consider how small process changes affect daily life. It closed with a prompt about improving clarity without adding complexity.","source":"Demo Wire","topic":"pakistan","image_url":null,"published_at":"2024-01-23T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic city note about coordination and clarity."},
  {"id":"demo-0024","url":"https://example.org/demo/24","title":"[Demo] Sky watchers share a simple observation log","body":"Sky watchers shared a simple observation log and general viewing checklist. The note mentioned timing, weather, and comfortable equipment. It did not name a real mission or object. The group emphasized patience and shared learning. It also suggested keeping expectations modest and recording what was actually seen rather than what was expected.","source":"Demo Wire","topic":"space","image_url":null,"published_at":"2024-01-24T00:00:00Z","importance":0.5,"cluster_id":null,"brief":"A synthetic sky-watching note about logs and patience."}
]
""",

    # ---- 14. seed script ----
    "pipelines/seed_demo.py": r"""from __future__ import annotations

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
""",

    # ---- 15. verify script ----
    "pipelines/verify_cache.py": r"""from __future__ import annotations

import sys

from app.core.store import get_store
from app.models.schemas import Edition

READER_IDS = ["demo-ayesha", "demo-bilal", "demo-sara"]


def main() -> None:
    store = get_store()
    failures: list[str] = []
    rows: list[tuple[str, int, str, int]] = []

    for reader_id in READER_IDS:
        editions = store.list_editions(reader_id)
        try:
            validated = [Edition.model_validate(edition.model_dump()) for edition in editions]
        except Exception as exc:
            failures.append(f"{reader_id}: validation failed: {exc}")
            continue
        if len(validated) != 14:
            failures.append(f"{reader_id}: expected 14 editions, found {len(validated)}")
        if not validated:
            failures.append(f"{reader_id}: no editions")
            continue
        lead = validated[0].front.lead
        if not lead.id or not lead.headline:
            failures.append(f"{reader_id}: empty lead")
        if not any(section.items for section in validated[0].sections):
            failures.append(f"{reader_id}: no non-empty sections")
        dates = [edition.date for edition in validated]
        if len(set(dates)) != len(dates):
            failures.append(f"{reader_id}: duplicate edition dates")
        rows.append((reader_id, len(validated), validated[0].date.isoformat(), len(validated[0].sections)))

    print(f"{'reader':12} {'editions':>8} {'latest':>12} {'sections':>8}")
    print("-" * 44)
    for reader_id, count, latest, sections in rows:
        print(f"{reader_id:12} {count:8d} {latest:>12} {sections:8d}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        sys.exit(1)

    print("OK: 3 readers x 14 editions valid")


if __name__ == "__main__":
    main()
""",

    # ---- 16. tests ----
    "backend/tests/test_fallback_editor.py": r"""from __future__ import annotations

import datetime as dt

import pytest

from app.models.schemas import ArticleRecord, Edition, Profile
from app.services.fallback_editor import build_edition


def _article(
    article_id: str,
    title: str,
    topic: str = "world",
    body: str = "One sentence here. Another sentence follows. A third sentence closes the note.",
    importance: float = 0.5,
) -> ArticleRecord:
    return ArticleRecord(
        id=article_id,
        url=f"https://example.org/{article_id}",
        title=title,
        body=body,
        source="Test Wire",
        topic=topic,
        importance=importance,
    )


def _profile(**kwargs) -> Profile:
    data = {"reader_id": "reader-test", "display_name": "Tester", "topic_weights": {"world": 0.5}}
    data.update(kwargs)
    return Profile(**data)


def _all_ids(edition: Edition) -> list[str]:
    ids = [edition.front.lead.id]
    ids.extend(article.id for article in edition.front.secondary)
    ids.extend(article.id for article in edition.front.briefs)
    for section in edition.sections:
        ids.extend(article.id for article in section.items)
    return ids


def test_zero_weights() -> None:
    profile = _profile(topic_weights={})
    articles = [_article(f"a{i}", f"Story number {i}") for i in range(10)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id


def test_three_articles() -> None:
    profile = _profile()
    articles = [_article(f"a{i}", f"Three story {i}") for i in range(3)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id
    assert len(_all_ids(edition)) >= 3


def test_empty_bodies() -> None:
    profile = _profile()
    articles = [
        ArticleRecord(
            id=f"empty{i}",
            url=f"https://example.org/empty{i}",
            title=f"Empty body story {i}",
            body="",
            brief="",
            source="Test Wire",
            topic="world",
        )
        for i in range(6)
    ]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    assert edition.front.lead.id


def test_no_articles_raises() -> None:
    profile = _profile()
    with pytest.raises(ValueError, match="no articles"):
        build_edition(profile, [], dt.date(2024, 1, 1), 1)


def test_near_duplicates_removed() -> None:
    profile = _profile()
    articles = [
        _article("a1", "This is a very similar title about the same topic"),
        _article("a2", "This is a very similar title about the same topic"),
        _article("a3", "Completely different story about something else entirely"),
        _article("a4", "Another story about cats and their daily habits"),
    ]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    ids = _all_ids(edition)
    assert "a1" in ids
    assert "a2" not in ids


def test_output_validates_against_edition() -> None:
    profile = _profile()
    articles = [_article(f"v{i}", f"Validation story {i}") for i in range(6)]
    edition = build_edition(profile, articles, dt.date(2024, 1, 1), 1)
    Edition.model_validate(edition.model_dump())
""",

    # ---- package __init__ files ----
    "backend/app/__init__.py": "",
    "backend/app/core/__init__.py": "",
    "backend/app/models/__init__.py": "",
    "backend/app/services/__init__.py": "",
    "backend/tests/__init__.py": "",
    "pipelines/__init__.py": "",
}


def main() -> None:
    for directory in DIRS:
        Path(directory).mkdir(parents=True, exist_ok=True)
    for path, content in FILES.items():
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        print(f"wrote {path}")
    print(f"\nDone: {len(FILES)} files, {len(DIRS)} directories")


if __name__ == "__main__":
    main()