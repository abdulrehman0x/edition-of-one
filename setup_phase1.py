#!/usr/bin/env python3
"""setup_phase1.py — Bootstraps the Edition of One monorepo (Phase 1).

Run:    python setup_phase1.py            (skips files that already exist)
        python setup_phase1.py --force    (overwrites everything)
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FORCE = "--force" in sys.argv


def write(rel: str, content: str) -> None:
    p = ROOT / rel
    if p.exists() and not FORCE:
        print(f"  keep  {rel} (exists; use --force to overwrite)")
        return
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content.lstrip("\n"), encoding="utf-8")
    print(f"  wrote {rel}")


def D(s: str) -> str:
    return textwrap.dedent(s)


DIRS = [
    "backend/app/core",
    "backend/app/models",
    "backend/app/services",
    "backend/app/api",
    "backend/tests",
    "backend/prompts",
    "pdf_generator/templates",
    "pdf_generator/static/fonts",
    "pipelines",
    "supabase/migrations",
    "docs",
    "data/cache",
    "data/llm_cache",
    "frontend/public",
]

print("Creating Edition of One Phase 1 structure...")
for d in DIRS:
    (ROOT / d).mkdir(parents=True, exist_ok=True)
    print(f"  dir  {d}")

# ---------------------------------------------------------------------------
# 1. backend/requirements.txt
# ---------------------------------------------------------------------------
write(
    "backend/requirements.txt",
    D(
        """\
fastapi
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
# optional, only used when LLM_OFFLINE=0 (falls back to hashing embeddings):
# sentence-transformers
"""
    ),
)

# ---------------------------------------------------------------------------
# 2. backend/Dockerfile
# ---------------------------------------------------------------------------
write(
    "backend/Dockerfile",
    D(
        """\
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \\
    libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b \\
    libffi-dev fonts-dejavu-core \\
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY backend/prompts /app/prompts
COPY pdf_generator /app/pdf_generator
COPY pipelines /app/pipelines
COPY data/fallback_articles.json /app/data/fallback_articles.json

# config.py resolves data/ relative to APP_ROOT (inside the image the file
# lives at /app/app/core, so the parents[3] heuristic would point at "/").
ENV APP_ROOT=/app
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""
    ),
)

# ---------------------------------------------------------------------------
# 3. docker-compose.yml
# ---------------------------------------------------------------------------
write(
    "docker-compose.yml",
    D(
        """\
services:
  api:
    build:
      context: .
      dockerfile: backend/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./pdf_generator:/app/pdf_generator
    environment:
      - LLM_OFFLINE=${LLM_OFFLINE:-1}
    env_file:
      - path: .env
        required: false

  # web:
  #   image: node:20
  #   working_dir: /app
  #   ports:
  #     - "3000:3000"
  #   volumes:
  #     - ./frontend:/app
  #   command: ["npm", "run", "dev"]
"""
    ),
)

# ---------------------------------------------------------------------------
# 4. Makefile
# ---------------------------------------------------------------------------
makefile_lines = [
    "PYTHON ?= python",
    "export PYTHONPATH=backend:.",
    "",
    ".PHONY: setup snapshot seed verify api test demo pdf pdfcheck",
    "",
    "setup:",
    "\t$(PYTHON) -m pip install -r backend/requirements.txt",
    "",
    "snapshot:",
    "\t$(PYTHON) pipelines/snapshot_feeds.py",
    "",
    "seed:",
    "\t$(PYTHON) pipelines/seed_demo.py",
    "",
    "verify:",
    "\t$(PYTHON) pipelines/verify_cache.py",
    "",
    "api:",
    "\tuvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend",
    "",
    "test:",
    "\tpytest backend/tests",
    "",
    "demo:",
    "\t$(PYTHON) pipelines/seed_demo.py && $(PYTHON) pipelines/verify_cache.py",
    "",
    "pdf:",
    "\t$(PYTHON) pdf_generator/render.py --all-demo",
    "",
    "pdfcheck:",
    "\t$(PYTHON) pdf_generator/render.py --all-demo --check",
    "",
]
write("Makefile", "\n".join(makefile_lines))

# ---------------------------------------------------------------------------
# 5. .env.example
# ---------------------------------------------------------------------------
write(
    ".env.example",
    D(
        """\
LLM_OFFLINE=1
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
# /dev/* endpoints (including DELETE /dev/reset). Set to 0 in any deployment.
ENABLE_DEV=1
# Optional overrides:
# APP_ROOT=
# CACHE_DIR=
# LLM_CACHE_DIR=
"""
    ),
)

# ---------------------------------------------------------------------------
# 6. .gitignore  (data/cache/ is tracked on purpose, except volatile files)
# ---------------------------------------------------------------------------
write(
    ".gitignore",
    D(
        """\
.env
node_modules/
__pycache__/
*.pyc
.next/
out/
data/llm_cache/
data/pdfs/
data/cache/weather_*.json
frontend/node_modules/
"""
    ),
)

# ---------------------------------------------------------------------------
# 7. supabase/migrations/001_init.sql
# ---------------------------------------------------------------------------
write(
    "supabase/migrations/001_init.sql",
    D(
        """\
create extension if not exists vector;

-- Generic key/value table used by SupabaseStore.
create table if not exists kv (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz default now()
);

create table if not exists readers (
  id text primary key,
  name text not null,
  profile jsonb not null default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists sources (
  id text primary key,
  name text not null,
  url text not null,
  topics text[] default '{}',
  created_at timestamptz default now()
);

create table if not exists articles (
  id text primary key,
  source_id text references sources(id) on delete set null,
  title text not null,
  url text,
  body text,
  topics text[] default '{}',
  published_at timestamptz,
  embedding vector(384),
  created_at timestamptz default now()
);

create table if not exists editions (
  id text primary key,
  reader_id text references readers(id) on delete cascade,
  date date not null,
  payload jsonb not null,
  created_at timestamptz default now()
);

create table if not exists events (
  id bigserial primary key,
  reader_id text references readers(id) on delete cascade,
  article_id text,
  event_type text not null,
  value double precision default 1.0,
  created_at timestamptz default now()
);

create index if not exists articles_embedding_idx
  on articles using ivfflat (embedding vector_cosine_ops) with (lists = 100);
"""
    ),
)

# ---------------------------------------------------------------------------
# 8a. docs/CONTRACT.md
# ---------------------------------------------------------------------------
write(
    "docs/CONTRACT.md",
    D(
        """\
# Edition of One — Data Contract (Phase 1)

All wire formats are Pydantic v2 models defined in
`backend/app/models/schemas.py`.

## Enums

- `Topic` — one of: world, pakistan, politics, business, markets, technology, ai,
  science, space, health, sport, cricket, football, culture, film_music,
  education, climate, startups, opinion.
- `Slot` — lead | secondary | feature | standard | brief.
- `EventType` — impression | click | skip | dwell | thumb_up | thumb_down |
  save | pdf_open.

## Models

- `ArticleRecord` {id, title, url, source, source_id, topics, published_at,
  body: Body, art: Art, importance}
- `Body` {short, medium, long}
- `Art` {kind, url, caption, alt}
- `Weather` {city, temp_c, condition, high_c, low_c}
- `Section` {name, slug, articles}
- `Front` {lead, secondary, briefs, weather, quote}
- `QuizQ` {question, options, answer}
- `WordSearch` {grid, words}
- `MarketRow` {symbol, price, change_pct}
- `OnThisDay` {year, text}
- `BackPage` {quiz, word_search, on_this_day}
- `GalleryRow` {title, url, caption}
- `PressGallery` {rows}
- `Chapter` {title, articles, slot}
- `Edition` {id, reader_id, date, nameplate, dateline, front, sections,
  back_page, press_gallery, chapters, outside_bubble}
- `Profile` {reader_id, name, topics, weights, location, tone,
  outside_bubble_ratio}
- `Event` {reader_id, article_id, event_type, value, ts}

## Storage

- `FileStore` keeps JSON at `data/cache/<key>.json` (keys are sanitised).
- `SupabaseStore` uses the `kv` table in `supabase/migrations/001_init.sql`;
  silently degrades to `FileStore` on connection error.

## Endpoints

App entry point: `app.main:app` (re-exports `app.api.main:app`).

- `GET  /health`
- `POST /onboarding`
- `GET  /edition/{reader_id}?date=YYYY-MM-DD|today`
- `GET  /archive/{reader_id}`
- `POST /events`
- `GET  /profile/{reader_id}`
- `GET  /dev/readers`          (only when ENABLE_DEV=1)
- `DELETE /dev/reset`          (only when ENABLE_DEV=1)
"""
    ),
)

