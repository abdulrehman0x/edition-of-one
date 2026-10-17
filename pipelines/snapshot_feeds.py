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
