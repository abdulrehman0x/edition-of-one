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