# ---------------------------------------------------------------------------
# 8b. backend/app/models/schemas.py
# ---------------------------------------------------------------------------
write(
    "backend/app/models/schemas.py",
    D(
        """\
from __future__ import annotations

from typing import Literal, Optional, List, Dict

from pydantic import BaseModel, Field

Topic = Literal[
    "world", "pakistan", "politics", "business", "markets", "technology",
    "ai", "science", "space", "health", "sport", "cricket", "football",
    "culture", "film_music", "education", "climate", "startups", "opinion",
]

Slot = Literal["lead", "secondary", "feature", "standard", "brief"]

EventType = Literal[
    "impression", "click", "skip", "dwell", "thumb_up",
    "thumb_down", "save", "pdf_open",
]


class Art(BaseModel):
    kind: Literal["image", "svg", "none"] = "none"
    url: Optional[str] = None
    caption: Optional[str] = None
    alt: Optional[str] = None


class Body(BaseModel):
    short: str = ""
    medium: str = ""
    long: str = ""


class ArticleRecord(BaseModel):
    id: str
    title: str
    url: str = ""
    source: str = ""
    source_id: str = ""
    topics: List[Topic] = Field(default_factory=list)
    published_at: Optional[str] = None
    body: Body = Field(default_factory=Body)
    art: Art = Field(default_factory=Art)
    importance: float = 0.5


class Weather(BaseModel):
    city: str = ""
    temp_c: Optional[float] = None
    condition: str = ""
    high_c: Optional[float] = None
    low_c: Optional[float] = None


class Section(BaseModel):
    name: str
    slug: str
    articles: List[ArticleRecord] = Field(default_factory=list)


class QuizQ(BaseModel):
    question: str
    options: List[str]
    answer: int = 0


class WordSearch(BaseModel):
    grid: List[str] = Field(default_factory=list)
    words: List[str] = Field(default_factory=list)


class MarketRow(BaseModel):
    symbol: str
    price: Optional[float] = None
    change_pct: Optional[float] = None


class OnThisDay(BaseModel):
    year: Optional[int] = None
    text: str = ""


class BackPage(BaseModel):
    quiz: List[QuizQ] = Field(default_factory=list)
    word_search: Optional[WordSearch] = None
    on_this_day: List[OnThisDay] = Field(default_factory=list)


class GalleryRow(BaseModel):
    title: str
    url: str = ""
    caption: str = ""


class PressGallery(BaseModel):
    rows: List[GalleryRow] = Field(default_factory=list)


class Front(BaseModel):
    lead: Optional[ArticleRecord] = None
    secondary: List[ArticleRecord] = Field(default_factory=list)
    briefs: List[ArticleRecord] = Field(default_factory=list)
    weather: Optional[Weather] = None
    quote: str = ""


class Chapter(BaseModel):
    title: str
    articles: List[ArticleRecord] = Field(default_factory=list)
    slot: Slot = "standard"


class Edition(BaseModel):
    id: str
    reader_id: str
    date: str
    nameplate: str = "Edition of One"
    dateline: str = ""
    front: Front = Field(default_factory=Front)
    sections: List[Section] = Field(default_factory=list)
    back_page: BackPage = Field(default_factory=BackPage)
    press_gallery: Optional[PressGallery] = None
    chapters: List[Chapter] = Field(default_factory=list)
    outside_bubble: List[ArticleRecord] = Field(default_factory=list)


class Profile(BaseModel):
    reader_id: str
    name: str = ""
    topics: List[Topic] = Field(default_factory=list)
    weights: Dict[str, float] = Field(default_factory=dict)
    location: str = ""
    tone: str = "neutral"
    outside_bubble_ratio: float = 0.15


class Event(BaseModel):
    reader_id: str
    article_id: Optional[str] = None
    event_type: EventType
    value: float = 1.0
    ts: Optional[str] = None
"""
    ),
)

# ---------------------------------------------------------------------------
# Package __init__ files
# ---------------------------------------------------------------------------
for pkg in [
    "backend/app/__init__.py",
    "backend/app/core/__init__.py",
    "backend/app/models/__init__.py",
    "backend/app/services/__init__.py",
    "backend/app/api/__init__.py",
]:
    write(pkg, "")

# Entry point used by the Makefile and the Dockerfile (app.main:app).
write(
    "backend/app/main.py",
    D(
        """\
from .api.main import app  # noqa: F401
"""
    ),
)

# ---------------------------------------------------------------------------
# 9. backend/app/core/store.py
# ---------------------------------------------------------------------------
write(
    "backend/app/core/store.py",
    D(
        """\
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional, Protocol, List


class Store(Protocol):
    def get(self, key: str) -> Optional[Any]: ...
    def put(self, key: str, value: Any) -> None: ...
    def list(self, prefix: str = "") -> List[str]: ...
    def delete(self, key: str) -> None: ...


class FileStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Whitelist characters so ids from the network can't escape root.
        safe = re.sub(r"[^A-Za-z0-9_./-]", "_", key.strip("/")).replace("..", "_")
        return self.root / f"{safe}.json"

    def get(self, key: str) -> Optional[Any]:
        p = self._path(key)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None

    def put(self, key: str, value: Any) -> None:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            json.dumps(value, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    def list(self, prefix: str = "") -> List[str]:
        base = self.root
        out: List[str] = []
        for p in base.rglob("*.json"):
            rel = p.relative_to(base).with_suffix("")
            key = str(rel).replace(os.sep, "/")
            if not prefix or key.startswith(prefix):
                out.append(key)
        return sorted(out)

    def delete(self, key: str) -> None:
        p = self._path(key)
        if p.exists():
            p.unlink()


class SupabaseStore:
    def __init__(self, url: str, key: str, cache_dir: str) -> None:
        self._fallback: Optional[FileStore] = None
        try:
            from supabase import create_client  # type: ignore
            self.client = create_client(url, key)
            # Probe the table we actually use, so a missing migration
            # degrades to FileStore instead of failing silently later.
            self.client.table("kv").select("key").limit(1).execute()
        except Exception:
            self.client = None
            self._fallback = FileStore(Path(cache_dir))

    def get(self, key: str) -> Optional[Any]:
        if self._fallback is not None:
            return self._fallback.get(key)
        try:
            res = self.client.table("kv").select("value").eq("key", key).execute()
            return res.data[0]["value"] if res.data else None
        except Exception:
            return None

    def put(self, key: str, value: Any) -> None:
        if self._fallback is not None:
            return self._fallback.put(key, value)
        try:
            self.client.table("kv").upsert({"key": key, "value": value}).execute()
        except Exception:
            pass

    def list(self, prefix: str = "") -> List[str]:
        if self._fallback is not None:
            return self._fallback.list(prefix)
        try:
            res = self.client.table("kv").select("key").like("key", f"{prefix}%").execute()
            return sorted(r["key"] for r in res.data)
        except Exception:
            return []

    def delete(self, key: str) -> None:
        if self._fallback is not None:
            return self._fallback.delete(key)
        try:
            self.client.table("kv").delete().eq("key", key).execute()
        except Exception:
            pass


def get_store() -> Store:
    from .config import get_settings
    s = get_settings()
    if s.store == "supabase" and s.supabase_url and s.supabase_key:
        return SupabaseStore(s.supabase_url, s.supabase_key, s.cache_dir)
    return FileStore(Path(s.cache_dir))
"""
    ),
)

