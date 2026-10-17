from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.services.extras import enrich_stored  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Add gallery, back page and broadcast to stored editions.")
    ap.add_argument("--audio", action="store_true",
                    help="also synthesise MP3s (needs network, edge-tts, LLM_OFFLINE=0)")
    ap.add_argument("--last", type=int, default=3,
                    help="only the newest N editions per reader (default 3)")
    args = ap.parse_args()

    store = get_store()
    by_reader: dict = {}
    for k in store.list("editions/"):
        parts = k.split("/")
        if len(parts) == 3:  # editions/<reader>/<date>
            by_reader.setdefault(parts[1], []).append(parts[2])

    total = 0
    for reader, dates in sorted(by_reader.items()):
        for d in sorted(dates, reverse=True)[: args.last]:
            res = enrich_stored(reader, d, with_audio=args.audio)
            status = res.get("broadcast_mode") if res.get("ok") else res.get("reason")
            print(f"  {reader} {d}: {status}")
            total += 1
    print(f"Enriched {total} editions.")


if __name__ == "__main__":
    main()
