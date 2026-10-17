from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "backend"))

try:
    from jinja2 import Environment, FileSystemLoader  # type: ignore
except Exception as exc:  # pragma: no cover
    print(f"Jinja2 required: {exc}")
    raise SystemExit(0)


def _env() -> "Environment":
    # autoescape: article text comes from RSS/web pages and may contain markup.
    # The QR SVG is the only trusted HTML and is marked |safe in the macro.
    return Environment(
        loader=FileSystemLoader(str(HERE / "templates")),
        autoescape=True,
    )


def _decorate(edition: dict) -> dict:
    # Attach a rendered QR SVG (link back to the live edition).
    try:
        from qr import qr_svg  # noqa: WPS433
    except Exception:
        try:
            from pdf_generator.qr import qr_svg  # type: ignore
        except Exception:
            qr_svg = None  # type: ignore
    if qr_svg is not None:
        edition = dict(edition)
        base = os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
        edition["qr_svg"] = qr_svg(f"{base}/edition/{edition.get('reader_id', 'demo')}")
    return edition


def build_html(edition: dict, env: Optional["Environment"] = None) -> str:
    env = env or _env()
    tmpl = env.get_template("edition.html.j2")
    return tmpl.render(edition=_decorate(edition))


def render_pdf(html: str, out_path: Path) -> Path:
    from weasyprint import HTML, CSS  # type: ignore

    out_path.parent.mkdir(parents=True, exist_ok=True)
    css_path = HERE / "static/broadsheet.css"
    stylesheets = [CSS(filename=str(css_path))] if css_path.exists() else None
    HTML(string=html, base_url=str(HERE)).write_pdf(
        str(out_path), stylesheets=stylesheets
    )
    return out_path


def _all_demo() -> list:
    cache = ROOT / "data/cache/editions"
    if not cache.exists():
        return []
    return sorted(cache.rglob("*.json"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Render Edition of One broadsheets.")
    ap.add_argument("--all-demo", action="store_true")
    ap.add_argument("--edition", type=str, default=None)
    ap.add_argument("--out", type=str, default="data/pdfs")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    targets = []
    if args.all_demo:
        targets.extend(_all_demo())
    if args.edition:
        targets.append(Path(args.edition))

    if not targets:
        print("No editions found. Run `make seed` first.")
        return

    out_dir = ROOT / args.out

    for p in targets:
        p = Path(p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            print(f"  [skip] {p}")
            continue
        html = build_html(data)
        if args.check:
            print(f"  [check] {p} -> html {len(html)} bytes")
            continue
        # <reader>_<date>.pdf — the date alone collides across readers.
        out = out_dir / f"{p.parent.name}_{p.stem}.pdf"
        render_pdf(html, out)
        print(f"  wrote {out}")


if __name__ == "__main__":
    main()
