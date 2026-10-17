from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core.store import get_store
from ..services.profile_service import create_profile

router = APIRouter()


class OnboardingRequest(BaseModel):
    reader_id: str
    name: str = ""
    interests: List[str] = Field(default_factory=list)
    loves: List[str] = Field(default_factory=list)
    reading_time: str = "medium"
    location: str = ""
    tone: str = "neutral"


@router.post("")
async def onboard(req: OnboardingRequest):
    profile = create_profile(req)
    # "Loved" topics start at full weight, merely "liked" ones a little lower,
    # so the first edition already reflects the strength of the choice.
    base = 0.7 if req.loves else 1.0
    for t in profile.topics:
        profile.weights[t] = 1.0 if t in req.loves else base
    if req.reading_time in ("short", "medium", "long"):
        profile.reading_time_pref = req.reading_time
    get_store().put(f"profiles/{profile.reader_id}", profile.model_dump())
    return profile.model_dump()
