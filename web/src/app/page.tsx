"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { ArrowRight } from "lucide-react";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-[calc(100vh-72px)] w-full max-w-[1180px] flex-col justify-center px-5 pb-16 pt-10 md:px-8">
      <motion.div
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        className="max-w-3xl"
      >
        <p className="mono text-[11px] uppercase tracking-[0.24em] text-[var(--mute)]">
          Customer churn intelligence
        </p>
        <h1 className="display mt-3 text-[clamp(3.2rem,9vw,6.4rem)] leading-[0.9] tracking-[-0.04em] text-[var(--ink)]">
          CUNCT
        </h1>
        <p className="mt-6 max-w-xl text-lg leading-relaxed text-[var(--ink-soft)] md:text-xl">
          When a customer leaves, the reason is never in one place. CUNCT connects
          billing, support conversations, and product usage so you can see the full
          story in seconds.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.65 }}
        className="mt-12 grid gap-4 md:grid-cols-3"
      >
        {[
          {
            title: "What it is",
            body: "An investigation tool for churn. Ask one question. Get an answer that spans money, messages, and behavior.",
          },
          {
            title: "Why it helps",
            body: "CS and growth teams stop guessing. You see who canceled, what they complained about, and which feature they abandoned.",
          },
          {
            title: "Who it’s for",
            body: "Founders, CS leads, and product teams who need a clear churn narrative before the next renewal call.",
          },
        ].map((card) => (
          <div key={card.title} className="glass rounded-3xl p-5">
            <h2 className="display text-2xl tracking-tight">{card.title}</h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--mute)]">{card.body}</p>
          </div>
        ))}
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.3 }}
        className="mt-10 flex flex-wrap gap-3"
      >
        <Link
          href="/how-it-works"
          className="inline-flex items-center gap-2 rounded-full bg-[var(--signal)] px-6 py-3 text-sm font-medium text-white transition hover:bg-[var(--signal-deep)]"
        >
          How it works
          <ArrowRight className="h-4 w-4" />
        </Link>
        <Link
          href="/investigate"
          className="inline-flex items-center gap-2 rounded-full border border-[var(--ink)]/20 bg-white/50 px-6 py-3 text-sm text-[var(--ink)] transition hover:bg-white"
        >
          Start investigating
        </Link>
      </motion.div>
    </main>
  );
}
