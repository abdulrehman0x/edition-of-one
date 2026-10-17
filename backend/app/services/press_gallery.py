from __future__ import annotations

from typing import Dict, List

from ..models.schemas import ArticleRecord, GalleryRow, PressGallery


def _cluster_by_topic(articles: List[ArticleRecord]) -> Dict[str, List[ArticleRecord]]:
    clusters: Dict[str, List[ArticleRecord]] = {}
    for a in articles:
        for t in a.topics:
            clusters.setdefault(t, []).append(a)
    return clusters


def _agreed_facts(cluster: List[ArticleRecord]) -> List[str]:
    seen: Dict[str, int] = {}
    for a in cluster:
        for sent in (a.body.short or "").split(". "):
            sent = sent.strip().rstrip(".")
            if len(sent) >= 20:
                seen[sent] = seen.get(sent, 0) + 1
    agreed = [k for k, v in seen.items() if v >= 2]
    if not agreed and seen:
        agreed = [next(iter(seen))]
    return agreed[:3]


def _framing_differences(cluster: List[ArticleRecord]) -> List[str]:
    return [f"{a.source}: {a.title}" for a in cluster[:3]]


def build_gallery(articles: List[ArticleRecord]) -> PressGallery:
    # Topic clusters stand in for "same story" until real story clustering
    # (embeddings) lands; only clusters with 2+ articles are shown.
    clusters = _cluster_by_topic(articles)
    rows: List[GalleryRow] = []
    ranked = sorted(clusters.items(), key=lambda kv: len(kv[1]), reverse=True)[:5]
    for topic, cluster in ranked:
        if len(cluster) < 2:
            continue
        agreed = _agreed_facts(cluster)
        framing = _framing_differences(cluster)
        caption = f"Outlets agree: {agreed[0] if agreed else '…'}. Framings: " + " | ".join(framing)
        rows.append(
            GalleryRow(title=topic.replace("_", " ").title(), url="", caption=caption)
        )
    return PressGallery(rows=rows)