# ---------------------------------------------------------------------------
# 13a. backend/app/core/config.py
# ---------------------------------------------------------------------------
write(
    "backend/app/core/config.py",
    D(
        """\
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# APP_ROOT lets containers (where this file is /app/app/core/config.py)
# point at the right directory; locally we derive the repo root.
ROOT = Path(os.environ.get("APP_ROOT") or Path(__file__).resolve().parents[3])


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@dataclass(frozen=True)
class Settings:
    llm_offline: int = 1
    llm_provider: str = "deepseek"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    store: str = "file"
    public_base_url: str = "http://localhost:8000"
    demo_city: str = "Islamabad"
    demo_lat: float = 33.68
    demo_lon: float = 73.05
    supabase_url: str = ""
    supabase_key: str = ""
    enable_dev: int = 1
    cache_dir: str = str(ROOT / "data/cache")
    llm_cache_dir: str = str(ROOT / "data/llm_cache")
    fallback_articles_path: str = str(ROOT / "data/fallback_articles.json")


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings(
            llm_offline=int(_env("LLM_OFFLINE", "1")),
            llm_provider=_env("LLM_PROVIDER", "deepseek"),
            deepseek_api_key=_env("DEEPSEEK_API_KEY", ""),
            deepseek_base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
            deepseek_model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
            store=_env("STORE", "file"),
            public_base_url=_env("PUBLIC_BASE_URL", "http://localhost:8000"),
            demo_city=_env("DEMO_CITY", "Islamabad"),
            demo_lat=float(_env("DEMO_LAT", "33.68")),
            demo_lon=float(_env("DEMO_LON", "73.05")),
            supabase_url=_env("SUPABASE_URL", ""),
            supabase_key=_env("SUPABASE_KEY", ""),
            enable_dev=int(_env("ENABLE_DEV", "1")),
            cache_dir=_env("CACHE_DIR", str(ROOT / "data/cache")),
            llm_cache_dir=_env("LLM_CACHE_DIR", str(ROOT / "data/llm_cache")),
            fallback_articles_path=_env(
                "FALLBACK_ARTICLES", str(ROOT / "data/fallback_articles.json")
            ),
        )
    return _settings
"""
    ),
)

# ---------------------------------------------------------------------------
# 13b. backend/app/core/llm.py
# ---------------------------------------------------------------------------
write(
    "backend/app/core/llm.py",
    r"""
from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from .config import get_settings


class CircuitBreaker:
    def __init__(self, threshold: int = 3, pause: float = 120.0) -> None:
        self.threshold = threshold
        self.pause = pause
        self.failures = 0
        self.open_until = 0.0

    def allow(self) -> bool:
        return time.time() >= self.open_until

    def success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = time.time() + self.pause


_breaker = CircuitBreaker()


def _cache_path(prompt: str, model: str) -> Path:
    key = hashlib.sha256(f"{model}::{prompt}".encode("utf-8")).hexdigest()
    p = Path(get_settings().llm_cache_dir) / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def repair_json(text: str) -> Any:
    '''Best-effort extraction of a JSON object/array from LLM output.'''
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:
        pass

    # Slice from the first { or [ to the last matching closer.
    starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
    candidate = t
    if starts:
        i = min(starts)
        closer = "}" if t[i] == "{" else "]"
        j = t.rfind(closer)
        if j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                pass
        candidate = t[i:]

    try:
        from json_repair import repair_json as _rj  # type: ignore
        got = json.loads(_rj(candidate))
        if isinstance(got, (dict, list)) and got:
            return got
    except Exception:
        pass
    return {}


async def complete(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> Optional[str]:
    s = get_settings()
    model = model or s.deepseek_model
    cache_key = prompt + f"::t={temperature}"
    cache = _cache_path(cache_key, model)
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8")).get("text")
        except Exception:
            pass
    if s.llm_offline == 1 or not s.deepseek_api_key:
        return None
    if not _breaker.allow():
        return None
    try:
        import httpx  # type: ignore
    except Exception:
        return None
    url = f"{s.deepseek_base_url.rstrip('/')}/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {s.deepseek_api_key}"}
    delay = 1.0
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            cache.write_text(json.dumps({"text": text}), encoding="utf-8")
            _breaker.success()
            return text
        except Exception:
            _breaker.failure()
            if attempt < 2:
                await asyncio.sleep(delay)
                delay *= 2.0
    return None


def complete_sync(prompt: str, **kw) -> Optional[str]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(complete(prompt, **kw))
    # Already inside an event loop: run in a worker thread.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(complete(prompt, **kw))).result()
"""
)

# ---------------------------------------------------------------------------
# 13c. backend/app/core/embeddings.py
# ---------------------------------------------------------------------------
write(
    "backend/app/core/embeddings.py",
    D(
        """\
from __future__ import annotations

from typing import List

from .config import get_settings

_model = None
_hv = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _get_hv():
    global _hv
    if _hv is None:
        from sklearn.feature_extraction.text import HashingVectorizer  # type: ignore
        _hv = HashingVectorizer(
            n_features=384, alternate_sign=False, norm="l2", lowercase=True
        )
    return _hv


def embed(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    s = get_settings()
    if s.llm_offline == 0:
        try:
            m = _get_model()
            out = m.encode(texts, normalize_embeddings=True)
            return [[float(x) for x in v] for v in out]
        except Exception:
            pass
    hv = _get_hv()
    X = hv.transform(texts)
    return [[float(x) for x in row] for row in X.toarray()]


def embed_one(text: str) -> List[float]:
    v = embed([text])
    return v[0] if v else []
"""
    ),
)

# ---------------------------------------------------------------------------
# 13d. backend/app/core/prompts.py
# ---------------------------------------------------------------------------
write(
    "backend/app/core/prompts.py",
    D(
        """\
from __future__ import annotations

from pathlib import Path
from typing import Dict


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


def load_template(name: str) -> str:
    p = _prompts_dir() / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def render(template_name: str, **vars: object) -> str:
    t = load_template(template_name)
    for k, v in vars.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def available() -> Dict[str, bool]:
    names = ["onboarding_profile.md", "curator.md", "copy.md"]
    return {n: (_prompts_dir() / n).exists() for n in names}
"""
    ),
)

# ---------------------------------------------------------------------------
# 14. Prompt templates
# ---------------------------------------------------------------------------
write(
    "backend/prompts/onboarding_profile.md",
    D(
        """\
You are building a personalized newspaper profile for a reader.

Reader self-description:
"{{description}}"

Return JSON with this shape ONLY:
{
  "topics": ["world", "pakistan", "technology"],
  "weights": {"world": 1.0, "pakistan": 0.8},
  "tone": "neutral",
  "outside_bubble_ratio": 0.15
}

Rules:
- topics must be drawn from the Topic enum.
- weights are 0.0–1.0.
- outside_bubble_ratio is 0.0–0.5.
- No prose, no markdown fences.
"""
    ),
)
write(
    "backend/prompts/curator.md",
    D(
        """\
You are the Curator for "Edition of One", a personalised broadsheet.

Reader profile: {{profile_json}}

Available articles (compact JSON): {{articles_json}}

Task: select and slot articles into a daily edition. Return JSON ONLY:
{
  "lead": "<article_id>",
  "secondary": ["<id>", "<id>"],
  "feature": ["<id>"],
  "sections": [{"name": "World", "slug": "world", "ids": ["<id>"]}],
  "outside_bubble": ["<id>"]
}

Rules:
- Do not invent ids.
- Respect reader topic weights.
- Leave 15% of slots for outside_bubble.
- No prose, no fences.
"""
    ),
)
write(
    "backend/prompts/copy.md",
    D(
        """\
You are a sub-editor for "Edition of One". Rewrite the article below as a
tight {{tone}} broadsheet extract. Keep every fact grounded in the source.

Source title: {{title}}
Source body: {{body}}

Return JSON ONLY:
{
  "short": "<= 35 words",
  "medium": "<= 60 words",
  "long": "<= 90 words"
}
"""
    ),
)

# ---------------------------------------------------------------------------
# 10. backend/app/services/fallback_editor.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/fallback_editor.py",
    r"""
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
"""
)

# ---------------------------------------------------------------------------
# 11a. pipelines/feeds.yaml
# ---------------------------------------------------------------------------
write(
    "pipelines/feeds.yaml",
    D(
        """\
feeds:
  - {name: "BBC World", url: "https://feeds.bbci.co.uk/news/world/rss.xml", topics: [world]}
  - {name: "BBC Business", url: "https://feeds.bbci.co.uk/news/business/rss.xml", topics: [business, markets]}
  - {name: "BBC Technology", url: "https://feeds.bbci.co.uk/news/technology/rss.xml", topics: [technology, ai]}
  - {name: "BBC Science", url: "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml", topics: [science, climate]}
  - {name: "BBC Health", url: "https://feeds.bbci.co.uk/news/health/rss.xml", topics: [health]}
  - {name: "BBC Sport", url: "https://feeds.bbci.co.uk/sport/rss.xml", topics: [sport]}
  - {name: "Reuters World", url: "https://www.reutersagency.com/feed/?best-topics=world", topics: [world, politics]}
  - {name: "Al Jazeera", url: "https://www.aljazeera.com/xml/rss/all.xml", topics: [world, politics]}
  - {name: "Dawn Pakistan", url: "https://www.dawn.com/feeds/home", topics: [pakistan, politics]}
  - {name: "The News Pakistan", url: "https://www.thenews.com.pk/rss/1/1", topics: [pakistan]}
  - {name: "ESPN Cricinfo", url: "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", topics: [cricket, sport]}
  - {name: "Guardian World", url: "https://www.theguardian.com/world/rss", topics: [world, politics]}
  - {name: "Guardian Culture", url: "https://www.theguardian.com/culture/rss", topics: [culture, film_music]}
  - {name: "Ars Technica", url: "https://feeds.arstechnica.com/arstechnica/index", topics: [technology, ai]}
  - {name: "NASA", url: "https://www.nasa.gov/rss/dyn/breaking_news.rss", topics: [space, science]}
  - {name: "Nature", url: "https://www.nature.com/nature.rss", topics: [science, health]}
  - {name: "TechCrunch", url: "https://techcrunch.com/feed/", topics: [startups, technology]}
"""
    ),
)

