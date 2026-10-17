#!/usr/bin/env python3
"""Bootstrap script for the 'Edition of One' PDF generator.

Run this once from the repo root:

    python create_pdf_generator.py

It writes every file in the ``pdf_generator/`` package, the test file,
and appends the PDF targets to the ``Makefile`` (skipping if the section
is already present so it is safe to re-run).
"""
from __future__ import annotations

import os
import sys


FILES: dict[str, str] = {}


# ---------------------------------------------------------------------------
# pdf_generator/__init__.py
# ---------------------------------------------------------------------------
FILES["pdf_generator/__init__.py"] = ""


# ---------------------------------------------------------------------------
# pdf_generator/images.py
# ---------------------------------------------------------------------------
FILES["pdf_generator/images.py"] = r'''from __future__ import annotations

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
'''


# ---------------------------------------------------------------------------
# pdf_generator/qr.py
# ---------------------------------------------------------------------------
FILES["pdf_generator/qr.py"] = r'''from __future__ import annotations

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
'''


# ---------------------------------------------------------------------------
# pdf_generator/render.py
# ---------------------------------------------------------------------------
FILES["pdf_generator/render.py"] = r'''from __future__ import annotations

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
'''


# ---------------------------------------------------------------------------
# pdf_generator/templates/_macros.html.j2
# ---------------------------------------------------------------------------
FILES["pdf_generator/templates/_macros.html.j2"] = r'''{% macro kicker(art) -%}
{% if art.topic %}<div class="kicker">{{ art.topic }}</div>{% endif %}
{%- endmacro %}

{% macro source_link(art, prefix='Read at ') -%}
{% if art.source %}<a class="source-link" href="{{ art._link or '#' }}">{{ prefix }}{{ art.source }}</a>{% endif %}
{%- endmacro %}

{% macro why_line(art) -%}
{% if art.why %}<div class="why">Why: {{ art.why }}</div>{% endif %}
{%- endmacro %}

{% macro outside_tag(art) -%}
{% if art.outside_bubble %}<span class="outside-tag">Outside your usual reading</span>{% endif %}
{%- endmacro %}

{% macro ornament() -%}
<div class="ornament" aria-hidden="true">&#10086;</div>
{%- endmacro %}

{% macro article_image(art) -%}
{% if art._img %}
<figure class="art-figure">
  <img src="{{ art._img }}" alt="">
  {% if art._credit %}<figcaption>{{ art._credit }}</figcaption>{% endif %}
</figure>
{% else %}
{{ ornament() }}
{% endif %}
{%- endmacro %}

{% macro qr_block(svg, caption) -%}
{% if svg %}
<figure class="qr-figure">
  <div class="qr">{{ svg|safe }}</div>
  {% if caption %}<figcaption>{{ caption }}</figcaption>{% endif %}
</figure>
{% endif %}
{%- endmacro %}

{% macro press_gallery(pg) -%}
{% if pg %}
<div class="press-gallery">
  <div class="pg-title">One story, three papers</div>
  {% if pg.topic_label %}<div class="pg-topic">{{ pg.topic_label }}</div>{% endif %}
  <div class="pg-cols">
    {% for row in (pg.rows or []) %}
      <div class="pg-col">
        {% if row.source %}<div class="pg-source">{{ row.source }}</div>{% endif %}
        <a class="pg-headline" href="{{ row._link or row.url or '#' }}">{{ row.headline or '' }}</a>
        {% if row.emphasis %}<div class="pg-emph">{{ row.emphasis }}</div>{% endif %}
      </div>
    {% endfor %}
  </div>
  {% if pg.agreed_facts %}
    <div class="pg-agree">All outlets agree: {{ (pg.agreed_facts|join(' ')) }}</div>
  {% endif %}
  {% if pg.open_question %}
    <div class="pg-question"><em>{{ pg.open_question }}</em></div>
  {% endif %}
  <div class="pg-footnote">Framing differences, not fact-checks.</div>
</div>
{% endif %}
{%- endmacro %}
'''


