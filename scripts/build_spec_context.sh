#!/usr/bin/env bash
set -euo pipefail

OUT="${1:-.agent_spec_context.md}"

# Collect likely spec-kit/specify locations + common docs
CANDIDATES=(
  ".specify"
  "specs"
  "SPEC.md"
  "SPECIFICATION.md"
  "ARCHITECTURE.md"
  "docs"
  "README.md"
)

echo "# Spec Context Pack" > "$OUT"
echo "" >> "$OUT"
echo "Generated: $(date -Iseconds)" >> "$OUT"
echo "" >> "$OUT"

add_file () {
  local f="$1"
  echo -e "\n---\n" >> "$OUT"
  echo "## $f" >> "$OUT"
  echo '```' >> "$OUT"
  # Trim huge files to keep prompts sane
  head -n 4000 "$f" >> "$OUT" || true
  echo '```' >> "$OUT"
}

for p in "${CANDIDATES[@]}"; do
  if [ -d "$p" ]; then
    # Prefer markdown/text
    while IFS= read -r f; do
      add_file "$f"
    done < <(find "$p" -type f \( -name "*.md" -o -name "*.txt" -o -name "*.yml" -o -name "*.yaml" -o -name "*.json" \) | sort)
  elif [ -f "$p" ]; then
    add_file "$p"
  fi
done

echo "" >> "$OUT"
echo "_Note: truncated to keep context manageable._" >> "$OUT"
