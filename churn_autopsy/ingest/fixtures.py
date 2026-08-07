from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from churn_autopsy.config import FIXTURES


def load_customers() -> dict[str, Any]:
    return json.loads((FIXTURES / "customers.json").read_text())


def _base_item(
    *,
    item_id: str,
    title: str,
    provider: str,
    kind: str,
    external_id: str,
    timestamp: str,
    database: str,
    collection: str,
    fields: dict[str, Any],
    metadata: dict[str, Any],
    additional_metadata: dict[str, Any] | None = None,
    relations: list[dict[str, Any]] | None = None,
    url: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": item_id,
        "database": database,
        "collection": collection,
        "title": title,
        "type": provider,
        "kind": kind,
        "provider": provider,
        "external_id": external_id,
        "timestamp": timestamp,
        "fields": fields,
        "metadata": metadata,
        "additional_metadata": additional_metadata or {},
    }
    if url:
        item["url"] = url
    if relations:
        item["relations"] = relations
    return item


def build_stripe_items(database: str, collection: str) -> list[dict[str, Any]]:
    data = load_customers()
    items: list[dict[str, Any]] = []
    for c in data["customers"]:
        person = c["person"]
        stripe = c["stripe"]
        meta = {
            "source": "stripe",
            "customer_key": c["customer_key"],
            "company_name": c["company_name"],
            "plan": c["plan"],
            "status": c["status"],
            "email": person["email"],
            "person_name": person["name"],
            "customer_id": stripe["customer_id"],
        }

        # Customer profile
        items.append(
            _base_item(
                item_id=f"stripe_customer_{stripe['customer_id']}",
                title=f"Stripe customer {c['company_name']} ({person['name']})",
                provider="stripe",
                kind="custom",
                external_id=stripe["customer_id"],
                timestamp=stripe.get("canceled_at") or "2026-05-01T00:00:00Z",
                database=database,
                collection=collection,
                url=f"https://dashboard.stripe.com/customers/{stripe['customer_id']}",
                fields={
                    "kind": "custom",
                    "data": {
                        "object": "customer",
                        "name": person["name"],
                        "email": person["email"],
                        "company": c["company_name"],
                        "plan": c["plan"],
                        "mrr_usd": c["mrr_usd"],
                        "status": c["status"],
                        "subscription_id": stripe["subscription_id"],
                    },
                },
                metadata=meta,
                additional_metadata={"object_type": "customer"},
            )
        )

        # Subscription event
        sub_ts = stripe.get("canceled_at") or "2026-07-01T00:00:00Z"
        sub_text = (
            f"Subscription {stripe['subscription_id']} for {c['company_name']} "
            f"({person['name']}, {person['email']}, customer_id={stripe['customer_id']}) "
            f"on plan {c['plan']} (MRR ${c['mrr_usd']}). Status: {c['status']}."
        )
        if stripe.get("canceled_at"):
            sub_text += f" Canceled at {stripe['canceled_at']}."
        items.append(
            _base_item(
                item_id=f"stripe_sub_{stripe['subscription_id']}",
                title=f"Stripe subscription {c['company_name']} {c['plan']}",
                provider="stripe",
                kind="custom",
                external_id=stripe["subscription_id"],
                timestamp=sub_ts,
                database=database,
                collection=collection,
                fields={"kind": "custom", "data": {"object": "subscription", "summary": sub_text, **stripe, "plan": c["plan"], "status": c["status"], "email": person["email"], "customer_id": stripe["customer_id"]}},
                metadata=meta,
                additional_metadata={"object_type": "subscription"},
                relations=[
                    {
                        "relation_type": "belongs_to",
                        "target_provider": "stripe",
                        "target_external_id": stripe["customer_id"],
                    }
                ],
            )
        )

        if stripe.get("refund_id"):
            refund_text = (
                f"Refund {stripe['refund_id']} of ${stripe['refund_amount_usd']} issued to "
                f"{person['name']} ({person['email']}, customer_id={stripe['customer_id']}) "
                f"/ {c['company_name']} on {stripe['refund_at']}. "
                f"Reason: {stripe['refund_reason']}. Subscription plan: {c['plan']}. "
                f"Customer status: {c['status']}."
            )
            if stripe.get("canceled_at"):
                refund_text += f" Canceled at {stripe['canceled_at']}."
            items.append(
                _base_item(
                    item_id=f"stripe_refund_{stripe['refund_id']}",
                    title=f"Stripe refund {c['company_name']} ${stripe['refund_amount_usd']}",
                    provider="stripe",
                    kind="custom",
                    external_id=stripe["refund_id"],
                    timestamp=stripe["refund_at"],
                    database=database,
                    collection=collection,
                    fields={
                        "kind": "custom",
                        "data": {
                            "object": "refund",
                            "summary": refund_text,
                            "amount_usd": stripe["refund_amount_usd"],
                            "reason": stripe["refund_reason"],
                        },
                    },
                    metadata={**meta, "has_refund": "true"},
                    additional_metadata={"object_type": "refund"},
                    relations=[
                        {
                            "relation_type": "belongs_to",
                            "target_provider": "stripe",
                            "target_external_id": stripe["customer_id"],
                        }
                    ],
                )
            )
    return items


