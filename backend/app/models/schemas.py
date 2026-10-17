from __future__ import annotations
import datetime as dt
from typing import Literal, Optional
from pydantic import BaseModel, Field

Topic = Literal['world','pakistan','politics','business','markets','technology','ai','science','space','health','sport','cricket','football','culture','film_music','education','climate','startups','opinion']
Slot = Literal['lead','secondary','feature','standard','brief']
EventType = Literal['impression','click','skip','dwell','thumb_up','thumb_down','save','pdf_open']

class ArticleRecord(BaseModel):
    id: str; url: str; title: str; body: str = ''; source: str
    topic: Topic = 'world'; image_url: Optional[str] = None
    published_at: Optional[dt.datetime] = None; importance: float = 0.5
    cluster_id: Optional[str] = None; brief: str = ''

class Body(BaseModel):
    short: str; medium: str; long: str

class Art(BaseModel):
    id: str; headline: str; deck: str = ''; body: Body
    source: str; url: str; tracked_url: str = ''
    image: Optional[str] = None; topic: Topic; slot: Slot
    why: str = ''; outside_bubble: bool = False
    importance: float = 0.5; cluster_id: Optional[str] = None
    published_at: Optional[dt.datetime] = None; qr_svg: Optional[str] = None

class Weather(BaseModel):
    city: str; hi: int; lo: int; sky: str
class Section(BaseModel):
    name: str; items: list[Art] = Field(default_factory=list)
class Front(BaseModel):
    lead: Art; secondary: list[Art] = Field(default_factory=list); briefs: list[Art] = Field(default_factory=list)
class QuizQ(BaseModel):
    q: str; options: list[str]; answer_index: int; explain: str = ''
class WordSearch(BaseModel):
    size: int; grid: list[str]; words: list[str]
class MarketRow(BaseModel):
    label: str; value: str; change_pct: Optional[float] = None
class OnThisDay(BaseModel):
    year: int; text: str
class BackPage(BaseModel):
    quiz: list[QuizQ] = Field(default_factory=list); word_search: Optional[WordSearch] = None
    markets: list[MarketRow] = Field(default_factory=list); on_this_day: list[OnThisDay] = Field(default_factory=list)
class GalleryRow(BaseModel):
    source: str; url: str; headline: str; emphasis: str = ''
class PressGallery(BaseModel):
    topic_label: str; agreed_facts: list[str] = Field(default_factory=list)
    rows: list[GalleryRow] = Field(default_factory=list)
    only_in_one: list[dict] = Field(default_factory=list); open_question: str = ''
class Chapter(BaseModel):
    story_id: str; title: str; start_sec: float

class Edition(BaseModel):
    date: dt.date; issue_no: int; reader_id: str; reader_name: str; tagline: str = ''
    weather: Optional[Weather] = None; editors_note: str = ''
    front: Front; sections: list[Section] = Field(default_factory=list)
    back_page: BackPage = Field(default_factory=BackPage)
    press_gallery: Optional[PressGallery] = None
    audio_url: Optional[str] = None; audio_script: str = ''; chapters: list[Chapter] = Field(default_factory=list)
    pdf_url: Optional[str] = None; meta: dict = Field(default_factory=dict)

class Profile(BaseModel):
    reader_id: str; display_name: str = ''; interests_text: str = ''
    topic_weights: dict[str, float] = Field(default_factory=dict)
    topic_stats: dict[str, dict[str, float]] = Field(default_factory=dict)
    reading_minutes: int = 15; region_bias: float = 0.5
    tone: Literal['brief','deep'] = 'brief'; watch_entities: list[str] = Field(default_factory=list)
    centroid: list[float] = Field(default_factory=list)

class Event(BaseModel):
    reader_id: str; type: EventType; article_id: Optional[str] = None
    edition_date: Optional[dt.date] = None; value: float = 0.0; slot: str = ''
    ts: Optional[dt.datetime] = None
