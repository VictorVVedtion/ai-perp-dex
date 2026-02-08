#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:3310}"
TIMEOUT="${TIMEOUT:-15}"

declare -a ROUTE_MARKERS=(
  "/trade|AI Intent Input|Buy / Long"
  "/signals|Signal Betting|AI Intent Input|Connect your Agent"
  "/portfolio|Portfolio|Login with API Key|Register New Agent"
  "/markets|Market Overview|Propose New Market"
  "/skills|Skill Marketplace|Browse Strategies"
  "/chat|Agent Chat|Connect Agent"
)

fail() {
  echo "[FAIL] $1"
  exit 1
}

check_route_markers() {
  local route="$1"
  shift

  local html
  html="$(curl -sS -L --max-time "${TIMEOUT}" "${BASE_URL}${route}")" || fail "${route} unreachable"

  for marker in "$@"; do
    if ! printf '%s' "${html}" | grep -Fq "${marker}"; then
      fail "${route} missing marker: ${marker}"
    fi
  done

  echo "[OK]   ${route} markers"
}

check_route_assets() {
  local route="$1"
  local html
  html="$(curl -sS -L --max-time "${TIMEOUT}" "${BASE_URL}${route}")" || fail "${route} unreachable for asset check"

  local assets
  assets="$(printf '%s' "${html}" | grep -Eo '/_next/static/[^"[:space:]\\]+' | sort -u || true)"

  if [[ -z "${assets}" ]]; then
    fail "${route} no Next static assets discovered"
  fi

  while IFS= read -r asset; do
    [[ -z "${asset}" ]] && continue
    local code
    code="$(curl -s -o /dev/null -w "%{http_code}" --max-time "${TIMEOUT}" "${BASE_URL}${asset}")"
    if [[ "${code}" != "200" && "${code}" != "304" && "${code}" != "301" && "${code}" != "302" && "${code}" != "307" && "${code}" != "308" ]]; then
      fail "${route} static asset ${asset} -> HTTP ${code}"
    fi
  done <<< "${assets}"

  echo "[OK]   ${route} static assets"
}

echo "== UI Marker Assertions =="
for entry in "${ROUTE_MARKERS[@]}"; do
  IFS='|' read -r route marker1 marker2 marker3 <<< "${entry}"
  markers=()
  [[ -n "${marker1:-}" ]] && markers+=("${marker1}")
  [[ -n "${marker2:-}" ]] && markers+=("${marker2}")
  [[ -n "${marker3:-}" ]] && markers+=("${marker3}")
  check_route_markers "${route}" "${markers[@]}"
done

echo
echo "== Static Asset Assertions =="
for entry in "${ROUTE_MARKERS[@]}"; do
  IFS='|' read -r route _ <<< "${entry}"
  check_route_assets "${route}"
done

echo
echo "UI assertions completed successfully."
