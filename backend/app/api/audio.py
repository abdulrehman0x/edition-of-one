from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..services.broadcast import audio_file

router = APIRouter()


@router.get("/{reader_id}/{date}")
async def get_audio(reader_id: str, date: str):
    path = audio_file(reader_id, date)
    if not path.exists():
        raise HTTPException(status_code=404, detail="No audio for this edition")
    return FileResponse(str(path), media_type="audio/mpeg")
