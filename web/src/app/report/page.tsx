"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AnimatePresence, motion } from "framer-motion";
import { AskResponse, loadResult } from "@/lib/types";

const SOURCES = [
  { id: "stripe", label: "Stripe", hint: "billing · refunds · cancel" },
  { id: "intercom", label: "Intercom", hint: "what they said" },
  { id: "posthog", label: "PostHog", hint: "feature abandonment" },
  { id: "docs", label: "Documents", hint: "playbook · pricing notes" },
];

function hopSource(name: string): string | null {
  if (name.includes("stripe")) return "stripe";
  if (name.includes("intercom")) return "intercom";
  if (name.includes("posthog")) return "posthog";
  if (name.includes("docs") || name.includes("thinking")) return "docs";
  return null;
}

function useTypedText(text: string, active: boolean, speed = 12) {
  const [displayed, setDisplayed] = useState("");
  useEffect(() => {
    if (!active) {
      setDisplayed("");
      return;
    }
    let i = 0;
    setDisplayed("");
    const timer = setInterval(() => {
      i += 1;
      setDisplayed(text.slice(0, i));
      if (i >= text.length) clearInterval(timer);
    }, speed);
    return () => clearInterval(timer);
  }, [text, active, speed]);
  return displayed;
}

export default function ReportPage() {
  const [result, setResult] = useState<AskResponse | null>(null);
  const [activeHop, setActiveHop] = useState(-1);
  const [showEvidence, setShowEvidence] = useState(false);

  useEffect(() => {
    const stored = loadResult();
    setResult(stored);
    if (!stored) return;
    let cancelled = false;
    (async () => {
      for (let i = 0; i < stored.hops.length; i++) {
        if (cancelled) return;
        setActiveHop(i);
        await new Promise((r) => setTimeout(r, 500));
      }
      setTimeout(() => setShowEvidence(true), 300);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const lit = useMemo(() => {
    const set = new Set<string>();
    if (!result || activeHop < 0) return set;
    result.hops.slice(0, activeHop + 1).forEach((h) => {
      const s = hopSource(h.name);
      if (s) set.add(s);
    });
    return set;
  }, [result, activeHop]);

  const typedAnswer = useTypedText(
    result?.answer || "",
    result ? activeHop >= result.hops.length - 1 : false,
    8
  );

  if (!result) {
    return (
      <main className="mx-auto flex min-h-[60vh] max-w-[900px] flex-col items-start justify-center px-5 md:px-8">
        <h1 className="display text-4xl">No report yet</h1>
        <p className="mt-3 text-[var(--mute)]">Run an investigation first.</p>
        <Link
          href="/investigate"
          className="mt-6 rounded-full bg-[var(--signal)] px-5 py-3 text-sm text-white"
        >
          Go to Investigate
        </Link>
      </main>
    );
  }

  const person = result.entities.people?.[0];
  const company = result.entities.companies?.[0];
  const finished = activeHop >= result.hops.length - 1;

  return (
    <main className="mx-auto w-full max-w-[1180px] px-5 pb-20 pt-10 md:px-8">
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <p className="mono text-[11px] uppercase tracking-[0.22em] text-[var(--mute)]">
          Report
        </p>
        <h1 className="display mt-2 text-[clamp(2.2rem,5vw,3.8rem)] leading-[0.95] tracking-[-0.03em]">
          {person && company ? `${person} · ${company}` : "Investigation complete"}
        </h1>
        <p className="mt-3 max-w-2xl text-sm text-[var(--mute)]">{result.question}</p>
      </motion.div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
        <section className="glass rounded-3xl p-6">
          <p className="mono text-[11px] uppercase tracking-[0.18em] text-[var(--mute)]">
            Source path
          </p>
          <div className="mt-5 grid gap-3">
            {SOURCES.map((s) => {
              const on = lit.has(s.id);
              return (
                <motion.div
                  key={s.id}
                  animate={{ opacity: on ? 1 : 0.4, x: on ? 4 : 0 }}
                  className="rounded-2xl border border-white/70 bg-white/50 px-4 py-3"
                  style={{ boxShadow: on ? "inset 3px 0 0 var(--signal)" : "none" }}
                >
                  <p className="display text-xl">{s.label}</p>
                  <p className="mono mt-1 text-[10px] uppercase tracking-[0.14em] text-[var(--mute)]">
                    {s.hint}
                  </p>
                </motion.div>
              );
            })}
          </div>

          <ol className="mt-6 space-y-2">
            {result.hops.map((h, idx) => (
              <li
                key={`${h.name}-${idx}`}
                className={`mono flex justify-between rounded-xl px-3 py-2 text-[11px] ${
                  idx <= activeHop ? "bg-white/70 text-[var(--ink)]" : "text-[var(--mute)]"
                }`}
              >
                <span>
                  {idx + 1}. {h.name.replace(/_/g, " ")} · {h.mode}
                </span>
                <span>{Math.round(h.latency_ms)}ms</span>
              </li>
            ))}
          </ol>

          {finished && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-5 rounded-2xl border border-[var(--line)] bg-white/50 p-4"
            >
              <p className="mono text-[10px] uppercase tracking-[0.14em] text-[var(--mute)]">
                Why this feels real
              </p>
              <p className="mt-2 text-xs leading-relaxed text-[var(--ink-soft)]">
                Each number is a live HydraDB query. The answer is built from the chunks retrieved
                on the left, not from a hard-coded template.
              </p>
              <button
                type="button"
                onClick={() => setShowEvidence((s) => !s)}
                className="mt-3 text-xs font-medium text-[var(--signal-deep)] underline underline-offset-4"
              >
                {showEvidence ? "Hide evidence" : "Show evidence"}
              </button>
            </motion.div>
          )}
        </section>

        <section className="glass rounded-3xl p-6">
          <p className="mono text-[11px] uppercase tracking-[0.18em] text-[var(--mute)]">
            Findings
          </p>
          <AnimatePresence>
            {finished && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-5"
              >
                <pre className="whitespace-pre-wrap font-sans text-[0.98rem] leading-relaxed text-[var(--ink)]">
                  {typedAnswer}
                  {!typedAnswer.endsWith(result.answer) && (
                    <span className="ml-1 inline-block h-4 w-0.5 animate-pulse bg-[var(--signal)]" />
                  )}
                </pre>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="mt-8 grid grid-cols-2 gap-3 border-t border-[var(--line)] pt-5 sm:grid-cols-4">
            {[
              { label: "Latency", value: `${Math.round(result.metrics.latency_ms)}ms` },
              { label: "Lookups", value: String(result.metrics.hydra_calls) },
              {
                label: "Fast / Deep",
                value: `${result.metrics.fast_calls}/${result.metrics.thinking_calls}`,
              },
              { label: "Est. cost", value: `$${result.metrics.cost_usd.toFixed(4)}` },
            ].map((m) => (
              <div key={m.label}>
                <p className="mono text-[10px] uppercase tracking-[0.14em] text-[var(--mute)]">
                  {m.label}
                </p>
                <p className="display mt-1 text-2xl tracking-tight">{m.value}</p>
              </div>
            ))}
          </div>
        </section>
      </div>

      <AnimatePresence>
        {showEvidence && (
          <motion.section
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-6 overflow-hidden"
          >
            <div className="glass rounded-3xl p-6">
              <p className="mono text-[11px] uppercase tracking-[0.18em] text-[var(--mute)]">
                Source evidence (raw chunks retrieved from HydraDB)
              </p>
              <div className="mt-5 grid gap-4">
                {result.hops.map((h, idx) =>
                  h.chunks.length > 0 ? (
                    <div key={idx} className="rounded-2xl border border-[var(--line)] bg-white/50 p-4">
                      <p className="mono text-[10px] uppercase tracking-[0.14em] text-[var(--signal-deep)]">
                        {h.name.replace(/_/g, " ")} · {h.mode} · {Math.round(h.latency_ms)}ms
                      </p>
                      <div className="mt-3 space-y-3">
                        {h.chunks.map((ch, cidx) => (
                          <div key={cidx} className="text-xs leading-relaxed text-[var(--ink-soft)]">
                            <p className="font-medium text-[var(--ink)]">{ch.title}</p>
                            <p className="mt-1">{ch.snippet}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null
                )}
              </div>
            </div>
          </motion.section>
        )}
      </AnimatePresence>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/investigate"
          className="inline-flex items-center gap-2 rounded-full bg-[var(--signal)] px-5 py-3 text-sm font-medium text-white transition hover:bg-[var(--signal-deep)]"
        >
          Ask another
        </Link>
        <Link
          href="/how-it-works"
          className="inline-flex items-center gap-2 rounded-full border border-[var(--ink)]/20 bg-white/50 px-5 py-3 text-sm text-[var(--ink)] transition hover:bg-white"
        >
          Back to how it works
        </Link>
      </div>
    </main>
  );
}