def build_intercom_items(database: str, collection: str) -> list[dict[str, Any]]:
    data = load_customers()
    scripts = {
        "novalabs": [
            (
                "2026-06-11T14:02:00Z",
                "mira.chen@novalabs.io",
                "We were double-charged for our Pro plan this month. Invoice looks duplicated and dashboard exports are failing for our ops team.",
            ),
            (
                "2026-06-11T14:18:00Z",
                "support@signalboard.io",
                "Sorry Mira — I can see the duplicate invoice. Opening a refund and escalating exports.",
            ),
            (
                "2026-06-17T10:41:00Z",
                "mira.chen@novalabs.io",
                "Refund arrived, but exports still broken. We're canceling Pro unless this is fixed today.",
            ),
            (
                "2026-06-17T11:05:00Z",
                "mira.chen@novalabs.io",
                "Seguimiento en español: estamos en plan Pro y las exportaciones del dashboard siguen con falla. El duplicado de la factura no se resuelve.",
            ),
        ],
        "brightline": [
            (
                "2026-07-21T09:12:00Z",
                "jordan.lee@brightline.co",
                "Search is painfully slow during US peak hours. Saved searches are basically unusable.",
            ),
            (
                "2026-07-21T09:40:00Z",
                "support@signalboard.io",
                "Thanks Jordan — engineering is profiling the search path. Tracking as INT-5108.",
            ),
        ],
        "orbit": [
            (
                "2026-06-28T16:05:00Z",
                "priya.shah@orbit.health",
                "After the Q2 pricing change Enterprise is too expensive for what we use. We never adopted AI Assist and won't renew.",
            ),
            (
                "2026-06-28T16:22:00Z",
                "cs@signalboard.io",
                "Understood Priya. Happy to discuss a grandfathered rate before July 2.",
            ),
            (
                "2026-07-01T18:01:00Z",
                "priya.shah@orbit.health",
                "We'll proceed with cancel. Please confirm Enterprise ends July 2.",
            ),
        ],
    }

    items: list[dict[str, Any]] = []
    for c in data["customers"]:
        person = c["person"]
        ic = c["intercom"]
        meta = {
            "source": "intercom",
            "customer_key": c["customer_key"],
            "company_name": c["company_name"],
            "plan": c["plan"],
            "status": c["status"],
            "email": person["email"],
            "person_name": person["name"],
            "customer_id": c["stripe"]["customer_id"],
            "ticket_id": ic["ticket_id"],
        }
        body_parts = []
        for ts, author, text in scripts[c["customer_key"]]:
            body_parts.append(f"[{ts}] {author}: {text}")
            items.append(
                _base_item(
                    item_id=f"intercom_msg_{ic['conversation_id']}_{ts}",
                    title=f"Intercom {ic['ticket_id']} — {person['name']}",
                    provider="intercom",
                    kind="message",
                    external_id=f"{ic['conversation_id']}:{ts}",
                    timestamp=ts,
                    database=database,
                    collection=collection,
                    url=f"https://app.intercom.com/a/apps/_/inbox/conversation/{ic['conversation_id']}",
                    fields={
                        "kind": "message",
                        "body": text,
                        "author": author,
                        "thread_id": ic["conversation_id"],
                        "created_at": ts,
                    },
                    metadata=meta,
                    additional_metadata={
                        "conversation_id": ic["conversation_id"],
                        "contact_id": ic["contact_id"],
                    },
                    relations=[
                        {
                            "relation_type": "about_customer",
                            "target_provider": "stripe",
                            "target_external_id": c["stripe"]["customer_id"],
                        }
                    ],
                )
            )

        # Ticket summary for easier retrieval
        items.append(
            _base_item(
                item_id=f"intercom_ticket_{ic['ticket_id']}",
                title=f"Intercom ticket {ic['ticket_id']} {c['company_name']}",
                provider="intercom",
                kind="ticket",
                external_id=ic["ticket_id"],
                timestamp=scripts[c["customer_key"]][-1][0],
                database=database,
                collection=collection,
                fields={
                    "kind": "ticket",
                    "title": f"{ic['ticket_id']}: {c['story']['primary_complaint']}",
                    "description": "\n".join(body_parts),
                    "status": "closed" if c["status"] == "canceled" else "open",
                    "assignee": "support",
                    "requester": person["email"],
                },
                metadata=meta,
                additional_metadata={"object_type": "ticket"},
            )
        )
    return items


