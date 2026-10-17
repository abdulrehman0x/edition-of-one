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
    location: str = ""
    tone: str = "neutral"


@router.post("")
async def onboard(req: OnboardingRequest):
    profile = create_profile(req)
    get_store().put(f"profiles/{profile.reader_id}", profile.model_dump())
    return profile.model_dump()
