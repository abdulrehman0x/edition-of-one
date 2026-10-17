from __future__ import annotations

import asyncio
from typing import Dict, Optional, Union

from ..core.store import get_store
from .curator import build_edition_async

_locks: Dict[str, asyncio.Lock] = {}


def _lock(reader_id: str) -> asyncio.Lock:
    if reader_id not in _locks:
        _locks[reader_id] = asyncio.Lock()
    return _locks[reader_id]


async def get_or_build_edition(
    reader_id: str, date: str
) -> Optional[Union[dict, object]]:
    store = get_store()
    key = f"editions/{reader_id}/{date}"
    cached = store.get(key)
    if cached:
        return cached
    async with _lock(reader_id):
        cached = store.get(key)
        if cached:
            return cached
        edition = await build_edition_async(reader_id, date)
        if edition is not None:
            payload = edition.model_dump() if hasattr(edition, "model_dump") else edition
            store.put(key, payload)
        return edition
