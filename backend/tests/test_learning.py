import time

from app.core.store import FileStore
from app.models.schemas import Profile
from app.services.learning import LearningEngine


def _setup(tmp_path):
    store = FileStore(tmp_path)
    for i, (title, topics) in enumerate(
        [("Cricket final tonight", ["cricket", "sport"]), ("Budget debate", ["politics"])]
    ):
        store.put(
            f"articles/a{i}",
            {"id": f"a{i}", "title": title, "topics": topics, "body": {"short": title}},
        )
    profile = Profile(reader_id="r", topics=["politics"], weights={"politics": 0.6})
    store.put("profiles/r", profile.model_dump())
    return store


def _event(store, aid, kind, ts):
    store.put(
        f"events/r/{ts}_{kind}",
        {"reader_id": "r", "article_id": aid, "event_type": kind, "value": 1.0, "ts": ts},
    )


def test_likes_raise_weight_and_promote_topic(tmp_path):
    store = _setup(tmp_path)
    now = int(time.time() * 1000)
    for i in range(3):
        _event(store, "a0", "thumb_up", now + i)
    result = LearningEngine(store=store).advance("r", with_widgets=False)

    assert result["events_processed"] == 3
    assert result["deltas"]["cricket"] > 0.4
    profile = store.get("profiles/r")
    assert profile["weights"]["cricket"] > 0.65
    assert "cricket" in profile["topics"]          # promoted into the bubble
    assert "cricket" in result["explanation"]


def test_events_are_consumed_once(tmp_path):
    store = _setup(tmp_path)
    _event(store, "a0", "thumb_up", int(time.time() * 1000))
    engine = LearningEngine(store=store)
    assert engine.advance("r", with_widgets=False)["events_processed"] == 1
    assert engine.advance("r", with_widgets=False)["events_processed"] == 0


def test_dislikes_lower_weight_and_aux_keys_are_not_profiles(tmp_path):
    store = _setup(tmp_path)
    _event(store, "a1", "thumb_down", int(time.time() * 1000))
    LearningEngine(store=store).advance("r", with_widgets=False)

    assert store.get("profiles/r")["weights"]["politics"] < 0.6
    assert store.list("profiles/") == ["profiles/r"]


def test_advance_without_profile_reports_error(tmp_path):
    assert "error" in LearningEngine(store=FileStore(tmp_path)).advance("ghost")
