from __future__ import annotations

from typing import Any

import httpx

from churn_autopsy.config import Settings
from churn_autopsy.ingest.fixtures import build_posthog_items


def fetch_live_posthog_items(settings: Settings) -> list[dict[str, Any]]:
    if not settings.posthog_api_key or not settings.posthog_project_id:
        return build_posthog_items(settings.database, settings.collection)

    try:
        client = httpx.Client(
            base_url=settings.posthog_host,
            headers={"Authorization": f"Bearer {settings.posthog_api_key}"},
            timeout=60.0,
        )
        r = client.get(
            f"/api/projects/{settings.posthog_project_id}/persons",
            params={"limit": 50},
        )
        r.raise_for_status()
        persons = r.json().get("results", [])
        items: list[dict[str, Any]] = []
        for p in persons:
            distinct_ids = p.get("distinct_ids") or []
            distinct_id = distinct_ids[0] if distinct_ids else str(p.get("id"))
            props = p.get("properties") or {}
            email = props.get("email") or ""
            name = props.get("name") or email or distinct_id
            company = props.get("company") or ""
            plan = props.get("plan") or ""
            status = props.get("status") or ""
            abandoned = props.get("abandoned_feature") or ""
            summary = (
                f"PostHog person {name} email={email} distinct_id={distinct_id} "
                f"company={company} plan={plan} status={status}. "
                f"Primary abandoned feature signal: {abandoned}."
            )
            items.append(
                {
                    "id": f"posthog_person_{distinct_id}",
                    "database": settings.database,
                    "collection": settings.collection,
                    "title": f"PostHog person {name}",
                    "type": "posthog",
                    "kind": "custom",
                    "provider": "posthog",
                    "external_id": distinct_id,
                    "fields": {
                        "kind": "custom",
                        "data": {
                            "object": "person",
                            "summary": summary,
                            "properties": props,
                            "distinct_id": distinct_id,
                            "abandoned_feature": abandoned,
                        },
                    },
                    "metadata": {
                        "source": "posthog",
                        "email": email,
                        "person_name": name,
                        "company_name": company,
                        "plan": plan,
                        "status": status,
                        "distinct_id": distinct_id,
                    },
                    "additional_metadata": {"object_type": "person", "live": True},
                }
            )
        return items or build_posthog_items(settings.database, settings.collection)
    except Exception:
        return build_posthog_items(settings.database, settings.collection)
