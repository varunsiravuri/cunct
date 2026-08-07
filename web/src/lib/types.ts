export type DemoQuestion = { id: string; label: string; question: string };

export type AskResponse = {
  question: string;
  answer: string;
  entities: Record<string, string[]>;
  used_thinking: boolean;
  offline: boolean;
  metrics: {
    hydra_calls: number;
    fast_calls: number;
    thinking_calls: number;
    latency_ms: number;
    cost_usd: number;
  };
  hops: Array<{
    name: string;
    mode: string;
    query: string;
    latency_ms: number;
    filters: Record<string, string>;
    chunk_count: number;
    chunks: Array<{ title: string; snippet: string }>;
  }>;
};

export const RESULT_KEY = "cunct_last_result";

export function saveResult(result: AskResponse) {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(RESULT_KEY, JSON.stringify(result));
}

export function loadResult(): AskResponse | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(RESULT_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AskResponse;
  } catch {
    return null;
  }
}
