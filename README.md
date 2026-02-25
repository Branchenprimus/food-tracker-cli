# Food Tracker CLI

A fast, local-first CLI tool for tracking food entries with approximate macros. It uses a local SQLite database and supports JSON output for machine readability.

## Features

- ⚡️ **Fast Entry**: Quick logging via CLI args.
- 📊 **Local Database**: All data stored in `~/.local/share/food/food.db` (SQLite).
- 📈 **Reporting**: Daily totals, weekly summaries.
- 🤖 **Agent Ready**: JSON output mode for AI integration.
- 🖥️ **Web UI**: Optional local web interface.

## Installation

### Prerequisites
- Python 3.10 or higher

### Setup

It is recommended to use a virtual environment to avoid dependency conflicts.

```bash
# 1. Clone or navigate to directory
cd food-tracker-cli

# 2. Create virtual environment
python3 -m venv venv

# 3. Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Initialize Database
python -m cli.main init-db
```

## Deployment

See [SETUP.md](SETUP.md) for Cloudflare Access setup and API key integration.

### GitHub Actions
A CI/CD pipeline is configured in `.github/workflows/publish.yml`. It builds and pushes an arm64 deployment image (optimized for Raspberry Pi) to **GitHub Container Registry (ghcr.io)** for faster production rollout.

### Environment Types
- **Persistent deployment (`make deploy`)**
  - Uses `deploy/compose.yml`
  - Runs as the stable production-like instance
  - Persists DB/cache via bind mount `./data:/app/data` (`data/app.db`, `data/widget_cache.json` inside container)
  - Fixed URL: [http://localhost:8787](http://localhost:8787)
  - Reserved for external access (for example Cloudflare Tunnel -> `http://192.168.178.38:8787`)
- **Development (`make dev`)**
  - Uses `docker-compose.yml`
  - Builds a local image from your current source tree
  - Persists DB/cache in docker volume `food-data-dev` at `/app/data` (`data/app.db`, `data/widget_cache.json` inside container)
  - Independent URL: [http://localhost:8686](http://localhost:8686)
  - `make dev` prints the access URL after startup
  - Must not bind to `8787` so it cannot interfere with the deployed tunnel endpoint
- **Local development build (`make dev-local`)**
  - Alias for `make dev`
- **Branch verification**
  - `make master` was removed
  - Use CI (GitHub Actions) as the branch verification gate

### Production Deployment (Raspberry Pi)
> [!NOTE]
> If the Docker image is **Private** on GitHub, you must log in first:
> ```bash
> echo $CR_PAT | docker login ghcr.io -u USERNAME --password-stdin
> ```
> Alternatively, make the package **Public** in GitHub Package settings.

For production deployment on a Raspberry Pi:

1.  **Copy the deployment files**:
    - `deploy/compose.yml`
    - `Makefile`

2.  **Deploy (Start + Auto-Updates)**:
    ```bash
    make deploy
    ```
    This command pulls the latest image, then starts the persistent `food-tracker` on port `8787` plus `watchtower`.
    After initial deployment, watchtower keeps the deploy container on the newest `latest` image automatically.

3.  **View Logs**:
    ```bash
    make logs
    ```

4.  **Stop**:
    ```bash
    make down-deploy
    ```

### Typical Workflow
```bash
# 1) Start or update the persistent deployed instance
make deploy

# 2) Start a separate development instance
make dev
```

Expected URLs:
- Deploy: [http://localhost:8787](http://localhost:8787)
- Dev: [http://localhost:8686](http://localhost:8686)

Useful commands:
- Stop dev: `make down-dev`
- Stop deploy: `make down-deploy`
- Build and run local source (no registry image): `make dev-local`
- Dev logs: `make logs-dev`
- Deploy logs: `make logs-deploy`
- Backward-compatible alias for stopping dev: `make down`

## Usage

### CLI Commands
Current commands in `cli/main.py`:

```bash
# initialize db + migrations
python -m cli.main init-db

# add one entry
python -m cli.main add "Banana" 105 0.4 27 1.3

# list recent entries
python -m cli.main list --limit 10

# delete by id
python -m cli.main delete 1

# run web ui
python -m cli.main ui --host 0.0.0.0 --port 8787

# seed mock data (used by make dev if db is empty)
python -m cli.main seed-mock --if-empty
```

### Standalone Client (pipx)

For OpenClaw users who should not clone this repo, install the API client via pipx:

```bash
pipx install "git+https://github.com/Branchenprimus/food-tracker-cli.git"
```

Then configure key + endpoint:

```bash
export FOOD_TRACKER_API_KEY='ftk_...'
export FOOD_TRACKER_API_BASE='https://kcal-tracker.darwin-labs.org'
```

Use:

```bash
food-tracker-cli me
food-tracker-cli add "Cheeseburger" 650 28 52 35
food-tracker-cli list --limit 5
food-tracker-cli delete 123
```

PyPI release automation:
- Workflow: `.github/workflows/pypi-publish.yml`
- Trigger: push tag `v*` (for example `v2.1.0`)
- Auth: PyPI Trusted Publisher (OIDC), no PyPI token required.
- Configure on PyPI project:
  - Owner: `Branchenprimus`
  - Repository: `food-tracker-cli`
  - Workflow: `pypi-publish.yml`
  - Environment: `pypi`

### Web UI
The Web UI is available at:
- Deploy: [http://localhost:8787](http://localhost:8787)
- Dev: [http://localhost:8686](http://localhost:8686)

## Configuration

The database location defaults to:
- macOS/Linux: `~/.local/share/food/food.db`
- Windows: `~/AppData/Local/food/food.db`

You can override this by setting the `FOOD_TRACKER_DB` environment variable.

## API Integration (Agents)

For external agents, prefer HTTP API calls instead of direct local CLI DB writes.

- App API: `/api/*` (entries, stats, settings, api keys)
- Widget API: `/v1/widget/today` (separate route/flow)
- API key format: `ftk_...`
- Send key as either:
  - `Authorization: Bearer <api_key>`
  - `X-API-Key: <api_key>`

Notes:
- One API key per user is enforced. Generating a new key revokes/removes old keys.
- In `dev`, requests without API key can still resolve to `DEV_USER_EMAIL` fallback.

Security notes:
- Never commit API keys to git or paste them into shared logs.
- Prefer Cloudflare URL (`https`) over plain HTTP endpoints.
- Rotate keys if exposed; old key is revoked when a new one is generated.