# ---------------------------------------------------------------------------
# 11b. data/fallback_articles.json — 24 synthetic records / 12 topics
# ---------------------------------------------------------------------------
import json as _json  # noqa: E402

_fb = [
    ("fb-001", "World leaders gather for climate summit", ["world", "climate"], 0.85,
     "Delegates from over 190 countries met to discuss emissions targets and financing for developing nations."),
    ("fb-002", "Diplomatic talks resume after border incident", ["world", "politics"], 0.7,
     "Negotiators from both sides returned to the table on Tuesday, seeking a de-escalation framework."),
    ("fb-003", "Pakistan unveils new economic reform package", ["pakistan", "business"], 0.8,
     "The finance ministry announced tax incentives and subsidy reforms aimed at stabilising the rupee."),
    ("fb-004", "Education reform expands access to rural schools", ["pakistan", "education"], 0.65,
     "A new federal programme will fund teacher training and infrastructure in underserved districts."),
    ("fb-005", "Parliament debates electoral reform bill", ["politics"], 0.75,
     "Lawmakers began a two-day debate on proposed changes to the electoral commission's oversight."),
    ("fb-006", "Election commission announces voter registration drive", ["politics"], 0.6,
     "The commission will launch a nationwide registration campaign ahead of next year's polls."),
    ("fb-007", "Local startup raises Series A to expand logistics", ["business", "startups"], 0.7,
     "The Karachi-based company plans to expand its same-day delivery network to five new cities."),
    ("fb-008", "Trade balance improves as exports rebound", ["business", "markets"], 0.65,
     "Exports rose 12% year-on-year, driven by textiles and information technology services."),
    ("fb-009", "Chip breakthrough promises faster devices", ["technology", "ai"], 0.8,
     "Researchers demonstrated a 2nm prototype transistor that could double battery life in phones."),
    ("fb-010", "Major cloud outage affects services worldwide", ["technology"], 0.75,
     "A configuration error at a leading cloud provider disrupted thousands of websites for hours."),
    ("fb-011", "New open-weight AI model released", ["ai", "technology"], 0.85,
     "The release includes a permissive license and benchmarks showing competitive performance."),
    ("fb-012", "Regulators propose AI transparency rules", ["ai", "politics"], 0.7,
     "Draft rules require model cards and training-data disclosures for systems above a size threshold."),
    ("fb-013", "Gene-editing trial shows early promise", ["science", "health"], 0.8,
     "A small clinical trial reported reduced symptoms in patients with a rare blood disorder."),
    ("fb-014", "Quantum computing milestone reported", ["science", "technology"], 0.75,
     "A research team reported error-corrected logical qubits sustaining coherence for longer periods."),
    ("fb-015", "New satellite launches to monitor climate", ["space", "climate"], 0.8,
     "The satellite will track atmospheric methane and carbon dioxide concentrations daily."),
    ("fb-016", "Lunar mission enters final preparation", ["space", "science"], 0.75,
     "Engineers completed the final integration test ahead of next month's launch window."),
    ("fb-017", "Vaccine trial reports strong immune response", ["health", "science"], 0.8,
     "The candidate vaccine elicited neutralising antibodies in all participants of the phase two trial."),
    ("fb-018", "Mental health initiative expands to schools", ["health", "education"], 0.6,
     "The programme trains teachers to identify early signs of anxiety and depression in students."),
    ("fb-019", "Cricket test ends in dramatic draw", ["cricket", "sport"], 0.7,
     "A last-wicket stand denied the visitors victory on a tense final day in Lahore."),
    ("fb-020", "Football league title race tightens", ["football", "sport"], 0.65,
     "A late winner lifted the challengers to within two points of the leaders with three games to play."),
    ("fb-021", "Film festival opens with local premiere", ["culture", "film_music"], 0.6,
     "The ten-day festival will screen over eighty films, including a strong regional selection."),
    ("fb-022", "New album blends classical and electronic", ["culture", "film_music"], 0.55,
     "The composer's latest record has drawn praise for its experimental textures and orchestration."),
    ("fb-023", "Heatwave grips southern provinces", ["climate", "pakistan"], 0.75,
     "Temperatures exceeded 45°C in several districts, prompting health advisories and emergency measures."),
    ("fb-024", "Glacier melt accelerates in northern regions", ["climate", "science"], 0.8,
     "Satellite data shows glaciers retreating faster than previously modelled, raising flood risks."),
]

_fb_objs = []
for _id, _title, _topics, _imp, _body in _fb:
    _fb_objs.append(
        {
            "id": _id,
            "title": _title,
            "url": "",
            "source": "Fallback Wire",
            "source_id": "fallback_wire",
            "topics": _topics,
            "published_at": "2025-01-01T00:00:00Z",
            "body": {"short": _body, "medium": _body, "long": _body},
            "art": {"kind": "none", "url": None, "caption": None, "alt": None},
            "importance": _imp,
        }
    )

write("data/fallback_articles.json", _json.dumps(_fb_objs, indent=2))

# ---------------------------------------------------------------------------
# 12a. pipelines/snapshot_feeds.py
# ---------------------------------------------------------------------------
write(
    "pipelines/snapshot_feeds.py",
    D(
        """\
from __future__ import annotations

import asyncio
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

try:
    import yaml  # type: ignore
    import httpx  # type: ignore
    import feedparser  # type: ignore
    import trafilatura  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"Missing dependency: {exc}. Run `make setup`.")
    sys.exit(0)

from app.core.store import get_store  # noqa: E402


def _stable_id(feed_name: str, link: str) -> str:
    # hash() is randomised per process; sha1 keeps ids stable across runs.
    digest = hashlib.sha1(link.encode("utf-8")).hexdigest()[:12]
    return f"{feed_name.lower().replace(' ', '_')}-{digest}"


async def fetch_one(client: "httpx.AsyncClient", feed: dict) -> list:
    try:
        r = await client.get(feed["url"], timeout=10.0, follow_redirects=True)
        parsed = feedparser.parse(r.text)
    except Exception as exc:
        print(f"  [skip] {feed['name']}: {exc}")
        return []

    results = []
    for entry in parsed.entries[:5]:
        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        if not title or not link:
            continue
        summary = entry.get("summary", "")
        body_text = summary
        try:
            rr = await client.get(link, timeout=10.0, follow_redirects=True)
            extracted = trafilatura.extract(rr.text)
            if extracted:
                body_text = extracted
        except Exception:
            pass
        results.append(
            {
                "id": _stable_id(feed["name"], link),
                "title": title,
                "url": link,
                "source": feed["name"],
                "source_id": feed["name"].lower().replace(" ", "_"),
                "topics": feed.get("topics", []),
                "published_at": entry.get("published", ""),
                "body": {
                    "short": body_text[:280],
                    "medium": body_text[:600],
                    "long": body_text[:1200],
                },
                "art": {"kind": "none", "url": None, "caption": None, "alt": None},
                "importance": 0.6,
            }
        )
    return results


async def main() -> None:
    feeds_path = HERE / "feeds.yaml"
    if not feeds_path.exists():
        print("feeds.yaml not found; nothing to snapshot.")
        return
    data = yaml.safe_load(feeds_path.read_text(encoding="utf-8")) or {}
    feeds = data.get("feeds", [])
    store = get_store()
    total = 0
    async with httpx.AsyncClient(headers={"User-Agent": "EditionOfOne/1.0"}) as client:
        for feed in feeds:
            arts = await fetch_one(client, feed)
            for a in arts:
                store.put(f"articles/{a['id']}", a)
            total += len(arts)
            print(f"  {feed['name']}: {len(arts)} articles")
    print(f"Snapshotted {total} articles total.")


if __name__ == "__main__":
    asyncio.run(main())
"""
    ),
)

