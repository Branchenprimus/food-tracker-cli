from typing import List
from rich.console import Console
from rich.table import Table
from rich import box
from core.models import Entry, DailyStats

console = Console()

def print_entries(entries: List[Entry], title: str = "Food Entries"):
    if not entries:
        console.print("[yellow]No entries found.[/yellow]")
        return

    table = Table(title=title, box=box.ROUNDED)
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Date", style="magenta")
    table.add_column("Time", style="magenta")
    table.add_column("Title", style="white")
    table.add_column("Serving", justify="right")
    table.add_column("Kcal", justify="right", style="green")
    table.add_column("P (g)", justify="right", style="blue")
    table.add_column("C (g)", justify="right", style="yellow")
    table.add_column("F (g)", justify="right", style="red")
    table.add_column("Conf", justify="right")

    for entry in entries:
        table.add_row(
            str(entry.id),
            entry.entry_date.isoformat(),
            entry.entry_time.strftime("%H:%M"),
            entry.title,
            f"{entry.serving_amount:.1f}",
            f"{entry.kcal:.0f}",
            f"{entry.protein_g:.1f}",
            f"{entry.carbs_g:.1f}",
            f"{entry.fat_g:.1f}",
            f"{entry.confidence:.0%}"
        )

    console.print(table)

def print_daily_stats(stats: DailyStats):
    table = Table(title=f"Daily Summary: {stats.date}", box=box.SIMPLE)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")

    table.add_row("Entries", str(stats.entry_count))
    table.add_row("Total Kcal", f"{stats.total_kcal:.0f}", style="green")
    table.add_row("Total Protein", f"{stats.total_protein:.1f}g", style="blue")
    table.add_row("Total Carbs", f"{stats.total_carbs:.1f}g", style="yellow")
    table.add_row("Total Fat", f"{stats.total_fat:.1f}g", style="red")

    console.print(table)
