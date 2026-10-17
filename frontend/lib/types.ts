export type Topic =
 | "world"
 | "pakistan"
 | "politics"
 | "business"
 | "markets"
 | "technology"
 | "ai"
 | "science"
 | "space"
 | "health"
 | "sport"
 | "cricket"
 | "football"
 | "culture"
 | "film_music"
 | "education"
 | "climate"
 | "startups"
 | "opinion";

export type Slot = "lead" | "secondary" | "feature" | "standard" | "brief";

export type EventType =
 | "impression"
 | "click"
 | "skip"
 | "dwell"
 | "thumb_up"
 | "thumb_down"
 | "save"
 | "pdf_open";

export interface Art {
 kind: "image" | "svg" | "none";
 url?: string | null;
 caption?: string | null;
    alt?: string | null;
}

export interface Body {
  short: string;
  medium: string;
  long: string;
}

export interface ArticleRecord {
  id: string;
  title: string;
  url: string;
  source: string;
  source_id: string;
  topics: Topic[];
  published_at?: string | null;
  body: Body;
  art: Art;
  importance: number;
}

export interface Weather {
  city: string;
  temp_c?: number | null;
  condition: string;
  high_c?: number | null;
  low_c?: number | null;
}

export interface Section {
  name: string;
  slug: string;
  articles: ArticleRecord[];
}

export interface QuizQ {
  question: string;
  options: string[];
  answer: number;
}

export interface WordSearch {
 grid: string[];
    words: string[];
}

export interface MarketRow {
  symbol: string;
  price?: number | null;
  change_pct?: number | null;
}

export interface OnThisDay {
  year?: number | null;
  text: string;
}

export interface BackPage {
  quiz: QuizQ[];
  word_search?: WordSearch | null;
  on_this_day: OnThisDay[];
}

export interface GalleryRow {
  title: string;
  url: string;
  caption: string;
}

export interface PressGallery {
  rows: GalleryRow[];
}

export interface Front {
  lead?: ArticleRecord | null;
  secondary: ArticleRecord[];
  briefs: ArticleRecord[];
  weather?: Weather | null;
  quote: string;
}

export interface Chapter {
  title: string;
  articles: ArticleRecord[];
  slot: Slot;
}
export interface Edition {
  id: string;
  reader_id: string;
  date: string;
  nameplate: string;
  dateline: string;
  front: Front;
  sections: Section[];
  back_page: BackPage;
  press_gallery?: PressGallery | null;
  chapters: Chapter[];
  outside_bubble: ArticleRecord[];
  weight_snapshot?: Record<string, number>;
  why_text?: string;
  broadcast?: Broadcast | null;
}

export interface Profile {
  reader_id: string;
  name: string;
  topics: Topic[];
  weights: Record<string, number>;
  location: string;
  tone: string;
  outside_bubble_ratio: number;
  weight_deltas?: Record<string, number>;
  topic_stats?: Record<string, { alpha: number; beta: number }>;
  reading_time_pref?: string;
}

export interface Event {
  reader_id: string;
  article_id?: string | null;
  event_type: EventType;
  value: number;
  ts?: string | null;
}
export interface BroadcastChapter {
  title: string;
  start: number;
  duration: number;
}

export interface Broadcast {
  mode: "audio" | "script-only" | "unavailable";
  audio_url?: string | null;
  duration?: number;
  chapters: BroadcastChapter[];
  script?: {
    intro: string;
    chapters: { title: string; script: string }[];
    outro: string;
  };
}