# ---------------------------------------------------------------------------
# 12b. pipelines/seed_demo.py
# ---------------------------------------------------------------------------
write(
    "pipelines/seed_demo.py",
    D(
        """\
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
    edition.dateline = f"{profile.location} \\u2014 {date_str}"


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
"""
    ),
)

# ---------------------------------------------------------------------------
# 12c. pipelines/verify_cache.py
# ---------------------------------------------------------------------------
write(
    "pipelines/verify_cache.py",
    D(
        """\
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.models.schemas import Edition  # noqa: E402

READERS = ["demo-ayesha", "demo-bilal", "demo-sara"]


def main() -> None:
    store = get_store()
    ok = 0
    for reader in READERS:
        for i in range(14):
            d = (date.today() - timedelta(days=i)).isoformat()
            data = store.get(f"editions/{reader}/{d}")
            assert data is not None, f"missing edition for {reader} on {d}"
            ed = Edition(**data)
            assert ed.reader_id == reader, f"reader mismatch in {reader} {d}"
            assert ed.date == d, f"date mismatch in {reader} {d}"
            assert ed.front is not None, f"no front for {reader} {d}"
            assert ed.nameplate, f"missing nameplate in {reader} {d}"
            ok += 1
        print(f"  {reader}: 14 editions verified")
    print(f"Verified {ok} editions total.")


if __name__ == "__main__":
    main()
"""
    ),
)

# ---------------------------------------------------------------------------
# 15a. backend/app/services/ranker.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/ranker.py",
    D(
        """\
from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..models.schemas import ArticleRecord, Profile


class ThompsonBandit:
    def __init__(self) -> None:
        self.alpha: Dict[str, float] = {}
        self.beta: Dict[str, float] = {}

    def sample(self, topic: str) -> float:
        a = self.alpha.get(topic, 1.0)
        b = self.beta.get(topic, 1.0)
        return float(np.random.beta(a, b))

    def update(self, topic: str, reward: float) -> None:
        reward = max(0.0, min(1.0, reward))
        self.alpha[topic] = self.alpha.get(topic, 1.0) + reward
        self.beta[topic] = self.beta.get(topic, 1.0) + (1.0 - reward)


def cosine(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(va @ vb / (na * nb))


def cluster_cosine(vectors: List[List[float]], threshold: float = 0.85) -> List[int]:
    labels: List[int] = []
    centroids: List[List[float]] = []
    for v in vectors:
        assigned = -1
        for i, c in enumerate(centroids):
            if cosine(v, c) >= threshold:
                assigned = i
                break
        if assigned < 0:
            assigned = len(centroids)
            centroids.append(v)
        labels.append(assigned)
    return labels


def score_article(
    article: ArticleRecord,
    profile: Profile,
    bandit: Optional[ThompsonBandit] = None,
    category_counts: Optional[Dict[str, int]] = None,
    freshness: float = 1.0,
) -> float:
    relevance = 0.0
    if profile.weights:
        relevance = max((profile.weights.get(t, 0.0) for t in article.topics), default=0.0)
    if relevance == 0.0 and profile.topics:
        relevance = 0.2 if any(t in profile.topics for t in article.topics) else 0.05

    importance = float(article.importance)

    location = 1.0
    if profile.location:
        hay = (article.title + " " + article.body.short).lower()
        if profile.location.lower() in hay:
            location = 1.2

    exploration = 0.0
    if bandit is not None and article.topics:
        exploration = max(bandit.sample(t) for t in article.topics) * 0.1

    fatigue = 0.0
    if category_counts and article.topics:
        m = max(category_counts.get(t, 0) for t in article.topics)
        fatigue = min(1.0, m / 12.0) * 0.15

    return (
        0.45 * relevance
        + 0.25 * importance
        + 0.15 * freshness
        + 0.15 * location
        + exploration
        - fatigue
    )
"""
    ),
)

# ---------------------------------------------------------------------------
# 15b. backend/app/services/profile_service.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/profile_service.py",
    D(
        """\
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
    return re.search(r"\\b" + re.escape(word) + r"\\b", text) is not None


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
"""
    ),
)

# ---------------------------------------------------------------------------
# 15c. backend/app/services/guard.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/guard.py",
    r"""
from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple


def _numbers(text: str) -> Set[str]:
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", text or ""))


def _caps(text: str) -> Set[str]:
    '''Capitalised words that look like entities.

    Sentence-initial words are skipped: they are capitalised by grammar,
    not because they are names ("Inflation rose..." is not an entity).
    '''
    text = text or ""
    out: Set[str] = set()
    for m in re.finditer(r"\b[A-Z][a-zA-Z]{2,}\b", text):
        before = text[: m.start()].rstrip()
        if not before or before[-1] in ".!?":
            continue
        out.add(m.group(0))
    return out


def validate_grounding(
    claim: str,
    sources: List[str],
    allow_common: Optional[Set[str]] = None,
) -> Tuple[bool, List[str]]:
    allow_common = allow_common or set()
    problems: List[str] = []
    src_text = " ".join(sources or [])
    src_nums = _numbers(src_text)
    src_caps = _caps(src_text) | allow_common

    for n in _numbers(claim):
        if n not in src_nums:
            problems.append(f"number not grounded: {n}")

    for c in _caps(claim):
        if c in allow_common:
            continue
        if c not in src_caps:
            problems.append(f"entity not grounded: {c}")

    return (len(problems) == 0, problems)
"""
)

# ---------------------------------------------------------------------------
# 15d. backend/app/services/widgets.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/widgets.py",
    D(
        """\
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Optional

from ..core.config import get_settings

WEATHER_TTL = 3600

CITY_COORDS = {
    "islamabad": (33.68, 73.05),
    "rawalpindi": (33.60, 73.04),
    "karachi": (24.86, 67.01),
    "lahore": (31.55, 74.34),
    "peshawar": (34.01, 71.58),
    "quetta": (30.18, 66.99),
}


def _condition(code) -> str:
    try:
        c = int(code)
    except (TypeError, ValueError):
        return "unavailable"
    if c == 0:
        return "Clear"
    if c in (1, 2):
        return "Partly cloudy"
    if c == 3:
        return "Overcast"
    if c in (45, 48):
        return "Fog"
    if 51 <= c <= 67 or 80 <= c <= 82:
        return "Rain"
    if 71 <= c <= 77 or c in (85, 86):
        return "Snow"
    if c >= 95:
        return "Thunderstorm"
    return "Mixed"


def _cache_path(city: str) -> Path:
    s = get_settings()
    safe = "".join(ch if ch.isalnum() else "_" for ch in city.lower())
    return Path(s.cache_dir) / f"weather_{safe}.json"


def get_weather(city: str, lat: float, lon: float) -> Dict[str, Optional[object]]:
    # Blocking (urllib). Call from async code via asyncio.to_thread.
    cache = _cache_path(city)
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and time.time() - cache.stat().st_mtime < WEATHER_TTL:
        try:
            return json.loads(cache.read_text(encoding="utf-8"))
        except Exception:
            pass

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,weather_code"
        "&daily=temperature_2m_max,temperature_2m_min"
        "&timezone=auto"
    )
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = {
            "city": city,
            "temp_c": data.get("current", {}).get("temperature_2m"),
            "high_c": (data.get("daily", {}).get("temperature_2m_max") or [None])[0],
            "low_c": (data.get("daily", {}).get("temperature_2m_min") or [None])[0],
            "condition": _condition(data.get("current", {}).get("weather_code")),
        }
        cache.write_text(json.dumps(out), encoding="utf-8")
        return out
    except Exception:
        return {
            "city": city,
            "temp_c": None,
            "high_c": None,
            "low_c": None,
            "condition": "unavailable",
        }


def weather_for(city: str) -> Dict[str, Optional[object]]:
    # Weather for the reader's own city; unknown cities use the demo coords.
    s = get_settings()
    city = city or s.demo_city
    lat, lon = CITY_COORDS.get(city.strip().lower(), (s.demo_lat, s.demo_lon))
    return get_weather(city, lat, lon)
"""
    ),
)

# ---------------------------------------------------------------------------
# 15e. backend/app/services/curator.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/curator.py",
    D(
        """\
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
    edition.dateline = f"{city} \\u2014 {date_str}"
    return edition


async def curate(reader_id: str, date_str: str) -> Optional[Edition]:
    return await build_edition_async(reader_id, date_str)
"""
    ),
)

