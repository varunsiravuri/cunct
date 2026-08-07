"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

const STEPS = [
  {
    n: "01",
    title: "Ingest three live sources",
    body: "Stripe holds plans, refunds, and cancel dates. Intercom holds what the customer said. PostHog holds what they stopped doing in the product.",
  },
  {
    n: "02",
    title: "Link the same person",
    body: "CUNCT matches the customer across email and IDs, so Mira in Stripe is the same Mira in Intercom and PostHog — not three strangers.",
  },
  {
    n: "03",
    title: "Ask a hard question",
    body: "Not “search churn.” Ask: who canceled after a refund, what did they say, and which feature died first?",
  },
  {
    n: "04",
    title: "Answer in fast steps",
    body: "CUNCT breaks the question into small scoped lookups first. Deeper reasoning only runs when those steps aren’t enough — faster and cheaper.",
  },
];

export default function HowItWorksPage() {
  return (
    <main className="mx-auto w-full max-w-[1180px] px-5 pb-20 pt-10 md:px-8">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55 }}
      >
        <p className="mono text-[11px] uppercase tracking-[0.22em] text-[var(--mute)]">
          How it works
        </p>
        <h1 className="display mt-2 max-w-2xl text-[clamp(2.4rem,5vw,4rem)] leading-[0.95] tracking-[-0.03em]">
          From scattered signals to one churn story
        </h1>
        <p className="mt-4 max-w-xl text-[var(--mute)]">
          Most tools search one inbox. CUNCT follows the customer across systems in order —
          billing → support → product — then writes the autopsy.
        </p>
      </motion.div>

      <div className="mt-12 grid gap-4 lg:grid-cols-2">
        {STEPS.map((step, i) => (
          <motion.article
            key={step.n}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.08 * i, duration: 0.5 }}
            className="glass rounded-3xl p-6"
          >
            <p className="mono text-[11px] tracking-[0.18em] text-[var(--signal)]">{step.n}</p>
            <h2 className="display mt-2 text-2xl tracking-tight">{step.title}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--mute)]">{step.body}</p>
          </motion.article>
        ))}
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.35 }}
        className="mt-10 glass rounded-3xl p-6"
      >
        <p className="mono text-[11px] uppercase tracking-[0.18em] text-[var(--mute)]">
          Useful for
        </p>
        <ul className="mt-4 grid gap-3 text-sm text-[var(--ink-soft)] md:grid-cols-3">
          <li>Explaining a cancel on a CS call with evidence</li>
          <li>Spotting feature abandonment before churn hits revenue</li>
          <li>Comparing refund-driven churn vs pricing-driven churn</li>
        </ul>
      </motion.div>

      <div className="mt-10">
        <Link
          href="/investigate"
          className="inline-flex items-center gap-2 rounded-full bg-[var(--signal)] px-6 py-3 text-sm font-medium text-white transition hover:bg-[var(--signal-deep)]"
        >
          Try an investigation
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </main>
  );
}
