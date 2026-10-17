# Edition of One — Data Contract (Phase 1)

All wire formats are Pydantic v2 models defined in
`backend/app/models/schemas.py`.

## Enums

- `Topic` — one of: world, pakistan, politics, business, markets, technology, ai,
  science, space, health, sport, cricket, football, culture, film_music,
  education, climate, startups, opinion.
- `Slot` — lead | secondary | feature | standard | brief.
- `EventType` — impression | click | skip | dwell | thumb_up | thumb_down |
  save | pdf_open.

## Models

- `ArticleRecord` {id, title, url, source, source_id, topics, published_at,
  body: Body, art: Art, importance}
- `Body` {short, medium, long}
- `Art` {kind, url, caption, alt}
- `Weather` {city, temp_c, condition, high_c, low_c}
- `Section` {name, slug, articles}
- `Front` {lead, secondary, briefs, weather, quote}
- `QuizQ` {question, options, answer}
- `WordSearch` {grid, words}
- `MarketRow` {symbol, price, change_pct}
- `OnThisDay` {year, text}
- `BackPage` {quiz, word_search, on_this_day}
- `GalleryRow` {title, url, caption}
- `PressGallery` {rows}
- `Chapter` {title, articles, slot}
- `Edition` {id, reader_id, date, nameplate, dateline, front, sections,
  back_page, press_gallery, chapters, outside_bubble}
- `Profile` {reader_id, name, topics, weights, location, tone,
  outside_bubble_ratio}
- `Event` {reader_id, article_id, event_type, value, ts}

## Storage

- `FileStore` keeps JSON at `data/cache/<key>.json` (keys are sanitised).
- `SupabaseStore` uses the `kv` table in `supabase/migrations/001_init.sql`;
  silently degrades to `FileStore` on connection error.

## Endpoints

App entry point: `app.main:app` (re-exports `app.api.main:app`).

- `GET  /health`
- `POST /onboarding`
- `GET  /edition/{reader_id}?date=YYYY-MM-DD|today`
- `GET  /archive/{reader_id}`
- `POST /events`
- `GET  /profile/{reader_id}`
- `GET  /dev/readers`          (only when ENABLE_DEV=1)
- `DELETE /dev/reset`          (only when ENABLE_DEV=1)
