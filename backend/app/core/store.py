from __future__ import annotations

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
