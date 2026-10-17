from __future__ import annotations

import asyncio
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any, Optional

from .config import get_settings


class CircuitBreaker:
    def __init__(self, threshold: int = 3, pause: float = 120.0) -> None:
        self.threshold = threshold
        self.pause = pause
        self.failures = 0
        self.open_until = 0.0

    def allow(self) -> bool:
        return time.time() >= self.open_until

    def success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def failure(self) -> None:
        self.failures += 1
        if self.failures >= self.threshold:
            self.open_until = time.time() + self.pause


_breaker = CircuitBreaker()


def _cache_path(prompt: str, model: str) -> Path:
    key = hashlib.sha256(f"{model}::{prompt}".encode("utf-8")).hexdigest()
    p = Path(get_settings().llm_cache_dir) / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def repair_json(text: str) -> Any:
    '''Best-effort extraction of a JSON object/array from LLM output.'''
    if not text:
        return {}
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    try:
        return json.loads(t)
    except Exception:
        pass

    # Slice from the first { or [ to the last matching closer.
    starts = [i for i in (t.find("{"), t.find("[")) if i != -1]
    candidate = t
    if starts:
        i = min(starts)
        closer = "}" if t[i] == "{" else "]"
        j = t.rfind(closer)
        if j > i:
            try:
                return json.loads(t[i:j + 1])
            except Exception:
                pass
        candidate = t[i:]

    try:
        from json_repair import repair_json as _rj  # type: ignore
        got = json.loads(_rj(candidate))
        if isinstance(got, (dict, list)) and got:
            return got
    except Exception:
        pass
    return {}


async def complete(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
) -> Optional[str]:
    s = get_settings()
    model = model or s.deepseek_model
    cache_key = prompt + f"::t={temperature}"
    cache = _cache_path(cache_key, model)
    if cache.exists():
        try:
            return json.loads(cache.read_text(encoding="utf-8")).get("text")
        except Exception:
            pass
    if s.llm_offline == 1 or not s.deepseek_api_key:
        return None
    if not _breaker.allow():
        return None
    try:
        import httpx  # type: ignore
    except Exception:
        return None
    url = f"{s.deepseek_base_url.rstrip('/')}/v1/chat/completions"
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }
    headers = {"Authorization": f"Bearer {s.deepseek_api_key}"}
    delay = 1.0
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.post(url, json=body, headers=headers)
                r.raise_for_status()
                data = r.json()
            text = data["choices"][0]["message"]["content"]
            cache.write_text(json.dumps({"text": text}), encoding="utf-8")
            _breaker.success()
            return text
        except Exception:
            _breaker.failure()
            if attempt < 2:
                await asyncio.sleep(delay)
                delay *= 2.0
    return None


def complete_sync(prompt: str, **kw) -> Optional[str]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(complete(prompt, **kw))
    # Already inside an event loop: run in a worker thread.
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(lambda: asyncio.run(complete(prompt, **kw))).result()
