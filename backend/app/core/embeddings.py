from __future__ import annotations

from typing import List

from .config import get_settings

_model = None
_hv = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    return _model


def _get_hv():
    global _hv
    if _hv is None:
        from sklearn.feature_extraction.text import HashingVectorizer  # type: ignore
        _hv = HashingVectorizer(
            n_features=384, alternate_sign=False, norm="l2", lowercase=True
        )
    return _hv


def embed(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    s = get_settings()
    if s.llm_offline == 0:
        try:
            m = _get_model()
            out = m.encode(texts, normalize_embeddings=True)
            return [[float(x) for x in v] for v in out]
        except Exception:
            pass
    hv = _get_hv()
    X = hv.transform(texts)
    return [[float(x) for x in row] for row in X.toarray()]


def embed_one(text: str) -> List[float]:
    v = embed([text])
    return v[0] if v else []
