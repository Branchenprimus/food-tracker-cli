import argparse
import json
import os
import sys
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = os.getenv("FOOD_TRACKER_API_BASE", "https://kcal-tracker.darwin-labs.org")
DEFAULT_API_KEY = os.getenv("FOOD_TRACKER_API_KEY", "")


def _request(method: str, base_url: str, path: str, api_key: str, payload: dict | None = None):
    if not api_key:
        print("Error: missing API key. Set FOOD_TRACKER_API_KEY or pass --api-key.", file=sys.stderr)
        sys.exit(2)

    body = None
    headers = {"X-API-Key": api_key}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = Request(f"{base_url.rstrip('/')}{path}", method=method, headers=headers, data=body)
    try:
        with urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data) if data else {}
    except HTTPError as e:
        msg = e.read().decode("utf-8", errors="replace")
        print(f"HTTP {e.code}: {msg}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_me(args):
    data = _request("GET", args.base_url, "/api/me", args.api_key)
    print(json.dumps(data, indent=2))


def cmd_add(args):
    now = datetime.now()
    payload = {
        "title": args.title,
        "kcal": float(args.kcal),
        "fat_g": float(args.fat),
        "carbs_g": float(args.carbs),
        "protein_g": float(args.protein),
        "serving_amount": float(args.serving),
        "confidence": float(args.confidence),
        "entry_date": args.date or now.strftime("%Y-%m-%d"),
        "entry_time": args.time or now.strftime("%H:%M"),
    }
    data = _request("POST", args.base_url, "/api/entries", args.api_key, payload)
    print(f"Added entry: {data.get('title')} ({data.get('kcal')} kcal) [id={data.get('id')}]")


def cmd_list(args):
    path = "/api/entries"
    if args.date:
        path += f"?date={args.date}"
    data = _request("GET", args.base_url, path, args.api_key)
    for row in data[: args.limit]:
        print(
            f"[{row.get('id')}] {row.get('entry_date')} {row.get('entry_time')} - "
            f"{row.get('title')}: {row.get('kcal')} kcal"
        )


def cmd_delete(args):
    _request("DELETE", args.base_url, f"/api/entries/{args.entry_id}", args.api_key)
    print(f"Deleted entry {args.entry_id}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Food Tracker API client")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key (or set FOOD_TRACKER_API_KEY)")

    sub = parser.add_subparsers(dest="command", required=True)

    me = sub.add_parser("me", help="Show authenticated user")
    me.set_defaults(func=cmd_me)

    add = sub.add_parser("add", help="Add an entry")
    add.add_argument("title")
    add.add_argument("kcal", type=float)
    add.add_argument("fat", type=float)
    add.add_argument("carbs", type=float)
    add.add_argument("protein", type=float)
    add.add_argument("--serving", type=float, default=1.0)
    add.add_argument("--confidence", type=float, default=0.7)
    add.add_argument("--date", help="YYYY-MM-DD")
    add.add_argument("--time", help="HH:MM")
    add.set_defaults(func=cmd_add)

    ls = sub.add_parser("list", help="List entries")
    ls.add_argument("--date", help="YYYY-MM-DD")
    ls.add_argument("--limit", type=int, default=10)
    ls.set_defaults(func=cmd_list)

    delete = sub.add_parser("delete", help="Delete an entry")
    delete.add_argument("entry_id", type=int)
    delete.set_defaults(func=cmd_delete)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
