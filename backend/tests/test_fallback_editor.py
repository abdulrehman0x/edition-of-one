from app.models.schemas import ArticleRecord, Body, Profile
from app.services.fallback_editor import (
    build_edition,
    dedupe,
    extract_summary,
    jaccard,
    _tokens,
)


def _art(i, title, topics, text="", imp=0.6):
    return ArticleRecord(
        id=f"a{i}",
        title=title,
        topics=topics,
        body=Body(short=text, medium=text, long=text),
        importance=imp,
    )


def test_jaccard_identical():
    assert jaccard(_tokens("hello world"), _tokens("hello world")) == 1.0


def test_dedupe_removes_near_duplicates():
    arts = [
        _art(1, "Breaking news about the economy today"),
        _art(2, "Breaking news about the economy today"),
        _art(3, "A totally different headline on sport"),
    ]
    out = dedupe(arts)
    assert len(out) == 2


def test_extract_summary_respects_word_limit():
    text = "First sentence here. Second sentence follows. Third sentence is here too."
    s = extract_summary(text, 5)
    assert len(s.split()) <= 5


WORLD_TITLES = [
    "Floods displace thousands along river basin",
    "Summit negotiators narrow gap on shipping rules",
    "Central bank holds rates amid cooling prices",
    "Volcano alert raised near island resorts",
    "Opposition leaders demand fresh ballot count",
    "Aid convoy reaches besieged northern town",
    "Telescope captures distant galaxy cluster",
    "Rail strike enters second week",
]


def test_build_edition_slots_each_story_once():
    profile = Profile(
        reader_id="r1",
        topics=["world", "pakistan"],
        weights={"world": 1.0, "pakistan": 1.0},
        location="Islamabad",
        outside_bubble_ratio=0.2,
    )
    arts = [_art(i, t, ["world"]) for i, t in enumerate(WORLD_TITLES)]
    arts.append(_art(99, "Outside topic technology story", ["technology"]))
    ed = build_edition("r1", "2025-01-01", arts, profile)

    assert ed.front.lead is not None
    assert ed.front.secondary
    assert ed.outside_bubble and ed.outside_bubble[0].id == "a99"
    assert ed.reader_id == "r1"
    assert ed.date == "2025-01-01"

    ids = [ed.front.lead.id]
    ids += [a.id for a in ed.front.secondary]
    ids += [a.id for a in ed.front.briefs]
    for sec in ed.sections:
        ids += [a.id for a in sec.articles]
    assert len(ids) == len(set(ids)), "a story was placed in two slots"
