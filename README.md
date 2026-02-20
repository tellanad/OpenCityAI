# OpenCity AI

OpenCity AI is a lightweight, multi-tenant civic knowledge retrieval platform.

It is designed to help cities and civic tech communities improve access to public information using open-source LLMs plus RAG, with clear source citations and low infrastructure cost.

## What This Project Is

- A document-grounded retrieval and answer API (`/v1/query`)
- A user feedback capture API (`/v1/feedback`)
- A multi-city ingestion and sync pipeline (`/v1/admin/sync`)
- A city-isolated vector search layer (`city_id` payload filters)
- Persistent product analytics for iteration (`/v1/admin/analytics`)
- A simple web widget for embedding in city websites

## What This Project Is Not

- A replacement for city CRMs or case systems
- An autonomous decision engine
- A guarantee of completeness beyond ingested sources

## Architecture

```text
Client/Chat UI
  -> FastAPI
  -> Retrieval (Qdrant filter by city_id)
  -> Open-source LLM (Ollama)
  -> Grounded answer + citations
```

## Quick Start

1. Copy env file.

```bash
cp .env.example .env
```

2. Start services.

```bash
docker compose up --build
```

3. Check health.

- [http://localhost:8000/](http://localhost:8000/)
- [http://localhost:8000/docs](http://localhost:8000/docs)

## API

- `POST /v1/query`
- `POST /v1/query/stream` (SSE)
- `POST /v1/feedback`
- `POST /v1/admin/cities`
- `POST /v1/admin/sources`
- `POST /v1/admin/sync?city_id=...`
- `GET /v1/admin/status?city_id=...`
- `GET /v1/admin/analytics?city_id=...&days=...`

Admin routes require header `X-Admin-API-Key`.

## Example Query

```bash
curl -s http://localhost:8000/v1/query \
  -H 'Content-Type: application/json' \
  -d '{"city_id":"san_francisco","query":"How do I report a broken streetlight?"}'
```

## Example Streaming Query

```bash
curl -N http://localhost:8000/v1/query/stream \
  -H 'Content-Type: application/json' \
  -d '{"city_id":"san_francisco","query":"How do I report a broken streetlight?"}'
```

## Example Feedback

```bash
curl -s http://localhost:8000/v1/feedback \
  -H 'Content-Type: application/json' \
  -d '{"city_id":"san_francisco","query_id":"<query_id_from_meta>","helpful":false,"reason":"missing_info","escalation_requested":true}'
```

## Analytics Metrics

`GET /v1/admin/analytics` returns:

- Query volume
- Refusal rate
- Median latency
- Feedback coverage
- Helpful and escalation rates
- Top negative feedback reasons

## City Onboarding

City configuration lives under `cities/<city_id>/`.

- `city.yaml`
- `sources.yaml`

Add sources, then trigger sync.

## Cost Notes

A small pilot can run on one VM (8-16GB RAM, 4-8 vCPU) with predictable monthly infrastructure cost. See `/whitepaper/opencity_ai_whitepaper.md` for details.
