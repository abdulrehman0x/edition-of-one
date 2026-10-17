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
