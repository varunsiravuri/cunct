from __future__ import annotations

"""Offline retrieval stub so demos work before Hydra credentials arrive."""

import json
from typing import Any

from churn_autopsy.config import FIXTURES, get_settings
from churn_autopsy.ingest.fixtures import (
    build_intercom_items,
    build_posthog_items,
    build_stripe_items,
)


def _all_items() -> list[dict[str, Any]]:
    s = get_settings()
    return (
        build_stripe_items(s.database, s.collection)
        + build_intercom_items(s.database, s.collection)
        + build_posthog_items(s.database, s.collection)
    )


def _doc_chunks() -> list[dict[str, Any]]:
    chunks = []
    for path in (FIXTURES / "docs").glob("*.md"):
        chunks.append(
            {
                "chunk_content": path.read_text(),
                "metadata": {"source": "document", "filename": path.name},
            }
        )
    return chunks


def _item_text(item: dict[str, Any]) -> str:
    fields = item.get("fields") or {}
    meta = item.get("metadata") or {}
    prefix = (
        f"[meta source={meta.get('source')} email={meta.get('email')} "
        f"customer_id={meta.get('customer_id')} company={meta.get('company_name')} "
        f"person={meta.get('person_name')} plan={meta.get('plan')} status={meta.get('status')}] "
    )
    if fields.get("kind") == "message":
        return prefix + f"{fields.get('author')}: {fields.get('body')}"
    if fields.get("kind") == "ticket":
        return prefix + f"{fields.get('title')}\n{fields.get('description')}"
    data = fields.get("data") or {}
    if isinstance(data, dict) and data.get("summary"):
        return prefix + str(data["summary"])
    return prefix + json.dumps(fields)


def offline_query(
    query: str,
    *,
    metadata_filters: dict[str, Any] | None = None,
    mode: str = "fast",
) -> dict[str, Any]:
    filters = metadata_filters or {}
    items = _all_items()
    chunks: list[dict[str, Any]] = []

    if filters.get("source") == "document":
        chunks = _doc_chunks()
    else:
        for item in items:
            meta = item.get("metadata") or {}
            ok = True
            for k, v in filters.items():
                if str(meta.get(k, "")).lower() != str(v).lower():
                    ok = False
                    break
            if not ok:
                continue
            chunks.append(
                {
                    "chunk_content": _item_text(item),
                    "metadata": meta,
                    "title": item.get("title"),
                    "provider": item.get("provider"),
                }
            )

    # Light query-term boost if no filters matched anything useful
    if not chunks:
        q = query.lower()
        for item in items:
            text = _item_text(item).lower()
            if any(tok in text for tok in q.split() if len(tok) > 3):
                chunks.append(
                    {
                        "chunk_content": _item_text(item),
                        "metadata": item.get("metadata") or {},
                        "title": item.get("title"),
                    }
                )

    return {
        "chunks": chunks[:12],
        "_meta": {"latency_ms": 8.0, "mode": mode, "query": query, "offline": True},
    }
