# Edition of One — Frontend

Next.js 14 App Router web client.

## Quickstart

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000

The app expects the API at `http://localhost:8000`. When the API is unreachable,
the client loads `/sample-edition.json` as a fallback and shows an offline banner.

## Structure

- `app/` — routes (onboarding, today, edition/[date], archive, profile)
- `components/` — newspapers UI components
- `components/extras/` — audio, press gallery, back page
- `lib/` — types, api wrappers, reader id, tracker

## Learning loop

Feedback buttons and reading time are sent to `POST /events`. The profile page's
"Advance one night" button calls `POST /profile/{id}/advance`, which re-weights
topics and builds tomorrow's edition (see `backend/app/services/learning.py`).
