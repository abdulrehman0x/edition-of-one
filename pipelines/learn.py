from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.core.store import get_store  # noqa: E402
from app.services.learning import LearningEngine  # noqa: E402


def main() -> None:
    store = get_store()
    engine = LearningEngine(store=store)
    readers = sorted({k.split("/")[-1] for k in store.list("profiles/")})
    if not readers:
        print("No profiles found. Run `make seed` first.")
        return

    for rid in readers:
        result = engine.advance(rid)
        if "error" in result:
            print(f"  [skip] {rid}: {result['error']}")
            continue
        pretty = {k: v for k, v in result["deltas"].items() if abs(v) > 0.005}
        print(f"  {rid}: {result['events_processed']} events processed")
        print(f"    edition: {result['date']}")
        if pretty:
            print(f"    deltas: {json.dumps(pretty)}")
        print(f"    why: {result['explanation']}")


if __name__ == "__main__":
    main()
