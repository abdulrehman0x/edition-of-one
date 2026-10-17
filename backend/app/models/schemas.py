from __future__ import annotations

from typing import Literal, Optional, List, Dict

from pydantic import BaseModel, Field

Topic = Literal[
    "world", "pakistan", "politics", "business", "markets", "technology",
    "ai", "science", "space", "health", "sport", "cricket", "football",
    "culture", "film_music", "education", "climate", "startups", "opinion",
]

Slot = Literal["lead", "secondary", "feature", "standard", "brief"]

EventType = Literal[
    "impression", "click", "skip", "dwell", "thumb_up",
    "thumb_down", "save", "pdf_open",
]


class Art(BaseModel):
    kind: Literal["image", "svg", "none"] = "none"
    url: Optional[str] = None
    caption: Optional[str] = None
    alt: Optional[str] = None


class Body(BaseModel):
    short: str = ""
    medium: str = ""
    long: str = ""


class ArticleRecord(BaseModel):
    id: str
    title: str
    url: str = ""
    source: str = ""
    source_id: str = ""
    topics: List[Topic] = Field(default_factory=list)
    published_at: Optional[str] = None
    body: Body = Field(default_factory=Body)
    art: Art = Field(default_factory=Art)
    importance: float = 0.5


class Weather(BaseModel):
    city: str = ""
    temp_c: Optional[float] = None
    condition: str = ""
    high_c: Optional[float] = None
    low_c: Optional[float] = None


class Section(BaseModel):
    name: str
    slug: str
    articles: List[ArticleRecord] = Field(default_factory=list)


class QuizQ(BaseModel):
    question: str
    options: List[str]
    answer: int = 0


class WordSearch(BaseModel):
    grid: List[str] = Field(default_factory=list)
    words: List[str] = Field(default_factory=list)


class MarketRow(BaseModel):
    symbol: str
    price: Optional[float] = None
    change_pct: Optional[float] = None


class OnThisDay(BaseModel):
    year: Optional[int] = None
    text: str = ""


class BackPage(BaseModel):
    quiz: List[QuizQ] = Field(default_factory=list)
    word_search: Optional[WordSearch] = None
    on_this_day: List[OnThisDay] = Field(default_factory=list)


class GalleryRow(BaseModel):
    title: str
    url: str = ""
    caption: str = ""


class PressGallery(BaseModel):
    rows: List[GalleryRow] = Field(default_factory=list)


class Front(BaseModel):
    lead: Optional[ArticleRecord] = None
    secondary: List[ArticleRecord] = Field(default_factory=list)
    briefs: List[ArticleRecord] = Field(default_factory=list)
    weather: Optional[Weather] = None
    quote: str = ""


class Chapter(BaseModel):
    title: str
    articles: List[ArticleRecord] = Field(default_factory=list)
    slot: Slot = "standard"


class Edition(BaseModel):
    id: str
    reader_id: str
    date: str
    nameplate: str = "Edition of One"
    dateline: str = ""
    front: Front = Field(default_factory=Front)
    sections: List[Section] = Field(default_factory=list)
    back_page: BackPage = Field(default_factory=BackPage)
    press_gallery: Optional[PressGallery] = None
    chapters: List[Chapter] = Field(default_factory=list)
    outside_bubble: List[ArticleRecord] = Field(default_factory=list)


class Profile(BaseModel):
    reader_id: str
    name: str = ""
    topics: List[Topic] = Field(default_factory=list)
    weights: Dict[str, float] = Field(default_factory=dict)
    location: str = ""
    tone: str = "neutral"
    outside_bubble_ratio: float = 0.15


class Event(BaseModel):
    reader_id: str
    article_id: Optional[str] = None
    event_type: EventType
    value: float = 1.0
    ts: Optional[str] = None
