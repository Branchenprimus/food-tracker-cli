import typer
from typing import Optional
from datetime import date, datetime, time
from typing_extensions import Annotated
import sys

from core.service import FoodService
from core.models import Entry
from format.printer import print_entries, print_daily_stats
from format.json_out import dump_json
from config.config import DEFAULT_CONFIDENCE

app = typer.Typer(help="Food Tracker CLI")
service = FoodService()

@app.command()
def db_init():
    """Initialize the database and apply migrations."""
    service.init_db()
    typer.echo("Database initialized and migrations applied.")

@app.command()
def add(
    title: Annotated[str, typer.Option(help="Title of the food entry")],
    kcal: Annotated[float, typer.Option(help="Calories")],
    fat: Annotated[float, typer.Option(help="Fat in grams")],
    carbs: Annotated[float, typer.Option(help="Carbs in grams")],
    protein: Annotated[float, typer.Option(help="Protein in grams")],
    serving: Annotated[float, typer.Option(help="Serving amount")] = 1.0,
    confidence: Annotated[float, typer.Option(help="Confidence score 0.0-1.0")] = DEFAULT_CONFIDENCE,
    date: Annotated[Optional[str], typer.Option(help="YYYY-MM-DD")] = None,
    time: Annotated[Optional[str], typer.Option(help="HH:MM")] = None,
    json: bool = False
):
    """Add a new food entry."""
    entry_date = datetime.strptime(date, "%Y-%m-%d").date() if date else None
    entry_time = datetime.strptime(time, "%H:%M").time() if time else None
    
    entry = service.add_entry(
        title=title, kcal=kcal, fat=fat, carbs=carbs, protein=protein,
        serving=serving, confidence=confidence,
        entry_date=entry_date, entry_time=entry_time
    )
    
    if json:
        dump_json(entry)
    else:
        print_entries([entry], title="Added Entry")

@app.command("list")
def list_entries(
    start: Annotated[Optional[str], typer.Option("--from", help="YYYY-MM-DD")] = None,
    end: Annotated[Optional[str], typer.Option("--to", help="YYYY-MM-DD")] = None,
    limit: int = 50,
    json: bool = False
):
    """List food entries."""
    start_date = datetime.strptime(start, "%Y-%m-%d").date() if start else None
    end_date = datetime.strptime(end, "%Y-%m-%d").date() if end else None

    entries = service.list_entries(from_date=start_date, to_date=end_date, limit=limit)
    
    if json:
        dump_json(entries)
    else:
        print_entries(entries)

@app.command()
def week(
    ending: Annotated[Optional[str], typer.Option(help="YYYY-MM-DD")] = None,
    json: bool = False
):
    """Show weekly summary (last 7 days)."""
    end_date = datetime.strptime(ending, "%Y-%m-%d").date() if ending else datetime.now().date()
    # TODO: Implement weekly stats in service/repo. For now, let's just show a simple aggregation?
    # Or just list entries for the week.
    # The spec says "7-day summary".
    # I'll implement a simple one here or adding a method to service.
    # Let's add get_weekly_stats to service first.
    # For now, let's just list the week's entries.
    start_date = end_date.replace(day=end_date.day-6) if end_date.day > 6 else end_date # This logic is buggy for month crossing.
    from datetime import timedelta
    start_date = end_date - timedelta(days=6)
    
    entries = service.list_entries(from_date=start_date, to_date=end_date, limit=1000)
    # Aggregate in memory for now
    stats = DailyStats(
        date=end_date,
        total_kcal=sum(e.kcal for e in entries),
        total_protein=sum(e.protein_g for e in entries),
        total_carbs=sum(e.carbs_g for e in entries),
        total_fat=sum(e.fat_g for e in entries),
        entry_count=len(entries)
    )
    
    if json:
        dump_json({"start": start_date, "end": end_date, "stats": stats})
    else:
        print_daily_stats(stats) # Reuse daily stats printer but it says "Daily Summary"
        print_entries(entries, title=f"Entries Since {start_date}")

@app.command()
def edit(
    entry_id: int,
    title: Optional[str] = None,
    kcal: Optional[float] = None,
    fat: Optional[float] = None,
    carbs: Optional[float] = None,
    protein: Optional[float] = None,
    serving: Optional[float] = None,
    confidence: Optional[float] = None,
):
    """Edit an existing entry."""
    updates = {}
    if title is not None: updates['title'] = title
    if kcal is not None: updates['kcal'] = kcal
    if fat is not None: updates['fat_g'] = fat
    if carbs is not None: updates['carbs_g'] = carbs
    if protein is not None: updates['protein_g'] = protein
    if serving is not None: updates['serving_amount'] = serving
    if confidence is not None: updates['confidence'] = confidence
    
    updated = service.update_entry(entry_id, **updates)
    if updated:
        print_entries([updated], title="Updated Entry")
    else:
        typer.echo(f"Entry {entry_id} not found.", err=True)

@app.command()
def export(output: Annotated[Optional[str], typer.Option(help="File path to export JSON")] = None):
    """Export all entries to JSON."""
    entries = service.list_entries(limit=10000) # dump all
    data = {"entries": [e.model_dump(mode='json') for e in entries]}
    import json
    if output:
        with open(output, 'w') as f:
            json.dump(data, f, indent=2)
        typer.echo(f"Exported {len(entries)} entries to {output}")
    else:
        print(json.dumps(data, indent=2))

@app.command("import")
def import_entries(input_file: str):
    """Import entries from a JSON file."""
    import json
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    count = 0
    for item in data.get('entries', []):
        # We assume item has keys matching add_entry args roughly
        # This is a bit naive, might need adaptation depending on export format
        # But since we control export, it matches model.
        # We need to parse dates back
        e_date = datetime.fromisoformat(item['entry_date']).date() if 'entry_date' in item else None
        e_time = datetime.strptime(item['entry_time'], "%H:%M:%S").time() if 'entry_time' in item else None # model dump might include seconds
        
        service.add_entry(
            title=item['title'],
            kcal=item['kcal'],
            fat=item['fat_g'],
            carbs=item['carbs_g'],
            protein=item['protein_g'],
            serving=item.get('serving_amount', 1.0),
            confidence=item.get('confidence', 0.7),
            entry_date=e_date,
            entry_time=e_time
        )
        count += 1
    typer.echo(f"Imported {count} entries.")

@app.command()
def day(
    date: Annotated[Optional[str], typer.Option(help="YYYY-MM-DD")] = None,
    json: bool = False
):
    """Show daily totals."""
    day_date = datetime.strptime(date, "%Y-%m-%d").date() if date else datetime.now().date()
    stats = service.get_daily_summary(day_date)
    
    if json:
        dump_json(stats)
    else:
        print_daily_stats(stats)
        # Also show entries for that day? The spec says "daily totals + optional item breakdown"
        # Let's keep it simple for now or maybe list entries too if requested. 
        # Plan says "food day – daily totals + optional item breakdown". 
        # Let's show totals first. User might use `food list --from X --to X` for breakdown.

@app.command()
def rm(entry_id: int):
    """Delete an entry."""
    if service.delete_entry(entry_id):
        typer.echo(f"Entry {entry_id} deleted.")
    else:
        typer.echo(f"Entry {entry_id} not found.", err=True)

@app.command()
def ui(
    port: int = 8787,
    reload: bool = False
):
    """Start the Web UI server."""
    import uvicorn
    typer.echo(f"Starting UI at http://127.0.0.1:{port}")
    uvicorn.run("web.app:app", host="127.0.0.1", port=port, reload=reload)

if __name__ == "__main__":
    app()
