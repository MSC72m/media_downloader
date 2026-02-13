# Media Downloader Agent Handbook (Python Desktop)

This document is the single source of truth for AI/code agents in this repository.
It is tailored for this codebase and must be followed unless the user explicitly overrides a rule.

This repository is a Python desktop application (CustomTkinter/Tkinter), not Android/Kotlin.
Any Android/Kotlin guidance is out of scope and must be ignored.

## 1. Mission and Priority Order
1. Correctness
2. Security and privacy
3. Reliability and performance
4. Maintainability and readability
5. Delivery speed

If two goals conflict, the higher item wins.

## 2. Agent Operating Protocol (Mandatory)
- Restate the goal, constraints, and success criteria before implementing.
- If requirements are unclear or contradictory, ask clarifying questions before coding.
- Do not guess high-impact behavior.
- State assumptions explicitly when proceeding with incomplete input.
- For non-trivial work, provide a short plan with checkpoints.
- Implement the smallest working vertical slice first, then harden and refactor.
- Report what changed, why, and how it was validated.

## 3. Clarification Gate (Mandatory)
Ask for clarification before coding if any of these are true:
- Scope is ambiguous.
- Acceptance criteria are missing.
- Security or privacy impact is unclear.
- Data contracts are undefined.
- Backward compatibility expectations are unknown.
- Runtime, performance, or UX constraints are undefined.

## 4. Spec-Driven Development (Mandatory)
Do not implement major changes without a usable spec.

### 4.1 Minimum Spec Contents
- Problem statement
- Goal and non-goals
- Functional requirements
- Non-functional requirements
- Constraints (platform, policy, security, performance)
- Inputs/outputs and data contracts
- Edge cases and failure behavior
- Acceptance criteria (testable)
- Validation plan

### 4.2 Spec Lifecycle
1. Draft spec
2. Clarify gaps
3. Freeze scope for the iteration
4. Build MVP slice
5. Validate behavior
6. Refactor/harden
7. Re-validate
8. Update docs/decisions

## 5. Decision Support Protocol (Mandatory)
When multiple valid options exist:
- Present 2-3 choices.
- Put the recommended option first.
- Explain tradeoffs (complexity, risk, testability, performance, migration cost).
- Ask for confirmation if the choice is high impact.

### 5.1 System Design Collaboration (Mandatory)
- The agent is a design partner for the engineer, not an isolated code generator.
- For new features, propose how the new piece fits existing architecture:
  - boundary placement (`handler` vs `service` vs `coordinator` vs `ui`)
  - data contracts and state ownership
  - migration impact and backward compatibility
- Always present integration options and tradeoffs before deep implementation.
- Confirm design direction with the engineer when introducing new abstractions.

## 6. Repository-First Workflow (Mandatory)
Before editing:
- Understand current directory structure and existing architecture.
- Reuse existing modules/patterns before writing new ones.
- Prefer extending existing classes/services over introducing parallel implementations.
- Search for existing helpers before creating new helper methods.
- Avoid duplication across platforms/services.

## 7. Repository Architecture Boundaries
Use existing layers as intended.

- `src/application`: wiring, orchestration, DI factories.
- `src/coordinators`: app/UI flow orchestration across services.
- `src/handlers`: per-platform URL handling and UI callback bridging.
- `src/services`: platform/network/cookie/download logic.
- `src/core`: config, enums, interfaces, models.
- `src/ui`: dialogs/components/theme/UI behavior.
- `src/utils`: shared utilities.
- `tests`: unit/integration/real-world tests.

Do not move business logic into UI classes when service/coordinator layers already exist.

## 8. Configuration and Constants Policy (Mandatory)
- Centralize runtime-tunable settings in `src/core/config.py`.
- Do not scatter behavior-changing literals across files.
- Non-tunable constants belong at top-of-file or class-level in `UPPER_SNAKE_CASE`.
- Use explicit units in names, for example `*_SECONDS`, `*_MS`, `*_BYTES`.
- Validate external config at load boundaries and use safe defaults.
- Do not bury fallback defaults deep in business logic.

