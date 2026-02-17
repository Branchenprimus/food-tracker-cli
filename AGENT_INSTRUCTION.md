# Agent Instructions for Food Tracker

This document provides guidelines for AI agents interacting with the Food Tracker CLI via the `food-tracker` wrapper script.

## 🚀 Getting Started

The most reliable way to interact with the application is through the `./food-tracker` wrapper script. This script executes commands inside the running Docker container, ensuring access to the correct environment and database.

**Prerequisites:**
- The Docker container must be running (`make dev` or `make deploy`).
- You may need `sudo` privileges if the user is not in the `docker` group.

## 🛠️ Core Commands

### 1. Adding Entries
Use the `add` command to log food. 
- **Required**: `--title`
- **Recommended**: `--kcal` (approximate is fine)
- **Optional**: `--protein`, `--carbs`, `--fat`, `--date`, `--time`

```bash
# Basic usage
./food-tracker add --title "Grilled Chicken Salad" --kcal 450

# Detailed usage
./food-tracker add --title "Oatmeal with Blueberries" --kcal 300 --carbs 45 --protein 10 --fat 5
```

### 2. Retrieving Data (Machine Readable)
**ALWAYS use the `--json` flag** when reading data. This ensures the output is structured and easy to parse.

#### List Recent Entries
Values are returned in a JSON array.

```bash
./food-tracker list --json --limit 5
```

#### Get Daily Stats
Returns totals for the current day (or specified date).

```bash
./food-tracker day --json
```

#### Get Weekly Summary
Returns a summary of the last 7 days.

```bash
./food-tracker week --json
```

### 3. Modifying Data
You can edit or delete entries using their `id`.

```bash
# Delete an entry
./food-tracker rm <ID>

# Update an entry (e.g., correct calories)
./food-tracker edit <ID> --kcal 500
```

## 🤖 Best Practices for Agents

1.  **Use JSON**: Always append `--json` to `list`, `day`, and `week` commands for reliable parsing.
2.  **Estimate Macros**: If exact macros are unknown, provide a reasonable estimate for calories.
3.  **Check Context**: Before adding a duplicate entry, check `list` to see if it was already logged recently.
4.  **Error Handling**: If a command fails, check the error message. Common issues include missing arguments or database locks (rare).

## 🔍 Troubleshooting

- **"docker: command not found"**: Ensure Docker is installed and in the PATH.
- **Permission Denied**: Try running with `sudo ./food-tracker ...`.
- **Container not running**: The wrapper script requires the `food-tracker` container to be active.