# ---------------------------------------------------------------------------
# pdf_generator/templates/edition.html.j2
# ---------------------------------------------------------------------------
FILES["pdf_generator/templates/edition.html.j2"] = r'''{% import "_macros.html.j2" as m -%}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Edition of One — {{ edition.reader_name or '' }}</title>
<link rel="stylesheet" href="pdf_generator/static/broadsheet.css">
{% if page == 'A4' %}
<style>
@page { size: A4; margin: 10mm 9mm 12mm; }
html { font-size: 6.84pt; }
body { font-size: 6.84pt; line-height: 1.3; }
.nameplate { font-size: 47.5pt; }
.dateline-strip { font-size: 6.1pt; }
.kicker { font-size: 5.4pt; }
.lead-headline { font-size: 28.8pt; }
.lead-deck { font-size: 8.6pt; }
.art-figure figcaption { font-size: 5pt; }
.dropcap::first-letter { font-size: 24.5pt; }
.source-link { font-size: 5.8pt; }
.qr { width: 15.8mm; height: 15.8mm; }
.qr-figure figcaption { font-size: 4.7pt; }
.box-title { font-size: 7.9pt; }
.editor-note { font-size: 6.5pt; }
.brief-headline { font-size: 7.6pt; }
.brief-body { font-size: 6.1pt; }
.sec-headline { font-size: 10.1pt; }
.sec-body { font-size: 6.3pt; }
.inside-line { font-size: 5.8pt; }
.why-lead { font-size: 5.4pt; }
.section-header { font-size: 13pt; }
.pg-title { font-size: 10.1pt; }
.pg-topic { font-size: 7.2pt; }
.pg-source { font-size: 5.4pt; }
.pg-headline { font-size: 9.4pt; }
.pg-emph { font-size: 6.1pt; }
.pg-agree { font-size: 6.5pt; }
.pg-question { font-size: 6.5pt; }
.pg-footnote { font-size: 5pt; }
.feature-headline { font-size: 15.8pt; }
.feature-deck { font-size: 7.9pt; }
.story-headline { font-size: 7.9pt; }
.story-deck { font-size: 6.5pt; }
.story-body { font-size: 6.1pt; }
.why { font-size: 5.4pt; }
.outside-tag { font-size: 4.7pt; }
.ornament { font-size: 17.3pt; }
.back-title { font-size: 8.6pt; }
.quiz li { font-size: 6.5pt; }
.q-opts { font-size: 6.1pt; }
.wordsearch td { font-size: 5.8pt; }
.ws-words { font-size: 5.8pt; }
.markets { font-size: 6.1pt; }
.otd { font-size: 6.5pt; }
.quiz-answers { font-size: 5pt; }
</style>
{% endif %}
</head>
<body>

{# ===================== PAGE 1 — FRONT ===================== #}
<section class="front">
  <header class="nameplate-wrap">
    <h1 class="nameplate">Edition of One</h1>
    <div class="rule-double"></div>
    <div class="rule-thin"></div>
    <div class="dateline-strip">
      <span class="dl-left">Printed for {{ edition.reader_name or '' }}</span>
      <span class="dl-center">No. {{ edition.issue_no or '' }} &mdash; {{ edition._dateline }}</span>
      <span class="dl-right">{{ edition._weather or '' }}</span>
    </div>
    <div class="rule-thin"></div>
  </header>

  {% set lead = edition.lead %}
  {% if lead %}
  <div class="lead-row">
    <div class="lead-main">
      {{ m.kicker(lead) }}
      <h2 class="lead-headline">
        <a href="{{ lead._link or '#' }}">{{ lead.headline or '' }}</a>
      </h2>
      {% if lead.deck %}<p class="lead-deck">{{ lead.deck }}</p>{% endif %}
      {{ m.article_image(lead) }}
      <div class="lead-body">
        <p class="dropcap">{{ (lead.body or '')|words(110) }}</p>
      </div>
      <div class="lead-foot">
        {% if lead.source %}<a class="source-link" href="{{ lead._link or '#' }}">Read the original at {{ lead.source }}</a>{% endif %}
        {{ m.qr_block(lead._qr, 'Scan to read') }}
      </div>
    </div>
    <aside class="lead-side">
      <div class="box editor-box">
        <h3 class="box-title">From the Editor</h3>
        <p class="editor-note">{{ edition.editors_note or '' }}</p>
      </div>
      {% if edition._listen_qr %}
      <div class="box listen-box">
        <h3 class="box-title">Listen</h3>
        {{ m.qr_block(edition._listen_qr, 'Hear this edition') }}
      </div>
      {% endif %}
      {% if edition.briefs %}
      <div class="box briefs-box">
        <h3 class="box-title">In Brief</h3>
        {% for b in (edition.briefs or [])[:3] %}
          <div class="brief">
            <a class="brief-headline" href="{{ b._link or '#' }}">{{ b.headline or '' }}</a>
            <p class="brief-body">{{ (b.body or '')|words(35) }}</p>
          </div>
        {% endfor %}
      </div>
      {% endif %}
    </aside>
  </div>
  {% endif %}

  {% set secs = edition.secondary or [] %}
  {% if secs %}
  <div class="secondary-row">
    {% for a in secs[:4] %}
      <div class="sec-col">
        {{ m.kicker(a) }}
        <h3 class="sec-headline"><a href="{{ a._link or '#' }}">{{ a.headline or '' }}</a></h3>
        <p class="sec-body">{{ (a.body or '')|words(60) }}</p>
        {% if a.source %}<a class="source-link" href="{{ a._link or '#' }}">Read at {{ a.source }}</a>{% endif %}
        {% if loop.index0 < 2 %}{{ m.qr_block(a._qr, '') }}{% endif %}
      </div>
    {% endfor %}
  </div>
  {% endif %}

  <footer class="front-footer">
    <div class="inside-line">
      <strong>Inside:</strong>
      {{ (edition.sections or [])|map(attribute='name', default='')|join('  ·  ') }}
    </div>
    {% if lead and lead.why %}
      <div class="why-lead"><em>Why you are seeing this: {{ lead.why }}</em></div>
    {% endif %}
  </footer>
</section>

{# ===================== INSIDE PAGES ===================== #}
{% set sections = edition.sections or [] %}
{% if sections %}
  {% for sec in sections %}
    <section class="page inside">
      <div class="section-header">{{ sec.name or '' }}</div>

      {% if loop.first and edition.press_gallery %}
        {{ m.press_gallery(edition.press_gallery) }}
      {% endif %}

      {% set feat = sec.feature %}
      {% if feat %}
        <div class="feature-block">
          <div class="feature-img">
            {{ m.article_image(feat) }}
          </div>
          <div class="feature-text">
            {{ m.kicker(feat) }}
            <h3 class="feature-headline"><a href="{{ feat._link or '#' }}">{{ feat.headline or '' }}</a></h3>
            {% if feat.deck %}<p class="feature-deck">{{ feat.deck }}</p>{% endif %}
            <p class="dropcap feature-body">{{ (feat.body or '')|words(110) }}</p>
            {{ m.why_line(feat) }}
            {{ m.outside_tag(feat) }}
            {{ m.source_link(feat) }}
          </div>
        </div>
      {% endif %}

      {% set items = sec.items or [] %}
      {% if items %}
        <div class="section-columns">
          {% for a in items %}
            <div class="story">
              {{ m.kicker(a) }}
              <h4 class="story-headline"><a href="{{ a._link or '#' }}">{{ a.headline or '' }}</a></h4>
              {% if a.deck %}<p class="story-deck">{{ a.deck }}</p>{% endif %}
              <p class="story-body">{{ (a.body or '')|words(60) }}</p>
              {{ m.why_line(a) }}
              {{ m.outside_tag(a) }}
              {{ m.source_link(a) }}
            </div>
          {% endfor %}
        </div>
      {% endif %}
    </section>
  {% endfor %}
{% elif edition.press_gallery %}
  <section class="page inside">
    <div class="section-header">Across the Press</div>
    {{ m.press_gallery(edition.press_gallery) }}
  </section>
{% endif %}

{# ===================== BACK PAGE ===================== #}
{% if edition._has_backpage and edition.back_page %}
  {% set bp = edition.back_page %}
  <section class="page back">
    <div class="section-header back-header">The Back Page</div>
    <div class="back-cols">
      <div class="back-col">
        <h3 class="back-title">Quiz</h3>
        <ol class="quiz">
          {% for q in (bp.quiz or []) %}
            <li>
              <div class="q-text">{{ q.question or '' }}</div>
              {% if q.options %}
                <ol class="q-opts" type="A">
                  {% for opt in q.options %}<li>{{ opt }}</li>{% endfor %}
                </ol>
              {% endif %}
            </li>
          {% endfor %}
        </ol>
      </div>
      <div class="back-col">
        <h3 class="back-title">Word Search</h3>
        {% set ws = bp.word_search %}
        {% if ws %}
          <table class="wordsearch">
            {% for row in (ws.grid or []) %}
              <tr>{% for cell in row %}<td>{{ cell }}</td>{% endfor %}</tr>
            {% endfor %}
          </table>
          {% if ws.words %}<div class="ws-words">{{ (ws.words|join(', ')) }}</div>{% endif %}
        {% endif %}
      </div>
      <div class="back-col">
        <h3 class="back-title">Markets</h3>
        {% if bp.markets %}
          <table class="markets">
            {% for row in bp.markets %}
              {% set chg = (row.change if row.change is defined else '')|string %}
              <tr>
                <td class="mk-name">{{ row.name or '' }}</td>
                <td class="mk-val">{{ row.value if row.value is defined else (row.price if row.price is defined else '') }}</td>
                <td class="mk-chg">
                  {% if chg.startswith('-') %}&#9660;{% elif chg %}&#9650;{% endif %}
                  {{ chg }}
                </td>
              </tr>
            {% endfor %}
          </table>
        {% endif %}
        <h3 class="back-title">On This Day</h3>
        {% for otd in (bp.on_this_day or []) %}
          <div class="otd"><strong>{{ otd.year or '' }}</strong> {{ otd.text or '' }}</div>
        {% endfor %}
      </div>
    </div>
    {% if bp._answers %}
      <div class="quiz-answers">
        <strong>Answers:</strong> {{ (bp._answers|join('   ')) }}
      </div>
    {% endif %}
  </section>
{% endif %}

</body>
</html>
'''


