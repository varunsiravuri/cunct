from __future__ import annotations

from typing import Any

import httpx

from churn_autopsy.config import Settings
from churn_autopsy.ingest.fixtures import build_stripe_items


def fetch_live_stripe_items(settings: Settings) -> list[dict[str, Any]]:
    """Pull recent customers from Stripe when a key is present."""
    if not settings.stripe_api_key:
        return build_stripe_items(settings.database, settings.collection)

    try:
        client = httpx.Client(
            base_url="https://api.stripe.com/v1",
            headers={"Authorization": f"Bearer {settings.stripe_api_key}"},
            timeout=60.0,
        )
        customers = client.get("/customers", params={"limit": 50}).json().get("data", [])
        refunds = client.get("/refunds", params={"limit": 50}).json().get("data", [])
        items: list[dict[str, Any]] = []

        for cus in customers:
            email = cus.get("email") or ""
            name = cus.get("name") or email or cus["id"]
            md = cus.get("metadata") or {}
            plan = md.get("plan") or "unknown"
            status = md.get("status") or "unknown"
            company = md.get("company_name") or ""
            summary = (
                f"Stripe customer {name} ({email}, customer_id={cus['id']}) "
                f"company={company} Subscription plan: {plan}. Customer status: {status}. "
                f"MRR ${md.get('mrr_usd', '?')}. "
                f"Canceled at {md.get('canceled_at') or 'n/a'}. "
                f"Refund {md.get('refund_id') or 'none'} on {md.get('refund_at') or 'n/a'} "
                f"reason={md.get('refund_reason') or 'n/a'}. "
                f"Complaint: {md.get('primary_complaint') or 'n/a'}. "
                f"Abandoned feature signal: {md.get('feature_abandoned') or 'n/a'}."
            )
            meta = {
                "source": "stripe",
                "email": email,
                "person_name": name,
                "customer_id": cus["id"],
                "company_name": company,
                "plan": plan,
                "status": status,
            }
            if md.get("refund_id"):
                meta["has_refund"] = "true"

            items.append(
                {
                    "id": f"stripe_customer_{cus['id']}",
                    "database": settings.database,
                    "collection": settings.collection,
                    "title": f"Stripe customer {name}",
                    "type": "stripe",
                    "kind": "custom",
                    "provider": "stripe",
                    "external_id": cus["id"],
                    "timestamp": md.get("canceled_at") or md.get("refund_at") or None,
                    "fields": {
                        "kind": "custom",
                        "data": {
                            "object": "customer",
                            "summary": summary,
                            "name": name,
                            "email": email,
                            "metadata": md,
                        },
                    },
                    "metadata": meta,
                    "additional_metadata": {"object_type": "customer", "live": True},
                }
            )

        for ref in refunds:
            items.append(
                {
                    "id": f"stripe_refund_{ref['id']}",
                    "database": settings.database,
                    "collection": settings.collection,
                    "title": f"Stripe refund {ref['id']}",
                    "type": "stripe",
                    "kind": "custom",
                    "provider": "stripe",
                    "external_id": ref["id"],
                    "fields": {
                        "kind": "custom",
                        "data": {
                            "object": "refund",
                            "summary": f"Stripe refund {ref['id']} customer={ref.get('customer')} amount={ref.get('amount')}",
                            **{k: ref.get(k) for k in ("id", "customer", "amount", "status", "reason")},
                        },
                    },
                    "metadata": {
                        "source": "stripe",
                        "has_refund": "true",
                        "customer_id": ref.get("customer") or "",
                    },
                    "additional_metadata": {"object_type": "refund", "live": True},
                }
            )

        return items or build_stripe_items(settings.database, settings.collection)
    except Exception:
        return build_stripe_items(settings.database, settings.collection)
