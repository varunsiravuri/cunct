from __future__ import annotations

from typing import Any

import httpx

from churn_autopsy.config import Settings
from churn_autopsy.ingest.fixtures import build_intercom_items


def fetch_live_intercom_items(settings: Settings) -> list[dict[str, Any]]:
    if not settings.intercom_token:
        return build_intercom_items(settings.database, settings.collection)

    try:
        client = httpx.Client(
            base_url="https://api.intercom.io",
            headers={
                "Authorization": f"Bearer {settings.intercom_token}",
                "Accept": "application/json",
                "Intercom-Version": "2.11",
            },
            timeout=60.0,
        )
        conv = client.get("/conversations", params={"per_page": 20}).json()
        items: list[dict[str, Any]] = []
        for c in (conv.get("conversations") or [])[:20]:
            cid = str(c.get("id"))
            # Fetch full conversation for body + contacts
            detail = client.get(f"/conversations/{cid}").json()
            source = detail.get("source") or c.get("source") or {}
            body = source.get("body") or source.get("subject") or detail.get("title") or ""
            # strip simple HTML tags from Intercom bodies
            import re

            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body).strip()

            contact_email = ""
            contact_name = ""
            contacts = ((detail.get("contacts") or {}).get("contacts")) or []
            if contacts:
                contact_email = contacts[0].get("email") or ""
                contact_name = contacts[0].get("name") or ""
                # hydrate contact if email missing
                if not contact_email and contacts[0].get("id"):
                    cr = client.get(f"/contacts/{contacts[0]['id']}")
                    if cr.status_code == 200:
                        cj = cr.json()
                        contact_email = cj.get("email") or ""
                        contact_name = cj.get("name") or contact_name

            # also pull conversation parts
            parts = ((detail.get("conversation_parts") or {}).get("conversation_parts")) or []
            part_texts = []
            for p in parts[:10]:
                t = p.get("body") or ""
                t = re.sub(r"<[^>]+>", " ", t)
                t = re.sub(r"\s+", " ", t).strip()
                if t:
                    author = ((p.get("author") or {}).get("email")) or ((p.get("author") or {}).get("name")) or "unknown"
                    part_texts.append(f"{author}: {t}")
            full_text = body
            if part_texts:
                full_text = (body + "\n" + "\n".join(part_texts)).strip()

            company = ""
            plan = ""
            status = ""
            # parse markers we seeded: [NovaLabs | plan=pro | status=canceled | key=novalabs]
            m = re.search(r"\[([^\|]+)\s*\|\s*plan=([^\|]+)\s*\|\s*status=([^\|\]]+)", full_text)
            if m:
                company, plan, status = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()

            items.append(
                {
                    "id": f"intercom_conv_{cid}",
                    "database": settings.database,
                    "collection": settings.collection,
                    "title": f"Intercom conversation {cid} — {contact_name or contact_email or 'unknown'}",
                    "type": "intercom",
                    "kind": "ticket",
                    "provider": "intercom",
                    "external_id": cid,
                    "fields": {
                        "kind": "ticket",
                        "title": f"Conversation {cid}",
                        "description": full_text or f"Intercom conversation {cid}",
                        "status": detail.get("state") or c.get("state") or "open",
                        "requester": contact_email,
                    },
                    "metadata": {
                        "source": "intercom",
                        "email": contact_email,
                        "person_name": contact_name,
                        "company_name": company,
                        "plan": plan,
                        "status": status,
                        "ticket_id": cid,
                    },
                    "additional_metadata": {"object_type": "conversation", "live": True},
                }
            )
        return items or build_intercom_items(settings.database, settings.collection)
    except Exception:
        return build_intercom_items(settings.database, settings.collection)
