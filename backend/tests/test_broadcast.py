import os

os.environ["LLM_OFFLINE"] = "1"

from app.models.schemas import ArticleRecord, Body, Edition, Front
from app.services.broadcast import audio_file, build_broadcast


def _edition():
    lead = ArticleRecord(id="a1", title="Lead", body=Body(short="Short lead.", medium="Medium lead text."))
    return Edition(id="e", reader_id="r", date="2026-01-01", front=Front(lead=lead))


def test_offline_broadcast_is_script_only_with_timeline():
    b = build_broadcast(_edition(), with_audio=True)
    assert b["mode"] == "script-only" and b["audio_url"] is None
    assert b["chapters"][0]["title"] == "Lead"
    assert b["chapters"][0]["start"] > 0
    assert b["duration"] > 0


def test_audio_path_is_sanitised():
    p = audio_file("../../etc", "2026-01-01")
    assert ".." not in p.parts
