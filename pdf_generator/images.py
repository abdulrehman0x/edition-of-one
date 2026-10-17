from __future__ import annotations

import base64
import hashlib
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from PIL import Image, ImageEnhance, ImageOps

USER_AGENT = (
    "EditionOfOne-Print/1.0 (+https://editionofone.local; "
    "grayscale broadsheet renderer)"
)


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()


def _timeout() -> float:
    try:
        return float(os.environ.get("PDF_HTTP_TIMEOUT", "4"))
    except Exception:
        return 4.0


def prepare_image(url: str, cache_dir: str = "data/cache/img") -> str | None:
    """Fetch, grayscale, and JPEG-compress an image. Return a data URI or None."""
    if not url or not isinstance(url, str):
        return None
    if os.environ.get("PDF_OFFLINE") == "1":
        return None

    try:
        os.makedirs(cache_dir, exist_ok=True)
    except Exception:
        pass

    key = _sha1(url)
    cache_path = os.path.join(cache_dir, key + ".jpg")

    if os.path.exists(cache_path):
        try:
            with open(cache_path, "rb") as f:
                data = f.read()
            if data:
                return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
        except Exception:
            pass

    try:
        with httpx.Client(
            timeout=_timeout(),
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:
            r = client.get(url)
            r.raise_for_status()
            content = r.content
        if not content:
            return None

        img = Image.open(io.BytesIO(content))
        img = img.convert("L")
        img = ImageOps.autocontrast(img, cutoff=1)
        img = ImageEnhance.Contrast(img).enhance(1.15)

        if img.width > 1200:
            ratio = 1200.0 / float(img.width)
            new_h = max(1, int(img.height * ratio))
            img = img.resize((1200, new_h), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=70)
        data = buf.getvalue()

        try:
            with open(cache_path, "wb") as f:
                f.write(data)
        except Exception:
            pass

        return "data:image/jpeg;base64," + base64.b64encode(data).decode("ascii")
    except Exception:
        return None


def prepare_many(
    urls,
    budget_seconds: float = 12,
) -> dict[str, str | None]:
    """Prepare several images concurrently, giving up after `budget_seconds`."""
    urls = [u for u in urls if u]
    result: dict[str, str | None] = {u: None for u in urls}
    if not urls:
        return result

    try:
        budget_seconds = float(budget_seconds)
    except Exception:
        budget_seconds = 12.0

    executor = ThreadPoolExecutor(max_workers=4)
    try:
        futures = {executor.submit(prepare_image, u): u for u in urls}
        try:
            for fut in as_completed(futures, timeout=budget_seconds):
                u = futures[fut]
                try:
                    result[u] = fut.result()
                except Exception:
                    result[u] = None
        except Exception:
            # Budget exceeded — leave unresolved urls as None.
            pass
    finally:
        try:
            executor.shutdown(wait=False)
        except Exception:
            pass

    return result
