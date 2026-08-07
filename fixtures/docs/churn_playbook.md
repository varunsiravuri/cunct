# Churn Playbook — SignalBoard CS

## When to investigate churn

Trigger an autopsy when any of the following are true:

1. Stripe subscription status becomes `canceled`
2. A refund is issued for a Pro or Growth plan within 14 days of cancel
3. Intercom ticket mentions billing dispute, double charge, or pricing
4. PostHog shows a sharp drop in a core feature the week before cancel

## Entity matching

Match the same customer across systems using:

- email (primary)
- Stripe `customer_id`
- Intercom contact email
- PostHog `distinct_id` / person properties.email

## NovaLabs case note (June 2026)

Mira Chen (mira.chen@novalabs.io) at NovaLabs was on Pro ($490 MRR).
She reported a duplicate June invoice and failing dashboard exports.
Finance issued refund `re_novalabs_doublecharge` on 2026-06-12.
She canceled on 2026-06-18 after exports remained broken.
PostHog shows dashboard-exports collapsed the week of 2026-06-09.

## Orbit Health case note (July 2026)

Priya Shah canceled Enterprise after the Q2 pricing increase.
She explicitly said AI Assist was never adopted.
Cancel date: 2026-07-02. No refund.

## Brightline watchlist

Jordan Lee is still active on Growth but at-risk due to search latency
and falling saved-searches usage after 2026-07-20.
