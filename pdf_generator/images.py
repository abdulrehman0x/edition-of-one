from __future__ import annotations

import base64
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List

try:
    from PIL import Image, ImageEnhance  # type: ignore
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageEnhance = None  # type: ignore

_CACHE: Dict[str, str] = {}
_POOL = ThreadPoolExecutor(max_workers=4)


def _process(data: bytes, contrast: float = 1.15, thumb: int = 480) -> str:
    if Image is None:
        return base64.b64encode(data).decode("ascii")
    img = Image.open(io.BytesIO(data)).convert("L")
    if ImageEnhance is not None:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    img.thumbnail((thumb, thumb))
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def grayscale_thumb_b64(data: bytes, key: str) -> str:
    if key in _CACHE:
        return _CACHE[key]
    b64 = _process(data)
    _CACHE[key] = b64
    return b64


def prewarm(items: List[tuple]) -> Dict[str, str]:
    futures = {
        key: _POOL.submit(grayscale_thumb_b64, data, key) for key, data in items
    }
    return {k: f.result() for k, f in futures.items()}
