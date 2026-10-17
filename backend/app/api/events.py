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
    ns = time.time_ns()
    payload = ev.model_dump()
    # The learning engine selects events by this millisecond timestamp;
    # without it every event looks like it happened at time 0 and is ignored.
    payload["ts"] = ns // 1_000_000
    get_store().put(f"events/{ev.reader_id}/{ns}_{ev.event_type}", payload)
    return {"ok": True}