# ---------------------------------------------------------------------------
# pdf_generator/static/broadsheet.css
# ---------------------------------------------------------------------------
FILES["pdf_generator/static/broadsheet.css"] = r'''/* ============================================================
   Edition of One — broadsheet stylesheet (WeasyPrint-safe)
   ============================================================ */

@font-face {
  font-family: 'Playfair Display';
  src: local('Playfair Display'), local('PlayfairDisplay-Regular'),
       url('fonts/PlayfairDisplay-Regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: 'Playfair Display';
  src: local('Playfair Display Bold'), local('PlayfairDisplay-Bold'),
       url('fonts/PlayfairDisplay-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}
@font-face {
  font-family: 'Libre Caslon Text';
  src: local('Libre Caslon Text'), local('LibreCaslonText-Regular'),
       url('fonts/LibreCaslonText-Regular.ttf') format('truetype');
  font-weight: 400;
  font-style: normal;
}
@font-face {
  font-family: 'Libre Caslon Text';
  src: local('Libre Caslon Text Italic'), local('LibreCaslonText-Italic'),
       url('fonts/LibreCaslonText-Italic.ttf') format('truetype');
  font-weight: 400;
  font-style: italic;
}
@font-face {
  font-family: 'Libre Caslon Text';
  src: local('Libre Caslon Text Bold'), local('LibreCaslonText-Bold'),
       url('fonts/LibreCaslonText-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}
@font-face {
  font-family: 'UnifrakturCook';
  src: local('UnifrakturCook'), local('UnifrakturCook Bold'),
       url('fonts/UnifrakturCook-Bold.ttf') format('truetype');
  font-weight: 700;
  font-style: normal;
}

/* ---------- Page setup ---------- */
@page {
  size: A3;
  margin: 16mm 14mm 18mm;
  background: #f5efe0;
  @top-center {
    content: string(section-name) "  ·  " string(edition-date);
    font-family: 'Libre Caslon Text', Georgia, 'Times New Roman', serif;
    font-size: 8pt;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: #333;
  }
  @bottom-center {
    content: counter(page);
    font-family: 'Libre Caslon Text', Georgia, 'Times New Roman', serif;
    font-size: 9pt;
    color: #333;
  }
}
@page :first {
  @top-center { content: none; }
}

/* ---------- Base ---------- */
html {
  color: #111;
  font-size: 9.5pt;
  line-height: 1.32;
  hyphens: auto;
  font-family: 'Libre Caslon Text', 'Caslon', Georgia, 'Times New Roman', serif;
}
body {
  margin: 0;
  padding: 0;
  background: #f5efe0;
  font-size: 9.5pt;
}
p { orphans: 2; widows: 2; }
a { color: inherit; text-decoration: none; }

/* ---------- Front nameplate ---------- */
.nameplate-wrap { text-align: center; margin-bottom: 4mm; }
.nameplate {
  font-family: 'UnifrakturCook', 'Playfair Display', Georgia, serif;
  font-weight: 700;
  font-size: 66pt;
  line-height: 1;
  letter-spacing: .01em;
  margin: 0 0 2mm 0;
}
.rule-double {
  border-top: 2pt double #111;
  height: 0;
  margin: 0 0 1mm 0;
}
.rule-thin { border-top: .5pt solid #333; margin: 1mm 0; }

.dateline-strip {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 8.5pt;
  letter-spacing: .06em;
  text-transform: uppercase;
  padding: 1mm 0;
}
.dl-left { flex: 1; text-align: left; }
.dl-center { flex: 1; text-align: center; font-weight: 700; string-set: edition-date content(); }
.dl-right { flex: 1; text-align: right; }

/* ---------- Front lead ---------- */
.lead-row {
  display: flex;
  gap: 6mm;
  margin-top: 4mm;
  padding-bottom: 3mm;
  border-bottom: .5pt solid #333;
}
.lead-main {
  flex: 0 0 64%;
  padding-right: 6mm;
  border-right: .5pt solid #333;
}
.lead-side { flex: 0 0 36%; }

.kicker {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 7.5pt;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: #333;
  margin-bottom: 1mm;
  font-weight: 700;
}
.lead-headline {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 40pt;
  line-height: 1.02;
  margin: 0 0 2mm 0;
  letter-spacing: -.005em;
}
.lead-headline a { color: #111; }
.lead-deck {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-style: italic;
  font-size: 12pt;
  line-height: 1.28;
  margin: 0 0 3mm 0;
  color: #222;
}
.art-figure { margin: 0 0 3mm 0; }
.art-figure img { width: 100%; height: auto; display: block; }
.art-figure figcaption {
  font-size: 7pt;
  color: #444;
  font-style: italic;
  margin-top: 1mm;
}
.lead-body {
  column-count: 2;
  column-gap: 7mm;
  column-rule: .5pt solid #333;
}
.lead-body p { margin: 0 0 2mm 0; text-align: justify; }

.dropcap::first-letter {
  float: left;
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 34pt;
  line-height: .85;
  padding: 2pt 4pt 0 0;
}

.lead-foot {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 4mm;
  margin-top: 3mm;
}
.source-link {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 8pt;
  font-style: italic;
  color: #333;
  border-bottom: .5pt solid #333;
}

/* ---------- QR ---------- */
.qr-figure { margin: 0; text-align: center; }
.qr { width: 22mm; height: 22mm; }
.qr svg { width: 100%; height: 100%; display: block; }
.qr-figure figcaption {
  font-size: 6.5pt;
  color: #333;
  margin-top: 1mm;
  letter-spacing: .05em;
  text-transform: uppercase;
}
.sec-col .qr { width: 16mm; height: 16mm; }

/* ---------- Aside boxes ---------- */
.box {
  border: .5pt solid #333;
  padding: 3mm;
  margin-bottom: 4mm;
  break-inside: avoid;
}
.box-title {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-size: 11pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin: 0 0 2mm 0;
  border-bottom: .5pt solid #333;
  padding-bottom: 1mm;
}
.editor-note {
  font-style: italic;
  font-size: 9pt;
  line-height: 1.35;
  margin: 0;
  text-align: justify;
}
.brief {
  padding: 2mm 0;
  border-bottom: .3pt dotted #666;
  break-inside: avoid;
}
.brief:last-child { border-bottom: none; }
.brief-headline {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 10.5pt;
  line-height: 1.15;
  display: block;
  margin-bottom: 1mm;
}
.brief-body { font-size: 8.5pt; margin: 0; text-align: justify; }

/* ---------- Secondary row ---------- */
.secondary-row {
  display: flex;
  margin-top: 4mm;
  padding-bottom: 3mm;
  border-bottom: .5pt solid #333;
}
.sec-col {
  flex: 1 1 25%;
  padding: 0 3mm;
  border-right: .5pt solid #333;
  break-inside: avoid;
}
.sec-col:last-child { border-right: none; }
.sec-headline {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 14pt;
  line-height: 1.1;
  margin: 0 0 2mm 0;
}
.sec-body {
  font-size: 8.8pt;
  margin: 0 0 2mm 0;
  text-align: justify;
}

/* ---------- Front footer ---------- */
.front-footer { margin-top: 3mm; }
.inside-line {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 8pt;
  letter-spacing: .12em;
  text-transform: uppercase;
  border-top: .5pt solid #333;
  border-bottom: .5pt solid #333;
  padding: 1.5mm 0;
  text-align: center;
}
.why-lead {
  font-size: 7.5pt;
  color: #333;
  margin-top: 2mm;
  text-align: center;
}

/* ---------- Inside pages ---------- */
.inside { break-before: page; }
.section-header {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-size: 18pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  border-top: 2pt solid #111;
  border-bottom: .5pt solid #333;
  padding: 2mm 0 1.5mm 0;
  margin: 0 0 4mm 0;
  string-set: section-name content();
}

/* ---------- Press gallery ---------- */
.press-gallery {
  border: 1pt solid #111;
  padding: 4mm;
  margin-bottom: 5mm;
  break-inside: avoid;
}
.pg-title {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-size: 14pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  text-align: center;
  margin-bottom: 3mm;
}
.pg-topic {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 10pt;
  font-style: italic;
  text-align: center;
  margin-bottom: 3mm;
}
.pg-cols { display: flex; gap: 5mm; }
.pg-col { flex: 1; border-left: .5pt solid #333; padding-left: 4mm; }
.pg-col:first-child { border-left: none; padding-left: 0; }
.pg-source {
  font-size: 7.5pt;
  text-transform: uppercase;
  letter-spacing: .14em;
  color: #333;
  font-weight: 700;
}
.pg-headline {
  display: block;
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 13pt;
  line-height: 1.14;
  margin: 1.5mm 0;
}
.pg-emph { font-size: 8.5pt; font-style: italic; color: #333; }
.pg-agree { margin-top: 3mm; font-size: 9pt; text-align: justify; }
.pg-question { margin-top: 2mm; font-size: 9pt; text-align: justify; }
.pg-footnote {
  margin-top: 2mm;
  font-size: 7pt;
  color: #555;
  font-style: italic;
  text-align: right;
}

/* ---------- Section feature ---------- */
.feature-block {
  display: flex;
  gap: 6mm;
  margin-bottom: 5mm;
  padding-bottom: 4mm;
  border-bottom: .5pt solid #333;
  break-inside: avoid;
}
.feature-img { flex: 0 0 38%; }
.feature-img .art-figure { margin: 0; }
.feature-text { flex: 1; }
.feature-headline {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 22pt;
  line-height: 1.06;
  margin: 0 0 2mm 0;
}
.feature-deck {
  font-style: italic;
  font-size: 11pt;
  margin: 0 0 2mm 0;
  text-align: justify;
}
.feature-body { margin: 0 0 2mm 0; text-align: justify; }

/* ---------- Section 4-column body ---------- */
.section-columns {
  column-count: 4;
  column-gap: 7mm;
  column-rule: .5pt solid #333;
}
.story { break-inside: avoid; margin-bottom: 4mm; }
.story-headline {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-weight: 700;
  font-size: 11pt;
  line-height: 1.14;
  margin: 0 0 1.5mm 0;
}
.story-deck {
  font-style: italic;
  font-size: 9pt;
  margin: 0 0 1.5mm 0;
  text-align: justify;
}
.story-body {
  font-size: 8.5pt;
  margin: 0 0 1.5mm 0;
  text-align: justify;
}

.why {
  font-size: 7.5pt;
  color: #666;
  font-style: italic;
  margin: 1mm 0;
  line-height: 1.2;
}
.outside-tag {
  display: inline-block;
  font-size: 6.5pt;
  letter-spacing: .1em;
  text-transform: uppercase;
  border: .5pt solid #333;
  padding: .5mm 1.5mm;
  margin: 1mm 0;
}

.ornament {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-size: 24pt;
  text-align: center;
  color: #333;
  border: .5pt solid #333;
  padding: 8mm 0;
  margin: 2mm 0;
  letter-spacing: .3em;
}

/* ---------- Back page ---------- */
.back { break-before: page; }
.back-header { string-set: section-name content(); }
.back-cols { display: flex; gap: 6mm; }
.back-col {
  flex: 1;
  padding-right: 4mm;
  border-right: .5pt solid #333;
}
.back-col:last-child { border-right: none; padding-right: 0; }
.back-title {
  font-family: 'Playfair Display', 'Playfair', Georgia, serif;
  font-size: 12pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .06em;
  margin: 0 0 2mm 0;
  border-bottom: .5pt solid #333;
  padding-bottom: 1mm;
}
.quiz { padding-left: 5mm; margin: 0 0 4mm 0; }
.quiz li { margin-bottom: 2mm; font-size: 9pt; }
.q-text { font-weight: 700; }
.q-opts {
  padding-left: 4mm;
  margin: 1mm 0 0 0;
  font-size: 8.5pt;
  list-style-type: upper-alpha;
}

.wordsearch { border-collapse: collapse; margin-bottom: 3mm; }
.wordsearch td {
  font-family: 'Courier New', 'DejaVu Sans Mono', monospace;
  font-size: 8pt;
  width: 4mm;
  height: 4mm;
  text-align: center;
  vertical-align: middle;
  border: .3pt solid #999;
  padding: 0;
}
.ws-words {
  font-family: 'Libre Caslon Text', Georgia, serif;
  font-size: 8pt;
  letter-spacing: .04em;
}

.markets {
  width: 100%;
  border-collapse: collapse;
  font-family: 'Courier New', 'DejaVu Sans Mono', monospace;
  font-size: 8.5pt;
  margin-bottom: 4mm;
}
.markets td { padding: .8mm 0; border-bottom: .3pt dotted #666; }
.mk-name { text-align: left; }
.mk-val { text-align: right; }
.mk-chg { text-align: right; width: 25%; }

.otd { font-size: 9pt; margin-bottom: 2mm; line-height: 1.3; }
.otd strong { font-weight: 700; }

.quiz-answers {
  margin-top: 6mm;
  padding-top: 2mm;
  border-top: .5pt solid #333;
  font-size: 7pt;
  text-align: center;
  color: #333;
  transform: rotate(180deg);
}
'''