## 9. Implementation Sequence (Default)
1. Understand existing flow and contracts.
2. Implement minimal behavior in current architecture.
3. Add/adjust tests.
4. Refactor for clarity and reuse.
5. Run lint, type checks, and tests.
6. Document tradeoffs and residual risks.

## 9.1 Simplicity Rule (KISS)
- Keep solutions as simple as possible while meeting requirements.
- Do not introduce abstraction until recurring pressure exists.
- Prefer clear direct code over clever indirection.
- Over-engineering is a defect.

## 9.2 SOLID (Pragmatic, Not Dogmatic)
- Single Responsibility: one reason to change per module.
- Open/Closed: extend behavior via composition/strategy, not branch explosion.
- Liskov: substitutes must preserve expected behavior/contracts.
- Interface Segregation: prefer small consumer-focused protocols.
- Dependency Inversion: depend on abstractions at boundaries.

## 9.3 GRASP (Practical)
- Information Expert: place logic where relevant data exists.
- Creator: instantiate where lifecycle knowledge naturally belongs.
- Controller: coordinators/handlers orchestrate; UI remains thin.
- Low Coupling + High Cohesion: reduce incidental dependencies.
- Polymorphism over type-switch cascades when behavior varies by service.

## 9.4 Pattern Catalog (Use Intentionally)
Use when there is clear pressure:
- Strategy: service/platform behavior variants.
- Factory/Abstract Factory: constructing platform-specific handlers/services.
- Adapter: wrapping third-party APIs (`yt-dlp`, `requests`, browser-cookie sources).
- Facade: simplifying complex subsystems to stable higher-level APIs.
- State Machine: explicit workflow transitions for auth/download flows.

Avoid pattern usage when:
- A plain function/module is enough.
- It increases indirection without lowering coupling.
- It hides behavior and complicates debugging.

## 9.5 Standard Library First Policy
Prefer Python stdlib before adding dependencies for trivial needs.

Prefer:
- `pathlib` over manual path string concatenation.
- `dataclasses`/`slots` for lightweight structured data where appropriate.
- `enum` for finite state sets.
- `collections` (`deque`, `Counter`, `defaultdict`) for fit-for-purpose containers.
- `functools`/`itertools` for composable transformations.
- `typing`/`typing_extensions` for explicit contracts.

Do not add dependencies for syntax sugar that stdlib already covers.

## 10. Clean Code Principles (Mandatory)
- Use guard clauses and early returns.
- Keep happy path obvious.
- Keep functions focused and cohesive.
- Keep module responsibilities tight.
- Prefer expressive naming over comments.
- Comments explain why, not what.
- Remove dead code and stale comments.
- Keep public API surface minimal.

## 11. Control Flow and Pythonic Patterns
Use these intentionally when they improve clarity:
- Assignment expressions (`:=`) to avoid duplicated lookups.
- Structural pattern matching (`match/case`) for clean branching by shape/type.
- `if value := ...` for one-pass check-and-use logic.
- Prefer `dict.get` + explicit validation over chained indexing.
- Prefer comprehensions/generators for transformation pipelines.

Avoid:
- Deep `if/elif` pyramids when `match/case` or dispatch tables are clearer.
- Duplicate checks for the same expensive expression.
- Overusing walrus where readability worsens.

## 12. Python Performance and Correctness Rules
- Use `set`/`dict` membership for repeated lookups (`O(1)` expected).
- Use `list` only when order and duplicates are required.
- Compile regex when reused.
- Patch/mock symbols where they are used, not where they originate.
- Prefer streaming/chunking for large downloads.
- Use temp files and atomic replace for download writes.
- Avoid repeated parsing/allocations in hot loops.
- Use lazy logging formatting (`logger.info("x=%s", x)`), not eager f-strings in hot paths.

## 13. Import and Module Hygiene
- Keep imports at module top by default.
- Allowed local imports only for:
  - optional heavy dependencies
  - explicit circular dependency breaks
  - startup performance-sensitive paths
- Keep type-only imports under `if TYPE_CHECKING:`.
- Keep import groups ordered: stdlib, third-party, first-party.
- Avoid inline imports inside classes/functions unless there is a concrete reason.

