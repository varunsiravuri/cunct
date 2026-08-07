#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "Missing .venv — create it first"
  exit 1
fi

source .venv/bin/activate

# Kill stale ports if needed
for port in 8000 3000; do
  pid=$(lsof -ti tcp:$port 2>/dev/null || true)
  if [[ -n "${pid:-}" ]]; then
    kill $pid 2>/dev/null || true
  fi
done

echo "→ API on :8000"
uvicorn churn_autopsy.api:app --host 127.0.0.1 --port 8000 &
API_PID=$!

cleanup() {
  kill $API_PID 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
echo "→ UI on :3000"
cd web
pnpm dev --hostname 127.0.0.1 --port 3000
