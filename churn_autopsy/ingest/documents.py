from __future__ import annotations

from pathlib import Path
from typing import Any

from churn_autopsy.config import FIXTURES, Settings


def build_document_uploads(settings: Settings) -> tuple[list[tuple[str, bytes, str]], list[dict[str, Any]]]:
    docs_dir = FIXTURES / "docs"
    documents: list[tuple[str, bytes, str]] = []
    metadata: list[dict[str, Any]] = []

    mapping = [
        ("churn_playbook.md", "text/markdown", {
            "id": "doc_churn_playbook",
            "metadata": {
                "source": "document",
                "doc_type": "playbook",
                "company_name": "NovaLabs",
                "person_name": "Mira Chen",
                "email": "mira.chen@novalabs.io",
                "status": "canceled",
                "plan": "pro",
            },
            "additional_metadata": {"filename": "churn_playbook.md"},
        }),
        ("q2_pricing_notes.md", "text/markdown", {
            "id": "doc_q2_pricing",
            "metadata": {
                "source": "document",
                "doc_type": "pricing",
                "company_name": "Orbit Health",
                "person_name": "Priya Shah",
                "email": "priya.shah@orbit.health",
                "status": "canceled",
                "plan": "enterprise",
            },
            "additional_metadata": {"filename": "q2_pricing_notes.md"},
        }),
    ]

    for filename, content_type, meta in mapping:
        path = docs_dir / filename
        documents.append((filename, path.read_bytes(), content_type))
        metadata.append(meta)

    return documents, metadata
