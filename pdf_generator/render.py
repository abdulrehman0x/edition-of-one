from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from . import images as _images
from . import qr as _qr

try:  # best-effort import of the shared contract
    from backend.app.models.schemas import Edition  # type: ignore
except Exception:  # pragma: no cover
    Edition = Any  # type: ignore


WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://localhost:3000")

_PKG_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(_PKG_DIR, "templates")
STATIC_DIR = os.path.join(_PKG_DIR, "static")
REPO_ROOT = os.path.dirname(_PKG_DIR)


# --------------------------------------------------------------------------
# Normalization helpers
# --------------------------------------------------------------------------

def _to_plain(obj: Any) -> Any:
    """Recursively convert Pydantic models / objects / dataclasses to plain data."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {k: _to_plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_to_plain(v) for v in obj]
    if hasattr(obj, "model_dump"):
        try:
            return _to_plain(obj.model_dump())
        except Exception:
            pass
    if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
        try:
            return _to_plain(obj.dict())
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        try:
            return {k: _to_plain(v) for k, v in vars(obj).items() if not k.startswith("_")}
        except Exception:
            pass
    return str(obj)


def _get(d: Any, *keys, default=None):
    if not isinstance(d, dict):
        return default
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default


def _tracked(a: Any) -> str:
    if not isinstance(a, dict):
        return ""
    return a.get("tracked_url") or a.get("url") or ""


# --------------------------------------------------------------------------
# Field normalization
# --------------------------------------------------------------------------

def _normalize_fields(ed: dict) -> dict:
    if not isinstance(ed, dict):
        return {}

    if "briefs" not in ed or ed["briefs"] is None:
        ed["briefs"] = ed.get("front_briefs") or ed.get("in_brief") or []
    if "secondary" not in ed or ed["secondary"] is None:
        ed["secondary"] = ed.get("secondary_stories") or []
    if "sections" not in ed or ed["sections"] is None:
        ed["sections"] = []
    if not ed.get("editors_note"):
        ed["editors_note"] = ed.get("editor_note") or ed.get("editors_letter") or ""
    if not ed.get("reader_name"):
        ed["reader_name"] = ed.get("reader") or ed.get("name") or "Reader"

    # Promote a section's first item to `feature` if no explicit feature exists.
    for sec in ed.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        if not isinstance(sec.get("items"), list):
            sec["items"] = sec.get("stories") or []
        if not sec.get("feature") and sec["items"]:
            sec["feature"] = sec["items"][0]
            sec["items"] = sec["items"][1:]
        if not isinstance(sec.get("items"), list):
            sec["items"] = []

    return ed


# --------------------------------------------------------------------------
# Dates / weather
# --------------------------------------------------------------------------

def _parse_date(s: Any) -> _dt.date:
    if isinstance(s, _dt.datetime):
        return s.date()
    if isinstance(s, _dt.date):
        return s
    if s:
        try:
            return _dt.date.fromisoformat(str(s)[:10])
        except Exception:
            pass
    return _dt.date.today()


def _dateline(d: _dt.date) -> str:
    return f"{d.strftime('%A')}, {d.day} {d.strftime('%B %Y')}"


def _weather_text(w: Any) -> str:
    if not w:
        return ""
    if isinstance(w, str):
        return w
    if isinstance(w, dict):
        city = w.get("city") or w.get("location") or ""
        hi = w.get("high", w.get("temp_high", w.get("high_c", "")))
        lo = w.get("low", w.get("temp_low", w.get("low_c", "")))
        cond = w.get("condition") or w.get("summary") or w.get("text") or ""
        if hi != "" and lo != "":
            temp = f"{hi} / {lo}"
        else:
            temp = str(hi if hi != "" else (lo if lo != "" else ""))
        parts = [str(x) for x in (city, temp, cond) if x not in ("", None)]
        return ", ".join(parts)
    return str(w)


# --------------------------------------------------------------------------
# Asset attachment (images + QR)
# --------------------------------------------------------------------------

def _collect_image_urls(ed: dict) -> list[str]:
    urls: list[str] = []

    lead = ed.get("lead")
    if isinstance(lead, dict):
        u = lead.get("image_url") or lead.get("image")
        if u:
            urls.append(u)

    for a in (ed.get("secondary") or [])[:2]:
        if isinstance(a, dict):
            u = a.get("image_url") or a.get("image")
            if u:
                urls.append(u)

    for sec in ed.get("sections") or []:
        if isinstance(sec, dict):
            f = sec.get("feature")
            if isinstance(f, dict):
                u = f.get("image_url") or f.get("image")
                if u:
                    urls.append(u)

    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
        if len(out) >= 7:
            break
    return out


def _all_articles(ed: dict) -> list[dict]:
    arts: list[dict] = []
    lead = ed.get("lead")
    if isinstance(lead, dict):
        arts.append(lead)
    for a in ed.get("secondary") or []:
        if isinstance(a, dict):
            arts.append(a)
    for a in ed.get("briefs") or []:
        if isinstance(a, dict):
            arts.append(a)
    for sec in ed.get("sections") or []:
        if not isinstance(sec, dict):
            continue
        f = sec.get("feature")
        if isinstance(f, dict):
            arts.append(f)
        for a in sec.get("items") or []:
            if isinstance(a, dict):
                arts.append(a)
    return arts


def _attach_assets(ed: dict) -> None:
    img_urls = _collect_image_urls(ed)
    try:
        budget = float(os.environ.get("PDF_IMG_BUDGET", "12"))
    except Exception:
        budget = 12.0
    img_map = _images.prepare_many(img_urls, budget_seconds=budget) if img_urls else {}

    articles = _all_articles(ed)

    qr_urls: set[str] = set()
    for a in articles:
        t = _tracked(a)
        if t:
            qr_urls.add(t)
    qr_map = {u: _qr.qr_svg(u) for u in qr_urls}

    for a in articles:
        u = a.get("image_url") or a.get("image")
        a["_img"] = img_map.get(u) if u else None
        t = _tracked(a)
        a["_link"] = t
        a["_qr"] = qr_map.get(t, "")
        a["_credit"] = a.get("image_credit") or a.get("credit") or ""


def _attach_press_gallery(ed: dict) -> None:
    pg = ed.get("press_gallery")
    if not isinstance(pg, dict):
        return
    for row in pg.get("rows") or []:
        if isinstance(row, dict):
            row["_link"] = row.get("tracked_url") or row.get("url") or ""


def _has_backpage(ed: dict) -> bool:
    bp = ed.get("back_page")
    if not isinstance(bp, dict):
        return False
    for k in ("quiz", "word_search", "markets", "on_this_day", "quiz_answers"):
        if bp.get(k):
            return True
    return False


def _attach_backpage(ed: dict) -> None:
    bp = ed.get("back_page")
    if not isinstance(bp, dict):
        ed["_has_backpage"] = False
        return
    answers = bp.get("quiz_answers")
    if not answers:
        collected: list[str] = []
        for q in bp.get("quiz") or []:
            if isinstance(q, dict):
                ans = q.get("answer")
                if ans:
                    collected.append(str(ans))
        answers = collected
    bp["_answers"] = answers or []
    ed["_has_backpage"] = _has_backpage(ed)


# --------------------------------------------------------------------------
# Jinja filters
# --------------------------------------------------------------------------

def _words_filter(text: Any, n: int = 60) -> str:
    if text is None:
        return ""
    try:
        s = str(text).strip()
    except Exception:
        return ""
    if not s:
        return ""
    words = s.split()
    try:
        n = int(n)
    except Exception:
        n = 60
    if len(words) <= n:
        return s
    truncated = " ".join(words[:n])
    best = -1
    for term in (".", "!", "?"):
        idx = truncated.rfind(term)
        if idx > best and idx > int(len(truncated) * 0.5):
            best = idx
    if best > 0:
        return truncated[: best + 1]
    return truncated + "\u2026"


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml", "j2", "html.j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["words"] = _words_filter
    return env


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------

def build_html(
    edition: Edition,
    public_base: str | None = None,
    page: str = "A3",
) -> str:
    ed = _to_plain(edition)
    if not isinstance(ed, dict):
        ed = {}
    ed = _normalize_fields(ed)

    ed["_dateline"] = _dateline(_parse_date(ed.get("date")))
    ed["_weather"] = _weather_text(ed.get("weather"))

    _attach_press_gallery(ed)
    _attach_assets(ed)
    _attach_backpage(ed)

    audio_url = ed.get("audio_url")
    if audio_url:
        date_slug = _parse_date(ed.get("date")).isoformat()
        ed["_listen_qr"] = _qr.qr_svg(f"{WEB_BASE_URL}/edition/{date_slug}?listen=1")
    else:
        ed["_listen_qr"] = ""

    env = _make_env()
    tpl = env.get_template("edition.html.j2")
    return tpl.render(edition=ed, page=page, public_base=public_base or "")


def render_pdf(
    edition: Edition,
    out_path: str,
    public_base: str | None = None,
    page: str = "A3",
) -> str:
    html = build_html(edition, public_base=public_base, page=page)
    out_dir = os.path.dirname(os.path.abspath(out_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    HTML(string=html, base_url=REPO_ROOT).write_pdf(out_path)
    return out_path


def count_pages(edition: Edition) -> int:
    html = build_html(edition)
    doc = HTML(string=html, base_url=REPO_ROOT).render()
    try:
        return len(doc.pages)
    except Exception:
        return 0


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _render_all_demo() -> None:
    cache_root = os.path.join(REPO_ROOT, "data", "cache", "editions")
    out_dir = os.path.join(REPO_ROOT, "out")
    samples_dir = os.path.join(REPO_ROOT, "docs", "samples")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(samples_dir, exist_ok=True)

    readers = ["demo-ayesha", "demo-bilal", "demo-sara"]
    for reader in readers:
        rdir = os.path.join(cache_root, reader)
        if not os.path.isdir(rdir):
            continue
        files = sorted(f for f in os.listdir(rdir) if f.endswith(".json"))
        if not files:
            continue
        latest = files[-1]
        src = os.path.join(rdir, latest)
        try:
            with open(src, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        out_path = os.path.join(out_dir, f"{reader}.pdf")
        sample_path = os.path.join(samples_dir, f"{reader}.pdf")
        try:
            render_pdf(data, out_path)
            render_pdf(data, sample_path)
            print(out_path)
        except Exception as exc:  # pragma: no cover
            print(f"failed {reader}: {exc}", file=os.sys.stderr)


def _cli(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pdf_generator.render")
    ap.add_argument("--edition")
    ap.add_argument("--out")
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--page", default="A3", choices=["A3", "A4"])
    ap.add_argument("--all-demo", action="store_true")
    args = ap.parse_args(argv)

    if args.all_demo:
        _render_all_demo()
        return 0

    if not args.edition or not args.out:
        ap.error("--edition and --out are required unless --all-demo is used")

    with open(args.edition, "r", encoding="utf-8") as f:
        data = json.load(f)

    if args.html_only:
        html = build_html(data, page=args.page)
        print(html)
    else:
        render_pdf(data, args.out, page=args.page)
        print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
