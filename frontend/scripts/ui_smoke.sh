#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3300}"
OUT_DIR="${OUT_DIR:-/tmp/ai-perp-ux-smoke}"
WAIT_MS="${WAIT_MS:-3000}"

ROUTES=(
  "/"
  "/trade"
  "/signals"
  "/markets"
  "/portfolio"
  "/agents"
  "/skills"
  "/chat"
  "/connect"
)

SHOT_ROUTES=(
  "trade"
  "signals"
  "markets"
  "portfolio"
  "agents"
  "skills"
  "chat"
  "connect"
)

mkdir -p "${OUT_DIR}"

echo "== Route Health Check =="
for route in "${ROUTES[@]}"; do
  code=""
  for attempt in 1 2 3; do
    code="$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}${route}")"
    if [[ "${code}" == "200" || "${code}" == "301" || "${code}" == "302" || "${code}" == "307" || "${code}" == "308" ]]; then
      break
    fi
    sleep 1
  done
  if [[ "${code}" != "200" && "${code}" != "301" && "${code}" != "302" && "${code}" != "307" && "${code}" != "308" ]]; then
    echo "[FAIL] ${route} -> HTTP ${code}"
    exit 1
  fi
  echo "[OK]   ${route} -> HTTP ${code}"
done

echo
echo "== Screenshot Capture (Desktop + Mobile) =="
for route in "${SHOT_ROUTES[@]}"; do
  echo "[SHOT] /${route} desktop"
  npx playwright screenshot \
    --browser=chromium \
    --viewport-size=1366,900 \
    --wait-for-timeout="${WAIT_MS}" \
    "${BASE_URL}/${route}" \
    "${OUT_DIR}/${route}-desktop.png" >/dev/null

  echo "[SHOT] /${route} mobile"
  npx playwright screenshot \
    --browser=chromium \
    --viewport-size=390,844 \
    --wait-for-timeout="${WAIT_MS}" \
    "${BASE_URL}/${route}" \
    "${OUT_DIR}/${route}-mobile.png" >/dev/null
done

echo
echo "Smoke run completed."
echo "Artifacts: ${OUT_DIR}"
