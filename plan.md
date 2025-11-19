# Media Downloader Fixes & Cookie Refactoring Plan

## Status: Phase 1 Complete - Moving to Cookie Refactoring
Last Updated: 2025-01-19

---

## PHASE 1: FIX SOUNDCLOUD ISSUE ✓ COMPLETE

### Root Cause Analysis
1. **Error**: ValidationError when creating Download with `service_type="generic"`
2. **Location**: `platform_dialog_coordinator.py:224` in `generic_download()`
3. **Cause**: ServiceType enum doesn't include "generic" value
4. **Impact**: SoundCloud downloads fail because handler routes to generic_download

### Tasks

#### Task 1.1: Add GENERIC to ServiceType Enum ✅ COMPLETE
- File: `src/core/enums/service_type.py`
- Action: Add `GENERIC = "generic"` to ServiceType enum
- Rationale: Support generic downloads for unregistered platforms
- Status: Committed in 3b98480

#### Task 1.2: Update Download Model Validation ✅ COMPLETE
- File: `src/core/models.py`
- Action: Verify Download model accepts all ServiceType values
- Test: Create Download with service_type="generic"
- Status: Verified working - no changes needed

#### Task 1.3: Test SoundCloud Flow ⏳ PENDING
- Test URL: https://soundcloud.com/fm_freemusic/science-discoveries-light-flowing-music-for-corporate-projects-by-oleg-mazur-free-download
- Verify: URL detection → Handler → Dialog → Download creation
- Expected: No validation errors, download added to queue
- Action: Requires manual UI testing

#### Task 1.4: Merge to Main ⏳ NEXT
- Verify all tests pass (or fix test infrastructure)
- Merge feature/soundcloud-support-and-error-fixes → development
- Merge development → main
- Create new branch for cookie refactor

---

## PHASE 2: COOKIE SYSTEM REFACTORING

### Root Cause Analysis - Current System
1. **Current Implementation**:
   - Manual cookie file selection
   - Browser selection enum (Chrome, Firefox, Edge, etc.)
   - Cookie handler with file paths
   - UI components for browser selection
   
2. **Problems**:
   - Manual process requires user interaction
   - Cookies expire, no auto-refresh
   - Browser-specific complexity
   - Window/dialog overhead

### New Requirements
1. **Auto Cookie Generation**: Use headless browser to generate cookies
2. **Browser**: Use Playwright with Chromium (lightest option)
3. **Storage**: Save cookies in JSON with timestamp
4. **Expiry**: Regenerate if >8 hours old
5. **Startup**: Generate on app init, block YouTube downloads until ready
6. **State Management**: Track cookie generation state
7. **Cleanup**: Remove browser selection UI/logic/enums

### Tasks

#### Task 2.1: Remove Old Cookie System
- [ ] **File**: `src/core/enums/browser_type.py` - DELETE entire file
- [ ] **File**: `src/core/models.py` - Remove `selected_browser` field from Download
- [ ] **File**: `src/services/cookies/` - Review and remove browser-specific logic
- [ ] **Search**: Grep for "browser_type", "BrowserType", "selected_browser" - remove all references
- [ ] **UI**: Remove browser selection components from dialogs/windows

#### Task 2.2: Add Dependencies
- [ ] **File**: `requirements.txt`
  - Add: `playwright>=1.40.0`
- [ ] **Terminal**: Run `playwright install chromium`
- [ ] **Verify**: Chromium installed successfully

#### Task 2.3: Create Cookie State Model
- [ ] **File**: `src/core/models.py`
  - Add `CookieState` model:
    ```python
    class CookieState(BaseModel):
        generated_at: datetime
        expires_at: datetime
        is_valid: bool
        is_generating: bool
        cookie_path: str
        error_message: Optional[str]
    ```

#### Task 2.4: Create Cookie Generator Service
- [ ] **File**: `src/services/cookies/cookie_generator.py` - NEW FILE
  - Class: `CookieGenerator`
  - Method: `async generate_cookies() -> CookieState`
  - Method: `is_expired() -> bool`
  - Method: `get_state() -> CookieState`
  - Logic:
    - Launch Playwright Chromium in headless incognito mode
    - Navigate to youtube.com
    - Wait for page load
    - Extract cookies
    - Save to JSON with timestamp
    - Return CookieState

#### Task 2.5: Create Cookie Manager Service
- [ ] **File**: `src/services/cookies/cookie_manager.py` - NEW FILE
  - Class: `CookieManager`
  - Method: `initialize() -> None` - Load or generate cookies
  - Method: `get_cookies() -> str` - Return cookie file path
  - Method: `refresh_if_needed() -> None` - Check expiry and regenerate
  - Method: `get_state() -> CookieState` - Return current state
  - Storage: `~/.media_downloader/cookies.json`
  - State file: `~/.media_downloader/cookie_state.json`

