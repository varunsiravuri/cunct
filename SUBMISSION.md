# Submission notes — Churn Autopsy

## Connectors used

1. **Stripe** — customers, subscriptions, refunds
2. **Intercom** — support conversations / tickets
3. **PostHog** — weekly feature usage snapshots
4. **Documents** — `churn_playbook.md`, `q2_pricing_notes.md`

We support both **native HydraDB connectors** (`POST /connectors` → configure → sync) and a **direct app_knowledge fallback** for reproducible fixture demos.

```bash
python -m churn_autopsy.demo.cli connectors     # native HydraDB connectors
python -m churn_autopsy.demo.cli ingest --fixtures-only  # reproducible demo data
```

Credentials: Discord-provided live keys when available; otherwise reproducible fixtures under `fixtures/`.

## Headline multi-hop question

**Q:** Which Pro customers canceled after a refund, what did they say in Intercom, and which feature did they stop using before cancel?

**Expected:**
- Person: Mira Chen / NovaLabs / mira.chen@novalabs.io
- Stripe: Pro canceled after refund `re_novalabs_doublecharge` (2026-06-12), cancel 2026-06-18
- Intercom: double-charged + dashboard exports failing
- PostHog: `dashboard-exports` collapsed week of 2026-06-09

## Fast vs thinking strategy

| Hop | Mode | Why |
|-----|------|-----|
| Stripe cancel/refund lookup | fast + metadata (`source=stripe`, `plan=pro`, `has_refund=true`) | Exact filters beat semantic search |
| Intercom by email | fast + `email=` | Actor / thread scoped |
| PostHog by email | fast + `email=` | Feature drop scoped |
| Documents | fast + `source=document` | Policy lookup scoped |
| Cross-customer comparison | thinking only if fast hops are weak | Cost/latency escape hatch |

## Eval suite

16 questions across the categories requested by the challenge:

| # | Category | Result |
|---|----------|--------|
| 1 | multi-hop | correct |
| 2 | multi-hop | correct |
| 3 | temporal | correct |
| 4 | actor | correct |
| 5 | metadata_filter | correct |
| 6 | documents | correct |
| 7 | entity_dedup | correct |
| 8 | attribution | correct |
| 9 | thread | correct |
| 10 | knowledge_update | correct |
| 11 | metadata_filter | correct |
| 12 | actor | correct |
| 13 | multi-hop | correct |
| 14 | attribution | correct |
| 15 | multilingual | correct |
| 16 | thinking_trap | correct (4 fast + 1 thinking) |

## Metrics to report

From `python -m churn_autopsy.demo.cli eval`:

| Metric | FastLane | Thinking-only baseline |
|--------|----------|------------------------|
| Accuracy | 100% (16/16) | 62.5% (10/16) |
| Avg latency | 3,017 ms | 5,769 ms |
| Avg HydraDB calls | 2.7 | 1.0 |
| Fast-mode ratio | 97.7% | 0% |
| Total cost | $0.052 | $0.160 |

## 60s demo script

See [DEMO.md](./DEMO.md).
