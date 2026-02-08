#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3310}"
OUT_DIR="${OUT_DIR:-/tmp/ai-perp-ux-smoke-prod}"
LOG_FILE="${LOG_FILE:-/tmp/ai-perp-start.log}"

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]]; then
    kill "${SERVER_PID}" >/dev/null 2>&1 || true
    wait "${SERVER_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

echo "== Production Build =="
npm run -s build >/dev/null

echo "== Prepare Standalone Assets =="
mkdir -p .next/standalone/.next
rm -rf .next/standalone/.next/static
cp -R .next/static .next/standalone/.next/static
if [[ -d public ]]; then
  rm -rf .next/standalone/public
  cp -R public .next/standalone/public
fi

echo "== Start Production Server =="
PORT="${PORT}" node .next/standalone/server.js >"${LOG_FILE}" 2>&1 &
SERVER_PID=$!

for _ in {1..40}; do
  code="$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${PORT}/" || true)"
  if [[ "${code}" == "200" ]]; then
    break
  fi
  sleep 0.5
done

if [[ "${code:-}" != "200" ]]; then
  echo "[FAIL] production server failed to start on :${PORT}"
  echo "Log tail:"
  tail -n 40 "${LOG_FILE}" || true
  exit 1
fi

echo "== Run UI Smoke =="
BASE_URL="http://localhost:${PORT}" OUT_DIR="${OUT_DIR}" ./scripts/ui_smoke.sh

echo
echo "== Run UI Assertions =="
BASE_URL="http://localhost:${PORT}" ./scripts/ui_assert.sh
