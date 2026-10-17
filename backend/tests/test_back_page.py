from app.models.schemas import ArticleRecord, Body
from app.services.back_page import build_back_page, make_word_search
from app.services.press_gallery import build_gallery


def _art(i, topics):
    return ArticleRecord(
        id=f"a{i}", title=f"Headline {i}", topics=topics, source=f"Src{i}",
        body=Body(short=f"Short body number {i} with enough words."),
    )


def test_word_search_places_words_inside_grid():
    ws = make_word_search(["pakistan", "cricket", "climate"], size=12, seed=1)
    assert len(ws.grid) == 12 and all(len(r) == 12 for r in ws.grid)
    assert ws.words


def test_quiz_answer_points_at_the_real_headline():
    arts = [_art(i, ["world"]) for i in range(6)]
    bp = build_back_page(arts)
    assert len(bp.quiz) == 5
    for q, a in zip(bp.quiz, arts):
        assert q.options[q.answer] == a.title


def test_back_page_is_deterministic_per_seed():
    arts = [_art(i, ["world", "sport"][i % 2:i % 2 + 1]) for i in range(8)]
    assert build_back_page(arts, seed=3).word_search == build_back_page(arts, seed=3).word_search


def test_gallery_needs_two_articles_per_topic():
    rows = build_gallery([_art(1, ["world"]), _art(2, ["world"]), _art(3, ["sport"])]).rows
    assert [r.title for r in rows] == ["World"]
