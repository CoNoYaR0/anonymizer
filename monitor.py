import time
import httpx
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/status"
UPDATE_INTERVAL_SECONDS = 2  # How often to refresh the data

console = Console()

def get_status_data() -> dict | None:
    """Fetches data from the API's /status endpoint."""
    try:
        with httpx.Client(timeout=1.0) as client:
            response = client.get(API_URL)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
            return response.json()
    except httpx.RequestError as e:
        return {"error": f"Request failed: {e.__class__.__name__}", "detail": str(e)}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e.__class__.__name__}", "detail": str(e)}

def generate_dashboard(data: dict) -> Panel:
    """Generates the Rich Panel to be displayed."""
    if not data or "error" in data:
        error_message = data.get('detail', 'Could not connect to API. Is the server running?')
        return Panel(
            f"[bold red]Error[/bold red]\n{error_message}",
            title="API Monitor",
            border_style="red"
        )

    table = Table(show_header=False, box=None, expand=True)
    table.add_column(style="cyan", justify="right")
    table.add_column(style="white")

    # App-specific stats
    table.add_row("[bold]App CPU Usage:[/bold]", f"{data.get('app_cpu_usage_percent', 'N/A'):.1f}%")
    app_memory = data.get('app_memory_usage', {})
    table.add_row("[bold]App Memory Usage:[/bold]", f"{app_memory.get('used_mb', 'N/A')}")

    table.add_row("---", "---") # Separator

    # System-wide stats
    disk = data.get('system_disk_usage', {})
    table.add_row("[bold]Disk Total:[/bold]", f"{disk.get('total', 'N/A')}")
    table.add_row("[bold]Disk Used:[/bold]", f"{disk.get('used', 'N/A')} ({disk.get('percent', 0)}%)")

    return Panel(table, title="[bold green]API Status Monitor[/bold green]", border_style="green", expand=True)


if __name__ == "__main__":
    console.print("[yellow]Starting API monitor... Press Ctrl+C to exit.[/yellow]")
    with Live(generate_dashboard(get_status_data()), screen=True, redirect_stderr=False, refresh_per_second=4) as live:
        while True:
            try:
                time.sleep(UPDATE_INTERVAL_SECONDS)
                data = get_status_data()
                live.update(generate_dashboard(data))
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping monitor.[/yellow]")
                break
            except Exception as e:
                console.print(f"\n[bold red]An unexpected error occurred in the monitor loop: {e}[/bold red]")
                break
