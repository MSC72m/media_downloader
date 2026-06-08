# Media Downloader 1.0.0 Release Plan

**Branch:** `feature/complete-media-downloader-enhancement`
**Date:** 2026-06-08
**Goal:** Clean, test, refactor and prepare codebase for 1.0.0 release

---

## Current State

**Downloaders (10):** Twitter, Pinterest, Spotify, RadioJavan, YouTube, SoundCloud, TikTok, Instagram, Network, File

**Known Issues:**
1. RadioJavan session management is script-based (`refresh_radiojavan_session.py`) and inconsistent with YouTube's centralized approach
2. Cookie/Session managers use generic names even when platform-specific
3. CI/CD `quality_gate.sh` doesn't match `workflow.yml` (missing format check, uses mypy instead of basedpyright)
4. Token/cookie generation blocks the main thread
5. Duplicate patterns and legacy code to clean up

---

## PHASE 1: Testing & Validation

**Goal:** Test all 10 downloaders and create a report marking working/broken.

**Downloaders to test:**
- [ ] Twitter - `src/services/twitter/downloader.py`
- [ ] Pinterest - `src/services/pinterest/downloader.py`
- [ ] Spotify - `src/services/spotify/downloader.py`
- [ ] RadioJavan - `src/services/radiojavan/downloader.py`
- [ ] YouTube - `src/services/youtube/downloader.py`
- [ ] SoundCloud - `src/services/soundcloud/downloader.py`
- [ ] TikTok - `src/services/tiktok/downloader.py`
- [ ] Instagram - `src/services/instagram/downloader.py`
- [ ] Network - `src/services/network/downloader.py`
- [ ] File - `src/services/file/downloader.py`

**Deliverable:** `DOWNLOADER_STATUS.md` with ✅/❌/⚠️ status for each.

---

## PHASE 2: RadioJavan Session Refactoring

**Goal:** Match YouTube's centralized session pattern.

**Current YouTube pattern:**
```
YouTubeHandler -> CookieManager -> CookieGenerator (integrated, no external script)
```

**Current RadioJavan pattern (BROKEN):**
```
RadioJavanHandler -> RadioJavanCookieManager (exists but has script dependency)
+ refresh_radiojavan_session.py (standalone script, does not integrate with app)
```

**Tasks:**
- [ ] Remove `scripts/refresh_radiojavan_session.py` dependency
- [ ] Ensure `RadioJavanCookieManager.initialize()` is self-contained (no external script)
- [ ] Verify RadioJavan cookie generation works through `RadioJavanHandler` → `RadioJavanCookieManager` path
- [ ] Remove script-based session refresh code
- [ ] Test RadioJavan session generation end-to-end

---

## PHASE 3: Session Consistency

**Goal:** Make RadioJavan and YouTube session handling identical where applicable.

**Tasks:**
- [ ] Analyze YouTube incognito mode and session refresh patterns in `cookie_manager.py`
- [ ] Compare RadioJavan validation approach with YouTube in `radiojavan_cookie_manager.py`
- [ ] Make RadioJavan cookie validation match YouTube validation approach
- [ ] Ensure refresh timing and error recovery behavior is consistent
- [ ] Ensure background probe validation matches between both managers

---

## PHASE 4: CI/CD Quality Gate Unification

**Current mismatch:**
```
quality_gate.sh uses:           workflow.yml uses:
- ruff check ✓                  - ruff check ✓
- basedpyright (src) ✓          - mypy (src) ✗
- basedpyright (tests) ✓        - (no test typing)
- pytest ✓                      - pytest ✓
- (NO FORMAT CHECK) ✗           - ruff format --check ✓
```

**Tasks:**
- [ ] Add `uv run ruff format --check .` to `quality_gate.sh`
- [ ] Replace `mypy` with `basedpyright` in `workflow.yml` (AGENTS.md section 17 says basedpyright is the policy)
- [ ] Update `workflow.yml` to call `./scripts/quality_gate.sh` instead of duplicate commands
- [ ] Keep `quality_gate.sh` as single source of truth for local + CI

---

## PHASE 5: Threading Optimization

**Goal:** Move token/cookie generation to background threads so UI doesn't block.

**Current blocking points (identified):**
- `CookieManager.initialize()` calls `loop.run_until_complete()` on main thread
- `RadioJavanCookieManager.initialize()` same pattern
- Both use `_get_event_loop()` which blocks

**Tasks:**
- [ ] Move YouTube cookie initialization to background thread using `ThreadPoolExecutor`
- [ ] Move RadioJavan cookie initialization to background thread using `ThreadPoolExecutor`
- [ ] Add progress callbacks so UI can show loading state
- [ ] Ensure thread safety with existing `_lock` patterns
- [ ] Test UI responsiveness during token generation

---

## PHASE 6: Code Cleanup & Deduplication

**Tasks:**
- [ ] Remove downloaders marked as broken in Phase 1 testing
- [ ] Consolidate duplicate error handling patterns across downloaders
- [ ] Remove legacy session/cookie management code
- [ ] Clean up unused imports across all service files
- [ ] Remove dead/commented code
- [ ] Remove `scripts/refresh_radiojavan_session.py` if fully replaced

---

## PHASE 7: Verification & Testing

**Tasks:**
- [ ] Run `./scripts/quality_gate.sh` - all checks pass
- [ ] Run full pytest suite - coverage ≥ 25%
- [ ] End-to-end test each working downloader from Phase 1
- [ ] Verify YouTube session generation and refresh
- [ ] Verify RadioJavan session generation and refresh
- [ ] Test UI responsiveness during background token generation

---

## PHASE 8: Release Preparation

**Tasks:**
- [ ] Update version in `pyproject.toml` to `1.0.0`
- [ ] Create release notes documenting changes
- [ ] Verify Windows release workflow builds successfully
- [ ] Merge `feature/complete-media-downloader-enhancement` into `main`
- [ ] Create `v1.0.0` tag and trigger release workflow

---

## Quality Gates (AGENTS.md Section 17 - Mandatory)

Before claiming any phase complete, run:
```bash
uv run ruff check .
npx basedpyright --outputjson
npx basedpyright tests --outputjson
uv run pytest -q
```

Or simply: `./scripts/quality_gate.sh`

---

## Progress Log

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1 | ✅ Complete | Created DOWNLOADER_STATUS.md - 320 passed, 3 failed |
| Phase 2 | ⏳ Pending | |
| Phase 3 | ⏳ Pending | |
| Phase 4 | ⏳ Pending | |
| Phase 5 | ⏳ Pending | |
| Phase 6 | ⏳ Pending | |
| Phase 7 | ⏳ Pending | |
| Phase 8 | ⏳ Pending | |
