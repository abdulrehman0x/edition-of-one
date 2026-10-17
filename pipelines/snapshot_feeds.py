from __future__ import annotations

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
