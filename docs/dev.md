# Development Tooling Setup

This project needs a few tools beyond Python packages in `requirements-dev.txt`.

## Required Tools
- Python: `3.10+`
- `uv`: dependency/runtime manager used by project commands
- Node.js + `npx`: required to run `basedpyright` gate command

## Install

### 1) Python deps
```bash
uv sync --dev
```

### 2) Node tooling for type gate
Install Node.js if missing, then install `basedpyright`:
```bash
npm install --global basedpyright
```

You can also use `npx basedpyright ...` without global install, but global install is faster and more stable for repeated runs.

## Quality Gate
Primary local quality checks (source of truth):
- `uv run ruff check .`
- `npx basedpyright --outputjson`
- `npx basedpyright tests --outputjson`
- `uv run pytest -q`

Optional convenience wrapper (experimental):
```bash
./scripts/quality_gate.sh
```

## Notes
- CI currently uses a different type-check command path (`mypy`) in workflow config.
- Local agent policy requires the `basedpyright` gate for editor/LSP parity.
