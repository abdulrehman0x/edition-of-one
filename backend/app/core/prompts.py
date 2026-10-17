from __future__ import annotations

from pathlib import Path
from typing import Dict


def _prompts_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "prompts"


def load_template(name: str) -> str:
    p = _prompts_dir() / name
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def render(template_name: str, **vars: object) -> str:
    t = load_template(template_name)
    for k, v in vars.items():
        t = t.replace("{{" + k + "}}", str(v))
    return t


def available() -> Dict[str, bool]:
    names = ["onboarding_profile.md", "curator.md", "copy.md"]
    return {n: (_prompts_dir() / n).exists() for n in names}
