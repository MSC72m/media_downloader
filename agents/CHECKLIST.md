# Agent Execution Checklist (Derived From `agents/AGENTS.md`)

Use this for non-trivial work. It is an execution checklist, not a second policy source.

## 1) Intake
- Confirm objective in one sentence.
- Capture constraints, acceptance criteria, and unknowns.
- If ambiguity is material, ask clarifying questions before coding.

## 2) Choose Path
- If task is trivial (small/local/no high-impact risk), use fast path.
- Otherwise use standard path with a task spec.

## 3) Spec (Non-Trivial)
- Create spec from `docs/specs/TEMPLATE.md`.
- Save to `docs/specs/local/<YYYY-MM-DD>-<slug>.md` by default.
- Add executable acceptance checks in the spec.

## 4) Codebase Fit
- Locate ownership (`handler`/`service`/`coordinator`/`ui`).
- Reuse existing modules/patterns before adding new ones.
- Avoid duplication and helper sprawl.

## 5) Implement in Small Steps
- Keep happy path obvious and use early returns.
- Keep business logic out of UI.
- Keep config/constants policy aligned with `src/core/config.py`.
- Fix root causes over symptoms.

## 6) Validate
Primary (source-of-truth) gate commands:
- `uv run ruff check .`
- `npx basedpyright --outputjson`
- `npx basedpyright tests --outputjson`
- `uv run pytest -q`

Optional convenience wrapper (experimental):
- `./scripts/quality_gate.sh`

If the gate cannot run, report the blocker explicitly.

## 7) Report
- What changed
- Why this design/fix
- Validation evidence
- Residual risks and assumptions
