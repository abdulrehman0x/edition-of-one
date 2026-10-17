from __future__ import annotations

from fastapi import APIRouter

from ..core.store import get_store

router = APIRouter()


@router.get("/{reader_id}")
async def archive(reader_id: str):
    store = get_store()
    keys = store.list(f"editions/{reader_id}/")
    dates = [k.split("/")[-1] for k in keys]
    return {"reader_id": reader_id, "dates": sorted(dates, reverse=True)}
