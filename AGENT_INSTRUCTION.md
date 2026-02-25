# Agent Instructions for Food Tracker

This document provides guidelines for AI agents interacting with this project.

## Preferred Integration Path

Use the HTTP API exposed by the app instead of direct DB writes.

- App API base (dev): `http://localhost:8686`
- App API base (deploy): `http://localhost:8787`
- API key auth headers:
  - `X-API-Key: <ftk_...>`
  - or `Authorization: Bearer <ftk_...>`

## Operator Onboarding Flow

Expected real-world flow:
1. User requests access by sharing their email with operator.
2. Operator adds that email to Cloudflare Access policy.
3. User logs into Web UI (`https://kcal-tracker.darwin-labs.org/`) via Cloudflare.
4. User opens settings and generates API key.
5. User stores key in their local environment for agent usage.

Recommended env var:
- `FOOD_TRACKER_API_KEY=ftk_...`

## Authentication Behavior

- API keys are generated in the Web UI settings.
- One API key per user is enforced.
- Generating a new key revokes/removes old keys for that user.
- If an API key is supplied and invalid, API returns `403`.
- In `dev`, no-key requests can still resolve to `DEV_USER_EMAIL` fallback identity.
- Agent rule: always send API key for all `/api/*` calls.
- If key is rotated in UI, agents must update local env var before retrying calls.

## Core API Endpoints

- `POST /api/entries`
- `GET /api/entries?date=YYYY-MM-DD`
- `PUT /api/entries/{id}`
- `DELETE /api/entries/{id}`
- `GET /api/stats/day?date=YYYY-MM-DD`
- `GET /api/stats/streak`
- `GET /api/stats/history?start=YYYY-MM-DD&end=YYYY-MM-DD`
- `GET /api/settings/goals`
- `PUT /api/settings/goals`
- `GET /api/settings/api-keys`
- `POST /api/settings/api-keys`
- `DELETE /api/settings/api-keys/{id}`

## Example Requests

```bash
# set once in shell profile / runtime env
export FOOD_TRACKER_API_KEY='ftk_...'

# create entry
curl -X POST http://localhost:8686/api/entries \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $FOOD_TRACKER_API_KEY" \
  -d '{"title":"Banana","kcal":105,"fat_g":0.4,"carbs_g":27,"protein_g":1.3,"serving_amount":1,"confidence":0.9,"entry_date":"2026-02-25","entry_time":"10:30"}'

# list entries for one day
curl 'http://localhost:8686/api/entries?date=2026-02-25' -H "X-API-Key: $FOOD_TRACKER_API_KEY"
```

## Local CLI Notes

The local Typer CLI in `cli/main.py` exists for local admin/dev operations (`init-db`, `add`, `list`, `delete`, `ui`, `seed-mock`).
It writes via service/db internals and is not the recommended auth boundary for agent integrations.
