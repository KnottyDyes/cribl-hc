#!/usr/bin/env bash
set -euo pipefail

THEME="${1:-dark}"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${ROOT_DIR}/screenshots"
TARGET_DIR="${ROOT_DIR}/../cribl-hc/docs/screenshots"

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