## 14. Error Handling and Resilience
- No catch-and-ignore.
- Handle expected failure classes explicitly.
- Distinguish retryable vs non-retryable errors.
- Use bounded retries with backoff and cancellation.
- Keep fallback chains explicit and ordered.
- Log once near boundaries with context.
- Return typed/structured outcomes where practical.

### 14.1 Root-Cause First Policy (Mandatory)
- Fix root causes, not symptoms.
- Do not add band-aid fixes merely to pass tests/lint/LSP.
- Temporary mitigation is allowed only when root-cause fix is not feasible immediately.
- Any temporary workaround must be explicitly labeled with:
  - why root cause cannot be fixed now
  - impact/risk
  - removal plan
- High-impact temporary workarounds require engineer confirmation before merge.

## 15. Protocols, Interfaces, and Typing Rules
- Protocols are structural contracts, not inheritance mandates.
- Mocks/stubs should generally not inherit from protocol classes.
- Mocks/stubs must match protocol method signatures exactly.
- Keep parameter names and default values compatible with the protocol.
- Avoid broad `Any` in production code.
- In tests, use `cast(Any, ...)` only for unavoidable dynamic monkeypatching seams.

### 15.1 Typing Patterns Applied in This Repo
- Decorators preserving class type:
  - Use `TypeVar` in decorators that return classes (example: auto-register handlers).
- Dynamic handler constructors in tests:
  - Use explicit branching by handler type.
  - Use `cast(Any, handler_class)` only when constructor signatures vary dynamically.
- Monkeypatched fake modules:
  - Use `ModuleType` objects and cast to `Any` when assigning dynamic attributes.

## 16. Testing Strategy (Mandatory)
- Unit tests for domain/service logic first.
- Integration tests for boundary contracts and orchestration behavior.
- Real-network tests must degrade gracefully:
  - skip when upstream/network/geo restrictions block execution
  - do not fail CI for external service instability
- Add regression tests for bug fixes.
- Assert behavior and outcomes, not internal implementation details.

### 16.1 No Fake Green Rule
- “Passing tests” is insufficient if behavior is still wrong.
- Never weaken assertions just to make failures disappear.
- Never change tests away from intended behavior without agreement and rationale.
- Prefer updating tests to match legitimate contract changes, then document that change.

## 17. Lint, LSP, and Type Gates (Mandatory)
Required local quality gates before claiming completion:
- `uv run ruff check .`
- `npx basedpyright --outputjson`
- `npx basedpyright tests --outputjson` (for strict editor/LSP parity)
- `uv run pytest -q`

Rules:
- No `noqa`/ignore suppression as a default strategy.
- Fix root causes first.
- Use narrow and justified suppressions only when technically unavoidable.

### 17.2 Suppression Policy
- Avoid blanket ignores (`noqa`, broad pyright disables, global skips).
- If suppression is unavoidable, keep it local, minimal, and explained inline.
- Suppression without explanation is not allowed.

### 17.1 Common LSP Fix Patterns Used Here
- Protocol mock errors:
  - Remove unnecessary protocol inheritance.
  - Implement structural methods with correct signatures/defaults.
- Patch target mismatch:
  - Patch imported symbol in its consumer module.
  - Example: patch `src.services.spotify.downloader.BeautifulSoup`, not `bs4.BeautifulSoup`.
- Optional field access:
  - Guard `None` explicitly before `len` or indexing.

## 18. GUI (CustomTkinter/Tkinter) Best Practices
- Keep UI responsive:
  - do not run blocking network/file operations on the main thread
- Schedule UI updates on the main thread (`schedule_on_main_thread` pattern).
- Keep dialogs/components focused on rendering and input handling.
- Keep business logic in services/handlers/coordinators.
- For images in CTk, use `CTkImage` rather than raw `PhotoImage` for DPI scaling compatibility.
- Surface actionable errors in status bar/message queue.
- Preserve stable state transitions:
  - idle, loading, ready, error

