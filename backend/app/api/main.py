from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from . import archive, dev, edition, events, onboarding, profile

app = FastAPI(title="Edition of One", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def _startup() -> None:
    from ..core.store import get_store
    get_store()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


app.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
app.include_router(edition.router, prefix="/edition", tags=["edition"])
app.include_router(archive.router, prefix="/archive", tags=["archive"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(profile.router, prefix="/profile", tags=["profile"])
# /dev/reset wipes the store; keep it off outside local development.
if get_settings().enable_dev:
    app.include_router(dev.router, prefix="/dev", tags=["dev"])
