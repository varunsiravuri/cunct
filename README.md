# CunctHydra — Churn Autopsy

Cross-source churn investigation on **HydraDB**, built for the Cortex HydraDB challenge.

**Thesis:** How far can you push `mode: "fast"` for customer churn questions without sacrificing accuracy?

**Answer:** 16 difficult cross-source questions, **100% accuracy**, **97.7% fast-mode calls**, at **~1/3 the latency and 1/3 the cost** of a naive `thinking`-only baseline.

## Connectors

| Source | Role | HydraDB native connector | Direct app_knowledge fallback |
|--------|------|--------------------------|-------------------------------|
| **Stripe** | Plans, refunds, cancel dates, MRR | `cunct-stripe` | `fixtures/stripe` |
| **Intercom** | Support conversations / tickets | `cunct-intercom` | `fixtures/intercom` |
| **PostHog** | Product usage before churn | `cunct-posthog` | `fixtures/posthog` |
| **Documents** | Churn playbooks, pricing notes | — | `fixtures/docs/` |

Same customer appears as Stripe customer → Intercom contact → PostHog person → name in a PDF. HydraDB must link them.

## Quick start

```bash
# Python 3.12+ recommended (uv works well)
uv venv --python 3.12 .venv && source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env   # add keys

# 1. Set up native HydraDB connectors (production path)
python -m churn_autopsy.demo.cli connectors

# 2. Ingest fixture/demo data (reproducible path)
python -m churn_autopsy.demo.cli ingest --fixtures-only

# 3. Run the headline question and the full eval
python -m churn_autopsy.demo.cli demo
python -m churn_autopsy.demo.cli eval

# Demo UI (video / presentation)
chmod +x scripts/demo.sh
./scripts/demo.sh
# → http://127.0.0.1:3000
```

See [DEMO.md](./DEMO.md) for the 60-second recording script and [SUBMISSION.md](./SUBMISSION.md) for hackathon details.

> **Security note:** `.env` contains live API keys. If you shared or exposed it, rotate the credentials after the demo.

## Architecture

```
fixtures / live connectors / native HydraDB connectors
        │
        ▼
   ingest (app_knowledge + documents)
        │
        ▼
     HydraDB  (database: churn_autopsy)
        │
        ▼
  FastLane planner
   ├─ hop 1: Stripe (fast + metadata filters)
   ├─ hop 2: Intercom (fast, scoped by email/customer_id)
   ├─ hop 3: PostHog (fast, scoped by distinct_id)
   ├─ hop 4: Documents (fast, source=document)
   └─ hop N: thinking only if synthesis is weak
        │
        ▼
   answer + metrics (latency, #calls, fast vs thinking, est. cost)
```

## Challenge coverage

- **Multi-connector + document ingestion:** 3 HydraDB native connectors + 2 uploaded documents.
- **Difficult retrieval:** 16 questions across multi-hop, temporal, metadata-filter, entity-dedup, attribution, actor, thread, multilingual, knowledge-update, and a thinking-escalation trap.
- **Fast vs thinking competition:** measured accuracy, latency, call count, fast ratio, and estimated cost.

## Results

Latest `python -m churn_autopsy.demo.cli eval`:

| Metric | FastLane | Thinking-only baseline |
|--------|----------|------------------------|
| Accuracy | **100%** | **62.5%** |
| Avg latency | **3,017 ms** | **5,769 ms** |
| Avg HydraDB calls / question | **2.7** | **1.0** |
| Fast-mode calls | **97.7%** | **0%** |
| Total cost (16 questions) | **$0.052** | **$0.160** |

15 of 16 questions are answered entirely in fast mode. The one comparison question escalates to thinking after fast hops prove insufficient.

## Demo (60s)

1. Show native connectors set up for Stripe, Intercom, and PostHog.
2. Show one customer linked across Stripe / Intercom / PostHog / PDF.
3. Run the headline multi-hop question via FastLane (3 fast hops, 0 thinking).
4. Flash the eval scoreboard: FastLane vs thinking-only.
5. Show the comparison question that correctly escalates to thinking.
