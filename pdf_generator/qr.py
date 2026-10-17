from __future__ import annotations

import io


def qr_svg(url: str) -> str:
    try:
        import qrcode  # type: ignore
        import qrcode.image.svg as svg  # type: ignore
    except Exception:
        return ""
    img = qrcode.make(url, image_factory=svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    return buf.getvalue().decode("utf-8")
