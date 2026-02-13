# Agent Execution Checklist (Media Downloader)

Use this checklist on every non-trivial task.
Do not skip steps unless the engineer explicitly requests a shortcut.

## 1) Intake and Problem Framing
- Confirm objective in one sentence.
- List explicit constraints and acceptance criteria.
- List unknowns and assumptions.
- If ambiguity exists, ask clarifying questions before coding.

## 2) Plan in Small Steps
- Break the work into small, verifiable steps.
- Define expected outcome for each step.
- Identify likely risks and fallback options.
- Share the plan with the engineer for high-impact changes.

## 3) Understand Existing Code First
- Locate current implementation path and ownership:
  - `handler`, `service`, `coordinator`, `ui`, `core`.
- Identify reusable utilities and existing patterns.
- Check for duplication risk before adding new modules/helpers.
- Confirm where the new behavior should fit architecturally.

## 4) Design Fit and Tradeoffs
- Propose integration options (2-3 preferred, fine if more or less).
- Put recommended option first.
- Explain tradeoffs: complexity, risk, migration, testability, performance.
- Ask engineer confirmation when introducing new abstractions/patterns.

## 5) Root-Cause Investigation (Mandatory)
- Reproduce issue with evidence (logs/tests/diagnostics).
- Identify root cause, not just symptom.
- Validate root cause hypothesis before fix.
- Prefer systemic fix over local patch.
- If only mitigation is possible, request/confirm with engineer and document:
  - reason
  - impact
  - removal plan

## 6) Implementation Rules
- Use early returns and keep happy path obvious.
- Prefer reuse/extension over rewrite.
- Keep constants/config centralized (`src/core/config.py` for tunables).
- Avoid helper sprawl; create helpers only when justified.
- Keep imports clean and top-level (except justified local imports).
- Use Pythonic efficient structures (`set`/`dict` membership, compiled regex reuse).
- Keep side effects at boundaries.

## 7) GUI and Downloader-Specific Checks
- No blocking operations on UI thread.
- Use main-thread scheduling for UI updates.
- Keep UI logic thin; business logic in services/coordinators.
- Validate downloader robustness:
  - auth strategy order
  - bounded retries
  - fallback behavior
  - file completion verification

## 8) Tests and Diagnostics
- Add/adjust tests for changed behavior.
- Add regression test for bug fix.
- Ensure tests reflect contract, not implementation internals.
- Do not weaken tests just to get green.

## 9) Quality Gates (Mandatory)
Run and pass:
- `uv run ruff check .`
- `npx basedpyright --outputjson`
- `npx basedpyright tests --outputjson`
- `uv run pytest -q`

If any fail:
- fix root cause
- re-run full gates
- avoid broad suppressions

## 10) Final Engineering Report
- What changed (files/components)?
- Why this design/fix?
- Root cause and how it was resolved.
- Validation results (lint/type/tests).
- Residual risks and next-step options.
- OFC do not put them as .md files explain them in your output and don't waste response tokens be concise and pragmatic.

## 11) Done Criteria
- Requirements met and clarified.
- Root cause fixed or approved mitigation documented.
- Architecture fit confirmed.
- No avoidable duplication introduced.
- Quality gates all pass.
- Engineer has clear summary and tradeoffs.
