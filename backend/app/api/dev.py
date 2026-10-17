from __future__ import annotations

from fastapi import APIRouter

from ..core.store import get_store

router = APIRouter()


@router.get("/readers")
async def list_readers():
    keys = get_store().list("profiles/")
    return [k.split("/")[-1] for k in keys]


@router.delete("/reset")
async def reset():
    store = get_store()
    for k in store.list(""):
        store.delete(k)
    return {"ok": True}