# ---------------------------------------------------------------------------
# 15f. backend/app/services/edition_service.py
# ---------------------------------------------------------------------------
write(
    "backend/app/services/edition_service.py",
    D(
        """\
from __future__ import annotations

import asyncio
from typing import Dict, Optional, Union

from ..core.store import get_store
from .curator import build_edition_async

_locks: Dict[str, asyncio.Lock] = {}


def _lock(reader_id: str) -> asyncio.Lock:
    if reader_id not in _locks:
        _locks[reader_id] = asyncio.Lock()
    return _locks[reader_id]


async def get_or_build_edition(
    reader_id: str, date: str
) -> Optional[Union[dict, object]]:
    store = get_store()
    key = f"editions/{reader_id}/{date}"
    cached = store.get(key)
    if cached:
        return cached
    async with _lock(reader_id):
        cached = store.get(key)
        if cached:
            return cached
        edition = await build_edition_async(reader_id, date)
        if edition is not None:
            payload = edition.model_dump() if hasattr(edition, "model_dump") else edition
            store.put(key, payload)
        return edition
"""
    ),
)

# ---------------------------------------------------------------------------
# 16. backend/app/api/*.py
# ---------------------------------------------------------------------------
write(
    "backend/app/api/onboarding.py",
    D(
        """\
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
    location: str = ""
    tone: str = "neutral"


@router.post("")
async def onboard(req: OnboardingRequest):
    profile = create_profile(req)
    get_store().put(f"profiles/{profile.reader_id}", profile.model_dump())
    return profile.model_dump()
"""
    ),
)

write(
    "backend/app/api/edition.py",
    D(
        """\
from __future__ import annotations

from datetime import date as _date

from fastapi import APIRouter, HTTPException

from ..services.edition_service import get_or_build_edition

router = APIRouter()


@router.get("/{reader_id}")
async def get_edition(reader_id: str, date: str = "today"):
    d = _date.today().isoformat() if date == "today" else date
    ed = await get_or_build_edition(reader_id, d)
    if ed is None:
        raise HTTPException(status_code=404, detail="No edition available")
    return ed.model_dump() if hasattr(ed, "model_dump") else ed
"""
    ),
)

write(
    "backend/app/api/archive.py",
    D(
        """\
from __future__ import annotations

from fastapi import APIRouter

from ..core.store import get_store

router = APIRouter()


@router.get("/{reader_id}")
async def archive(reader_id: str):
    store = get_store()
    keys = store.list(f"editions/{reader_id}/")
    dates = [k.split("/")[-1] for k in keys]
    return {"reader_id": reader_id, "dates": sorted(dates, reverse=True)}
"""
    ),
)

write(
    "backend/app/api/events.py",
    D(
        """\
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
    store = get_store()
    ts = time.time_ns()
    key = f"events/{ev.reader_id}/{ts}_{ev.event_type}"
    store.put(key, ev.model_dump())
    return {"ok": True}
"""
    ),
)

write(
    "backend/app/api/profile.py",
    D(
        """\
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.store import get_store

router = APIRouter()


@router.get("/{reader_id}")
async def get_profile(reader_id: str):
    p = get_store().get(f"profiles/{reader_id}")
    if p is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p
"""
    ),
)

write(
    "backend/app/api/dev.py",
    D(
        """\
from __future__ import annotations

from fastapi import APIRouter

from ..core.store import get_store

router = APIRouter()


@router.get("/readers")
async def list_readers():
    keys = get_store().list("profiles/")
    return [k.split("/")[-1] for k in keys]


@router.delete("/reset")
async def reset():
    store = get_store()
    for k in store.list(""):
        store.delete(k)
    return {"ok": True}
"""
    ),
)

write(
    "backend/app/api/main.py",
    D(
        """\
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from . import archive, dev, edition, events, onboarding, profile

app = FastAPI(title="Edition of One", version="0.1.0")

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
# /dev/reset wipes the store; keep it off outside local development.
if get_settings().enable_dev:
    app.include_router(dev.router, prefix="/dev", tags=["dev"])
"""
    ),
)

# ---------------------------------------------------------------------------
# 17a. pdf_generator/images.py
# ---------------------------------------------------------------------------
write(
    "pdf_generator/images.py",
    D(
        """\
from __future__ import annotations

import base64
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

try:
    from PIL import Image, ImageEnhance  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore

_CACHE: Dict[str, str] = {}
_POOL = ThreadPoolExecutor(max_workers=4)


def _process(data: bytes, contrast: float = 1.15, thumb: int = 480) -> str:
    if Image is None:
        return base64.b64encode(data).decode("ascii")
    img = Image.open(io.BytesIO(data)).convert("L")
    if ImageEnhance is not None:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    img.thumbnail((thumb, thumb))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def grayscale_thumb_b64(data: bytes, key: str) -> str:
    if key in _CACHE:
        return _CACHE[key]
    b64 = _process(data)
    _CACHE[key] = b64
    return b64


def prewarm(items: List[tuple]) -> Dict[str, str]:
    futures = {
        key: _POOL.submit(grayscale_thumb_b64, data, key) for key, data in items
    }
    return {k: f.result() for k, f in futures.items()}
"""
    ),
)

# ---------------------------------------------------------------------------
# 17b. pdf_generator/qr.py
# ---------------------------------------------------------------------------
write(
    "pdf_generator/qr.py",
    D(
        """\
from __future__ import annotations

import io


def qr_svg(url: str) -> str:
    try:
        import qrcode  # type: ignore
        import qrcode.image.svg as svg  # type: ignore
    except Exception:
        return ""
    img = qrcode.make(url, image_factory=svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")
"""
    ),
)

# ---------------------------------------------------------------------------
# 17c. pdf_generator/render.py
# ---------------------------------------------------------------------------
write(
    "pdf_generator/render.py",
    D(
        """\
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

try:
    from jinja2 import Environment, FileSystemLoader  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"Jinja2 required: {exc}")
    raise SystemExit(0)


def _env() -> "Environment":
    # autoescape: article text comes from RSS/web pages and may contain markup.
    # The QR SVG is the only trusted HTML and is marked |safe in the macro.
    return Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=True,
    )


def _decorate(edition: dict) -> dict:
    # Attach a rendered QR SVG (link back to the live edition).
    try:
        from qr import qr_svg  # noqa: WPS433
    except Exception:
        try:
            from pdf_generator.qr import qr_svg  # type: ignore
        except Exception:
            qr_svg = None  # type: ignore
    if qr_svg is not None:
        edition = dict(edition)
        base = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        edition["qr_svg"] = qr_svg(f"{base}/edition/{edition.get('reader_id', 'demo')}")
    return edition


def build_html(edition: dict, env: Optional["Environment"] = None) -> str:
    env = env or _env()
    tmpl = env.get_template("edition.html.j2")
    return tmpl.render(edition=_decorate(edition))


def render_pdf(html: str, out_path: Path) -> Path:
    from weasyprint import HTML, CSS  # type: ignore

    out_path.parent.mkdir(parents=True, exist_ok=True)
    css_path = HERE / "static/broadsheet.css"
    stylesheets = [CSS(filename=str(css_path))] if css_path.exists() else None
    HTML(string=html, base_url=str(HERE)).write_pdf(
        str(out_path), stylesheets=stylesheets
    )
    return out_path


def _all_demo() -> list:
    cache = ROOT / "data/cache/editions"
    if not cache.exists():
        return []
    return sorted(cache.rglob("*.json"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Render Edition of One broadsheets.")
    ap.add_argument("--all-demo", action="store_true")
    ap.add_argument("--edition", type=str, default=None)
    ap.add_argument("--out", type=str, default="data/pdfs")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    targets = []
    if args.all_demo:
        targets.extend(_all_demo())
    if args.edition:
        targets.append(Path(args.edition))

    if not targets:
        print("No editions found. Run `make seed` first.")
        return

    out_dir = ROOT / args.out

    for p in targets:
        p = Path(p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            print(f"  [skip] {p}")
            continue
        html = build_html(data)
        if args.check:
            print(f"  [check] {p} -> html {len(html)} bytes")
            continue
        # <reader>_<date>.pdf — the date alone collides across readers.
        out = out_dir / f"{p.parent.name}_{p.stem}.pdf"
        render_pdf(html, out)
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
"""
    ),
)

