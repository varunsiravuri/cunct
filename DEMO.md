# 60-second video demo — CUNCT

## Start
```bash
./scripts/demo.sh
```
Open **http://127.0.0.1:3000** · fullscreen.

## Script

**0–10s · Native connectors**
Terminal: `python -m churn_autopsy.demo.cli connectors --dry-run`
> “We wire native HydraDB connectors for Stripe, Intercom, and PostHog, plus document uploads. HydraDB becomes the single context layer for churn.”

**10–20s · What it is** (`/`)
> “This is CUNCT. When customers churn, the reason is split across billing, support, and product. CUNCT connects those stories.”

**20–28s · How it works** (`/how-it-works`)
> “We run scoped fast queries: one for Stripe, one for Intercom, one for PostHog. We only escalate to thinking when the fast hops are not enough.”

**28–45s · Investigate** (`/investigate`)
Click the headline sample → **Run investigation**.
> “Who canceled Pro after a refund, what did they say, and which feature did they abandon?”

**45–55s · Report** (`/report`)
> “Mira Chen at NovaLabs — refund, double-charge complaint, dashboard-exports dropped. Three fast lookups. No deep mode needed.”

**55–60s · Scoreboard**
Show the eval table: FastLane 100% / 97.7% fast / $0.052 vs thinking-only 62.5% / $0.16.
> “Fast mode wins when retrieval is structured.”

One continuous browser session. No slides.
