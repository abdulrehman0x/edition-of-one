from __future__ import annotations

import asyncio
from datetime import date as _date

from fastapi import APIRouter, HTTPException

from ..services.edition_service import get_or_build_edition
from ..services.extras import enrich_stored

router = APIRouter()


def _day(date: str) -> str:
    return _date.today().isoformat() if date == "today" else date


@router.get("/{reader_id}")
async def get_edition(reader_id: str, date: str = "today"):
    ed = await get_or_build_edition(reader_id, _day(date))
    if ed is None:
        raise HTTPException(status_code=404, detail="No edition available")
    return ed.model_dump() if hasattr(ed, "model_dump") else ed


@router.post("/{reader_id}/enrich")
async def enrich(reader_id: str, date: str = "today", audio: bool = False):
    # Rebuilds the gallery/back page/broadcast for a stored edition;
    # audio=true also synthesises the MP3 (needs network and edge-tts).
    d = _day(date)
    await get_or_build_edition(reader_id, d)
    res = await asyncio.to_thread(enrich_stored, reader_id, d, audio)
    if not res.get("ok"):
        raise HTTPException(status_code=404, detail=res.get("reason", "failed"))
    return res
