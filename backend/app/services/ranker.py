from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np

from ..models.schemas import ArticleRecord, Profile


class ThompsonBandit:
    def __init__(self) -> None:
        self.alpha: Dict[str, float] = {}
        self.beta: Dict[str, float] = {}

    def sample(self, topic: str) -> float:
        a = self.alpha.get(topic, 1.0)
        b = self.beta.get(topic, 1.0)
        return float(np.random.beta(a, b))

    def update(self, topic: str, reward: float) -> None:
        reward = max(0.0, min(1.0, reward))
        self.alpha[topic] = self.alpha.get(topic, 1.0) + reward
        self.beta[topic] = self.beta.get(topic, 1.0) + (1.0 - reward)


def cosine(a: List[float], b: List[float]) -> float:
    va = np.array(a, dtype=float)
    vb = np.array(b, dtype=float)
    na = float(np.linalg.norm(va))
    nb = float(np.linalg.norm(vb))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(va @ vb / (na * nb))


def cluster_cosine(vectors: List[List[float]], threshold: float = 0.85) -> List[int]:
    labels: List[int] = []
    centroids: List[List[float]] = []
    for v in vectors:
        assigned = -1
        for i, c in enumerate(centroids):
            if cosine(v, c) >= threshold:
                assigned = i
                break
        if assigned < 0:
            assigned = len(centroids)
            centroids.append(v)
        labels.append(assigned)
    return labels


def score_article(
    article: ArticleRecord,
    profile: Profile,
    bandit: Optional[ThompsonBandit] = None,
    category_counts: Optional[Dict[str, int]] = None,
    freshness: float = 1.0,
) -> float:
    relevance = 0.0
    if profile.weights:
        relevance = max((profile.weights.get(t, 0.0) for t in article.topics), default=0.0)
    if relevance == 0.0 and profile.topics:
        relevance = 0.2 if any(t in profile.topics for t in article.topics) else 0.05

    importance = float(article.importance)

    location = 1.0
    if profile.location:
        hay = (article.title + " " + article.body.short).lower()
        if profile.location.lower() in hay:
            location = 1.2

    exploration = 0.0
    if bandit is not None and article.topics:
        exploration = max(bandit.sample(t) for t in article.topics) * 0.1

    fatigue = 0.0
    if category_counts and article.topics:
        m = max(category_counts.get(t, 0) for t in article.topics)
        fatigue = min(1.0, m / 12.0) * 0.15

    return (
        0.45 * relevance
        + 0.25 * importance
        + 0.15 * freshness
        + 0.15 * location
        + exploration
        - fatigue
    )
