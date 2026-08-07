"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Search } from "lucide-react";
import { AskResponse, DemoQuestion, saveResult } from "@/lib/types";

export default function InvestigatePage() {
  const router = useRouter();
  const [questions, setQuestions] = useState<DemoQuestion[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/demo/questions")
      .then((r) => r.json())
      .then((qs: DemoQuestion[]) => {
        setQuestions(qs);
        if (qs[0]) setQuestion(qs[0].question);
      })
      .catch(() => undefined);
  }, []);

  async function run() {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `Request failed (${res.status})`);
      }
      const data: AskResponse = await res.json();
      saveResult(data);
      router.push("/report");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something broke");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-[900px] px-5 pb-20 pt-10 md:px-8">
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55 }}
      >
        <p className="mono text-[11px] uppercase tracking-[0.22em] text-[var(--mute)]">
          Investigate
        </p>
        <h1 className="display mt-2 text-[clamp(2.2rem,5vw,3.6rem)] leading-[0.95] tracking-[-0.03em]">
          Ask what really caused the churn
        </h1>
        <p className="mt-4 max-w-xl text-[var(--mute)]">
          Pick a sample below or write your own. CUNCT will query Stripe, Intercom, and
          PostHog, then open the report on the next page.
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.12, duration: 0.55 }}
        className="glass mt-8 rounded-3xl p-6"
      >
        <label className="mono text-[11px] uppercase tracking-[0.18em] text-[var(--mute)]">
          Question
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={5}
          className="mt-3 w-full resize-none rounded-2xl border border-[var(--line)] bg-white/70 px-4 py-3 text-[1.05rem] leading-snug text-[var(--ink)] outline-none transition focus:border-[var(--signal)]"
        />

        <div className="mt-4 flex flex-wrap gap-2">
          {questions.map((q) => (
            <button
              key={q.id}
              type="button"
              onClick={() => setQuestion(q.question)}
              className="rounded-full border border-[var(--line)] bg-white/60 px-3 py-1.5 text-xs text-[var(--mute)] transition hover:border-[var(--signal)] hover:text-[var(--ink)]"
            >
              {q.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          disabled={loading}
          onClick={run}
          className="mt-6 inline-flex items-center gap-2 rounded-full bg-[var(--signal)] px-6 py-3 text-sm font-medium text-white transition hover:bg-[var(--signal-deep)] disabled:opacity-60"
        >
          <Search className="h-4 w-4" />
          {loading ? "Tracing sources…" : "Run investigation"}
        </button>

        {error && <p className="mt-4 text-sm text-[var(--heat)]">{error}</p>}
      </motion.div>
    </main>
  );
}
