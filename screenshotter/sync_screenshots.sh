#!/usr/bin/env bash
set -euo pipefail

THEME="${1:-dark}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Captures land next to this script. The destination is the cribl-hc repo,
# which may be this script's parent (screenshotter/ inside the repo) or a
# sibling checkout; CRIBL_HC_ROOT overrides either.
SOURCE_DIR="${SCRIPT_DIR}/screenshots"
if [[ -n "${CRIBL_HC_ROOT:-}" ]]; then
  REPO_ROOT="${CRIBL_HC_ROOT}"
elif [[ -d "${SCRIPT_DIR}/../docs/screenshots" ]]; then
  REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
elif [[ -d "${SCRIPT_DIR}/../cribl-hc/docs/screenshots" ]]; then
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../cribl-hc" && pwd)"
else
  printf 'Cannot locate the cribl-hc repo. Set CRIBL_HC_ROOT.\n' >&2
  exit 1
fi
TARGET_DIR="${REPO_ROOT}/docs/screenshots"

copy_theme() {
  local theme="$1"
  local source="${SOURCE_DIR}/${theme}"
  local target="$2"

  if [[ ! -d "${source}" ]]; then
    printf 'Source directory not found: %s\n' "${source}" >&2
    exit 1
  fi

  mkdir -p "${target}"
  cp "${source}/credential_input.png" "${target}/credential_input.png"
  cp "${source}/analysis_completion.png" "${target}/analysis_completion.png"
  cp "${source}/review_analysis_full.png" "${target}/review_analysis_full.png"
}

case "${THEME}" in
  dark)
    copy_theme "dark" "${TARGET_DIR}"
    ;;
  light)
    copy_theme "light" "${TARGET_DIR}/light"
    ;;
  both)
    copy_theme "dark" "${TARGET_DIR}"
    copy_theme "light" "${TARGET_DIR}/light"
    ;;
  *)
    printf 'Usage: %s [dark|light|both]\n' "$0" >&2
    exit 1
    ;;
  esac

printf 'Screenshots synced to %s (theme: %s)\n' "${TARGET_DIR}" "${THEME}"
