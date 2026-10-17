"""Snapshot feeds: pull live RSS articles into the local cache.

Run from the repo root:

    python pipelines/snapshot_feeds.py [--force]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services import rss_ingest  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pipelines.snapshot_feeds")
    ap.add_argument("--force", action="store_true", help="Ignore cache TTL")
    ap.add_argument("--out", default="data/cache/articles.json")
    args = ap.parse_args(argv)

    result = rss_ingest.ingest(force=args.force)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"updated_at": time.time(), "articles": result["articles"]}
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(
        "snapshot: "
        + str(len(result["articles"]))
        + " articles ("
        + str(result["fetched"])
        + " fetched, cached="
        + str(result["cached"])
        + ") -> "
        + str(out_path)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
