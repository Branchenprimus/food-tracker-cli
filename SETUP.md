# Setup Guide

This guide explains:
- Cloudflare Access login for the Web UI
- Cloudflare-only user access model
- API key usage for OpenClaw integration

## 1. Cloudflare Access (Google IdP + Email Policy)

Prerequisites:
- Cloudflare Zero Trust enabled
- your app is exposed through Cloudflare (for example via Cloudflare Tunnel)

Steps:
1. In Zero Trust, create an Application for your Food Tracker URL.
2. Add Login Method: Google IdP.
3. Create an Access Policy:
   - Action: `Allow`
   - Include: allowed user emails (or allowed Google group)
4. Ensure the app forwards Cloudflare Access identity headers to origin.

The backend expects:
- `CF-Access-Authenticated-User-Email`

In `dev`, if this header is missing, backend falls back to:
- `DEV_USER_EMAIL` (default: `dev@local.foodtracker`)

## 2. Environment Variables

Recommended runtime env vars:
- `APP_ENV=prod` (or `dev`)
- `APP_GIT_REF=master` (or `dev`)
- `FOOD_TRACKER_DB=data/app.db`
- `FOOD_TRACKER_CACHE=data/widget_cache.json`
- `FOOD_TRACKER_LEGACY_OWNER_EMAIL=owner@example.com` (for migrating old single-user entries)
- `WIDGET_API_TOKEN=...` (optional legacy widget token)

## 3. API Key Flow (OpenClaw)

In Web UI settings:
1. Enter key name (for example `OpenClaw`)
2. Click `Generate API key`
3. Copy the key immediately (shown once)

API endpoints:
- `POST /api/settings/api-keys` create key
- `GET /api/settings/api-keys` list keys
- `DELETE /api/settings/api-keys/{id}` revoke key

Use key in OpenClaw requests:
- `Authorization: Bearer <api_key>`
  or
- `X-API-Key: <api_key>`

For widget-style data:
- `GET /v1/widget/today`

With API key, response is user-scoped.

## 4. Local Development

Start dev stack:
```bash
make dev
```

In dev, seeding is automatic when DB is empty.

## 5. Notes

- API keys are stored hashed in DB (raw key is not stored).
- Cloudflare Access is the source of truth for who can access the web app.
- Existing legacy entries can be auto-assigned to `FOOD_TRACKER_LEGACY_OWNER_EMAIL`.