# ---------------------------------------------------------------------------
# 17d. pdf_generator/templates/_macros.html.j2
# ---------------------------------------------------------------------------
write(
    "pdf_generator/templates/_macros.html.j2",
    D(
        """\
{% macro nameplate(text) -%}
  <div class="nameplate">{{ text }}</div>
{%- endmacro %}

{% macro dateline(text) -%}
  <div class="dateline">{{ text }}</div>
{%- endmacro %}

{% macro article_lead(a) -%}
  {% if a %}
    <article class="lead-story">
      <h1 class="lead-headline">{{ a.title }}</h1>
      {% if a.body and a.body.long %}
        <p class="lead-body"><span class="dropcap">{{ a.body.long[0] }}</span>{{ a.body.long[1:] }}</p>
      {% elif a.body and a.body.medium %}
        <p class="lead-body">{{ a.body.medium }}</p>
      {% endif %}
      <div class="byline">{{ a.source }}</div>
    </article>
  {% endif %}
{%- endmacro %}

{% macro article_brief(a, klass='') -%}
  {% if a %}
    <article class="brief {{ klass }}">
      <h3>{{ a.title }}</h3>
      {% if a.body and a.body.short %}<p>{{ a.body.short }}</p>{% endif %}
    </article>
  {% endif %}
{%- endmacro %}

{% macro article_standard(a) -%}
  {% if a %}
    <article class="standard">
      <h2>{{ a.title }}</h2>
      {% if a.body and a.body.medium %}<p>{{ a.body.medium }}</p>{% endif %}
      <div class="byline">{{ a.source }}</div>
    </article>
  {% endif %}
{%- endmacro %}

{% macro qr_block(svg) -%}
  {% if svg %}
    <div class="qr">{{ svg|safe }}</div>
  {% endif %}
{%- endmacro %}
"""
    ),
)

# ---------------------------------------------------------------------------
# 17e. pdf_generator/templates/edition.html.j2
# ---------------------------------------------------------------------------
write(
    "pdf_generator/templates/edition.html.j2",
    D(
        """\
{% import "_macros.html.j2" as m %}
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{{ edition.nameplate }} — {{ edition.date }}</title>
  <link rel="stylesheet" href="static/broadsheet.css">
</head>
<body>

<header class="masthead">
  {{ m.nameplate(edition.nameplate or "Edition of One") }}
  {{ m.dateline(edition.dateline or edition.date) }}
</header>

<section class="front">
  <div class="col col-main">
    {{ m.article_lead(edition.front.lead) }}
  </div>
  <aside class="col col-side">
    {% if edition.front.weather and edition.front.weather.temp_c is not none %}
      <div class="weather">
        <div class="weather-city">{{ edition.front.weather.city }}</div>
        <div class="weather-temp">{{ edition.front.weather.temp_c }}°</div>
        <div class="weather-range">H {{ edition.front.weather.high_c }}° / L {{ edition.front.weather.low_c }}°</div>
        {% if edition.front.weather.condition %}<div class="weather-range">{{ edition.front.weather.condition }}</div>{% endif %}
      </div>
    {% endif %}
    {% if edition.front.quote %}
      <blockquote class="pullquote">{{ edition.front.quote }}</blockquote>
    {% endif %}
    {{ m.qr_block(edition.qr_svg) }}
  </aside>
</section>

<section class="secondary">
  {% for a in edition.front.secondary %}
    {{ m.article_standard(a) }}
  {% endfor %}
</section>

<section class="briefs">
  {% for a in edition.front.briefs %}
    {{ m.article_brief(a) }}
  {% endfor %}
</section>

{% for section in edition.sections %}
<section class="section-page">
  <h2 class="section-title">{{ section.name }}</h2>
  <div class="section-grid">
    {% for a in section.articles %}
      {{ m.article_standard(a) }}
    {% endfor %}
  </div>
</section>
{% endfor %}

{% if edition.outside_bubble %}
<section class="outside-bubble">
  <h2 class="section-title">Outside Your Bubble</h2>
  <div class="section-grid">
    {% for a in edition.outside_bubble %}
      {{ m.article_brief(a, klass='outside') }}
    {% endfor %}
  </div>
</section>
{% endif %}

<footer class="colophon">
  <span>Edition of One · {{ edition.reader_id }} · {{ edition.date }}</span>
</footer>

</body>
</html>
"""
    ),
)

# ---------------------------------------------------------------------------
# 17f. pdf_generator/static/broadsheet.css
# ---------------------------------------------------------------------------
write(
    "pdf_generator/static/broadsheet.css",
    D(
        """\
@page {
  size: A3;
  margin: 18mm 16mm 18mm 16mm;
  @bottom-center {
    content: counter(page) " / " counter(pages);
    font-family: "DejaVu Serif", serif;
    font-size: 8pt;
  }
}

html, body {
  background: #f5efe0;
  color: #1a1a1a;
  font-family: "DejaVu Serif", Georgia, serif;
  font-size: 9.5pt;
  line-height: 1.42;
  text-align: justify;
  hyphens: auto;
}

.masthead {
  border-bottom: 3px double #1a1a1a;
  margin-bottom: 6mm;
  padding-bottom: 2mm;
  text-align: center;
}

.nameplate {
  font-family: "DejaVu Serif", serif;
  font-weight: 900;
  font-size: 42pt;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}

.dateline {
  font-size: 8pt;
  letter-spacing: 0.3em;
  text-transform: uppercase;
  color: #444;
  margin-top: 1mm;
}

.front {
  display: flex;
  gap: 8mm;
  border-bottom: 1px solid #1a1a1a;
  padding-bottom: 4mm;
  margin-bottom: 4mm;
}

.col-main { flex: 3; }
.col-side  { flex: 1; border-left: 1px solid #1a1a1a; padding-left: 6mm; }

.lead-headline {
  font-family: "DejaVu Serif", serif;
  font-size: 26pt;
  line-height: 1.06;
  margin: 0 0 3mm 0;
  text-align: left;
}

.lead-body { column-count: 3; column-gap: 6mm; column-rule: 1px solid #b9a98a; }

.dropcap {
  float: left;
  font-size: 52pt;
  line-height: 0.86;
  padding-right: 2mm;
  font-weight: 700;
  color: #6b1d1d;
}

.byline {
  font-size: 7.5pt;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #555;
  margin-top: 2mm;
}

.secondary {
  column-count: 4;
  column-gap: 6mm;
  column-rule: 1px solid #b9a98a;
  margin-bottom: 4mm;
}

.briefs {
  column-count: 5;
  column-gap: 4mm;
  border-top: 1px solid #1a1a1a;
  padding-top: 3mm;
  margin-bottom: 6mm;
}

.brief h3 { font-size: 10pt; margin: 0 0 1mm 0; }

.standard h2 { font-size: 13pt; line-height: 1.15; margin: 0 0 2mm 0; }

.weather {
  border: 1px solid #1a1a1a;
  padding: 3mm;
  text-align: center;
  margin-bottom: 4mm;
}
.weather-city { font-size: 9pt; letter-spacing: 0.2em; text-transform: uppercase; }
.weather-temp { font-size: 22pt; font-weight: 700; }
.weather-range { font-size: 8pt; }

.pullquote {
  font-style: italic;
  font-size: 11pt;
  border-top: 1px solid #1a1a1a;
  border-bottom: 1px solid #1a1a1a;
  padding: 3mm 0;
  margin: 4mm 0;
  text-align: left;
}

.qr svg { width: 32mm; height: 32mm; }

.section-page {
  border-top: 2px solid #1a1a1a;
  padding-top: 4mm;
  margin-top: 6mm;
  page-break-before: always;
}

.section-title {
  font-size: 18pt;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  margin: 0 0 3mm 0;
}

.section-grid {
  column-count: 4;
  column-gap: 6mm;
  column-rule: 1px solid #b9a98a;
}

.outside-bubble {
  border-top: 1px solid #1a1a1a;
  padding-top: 4mm;
  margin-top: 6mm;
}

.outside { font-style: italic; }

.colophon {
  margin-top: 8mm;
  border-top: 1px solid #1a1a1a;
  padding-top: 2mm;
  font-size: 7.5pt;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: #555;
  text-align: center;
}
"""
    ),
)

# ---------------------------------------------------------------------------
# 18. Tests
# ---------------------------------------------------------------------------
write(
    "backend/tests/conftest.py",
    D(
        """\
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))
"""
    ),
)

