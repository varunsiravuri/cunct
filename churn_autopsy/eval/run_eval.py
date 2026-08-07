from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from churn_autopsy.config import ROOT, get_settings
from churn_autopsy.hydra_client import HydraClient
from churn_autopsy.planner.fastlane import FastLanePlanner

console = Console()
QUESTIONS_PATH = Path(__file__).with_name("questions.json")


@dataclass
class QuestionScore:
    id: str
    category: str
    correct: bool
    score: float
    missing: list[str]
    latency_ms: float
    hydra_calls: int
    fast_calls: int
    thinking_calls: int
    cost_usd: float
    used_thinking: bool
    answer: str


def score_answer(answer: str, expected: dict[str, Any]) -> tuple[bool, float, list[str]]:
    text = answer.lower()
    missing: list[str] = []
    checks = 0
    hits = 0

    for needle in expected.get("must_include") or []:
        checks += 1
        if needle.lower() in text:
            hits += 1
        else:
            missing.append(needle)

    for group in expected.get("must_include_any") or []:
        checks += 1
        if any(opt.lower() in text for opt in group):
            hits += 1
        else:
            missing.append("ANY(" + "|".join(group) + ")")

    for needle in expected.get("must_not_include") or []:
        checks += 1
        if needle.lower() in text:
            missing.append(f"FORCED_ABSENCE_FAILED:{needle}")
        else:
            hits += 1

    score = hits / checks if checks else 0.0
    return score >= 0.8, score, missing


def run_eval(*, include_thinking_baseline: bool = True, offline: bool = False) -> dict[str, Any]:
    settings = get_settings()
    questions = json.loads(QUESTIONS_PATH.read_text())
    rows: list[QuestionScore] = []
    baseline_rows: list[dict[str, Any]] = []
    offline = offline or not settings.api_key

    def _run_suite(planner: FastLanePlanner) -> None:
        for q in questions:
            t0 = time.perf_counter()
            result = planner.run(q["question"])
            wall = (time.perf_counter() - t0) * 1000
            ok, score, missing = score_answer(result.answer, q["expected"])
            rows.append(
                QuestionScore(
                    id=q["id"],
                    category=q["category"],
                    correct=ok,
                    score=score,
                    missing=missing,
                    latency_ms=result.total_latency_ms or wall,
                    hydra_calls=result.hydra_calls,
                    fast_calls=result.fast_calls,
                    thinking_calls=result.thinking_calls,
                    cost_usd=result.estimated_cost_usd(settings),
                    used_thinking=result.used_thinking,
                    answer=result.answer,
                )
            )

            if include_thinking_baseline:
                b = planner.run(q["question"], force_thinking_baseline=True)
                bok, bscore, bmissing = score_answer(b.answer, q["expected"])
                baseline_rows.append(
                    {
                        "id": q["id"],
                        "correct": bok,
                        "score": bscore,
                        "missing": bmissing,
                        "latency_ms": b.total_latency_ms,
                        "hydra_calls": b.hydra_calls,
                        "cost_usd": b.estimated_cost_usd(settings),
                    }
                )

    if offline:
        console.print("[yellow]Offline eval against fixtures[/yellow]")
        _run_suite(FastLanePlanner(None, settings, offline=True))
    else:
        with HydraClient(settings) as client:
            _run_suite(FastLanePlanner(client, settings))

    accuracy = sum(1 for r in rows if r.correct) / len(rows) if rows else 0
    report = {
        "database": settings.database,
        "accuracy": accuracy,
        "avg_latency_ms": sum(r.latency_ms for r in rows) / len(rows) if rows else 0,
        "avg_hydra_calls": sum(r.hydra_calls for r in rows) / len(rows) if rows else 0,
        "fast_call_ratio": (
            sum(r.fast_calls for r in rows) / max(1, sum(r.hydra_calls for r in rows))
        ),
        "total_cost_usd": sum(r.cost_usd for r in rows),
        "questions": [asdict(r) for r in rows],
        "thinking_baseline": baseline_rows,
    }

    out = ROOT / "eval_results.json"
    out.write_text(json.dumps(report, indent=2))
    _print_table(rows, accuracy)
    console.print(f"[green]Wrote {out}[/green]")
    return report


def _print_table(rows: list[QuestionScore], accuracy: float) -> None:
    table = Table(title=f"Churn Autopsy Eval — accuracy {accuracy:.0%}")
    table.add_column("ID")
    table.add_column("OK")
    table.add_column("Score")
    table.add_column("Latency ms")
    table.add_column("Calls")
    table.add_column("Fast/Think")
    table.add_column("Cost $")
    for r in rows:
        table.add_row(
            r.id,
            "✓" if r.correct else "✗",
            f"{r.score:.2f}",
            f"{r.latency_ms:.0f}",
            str(r.hydra_calls),
            f"{r.fast_calls}/{r.thinking_calls}",
            f"{r.cost_usd:.4f}",
        )
    console.print(table)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--no-baseline", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    run_eval(include_thinking_baseline=not args.no_baseline, offline=args.offline)
