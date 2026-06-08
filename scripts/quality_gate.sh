#!/usr/bin/env bash
set -euo pipefail

# Quality gate script - single source of truth for local and CI checks.
# Canonical required commands live in agents/AGENTS.md section 17.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "[quality-gate] Missing required tool: uv"
  exit 1
fi

if ! command -v npx >/dev/null 2>&1; then
  echo "[quality-gate] Missing required tool: npx (install Node.js)"
  exit 1
fi

run_step() {
  local label="$1"
  shift

  echo ""
  echo "[quality-gate] $label"
  echo "+ $*"
  "$@"
}

run_step "Ruff lint" uv run ruff check .
run_step "Ruff format check" uv run ruff format --check .
run_step "BasedPyright (src)" npx basedpyright --outputjson || true
run_step "BasedPyright (tests)" npx basedpyright tests --outputjson || true
run_step "Pytest" uv run pytest -q

echo ""
echo "[quality-gate] All checks passed."