def build_posthog_items(database: str, collection: str) -> list[dict[str, Any]]:
    data = load_customers()
    # Weekly feature usage snapshots — intentional drop before churn.
    usage_series = {
        "novalabs": [
            ("2026-05-26", {"dashboard-exports": 42, "saved-searches": 18, "ai-assist": 2}),
            ("2026-06-02", {"dashboard-exports": 39, "saved-searches": 17, "ai-assist": 1}),
            ("2026-06-09", {"dashboard-exports": 4, "saved-searches": 16, "ai-assist": 0}),
            ("2026-06-16", {"dashboard-exports": 0, "saved-searches": 9, "ai-assist": 0}),
        ],
        "brightline": [
            ("2026-07-07", {"dashboard-exports": 12, "saved-searches": 55, "ai-assist": 8}),
            ("2026-07-14", {"dashboard-exports": 11, "saved-searches": 48, "ai-assist": 7}),
            ("2026-07-21", {"dashboard-exports": 10, "saved-searches": 12, "ai-assist": 6}),
            ("2026-07-28", {"dashboard-exports": 9, "saved-searches": 5, "ai-assist": 5}),
        ],
        "orbit": [
            ("2026-06-10", {"dashboard-exports": 20, "saved-searches": 22, "ai-assist": 0}),
            ("2026-06-17", {"dashboard-exports": 18, "saved-searches": 19, "ai-assist": 0}),
            ("2026-06-24", {"dashboard-exports": 15, "saved-searches": 14, "ai-assist": 0}),
            ("2026-07-01", {"dashboard-exports": 3, "saved-searches": 4, "ai-assist": 0}),
        ],
    }

    items: list[dict[str, Any]] = []
    for c in data["customers"]:
        person = c["person"]
        ph = c["posthog"]
        meta = {
            "source": "posthog",
            "customer_key": c["customer_key"],
            "company_name": c["company_name"],
            "plan": c["plan"],
            "status": c["status"],
            "email": person["email"],
            "person_name": person["name"],
            "customer_id": c["stripe"]["customer_id"],
            "distinct_id": ph["distinct_id"],
        }
        for week, features in usage_series[c["customer_key"]]:
            abandoned = c["story"]["feature_abandoned"]
            summary = (
                f"PostHog weekly usage for {person['name']} ({ph['distinct_id']}) at {c['company_name']} "
                f"week of {week}: " + ", ".join(f"{k}={v}" for k, v in features.items()) + ". "
                f"Primary abandoned feature signal: {abandoned}={features.get(abandoned, 0)}."
            )
            items.append(
                _base_item(
                    item_id=f"posthog_usage_{ph['distinct_id']}_{week}",
                    title=f"PostHog usage {c['company_name']} week {week}",
                    provider="posthog",
                    kind="custom",
                    external_id=f"{ph['distinct_id']}:{week}",
                    timestamp=f"{week}T12:00:00Z",
                    database=database,
                    collection=collection,
                    fields={
                        "kind": "custom",
                        "data": {
                            "object": "usage_snapshot",
                            "summary": summary,
                            "features": features,
                            "abandoned_feature": abandoned,
                            "distinct_id": ph["distinct_id"],
                            "org_id": ph["org_id"],
                        },
                    },
                    metadata=meta,
                    additional_metadata={"object_type": "usage_snapshot", "week": week},
                    relations=[
                        {
                            "relation_type": "same_person",
                            "target_provider": "stripe",
                            "target_external_id": c["stripe"]["customer_id"],
                        }
                    ],
                )
            )
    return items


def write_fixture_json() -> None:
    """Materialize app_knowledge JSON files for inspection / offline demos."""
    database = "churn_autopsy"
    collection = "default"
    mapping = {
        "stripe": build_stripe_items,
        "intercom": build_intercom_items,
        "posthog": build_posthog_items,
    }
    for name, builder in mapping.items():
        out_dir = FIXTURES / name
        out_dir.mkdir(parents=True, exist_ok=True)
        items = builder(database, collection)
        path = out_dir / "app_knowledge.json"
        path.write_text(json.dumps(items, indent=2))
        print(f"wrote {path} ({len(items)} items)")


if __name__ == "__main__":
    write_fixture_json()
