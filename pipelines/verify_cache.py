from __future__ import annotations

import sys

from app.core.store import get_store
from app.models.schemas import Edition

READER_IDS = ["demo-ayesha", "demo-bilal", "demo-sara"]


def main() -> None:
    store = get_store()
    failures: list[str] = []
    rows: list[tuple[str, int, str, int]] = []

    for reader_id in READER_IDS:
        editions = store.list_editions(reader_id)
        try:
            validated = [Edition.model_validate(edition.model_dump()) for edition in editions]
        except Exception as exc:
            failures.append(f"{reader_id}: validation failed: {exc}")
            continue
        if len(validated) != 14:
            failures.append(f"{reader_id}: expected 14 editions, found {len(validated)}")
        if not validated:
            failures.append(f"{reader_id}: no editions")
            continue
        lead = validated[0].front.lead
        if not lead.id or not lead.headline:
            failures.append(f"{reader_id}: empty lead")
        if not any(section.items for section in validated[0].sections):
            failures.append(f"{reader_id}: no non-empty sections")
        dates = [edition.date for edition in validated]
        if len(set(dates)) != len(dates):
            failures.append(f"{reader_id}: duplicate edition dates")
        rows.append((reader_id, len(validated), validated[0].date.isoformat(), len(validated[0].sections)))

    print(f"{'reader':12} {'editions':>8} {'latest':>12} {'sections':>8}")
    print("-" * 44)
    for reader_id, count, latest, sections in rows:
        print(f"{reader_id:12} {count:8d} {latest:>12} {sections:8d}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        sys.exit(1)

    print("OK: 3 readers x 14 editions valid")


if __name__ == "__main__":
    main()