write(
    "backend/tests/test_fallback_editor.py",
    D(
        """\
from app.models.schemas import ArticleRecord, Body, Profile
from app.services.fallback_editor import (
    build_edition,
    dedupe,
    extract_summary,
    jaccard,
    _tokens,
)


def _art(i, title, topics, text="", imp=0.6):
    return ArticleRecord(
        id=f"a{i}",
        title=title,
        topics=topics,
        body=Body(short=text, medium=text, long=text),
        importance=imp,
    )


def test_jaccard_identical():
    assert jaccard(_tokens("hello world"), _tokens("hello world")) == 1.0


def test_dedupe_removes_near_duplicates():
    arts = [
        _art(1, "Breaking news about the economy today"),
        _art(2, "Breaking news about the economy today"),
        _art(3, "A totally different headline on sport"),
    ]
    out = dedupe(arts)
    assert len(out) == 2


def test_extract_summary_respects_word_limit():
    text = "First sentence here. Second sentence follows. Third sentence is here too."
    s = extract_summary(text, 5)
    assert len(s.split()) <= 5


WORLD_TITLES = [
    "Floods displace thousands along river basin",
    "Summit negotiators narrow gap on shipping rules",
    "Central bank holds rates amid cooling prices",
    "Volcano alert raised near island resorts",
    "Opposition leaders demand fresh ballot count",
    "Aid convoy reaches besieged northern town",
    "Telescope captures distant galaxy cluster",
    "Rail strike enters second week",
]


def test_build_edition_slots_each_story_once():
    profile = Profile(
        reader_id="r1",
        topics=["world", "pakistan"],
        weights={"world": 1.0, "pakistan": 1.0},
        location="Islamabad",
        outside_bubble_ratio=0.2,
    )
    arts = [_art(i, t, ["world"]) for i, t in enumerate(WORLD_TITLES)]
    arts.append(_art(99, "Outside topic technology story", ["technology"]))
    ed = build_edition("r1", "2025-01-01", arts, profile)

    assert ed.front.lead is not None
    assert ed.front.secondary
    assert ed.outside_bubble and ed.outside_bubble[0].id == "a99"
    assert ed.reader_id == "r1"
    assert ed.date == "2025-01-01"

    ids = [ed.front.lead.id]
    ids += [a.id for a in ed.front.secondary]
    ids += [a.id for a in ed.front.briefs]
    for sec in ed.sections:
        ids += [a.id for a in sec.articles]
    assert len(ids) == len(set(ids)), "a story was placed in two slots"
"""
    ),
)

write(
    "backend/tests/test_json_repair.py",
    D(
        """\
from app.core.llm import repair_json


def test_plain_json():
    assert repair_json('{"a": 1}') == {"a": 1}


def test_code_fence():
    assert repair_json('```json\\n{"a": 1}\\n```') == {"a": 1}


def test_prose_wrapped():
    got = repair_json('Sure! Here you go: {"a": 2, "b": [1,2,3]}')
    assert isinstance(got, dict) and got.get("a") == 2


def test_prose_wrapped_list():
    got = repair_json('Result: [{"a": 1}, {"a": 2}] hope that helps')
    assert isinstance(got, list) and len(got) == 2


def test_broken_json_returns_dict():
    got = repair_json('{a: 1,')
    assert isinstance(got, (dict, list))
"""
    ),
)

write(
    "backend/tests/test_ranker.py",
    D(
        """\
from app.models.schemas import ArticleRecord, Body, Profile
from app.services.ranker import (
    ThompsonBandit,
    cluster_cosine,
    cosine,
    score_article,
)


def _mk(i, topics, imp=0.6):
    return ArticleRecord(id=f"a{i}", title=f"Title {i}", topics=topics,
                         body=Body(), importance=imp)


def test_cosine_identity():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6


def test_score_prefers_weighted_topic():
    profile = Profile(reader_id="r", topics=["world"], weights={"world": 1.0, "sport": 0.1})
    a_world = _mk(1, ["world"])
    a_sport = _mk(2, ["sport"])
    assert score_article(a_world, profile) > score_article(a_sport, profile)


def test_thompson_bandit_updates():
    tb = ThompsonBandit()
    _ = tb.sample("world")
    tb.update("world", 1.0)
    assert tb.alpha["world"] > 1.0


def test_cluster_cosine_groups_identical():
    labels = cluster_cosine([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])
    assert labels[0] == labels[1]
    assert labels[2] != labels[0]
"""
    ),
)

write(
    "backend/tests/test_guard.py",
    D(
        """\
from app.services.guard import validate_grounding


def test_numbers_must_be_grounded():
    ok, problems = validate_grounding("Inflation rose to 12.5%", ["Prices rose to 12.5% this year."])
    assert ok, problems


def test_unknown_number_flagged():
    ok, problems = validate_grounding("Inflation rose to 99%", ["Prices rose modestly."])
    assert not ok
    assert any("99" in p for p in problems)


def test_entities_grounded():
    ok, _ = validate_grounding("Pakistan welcomed the decision", ["Pakistan welcomed the decision."])
    assert ok


def test_unknown_mid_sentence_entity_flagged():
    ok, problems = validate_grounding(
        "Officials met Reuters editors", ["Officials met local editors."]
    )
    assert not ok
    assert any("Reuters" in p for p in problems)
"""
    ),
)

write(
    "backend/tests/test_profile_service.py",
    D(
        """\
from types import SimpleNamespace

from app.services.profile_service import _keywords_to_topics, create_profile


def test_ai_keyword_needs_word_boundary():
    assert "ai" not in _keywords_to_topics("please maintain my email")
    assert "ai" in _keywords_to_topics("I follow AI and tech")


def test_create_profile_defaults():
    req = SimpleNamespace(reader_id="r", name="", interests=[], location="", tone="")
    p = create_profile(req)
    assert p.topics and p.name == "r"
"""
    ),
)

write(
    "backend/tests/test_api_offline.py",
    D(
        """\
import os
import tempfile

# Isolate from the real data/cache; must be set before the app reads settings.
os.environ["LLM_OFFLINE"] = "1"
os.environ["CACHE_DIR"] = tempfile.mkdtemp(prefix="eo_cache_")
os.environ["LLM_CACHE_DIR"] = tempfile.mkdtemp(prefix="eo_llm_")

from fastapi.testclient import TestClient

import app.services.curator as curator
from app.api.main import app

# No network in tests.
curator.weather_for = lambda city: {
    "city": city, "temp_c": 30.0, "high_c": 33.0, "low_c": 22.0, "condition": "Clear",
}

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_onboarding_and_edition():
    payload = {
        "reader_id": "test-reader",
        "name": "Test",
        "interests": ["world", "technology", "pakistan"],
        "location": "Islamabad",
        "tone": "neutral",
    }
    r = client.post("/onboarding", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["reader_id"] == "test-reader"
    assert body["topics"]

    r2 = client.get("/edition/test-reader")
    assert r2.status_code == 200, r2.text
    ed = r2.json()
    assert ed["front"]["lead"] is not None
    assert ed["front"]["weather"]["city"] == "Islamabad"
    assert "Islamabad" in ed["dateline"]
"""
    ),
)

write(
    "backend/tests/test_pdf.py",
    D(
        """\
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pdf_generator"))

from render import build_html  # noqa: E402


def _sample():
    return {
        "id": "ed-test-2025-01-01",
        "reader_id": "test-reader",
        "date": "2025-01-01",
        "nameplate": "Edition of One",
        "dateline": "Islamabad \\u2014 2025-01-01",
        "front": {
            "lead": {
                "id": "a1",
                "title": "A lead story <b>unsafe</b>",
                "source": "Test Wire",
                "topics": ["world"],
                "body": {"short": "Short.", "medium": "Medium body.", "long": "Long body."},
            },
            "secondary": [],
            "briefs": [],
            "weather": {"city": "Islamabad", "temp_c": 30, "high_c": 33, "low_c": 22, "condition": ""},
            "quote": "A quote for the front page.",
        },
        "sections": [],
        "outside_bubble": [],
    }


def test_build_html_renders():
    html = build_html(_sample())
    assert "Edition of One" in html
    assert "A lead story" in html


def test_article_markup_is_escaped():
    html = build_html(_sample())
    assert "<b>unsafe</b>" not in html
    assert "&lt;b&gt;unsafe" in html
"""
    ),
)

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------
print()
print("=" * 68)
print("Phase 1 scaffold created.")
print("Next steps:")
print()
print("  cp .env.example .env")
print("  make setup")
print("  make seed")
print("  make verify")
print("  make test")
print("=" * 68)