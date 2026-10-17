import os
import tempfile

# Isolate from the real data/cache; must be set before the app reads settings.
os.environ["LLM_OFFLINE"] = "1"
os.environ["CACHE_DIR"] = tempfile.mkdtemp(prefix="eo_cache_")
os.environ["LLM_CACHE_DIR"] = tempfile.mkdtemp(prefix="eo_llm_")

from fastapi.testclient import TestClient

import app.services.curator as curator
from app.api.main import app

# No network in tests.
curator.weather_for = lambda city: {
    "city": city, "temp_c": 30.0, "high_c": 33.0, "low_c": 22.0, "condition": "Clear",
}

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_onboarding_and_edition():
    payload = {
        "reader_id": "test-reader",
        "name": "Test",
        "interests": ["world", "technology", "pakistan"],
        "location": "Islamabad",
        "tone": "neutral",
    }
    r = client.post("/onboarding", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["reader_id"] == "test-reader"
    assert body["topics"]

    r2 = client.get("/edition/test-reader")
    assert r2.status_code == 200, r2.text
    ed = r2.json()
    assert ed["front"]["lead"] is not None
    assert ed["front"]["weather"]["city"] == "Islamabad"
    assert "Islamabad" in ed["dateline"]
