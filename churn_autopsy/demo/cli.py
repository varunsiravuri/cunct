from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from churn_autopsy.config import get_settings
from churn_autopsy.hydra_client import HydraClient
from churn_autopsy.ingest.run_all import run_ingest
from churn_autopsy.planner.fastlane import FastLanePlanner

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()

DEFAULT_QUESTION = (
    "Which Pro customers canceled after a refund, what did they say in Intercom, "
    "and which feature did they stop using before cancel?"
)


@app.command()
def ingest(
    dry_run: bool = typer.Option(False, help="Build payloads without uploading"),
    fixtures_only: bool = typer.Option(False, help="Ignore live connector credentials"),
) -> None:
    """Ingest Stripe + Intercom + PostHog + documents into HydraDB."""
    run_ingest(dry_run=dry_run, prefer_live=not fixtures_only)


@app.command()
def connectors(
    dry_run: bool = typer.Option(False, help="Show what would be created without calling HydraDB"),
    sync: bool = typer.Option(True, help="Trigger sync after configuring"),
) -> None:
    """Set up native HydraDB connectors for Stripe, Intercom, and PostHog."""
    from churn_autopsy.connectors import HydraConnectorManager

    settings = get_settings()
    if dry_run:
        console.print("[cyan]Dry-run: would create native HydraDB connectors for:[/cyan]")
        for name, cred in (
            ("stripe", settings.stripe_api_key),
            ("intercom", settings.intercom_token),
            ("posthog", settings.posthog_api_key and settings.posthog_project_id),
        ):
            status = "credentials present" if cred else "missing credentials"
            console.print(f"  - {name}: {status}")
        return

    with HydraConnectorManager(settings) as mgr:
        providers = mgr.list_providers()
        supported = {p["provider"] for p in providers if p.get("supported")}
        needed = {"stripe", "intercom", "posthog"}
        missing_providers = needed - supported
        if missing_providers:
            console.print(f"[yellow]Providers not supported: {missing_providers}[/yellow]")

        results = mgr.setup_all()
        for name, result in results.items():
            if result.get("status") == "created_and_synced":
                cid = result.get("connector_id")
                console.print(f"[green]{name} connector created and synced[/green] ({cid})")
            elif result.get("status") == "skipped":
                console.print(f"[yellow]{name} skipped: {result.get('reason')}[/yellow]")
            else:
                console.print(f"[red]{name} failed: {result.get('error')}[/red]")

    if sync:
        console.print("[green]Sync triggered for all configured connectors.[/green]")


@app.command()
def ask(
    question: Optional[str] = typer.Argument(None),
    thinking_baseline: bool = typer.Option(False, help="Single thinking-mode query for comparison"),
    offline: bool = typer.Option(False, help="Use local fixtures (no Hydra API key needed)"),
) -> None:
    """Run FastLane autopsy on a natural-language question."""
    q = question or DEFAULT_QUESTION
    settings = get_settings()
    if offline or not settings.api_key:
        if not offline:
            console.print("[yellow]No HYDRA_DB_API_KEY — running offline against fixtures[/yellow]")
        planner = FastLanePlanner(None, settings, offline=True)
        result = planner.run(q, force_thinking_baseline=thinking_baseline)
    else:
        with HydraClient(settings) as client:
            planner = FastLanePlanner(client, settings)
            result = planner.run(q, force_thinking_baseline=thinking_baseline)

    table = Table(title="FastLane metrics")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("HydraDB calls", str(result.hydra_calls))
    table.add_row("Fast / Thinking", f"{result.fast_calls} / {result.thinking_calls}")
    table.add_row("Latency ms", f"{result.total_latency_ms:.0f}")
    table.add_row("Est. cost USD", f"{result.estimated_cost_usd(settings):.4f}")
    table.add_row("Entities", json.dumps(result.entities))
    console.print(Panel(result.answer, title="Autopsy answer", border_style="green"))
    console.print(table)
    for hop in result.hops:
        console.print(
            f"  • [{hop.mode}] {hop.name} — {hop.latency_ms:.0f}ms — filters={hop.filters}"
        )


@app.command("eval")
def eval_cmd(
    no_baseline: bool = typer.Option(False, help="Skip thinking-mode baseline comparison"),
    offline: bool = typer.Option(False, help="Score against local fixtures"),
) -> None:
    """Run the accuracy / latency / cost competition suite."""
    from churn_autopsy.eval.run_eval import run_eval

    run_eval(include_thinking_baseline=not no_baseline, offline=offline)


@app.command()
def demo(
    offline: bool = typer.Option(False, help="Use local fixtures (no Hydra API key needed)"),
) -> None:
    """60-second demo script: headline multi-hop + metrics."""
    console.print(
        Panel(
            "CunctHydra Churn Autopsy\nConnectors: Stripe · Intercom · PostHog · Documents",
            title="Demo",
            border_style="magenta",
        )
    )
    ask(DEFAULT_QUESTION, thinking_baseline=False, offline=offline)


if __name__ == "__main__":
    app()