#### Task 2.6: Integrate with Application Container
- [ ] **File**: `src/core/application/container.py`
  - Register `cookie_manager` as singleton
  - Initialize on app startup (before UI)
  - Handle async initialization properly

#### Task 2.7: Integrate with YouTube Downloader
- [ ] **File**: `src/services/youtube/downloader.py`
  - Get cookies from cookie_manager
  - Pass to yt-dlp via `--cookies` parameter
  - Remove browser selection logic

#### Task 2.8: Update YouTube Handler
- [ ] **File**: `src/handlers/youtube_handler.py`
  - Check cookie state before processing
  - If generating, queue request and notify user
  - Once ready, process queued requests

#### Task 2.9: Add UI State Indicators
- [ ] **File**: `src/ui/components/status_bar.py` or similar
  - Show "Generating cookies..." during generation
  - Show "Cookies ready" when complete
  - Show error if generation fails

#### Task 2.10: Update YouTube Dialog
- [ ] **File**: `src/ui/dialogs/youtube_dialog.py`
  - Remove browser selection dropdown
  - Remove browser-related UI elements
  - Simplify dialog layout

#### Task 2.11: Error Handling
- [ ] Handle Playwright installation missing
- [ ] Handle network errors during generation
- [ ] Handle file system errors (permissions)
- [ ] Provide fallback: allow manual cookie file selection

#### Task 2.12: Testing
- [ ] Unit tests for CookieGenerator
- [ ] Unit tests for CookieManager
- [ ] Integration test: Generate → Save → Load → Use
- [ ] Test expiry logic (mock time)
- [ ] Test concurrent requests during generation
- [ ] Test YouTube download with auto-cookies

---

## PHASE 3: METADATA FETCH ON DETECTION

### Requirements
- Fetch YouTube metadata immediately when link detected
- No need for browser selection window
- Show metadata in UI before download

### Tasks

#### Task 3.1: Update YouTube Handler
- [ ] **File**: `src/handlers/youtube_handler.py`
  - Fetch metadata in `can_handle()` or after detection
  - Store in detection result metadata
  - Use yt-dlp info extraction

#### Task 3.2: Update YouTube Dialog
- [ ] Pre-populate dialog with fetched metadata
- [ ] Show title, duration, thumbnail immediately
- [ ] Remove loading state (already loaded)

---

## BRANCH STRATEGY

### Current Branch
- `feature/soundcloud-support-and-error-fixes` - Fix SoundCloud issue

### Next Branch
- `feature/cookie-auto-generation` - Cookie refactoring

### Merge Order
1. Fix SoundCloud → merge to `development`
2. Merge `development` → `main`
3. Create new branch from updated `development`
4. Implement cookie refactor
5. Merge to `development` → `main`

---

## NOTES

### Design Principles Applied
- **Single Responsibility**: Each service has one job
- **Dependency Injection**: Use container for service management
- **State Management**: Centralized cookie state
- **Error Handling**: Graceful degradation with fallbacks
- **Async/Await**: Proper async cookie generation
- **Clean Code**: No if/else chains, early returns, clear naming

### Playwright vs Selenium
- **Chosen**: Playwright
- **Reasons**:
  - Lighter weight
  - Better async support
  - Built-in headless mode
  - Faster startup
  - Better cookie handling

### Storage Location
- **Path**: `~/.media_downloader/`
- **Files**:
  - `cookies.json` - Cookie data
  - `cookie_state.json` - State metadata

### Expiry Logic
```python
def is_expired(generated_at: datetime) -> bool:
    return datetime.now() - generated_at > timedelta(hours=8)
```

---

## COMPLETION CHECKLIST

### Phase 1: SoundCloud
- [x] ServiceType.GENERIC added
- [ ] SoundCloud downloads work (needs manual testing)
- [ ] Tests pass (test infrastructure has issues)
- [ ] Merged to main

### Phase 2: Cookies
- [ ] Old system removed
- [ ] Playwright installed
- [ ] CookieGenerator implemented
- [ ] CookieManager implemented
- [ ] Integrated with container
- [ ] YouTube downloads use auto-cookies
- [ ] UI updated
- [ ] Tests pass

### Phase 3: Metadata
- [ ] Metadata fetched on detection
- [ ] YouTube dialog pre-populated
- [ ] Tests pass

---

## END OF PLAN