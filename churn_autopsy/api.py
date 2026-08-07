from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from churn_autopsy.config import ROOT, get_settings
from churn_autopsy.hydra_client import HydraClient
from churn_autopsy.planner.fastlane import FastLanePlanner


def _chunk_snippet(chunk: dict[str, Any]) -> dict[str, Any]:
    """Return a short, readable snippet of a retrieved chunk for the UI evidence panel."""
    text = ""
    for key in ("chunk_content", "content", "text", "snippet", "body"):
        if chunk.get(key):
            text = str(chunk[key])
            break
    if not text:
        data = chunk.get("data") or chunk.get("fields", {}).get("data") or {}
        if isinstance(data, dict):
            for key in ("summary", "body", "description", "text"):
                if data.get(key):
                    text = str(data[key])
                    break
    # Clean up the markdown-ish document format for readability.
    if "## Title" in text:
        text = text.split("## Title")[1]

    title = chunk.get("title") or chunk.get("filename") or chunk.get("external_id") or ""
    if not title or title == "Retrieved context":
        first_line = text.strip().split("\n")[0]
        if first_line and not first_line.startswith("##"):
            title = first_line[:80]
    if not title:
        title = "Retrieved context"

    return {
        "title": title,
        "snippet": text.strip()[:320] + ("…" if len(text) > 320 else ""),
    }


app = FastAPI(title="Churn Autopsy API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_QUESTIONS = [
    {
        "id": "headline",
        "label": "Pro refund → Intercom → feature drop",
        "question": (
            "Which Pro customers canceled after a refund, what did they say in Intercom, "
            "and which feature did they stop using before cancel?"
        ),
    },
    {
        "id": "orbit",
        "label": "Orbit pricing + AI Assist",
        "question": (
            "Why did Orbit Health cancel Enterprise, and did they ever use AI Assist "
            "according to PostHog and Intercom?"
        ),
    },
    {
        "id": "brightline",
        "label": "Jordan Lee at-risk",
        "question": (
            "What did Jordan Lee say in Intercom about search, and which PostHog feature "
            "usage dropped afterward?"
        ),
    },
]


class AskRequest(BaseModel):
    question: str = Field(min_length=3)
    offline: bool = False
    thinking_baseline: bool = False


@app.get("/api/health")
def health() -> dict[str, Any]:
    s = get_settings()
    return {
        "ok": True,
        "database": s.database,
        "connectors": {
            "stripe": bool(s.stripe_api_key),
            "intercom": bool(s.intercom_token),
            "posthog": bool(s.posthog_api_key and s.posthog_project_id),
            "hydra": bool(s.api_key),
        },
    }


@app.get("/api/demo/questions")
def demo_questions() -> list[dict[str, str]]:
    return DEMO_QUESTIONS


@app.get("/api/eval/summary")
def eval_summary() -> dict[str, Any]:
    path = ROOT / "eval_results.json"
    if not path.exists():
        return {"available": False}
    data = json.loads(path.read_text())
    return {
        "available": True,
        "accuracy": data.get("accuracy"),
        "avg_latency_ms": data.get("avg_latency_ms"),
        "avg_hydra_calls": data.get("avg_hydra_calls"),
        "fast_call_ratio": data.get("fast_call_ratio"),
        "total_cost_usd": data.get("total_cost_usd"),
        "questions": [
            {
                "id": q.get("id"),
                "correct": q.get("correct"),
                "score": q.get("score"),
                "latency_ms": q.get("latency_ms"),
                "fast_calls": q.get("fast_calls"),
                "thinking_calls": q.get("thinking_calls"),
            }
            for q in data.get("questions") or []
        ],
    }


@app.post("/api/ask")
def ask(req: AskRequest) -> dict[str, Any]:
    settings = get_settings()
    offline = req.offline or not settings.api_key
    try:
        if offline:
            planner = FastLanePlanner(None, settings, offline=True)
            result = planner.run(req.question, force_thinking_baseline=req.thinking_baseline)
        else:
            with HydraClient(settings) as client:
                planner = FastLanePlanner(client, settings)
                result = planner.run(req.question, force_thinking_baseline=req.thinking_baseline)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {
        "question": result.question,
        "answer": result.answer,
        "entities": result.entities,
        "used_thinking": result.used_thinking,
        "metrics": {
            "hydra_calls": result.hydra_calls,
            "fast_calls": result.fast_calls,
            "thinking_calls": result.thinking_calls,
            "latency_ms": result.total_latency_ms,
            "cost_usd": result.estimated_cost_usd(settings),
        },
        "hops": [
            {
                "name": h.name,
                "mode": h.mode,
                "query": h.query,
                "latency_ms": h.latency_ms,
                "filters": h.filters,
                "chunk_count": len(h.chunks),
                "chunks": [
                    _chunk_snippet(ch) for ch in h.chunks[:5]
                ],
            }
            for h in result.hops
        ],
        "offline": offline,
    }


def main() -> None:
    import uvicorn

    uvicorn.run("churn_autopsy.api:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
