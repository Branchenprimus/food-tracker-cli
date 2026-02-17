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

### GitHub Actions
A CI/CD pipeline is configured in `.github/workflows/publish.yml`. It automatically builds and pushes multi-arch images (amd64, arm64) to **GitHub Container Registry (ghcr.io)** on every push to `master`.

### Local Development
To run the application locally (building from source):
```bash
make dev
```
This builds the `Dockerfile` in the current directory and starts the container.

### Production Deployment (Raspberry Pi)
For production deployment on a Raspberry Pi:

1.  **Copy the deployment files**:
    - `deploy/compose.yml`
    - `Makefile`

2.  **Deploy (Start + Auto-Updates)**:
    ```bash
    make deploy
    ```
    This command starts the `food-tracker` (port 8080) and `watchtower` (auto-updates enabled).

3.  **View Logs**:
    ```bash
    make logs
    ```

4.  **Stop**:
    ```bash
    make down
    ```

## Usage

### CLI Commands

**Add a food entry**
```bash
# Basic (time defaults to now)
python -m cli.main add --title "Banana" --kcal 105 --carbs 27 --protein 1.3 --fat 0.4

# With specific date/time and confidence score
python -m cli.main add --title "Dinner" --kcal 600 --confidence 0.8 --date 2023-10-27 --time 19:30
```

**List entries**
```bash
# Recent entries
python -m cli.main list

# Filter by date range
python -m cli.main list --from 2023-10-01 --to 2023-10-27
```

**View Stats**
```bash
# Daily summary
python -m cli.main day

# Weekly summary (last 7 days)
python -m cli.main week
```

**Edit & Delete**
```bash
# Delete entry #1
python -m cli.main rm 1

# Edit entry #2 (update calories)
python -m cli.main edit 2 --kcal 200
```

**Backup & Restore**
```bash
python -m cli.main export --output backup.json
python -m cli.main import backup.json
```

### Web UI

Start the local web server:
```bash
python -m cli.main ui
```
Open [http://127.0.0.1:8787](http://127.0.0.1:8787) in your browser.

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
docker