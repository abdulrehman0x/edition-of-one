from __future__ import annotations

import time
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..core.store import get_store
from ..models.schemas import EventType

router = APIRouter()


class EventIn(BaseModel):
    reader_id: str
    article_id: Optional[str] = None
    event_type: EventType
    value: float = 1.0


@router.post("")
async def record(ev: EventIn):
    store = get_store()
    ts = time.time_ns()
    key = f"events/{ev.reader_id}/{ts}_{ev.event_type}"
    store.put(key, ev.model_dump())
    return {"ok": True}