# ---------------------------------------------------------------------------
# pdf_generator/static/fonts/README.md
# ---------------------------------------------------------------------------
FILES["pdf_generator/static/fonts/README.md"] = r'''# Fonts

Place these exact files in this directory (`pdf_generator/static/fonts/`):

- `PlayfairDisplay-Regular.ttf`
- `PlayfairDisplay-Bold.ttf`
- `LibreCaslonText-Regular.ttf`
- `LibreCaslonText-Italic.ttf`
- `LibreCaslonText-Bold.ttf`
- `UnifrakturCook-Bold.ttf`

The stylesheet also declares `local()` sources, so if the fonts are already
installed on the system (e.g. via `fontconfig`) the layout works without these
files. As a final fallback the font stacks end in a generic `serif`.

## Source

Google Fonts:

- Playfair Display — https://fonts.google.com/specimen/Playfair+Display
- Libre Caslon Text — https://fonts.google.com/specimen/Libre+Caslon+Text
- UnifrakturCook — https://fonts.google.com/specimen/UnifrakturCook

Download the TTFs, rename them to the names above, and drop them here.
'''


# ---------------------------------------------------------------------------
# backend/tests/test_pdf.py
# ---------------------------------------------------------------------------
FILES["backend/tests/test_pdf.py"] = r'''from __future__ import annotations

import json
import os

import pytest

from pdf_generator.render import build_html, count_pages, render_pdf


REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
SAMPLE = os.path.join(REPO_ROOT, "frontend", "public", "sample-edition.json")


def _load_sample() -> dict:
    with open(SAMPLE, "r", encoding="utf-8") as f:
        return json.load(f)


def _clone(base: dict) -> dict:
    return json.loads(json.dumps(base))


@pytest.fixture(autouse=True)
def _fast_offline(monkeypatch):
    """Keep tests network-free and fast."""
    monkeypatch.setenv("PDF_HTTP_TIMEOUT", "1")
    monkeypatch.setenv("PDF_IMG_BUDGET", "3")
    yield


@pytest.fixture(scope="module")
def base_edition() -> dict:
    return _load_sample()


@pytest.fixture
def tmp_pdf(tmp_path):
    return str(tmp_path / "out.pdf")


def _assert_pdf(path: str) -> None:
    with open(path, "rb") as f:
        head = f.read(4)
    assert head == b"%PDF"


def test_render_sample(tmp_pdf, base_edition):
    render_pdf(base_edition, tmp_pdf)
    _assert_pdf(tmp_pdf)
    assert os.path.getsize(tmp_pdf) > 1000
    assert count_pages(base_edition) >= 3


def test_build_html_is_str(base_edition):
    html = build_html(base_edition)
    assert isinstance(html, str)
    assert "<!DOCTYPE html>" in html
    assert "Edition of One" in html


def test_broken_images(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    bad = "http://10.255.255.1/nope.jpg"

    def _break(art):
        if isinstance(art, dict):
            art["image_url"] = bad
            art["image"] = bad

    _break(ed.get("lead"))
    for a in ed.get("secondary") or []:
        _break(a)
    for sec in ed.get("sections") or []:
        _break(sec.get("feature"))
        for a in sec.get("items") or []:
            _break(a)

    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_empty_sections(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["sections"] = []
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_missing_back_page(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed.pop("back_page", None)
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_press_gallery_present(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["press_gallery"] = {
        "topic_label": "Test topic",
        "rows": [
            {
                "source": "Outlet A",
                "headline": "Headline from A",
                "url": "https://a.example/x",
                "emphasis": "angle A",
            },
            {
                "source": "Outlet B",
                "headline": "Headline from B",
                "url": "https://b.example/x",
                "emphasis": "angle B",
            },
            {
                "source": "Outlet C",
                "headline": "Headline from C",
                "url": "https://c.example/x",
                "emphasis": "angle C",
            },
        ],
        "agreed_facts": ["Fact one.", "Fact two."],
        "open_question": "What happens next?",
    }
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_200_character_headline(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    if isinstance(ed.get("lead"), dict):
        ed["lead"]["headline"] = "X" * 200
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_body_with_html_and_unicode(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    if isinstance(ed.get("lead"), dict):
        ed["lead"]["body"] = (
            "A body with <script>alert(1)</script> & < > \"quotes\" "
            "and unicode \u2713 \u00fcn\u00efc\u00f6d\u00e9 \u2014 and a \u2018curly\u2019 apostrophe."
        )
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)


def test_lead_only(tmp_pdf, base_edition):
    ed = _clone(base_edition)
    ed["sections"] = []
    ed["secondary"] = []
    ed["briefs"] = []
    ed["front_briefs"] = []
    ed["secondary_stories"] = []
    ed.pop("back_page", None)
    ed.pop("press_gallery", None)
    render_pdf(ed, tmp_pdf)
    _assert_pdf(tmp_pdf)
'''


