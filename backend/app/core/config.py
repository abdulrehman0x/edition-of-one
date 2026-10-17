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
