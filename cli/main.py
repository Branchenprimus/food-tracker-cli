import typer
import uvicorn
from foodtracker.service import FoodService
from foodtracker.models import Entry
from datetime import datetime, date, timedelta, time
import random
import os

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

@app.command()
def seed_mock(days: int = 14, entries_per_day: int = 4, if_empty: bool = True):
    """Seed mock entries for development."""
    service.init_db()
    seed_user = service.ensure_user(email=os.getenv("DEV_USER_EMAIL", "dev@local.foodtracker"))
    if if_empty and service.list_entries(limit=1, user_id=seed_user.id):
        typer.echo("Skipping seed: database already has data.")
        return

    foods = [
        ("Oats with Berries", 320, 8, 52, 12),
        ("Greek Yogurt Bowl", 280, 6, 26, 30),
        ("Chicken Rice Bowl", 640, 16, 74, 48),
        ("Pasta Bolognese", 710, 22, 78, 38),
        ("Salmon and Potatoes", 590, 24, 42, 46),
        ("Protein Shake", 210, 4, 12, 36),
        ("Banana and Peanut Butter", 330, 14, 31, 10),
        ("Egg Wrap", 420, 19, 32, 27),
    ]
    quarter_hours = [0, 15, 30, 45]

    created = 0
    start_day = date.today() - timedelta(days=max(days - 1, 0))
    for day_offset in range(days):
        target_day = start_day + timedelta(days=day_offset)
        for _ in range(entries_per_day):
            title, kcal, fat, carbs, protein = random.choice(foods)
            factor = random.uniform(0.8, 1.25)
            entry_time = time(hour=random.randint(7, 21), minute=random.choice(quarter_hours))
            service.add_entry(
                title=title,
                kcal=round(kcal * factor, 1),
                fat=round(fat * factor, 1),
                carbs=round(carbs * factor, 1),
                protein=round(protein * factor, 1),
                serving=1.0,
                confidence=0.85,
                entry_date=target_day,
                entry_time=entry_time,
                user_id=seed_user.id,
            )
            created += 1

    typer.echo(f"Seeded {created} mock entries over {days} days.")

if __name__ == "__main__":
    app()
