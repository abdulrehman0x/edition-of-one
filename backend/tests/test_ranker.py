from app.models.schemas import ArticleRecord, Body, Profile
from app.services.ranker import (
    ThompsonBandit,
    cluster_cosine,
    cosine,
    score_article,
)


def _mk(i, topics, imp=0.6):
    return ArticleRecord(id=f"a{i}", title=f"Title {i}", topics=topics,
                         body=Body(), importance=imp)


def test_cosine_identity():
    assert abs(cosine([1.0, 0.0], [1.0, 0.0]) - 1.0) < 1e-6


def test_score_prefers_weighted_topic():
    profile = Profile(reader_id="r", topics=["world"], weights={"world": 1.0, "sport": 0.1})
    a_world = _mk(1, ["world"])
    a_sport = _mk(2, ["sport"])
    assert score_article(a_world, profile) > score_article(a_sport, profile)


def test_thompson_bandit_updates():
    tb = ThompsonBandit()
    _ = tb.sample("world")
    tb.update("world", 1.0)
    assert tb.alpha["world"] > 1.0


def test_cluster_cosine_groups_identical():
    labels = cluster_cosine([[1.0, 0.0], [0.99, 0.01], [0.0, 1.0]])
    assert labels[0] == labels[1]
    assert labels[2] != labels[0]
