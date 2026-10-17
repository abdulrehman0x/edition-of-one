from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..core.store import get_store

router = APIRouter()


@router.get("/{reader_id}")
async def get_profile(reader_id: str):
    p = get_store().get(f"profiles/{reader_id}")
    if p is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p