## 19. Downloader and Media Workflow Practices
- Normalize URLs before extraction when needed.
- Build explicit auth strategy order and fallback paths.
- Verify downloaded file completion (existence, non-empty, final extension rules).
- Exclude auxiliary artifacts when validating media outputs.
- Keep retries bounded and classified by error type (network, auth, format, etc).

## 20. Reuse-First and Helper Hygiene
- Do not create new helper methods unless they simplify repeated logic materially.
- Prefer one reusable helper over many similar one-off helpers.
- Avoid file-local helper sprawl and helper-per-branch patterns.
- Delete obsolete helpers after refactor.

### 20.1 Helper Method Acceptance Criteria
Create a helper only if at least one is true:
- repeated logic appears in 2+ call sites
- it materially improves readability of a complex block
- it isolates volatility or side-effect boundaries

Avoid helpers that:
- are single-use and trivial
- hide simple logic behind indirection
- duplicate similar helpers in nearby modules

## 21. Anti-Patterns to Avoid
- Duplicated logic across platform services.
- Deep nested conditionals without early exits.
- Boolean mode flags that explode branch complexity.
- Business logic in UI classes.
- Hidden side effects and global mutable state.
- Broad exception swallowing.
- Excessive abstraction with no present pressure.
- Ad-hoc constants and magic literals in business paths.
- Inline function/class imports without strong reason.

## 22. Security and Privacy Rules
- Never commit secrets/tokens/cookies/passwords.
- Never log sensitive cookie/header values.
- Sanitize user-facing error messages.
- Keep auth/cookie handling explicit and minimal.

## 23. Documentation Requirements
For significant changes:
- Explain intent, design, and tradeoffs.
- Document behavior changes and migration notes.
- Capture assumptions and unresolved risks.

## 23.1 Code Review Protocol
- Prioritize findings by severity: bugs, regressions, correctness, security, then style.
- Give file/line references for findings.
- Distinguish hard issues from optional improvements.
- If no issues are found, state that explicitly and list residual risks/testing gaps.

## 24. Definition of Done
- Requirements clarified or assumptions explicitly approved.
- Architecture boundaries respected.
- Reuse-first approach applied (no avoidable duplicates).
- Config/constants policy followed.
- Lint/type/test gates all pass.
- UX behavior and error handling are coherent.
- Changes and validation are documented.

## 24.1 Problem Decomposition Rule
- Break non-trivial problems into small, verifiable steps.
- Validate each step before moving to the next.
- Keep the engineer informed of progress, discoveries, and blockers.
- If a step reveals a deeper issue, re-plan and communicate updated options.

## 25. Practical Good/Bad Examples

### Good
- Early return guard:
```python
if not (cookie_path := self.auto_cookie_manager.get_cookies()):
    return False
```

- Set membership for repeated checks:
```python
RETRYABLE = {"network", "rate_limit"}
if error_type in RETRYABLE:
    return retry()
```

- Structural protocol mock (no inheritance):
```python
class MockErrorNotifier:
    def show_error(self, title: str, message: str) -> None: ...
    def handle_exception(self, exception: Exception, context: str = "", service: str = "") -> None: ...
```

### Bad
- Duplicate lookup and deep nesting:
```python
if self.auto_cookie_manager:
    if self.auto_cookie_manager.get_cookies():
        cookie_path = self.auto_cookie_manager.get_cookies()
```

- List membership in hot checks:
```python
if browser in ["chrome", "firefox", "zen", "edge", "brave"]:
    ...
```

## 26. Agent Behavior in This Repo
- Prioritize understanding existing patterns before introducing new ones.
- Prefer updating/extending existing code paths over rewrites.
- Keep code simple (KISS) while preserving solid engineering rigor.
- Escalate ambiguity early with clear options and tradeoffs.

## 27. GOF Pattern Opportunity Protocol
- Do not force pattern usage.
- When a GOF pattern is a good fit, present it as an option, not a mandate.
- Provide:
  - pattern name
  - specific problem it solves here
  - why simpler alternatives may be insufficient
  - tradeoffs (complexity, indirection, testability, onboarding cost)
- Proceed with pattern adoption only after engineer acceptance for significant refactors.
