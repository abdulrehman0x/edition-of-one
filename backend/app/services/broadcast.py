from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from ..core.config import get_settings
from ..models.schemas import Edition

WORDS_PER_SECOND = 2.6   # used to estimate the timeline when there is no audio


def audio_file(reader_id: str, date_str: str) -> Path:
    # Ids come from URLs, so keep them to a safe character set.
    safe_reader = re.sub(r"[^A-Za-z0-9_-]", "_", reader_id)
    safe_date = re.sub(r"[^0-9-]", "_", date_str)
    return Path(get_settings().cache_dir) / "audio" / safe_reader / f"{safe_date}.mp3"


def _script_from_edition(edition: Edition) -> Dict[str, Any]:
    lead = edition.front.lead
    if lead:
        intro = f"Good morning. It's {edition.date}. We lead with: {lead.title}."
    else:
        intro = f"Good morning. It's {edition.date}, and this is your edition of one."
    chapters: List[Dict[str, str]] = []
    if lead:
        chapters.append({"title": lead.title, "script": lead.body.medium or lead.body.short})
    for a in edition.front.secondary:
        chapters.append({"title": a.title, "script": a.body.short})
    for sec in edition.sections:
        for a in sec.articles[:1]:
            chapters.append({"title": a.title, "script": a.body.short})
    outro = "That's your morning. Have a thoughtful day."
    return {"intro": intro, "chapters": chapters, "outro": outro}


def _estimate(text: str) -> float:
    return len((text or "").split()) / WORDS_PER_SECOND


def _try_edge_tts(text: str, out_path: Path) -> bool:
    try:
        import asyncio
        import edge_tts  # type: ignore
    except Exception:
        return False
    try:
        async def _run() -> None:
            await edge_tts.Communicate(text, voice="en-GB-RyanNeural").save(str(out_path))

        asyncio.run(_run())
        return out_path.exists() and out_path.stat().st_size > 0
    except Exception:
        return False


def _duration(path: Path, fallback: float) -> float:
    try:
        from mutagen.mp3 import MP3  # type: ignore
        return float(MP3(str(path)).info.length)
    except Exception:
        return fallback


def build_broadcast(edition: Edition, with_audio: bool = False) -> Dict[str, Any]:
    script = _script_from_edition(edition)
    texts = [script["intro"]] + [c["script"] for c in script["chapters"]] + [script["outro"]]
    estimates = [_estimate(t) for t in texts]

    def timeline(durations: List[float]) -> List[Dict[str, Any]]:
        t = durations[0]  # chapters start after the intro
        out = []
        for c, d in zip(script["chapters"], durations[1:-1]):
            out.append({"title": c["title"], "start": round(t, 1), "duration": round(d, 1)})
            t += d
        return out

    result: Dict[str, Any] = {
        "mode": "script-only",
        "audio_url": None,
        "script": script,
        "chapters": timeline(estimates),
        "duration": round(sum(estimates), 1),
    }

    # edge-tts needs the network, so it is skipped when running offline.
    if not with_audio or get_settings().llm_offline == 1:
        return result

    combined = audio_file(edition.reader_id, edition.date)
    combined.parent.mkdir(parents=True, exist_ok=True)
    parts: List[Path] = []
    for i, text in enumerate(texts):
        seg = combined.with_name(f"{combined.stem}_{i}.mp3")
        if not _try_edge_tts(text, seg):
            for p in parts:
                p.unlink(missing_ok=True)
            return result
        parts.append(seg)

    # MP3 frames can simply be concatenated; no ffmpeg needed.
    with combined.open("wb") as out:
        for p in parts:
            out.write(p.read_bytes())
    durations = [_duration(p, e) for p, e in zip(parts, estimates)]
    for p in parts:
        p.unlink(missing_ok=True)

    result.update(
        mode="audio",
        audio_url=f"/audio/{edition.reader_id}/{edition.date}",
        chapters=timeline(durations),
        duration=round(sum(durations), 1),
    )
    return result
