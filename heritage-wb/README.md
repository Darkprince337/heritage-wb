# Heritage of West Bengal

Digital archive and tourism guide for the monasteries and historic sites of West Bengal.
This repo is the backend: data model, REST API, and a retrieval-augmented chatbot.
(The single-page prototype of the frontend is a separate file; the Next.js app comes next.)

## Run

```bash
cp .env.example .env        # optional: add ANTHROPIC_API_KEY for generated chat answers
docker compose up --build
```

Open the app: http://localhost:8000 (API docs at http://localhost:8000/docs)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/sites` | List sites. Filters: `category` (mon, tem, pal, col, arc), `region`, `q`, `year_max` |
| GET | `/sites/near?lat=&lon=&km=` | Sites within a radius, nearest first (PostGIS) |
| GET | `/sites/{slug}` | One site with media and condition reports |
| GET | `/trails` | Heritage trails with ordered stops |
| POST | `/chat` | `{"question": "...", "lang": "en"\|"bn"}` returns an answer and source slugs |

Without `ANTHROPIC_API_KEY`, `/chat` returns `answer: null` plus the matching site slugs.

## Data model

`sites` (PostGIS point, EN/BN fields, founding year, negative = BCE), `media`, `condition_reports`
(dated preservation log), `trails` and `trail_stops`. Seed data lives in `backend/app/data/sites.json`.

## Roadmap

1. Rebuild the web app in Next.js (current one is plain HTML + Leaflet in backend/app/static)
2. Admin panel and auth, media uploads, Alembic migrations
3. pgvector embeddings for chat retrieval; image classification; crack detection for condition reports
4. 360° tours, offline PWA, Nepali and Hindi content

## Adding more tourist spots from OpenStreetMap

```bash
docker compose exec api python -m app.import_osm --dry-run     # preview
docker compose exec api python -m app.import_osm --limit 300   # import
```

Imported entries are basic (name, type, location). Review them and improve descriptions before publishing.
Map data (c) OpenStreetMap contributors, ODbL. In-app routes use the public OSRM demo server, which is for light use only.
