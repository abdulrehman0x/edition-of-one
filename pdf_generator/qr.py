from __future__ import annotations

import io
import re


def qr_svg(url: str) -> str:
    """Return an inline <svg> QR code for `url` sized via CSS viewBox, or ''."""
    if not url or not isinstance(url, str):
        return ""
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=1,
            image_factory=SvgPathImage,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()

        buf = io.BytesIO()
        img.save(buf)
        svg = buf.getvalue().decode("utf-8", "ignore")

        # Strip XML declaration.
        if svg.lstrip().startswith("<?xml"):
            svg = svg.split("?>", 1)[1].lstrip()

        # Ensure viewBox exists; qrcode's SvgPathImage normally sets it.
        if "viewBox=" not in svg:
            wm = re.search(r'width="([\d.]+)', svg)
            hm = re.search(r'height="([\d.]+)', svg)
            if wm and hm:
                svg = svg.replace(
                    "<svg ",
                    f'<svg viewBox="0 0 {wm.group(1)} {hm.group(1)}" ',
                    1,
                )

        # Remove fixed width/height so CSS can size the SVG.
        svg = re.sub(r'\swidth="[^"]*"', "", svg, count=1)
        svg = re.sub(r'\sheight="[^"]*"', "", svg, count=1)

        return svg.strip()
    except Exception:
        return ""
