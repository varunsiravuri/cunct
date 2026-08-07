from __future__ import annotations

import json
from typing import Any

from rich.console import Console

from churn_autopsy.config import get_settings
from churn_autopsy.hydra_client import HydraClient
from churn_autopsy.ingest.documents import build_document_uploads
from churn_autopsy.ingest.fixtures import (
    build_intercom_items,
    build_posthog_items,
    build_stripe_items,
    write_fixture_json,
)
from churn_autopsy.ingest.intercom_ingest import fetch_live_intercom_items
from churn_autopsy.ingest.posthog_ingest import fetch_live_posthog_items
from churn_autopsy.ingest.stripe_ingest import fetch_live_stripe_items

console = Console()


def _merge_by_id(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            out.append(item)
    return out


def collect_app_items(prefer_live: bool = True) -> list[dict[str, Any]]:
    settings = get_settings()
    fixtures = (
        build_stripe_items(settings.database, settings.collection)
        + build_intercom_items(settings.database, settings.collection)
        + build_posthog_items(settings.database, settings.collection)
    )

    if not prefer_live:
        console.print("[cyan]Using reproducible fixtures for Stripe / Intercom / PostHog[/cyan]")
        return fixtures

    live_parts: list[dict[str, Any]] = []
    sources_used: list[str] = []

    if settings.stripe_api_key:
        live_parts.extend(fetch_live_stripe_items(settings))
        sources_used.append("Stripe(live)")
    if settings.intercom_token:
        live_parts.extend(fetch_live_intercom_items(settings))
        sources_used.append("Intercom(live)")
    else:
        sources_used.append("Intercom(fixtures)")
    if settings.posthog_api_key and settings.posthog_project_id:
        live_parts.extend(fetch_live_posthog_items(settings))
        sources_used.append("PostHog(live)")

    if not live_parts:
        console.print("[cyan]No live keys — using fixtures for all sources[/cyan]")
        return fixtures

    console.print(f"[cyan]Sources: {', '.join(sources_used)} + fixture merge[/cyan]")
    return _merge_by_id(live_parts, fixtures)


def run_ingest(*, dry_run: bool = False, prefer_live: bool = True) -> dict[str, Any]:
    settings = get_settings()
    write_fixture_json()
    items = collect_app_items(prefer_live=prefer_live)
    docs, doc_meta = build_document_uploads(settings)

    summary = {
        "database": settings.database,
        "collection": settings.collection,
        "app_knowledge_count": len(items),
        "documents": [d[0] for d in docs],
        "by_provider": {},
    }
    for it in items:
        summary["by_provider"][it["provider"]] = summary["by_provider"].get(it["provider"], 0) + 1

    console.print(json.dumps(summary, indent=2))

    if dry_run:
        console.print("[yellow]dry-run: skipped HydraDB upload[/yellow]")
        return summary

    with HydraClient(settings) as client:
        console.print("[green]Ensuring database…[/green]")
        client.ensure_database()
        console.print(f"[green]Ingesting {len(items)} app sources…[/green]")
        client.ingest_app_knowledge(items)
        console.print(f"[green]Ingesting {len(docs)} documents…[/green]")
        client.ingest_documents(docs, doc_meta)
        console.print("[green]Waiting for ingest to settle…[/green]")
        client.wait_ingest()

    console.print("[bold green]Ingest complete.[/bold green]")
    return summary


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest Churn Autopsy sources into HydraDB")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--fixtures-only", action="store_true", help="Ignore live credentials")
    args = parser.parse_args()
    run_ingest(dry_run=args.dry_run, prefer_live=not args.fixtures_only)
