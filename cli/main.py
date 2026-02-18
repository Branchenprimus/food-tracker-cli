import typer
import uvicorn
from foodtracker.service import FoodService
from foodtracker.models import Entry
from datetime import datetime, date

app = typer.Typer()
service = FoodService()

@app.command()
def init_db():
    service.init_db()
    typer.echo("Database initialized.")

@app.command()
def add(title: str, kcal: float, fat: float, carbs: float, protein: float, 
        serving: float = 1.0, confidence: float = 0.7):
    """Add a new food entry."""
    entry = service.add_entry(title, kcal, fat, carbs, protein, serving, confidence)
    typer.echo(f"Added entry: {entry.title} ({entry.kcal} kcal)")

@app.command()
def list(limit: int = 10):
    """List recent entries."""
    entries = service.list_entries(limit=limit)
    for e in entries:
        typer.echo(f"[{e.id}] {e.entry_date} {e.entry_time} - {e.title}: {e.kcal} kcal")

@app.command()
def delete(entry_id: int):
    """Delete an entry by ID."""
    if service.delete_entry(entry_id):
        typer.echo(f"Deleted entry {entry_id}")
    else:
        typer.echo(f"Entry {entry_id} not found")

@app.command()
def ui(host: str = "0.0.0.0", port: int = 8787, reload: bool = False):
    """Start the Web UI server."""
    typer.echo("Initializing database...")
    service.init_db()
    typer.echo(f"Starting UI at http://{host}:{port}")
    # Update to point to the new location of the API app
    uvicorn.run("foodtracker.api:app", host=host, port=port, reload=reload)

if __name__ == "__main__":
    app()
