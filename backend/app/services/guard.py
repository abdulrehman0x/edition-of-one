from __future__ import annotations

import re
from typing import List, Optional, Set, Tuple


def _numbers(text: str) -> Set[str]:
    return set(re.findall(r"\b\d+(?:[.,]\d+)?\b", text or ""))


def _caps(text: str) -> Set[str]:
    '''Capitalised words that look like entities.

    Sentence-initial words are skipped: they are capitalised by grammar,
    not because they are names ("Inflation rose..." is not an entity).
    '''
    text = text or ""
    out: Set[str] = set()
    for m in re.finditer(r"\b[A-Z][a-zA-Z]{2,}\b", text):
        before = text[: m.start()].rstrip()
        if not before or before[-1] in ".!?":
            continue
        out.add(m.group(0))
    return out


def validate_grounding(
    claim: str,
    sources: List[str],
    allow_common: Optional[Set[str]] = None,
) -> Tuple[bool, List[str]]:
    allow_common = allow_common or set()
    problems: List[str] = []
    src_text = " ".join(sources or [])
    src_nums = _numbers(src_text)
    src_caps = _caps(src_text) | allow_common

    for n in _numbers(claim):
        if n not in src_nums:
            problems.append(f"number not grounded: {n}")

    for c in _caps(claim):
        if c in allow_common:
            continue
        if c not in src_caps:
            problems.append(f"entity not grounded: {c}")

    return (len(problems) == 0, problems)
