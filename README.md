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
python -m cli.main db-init
```

## Deployment

See [SETUP.md](SETUP.md) for Cloudflare Access setup, multi-user admin flow, and OpenClaw API key integration.

### GitHub Actions
A CI/CD pipeline is configured in `.github/workflows/publish.yml`. It automatically builds and pushes multi-arch images (amd64, arm64) to **GitHub Container Registry (ghcr.io)** on every push to `master`.

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

### CLI Commands (via Wrapper Script)
A wrapper script `food-tracker` is provided for easy access. If you need sudo permissions for Docker, prefix commands with `sudo`.

**Add a food entry**
```bash
# Basic (time defaults to now)
./food-tracker add --title "Banana" --kcal 105 --carbs 27 --protein 1.3 --fat 0.4

# With specific date/time and confidence score
./food-tracker add --title "Dinner" --kcal 600 --confidence 0.8 --date 2023-10-27 --time 19:30
```

**List entries**
```bash
# Recent entries
./food-tracker list

# Filter by date range
./food-tracker list --from 2023-10-01 --to 2023-10-27
```

**View Stats**
```bash
# Daily summary
./food-tracker day

# Weekly summary (last 7 days)
./food-tracker week
```

**Edit & Delete**
```bash
# Delete entry #1
./food-tracker rm 1

# Edit entry #2 (update calories)
./food-tracker edit 2 --kcal 200
```

**Backup & Restore**
```bash
# Export to a file inside the container, then copy it out if needed
./food-tracker export --output backup.json
```

### Web UI
The Web UI is available at:
- Deploy: [http://localhost:8787](http://localhost:8787)
- Dev: [http://localhost:8686](http://localhost:8686)

## Configuration

The database location defaults to:
- macOS/Linux: `~/.local/share/food/food.db`
- Windows: `~/AppData/Local/food/food.db`

You can override this by setting the `FOOD_DB_PATH` environment variable.

## Agent Integration

All commands support a `--json` flag to output structured JSON data instead of formatted tables.

```bash
python -m cli.main list --json
```
