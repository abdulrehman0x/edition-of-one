from __future__ import annotations

import random
from typing import List, Optional

from ..models.schemas import ArticleRecord, BackPage, OnThisDay, QuizQ, WordSearch

# Fixed "from history" items. They are not matched to today's date.
_HISTORICAL = [
    (1947, "Pakistan gains independence."),
    (1969, "Apollo 11 lands the first humans on the Moon."),
    (1989, "The World Wide Web is proposed at CERN."),
    (2008, "The global financial crisis deepens."),
    (2015, "The Paris climate agreement is adopted."),
    (2020, "WHO declares COVID-19 a pandemic."),
]

_DIRECTIONS = [(0, 1), (1, 0), (1, 1), (1, -1), (0, -1), (-1, 0), (-1, -1), (-1, 1)]


def make_word_search(words: List[str], size: int = 12, seed: int = 42) -> WordSearch:
    rng = random.Random(seed)
    grid: List[List[str]] = [["" for _ in range(size)] for _ in range(size)]
    placed: List[str] = []

    for raw in words:
        word = raw.upper().replace(" ", "").replace("-", "").replace("_", "")
        if not word or len(word) > size:
            continue
        for _ in range(200):
            dr, dc = rng.choice(_DIRECTIONS)
            r = rng.randint(0, size - 1)
            c = rng.randint(0, size - 1)
            end_r = r + dr * (len(word) - 1)
            end_c = c + dc * (len(word) - 1)
            if not (0 <= end_r < size and 0 <= end_c < size):
                continue
            cells = [(r + dr * i, c + dc * i) for i in range(len(word))]
            if any(grid[rr][cc] and grid[rr][cc] != ch for (rr, cc), ch in zip(cells, word)):
                continue
            for (rr, cc), ch in zip(cells, word):
                grid[rr][cc] = ch
            placed.append(word)
            break

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for r in range(size):
        for c in range(size):
            if not grid[r][c]:
                grid[r][c] = rng.choice(letters)

    return WordSearch(grid=["".join(row) for row in grid], words=placed)


def _quiz_from_articles(articles: List[ArticleRecord]) -> List[QuizQ]:
    out: List[QuizQ] = []
    for a in articles[:5]:
        opts = [a.title]
        for b in articles:
            if len(opts) >= 4:
                break
            if b.id != a.id and b.title not in opts:
                opts.append(b.title)
        while len(opts) < 4:
            opts.append(f"None of the above ({len(opts)})")
        random.Random(sum(ord(c) for c in a.id)).shuffle(opts)
        topic = a.topics[0].replace("_", " ") if a.topics else "today's news"
        out.append(
            QuizQ(
                question=f"Which of these headlines ran under {topic}?",
                options=opts,
                answer=opts.index(a.title),
            )
        )
    return out


def build_back_page(
    articles: List[ArticleRecord],
    words: Optional[List[str]] = None,
    seed: int = 42,
) -> BackPage:
    if words is None:
        firsts = [a.topics[0] for a in articles[:12] if a.topics]
        words = list(dict.fromkeys(firsts))[:8]
    return BackPage(
        quiz=_quiz_from_articles(articles),
        word_search=make_word_search(words, seed=seed) if words else None,
        on_this_day=[OnThisDay(year=y, text=t) for y, t in _HISTORICAL[:4]],
    )
