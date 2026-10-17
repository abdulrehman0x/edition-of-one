from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from ..core.store import get_store
from ..models.schemas import Profile
from ..services.learning import LearningEngine

router = APIRouter()


@router.get("/{reader_id}")
async def get_profile(reader_id: str):
    p = get_store().get(f"profiles/{reader_id}")
    if p is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p


@router.post("/{reader_id}/advance")
async def advance(reader_id: str):
    # Demo hook for "a night passes": learn from events, build tomorrow's edition.
    store = get_store()
    if store.get(f"profiles/{reader_id}") is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await asyncio.to_thread(LearningEngine(store).advance, reader_id)


@router.get("/{reader_id}/history")
async def history(reader_id: str):
    return LearningEngine(get_store()).weight_history(reader_id)


@router.delete("/{reader_id}/topics/{topic}")
async def remove_topic(reader_id: str, topic: str):
    store = get_store()
    data = store.get(f"profiles/{reader_id}")
    if data is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = Profile(**data)
    profile.topics = [t for t in profile.topics if t != topic]
    profile.weights = {k: v for k, v in profile.weights.items() if k != topic}
    store.put(f"profiles/{reader_id}", profile.model_dump())
    return profile.model_dump()
