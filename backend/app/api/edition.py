from __future__ import annotations

from datetime import date as _date

from fastapi import APIRouter, HTTPException

from ..services.edition_service import get_or_build_edition

router = APIRouter()


@router.get("/{reader_id}")
async def get_edition(reader_id: str, date: str = "today"):
    d = _date.today().isoformat() if date == "today" else date
    ed = await get_or_build_edition(reader_id, d)
    if ed is None:
        raise HTTPException(status_code=404, detail="No edition available")
    return ed.model_dump() if hasattr(ed, "model_dump") else ed