# ---------------------------------------------------------------------------
# Makefile append
# ---------------------------------------------------------------------------
MAKEFILE_APPEND = r'''
# --- Edition of One: PDF targets (append to Makefile) ---
pdf:
	python -m pdf_generator.render --edition frontend/public/sample-edition.json --out out/sample.pdf

pdfcheck:
	python -m pdf_generator.render --all-demo
	@mkdir -p docs/samples
	@for f in out/*.pdf; do \
		[ -f "$$f" ] || continue; \
		name=$$(basename "$$f" .pdf); \
		pdfinfo "$$f" >/dev/null; \
		pdftoppm -r 60 -png -f 1 -l 1 "$$f" "docs/samples/$$name"; \
	done

.PHONY: pdf pdfcheck
'''

MAKEFILE_MARKER = "# --- Edition of One: PDF targets"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def main() -> int:
    written = 0
    for path, content in FILES.items():
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"wrote {path}")
        written += 1

    mk = "Makefile"
    existing = ""
    if os.path.exists(mk):
        with open(mk, "r", encoding="utf-8") as f:
            existing = f.read()

    if MAKEFILE_MARKER in existing:
        print(f"skipped {mk} (PDF targets section already present)")
    else:
        with open(mk, "a", encoding="utf-8") as f:
            if existing and not existing.endswith("\n"):
                f.write("\n")
            f.write(MAKEFILE_APPEND)
        print(f"appended PDF targets to {mk}")

    print(f"\nDone. {written} file(s) written.")
    return 0


if __name__ == "__main__":
    sys.exit(main())