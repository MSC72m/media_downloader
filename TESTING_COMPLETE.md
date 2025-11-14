# Complete Testing Guide

This guide covers all functionality that needs testing after the major refactoring and feature additions.

---

## 🎯 Critical Test: Instagram Authentication State

### Test 1.1: Login Cancellation
**Steps:**
1. Launch app
2. Click "Instagram Login" button
3. Verify button changes to "Logging in..."
4. **Cancel the dialog** (click X or Cancel)
5. **EXPECTED:** Button immediately resets to "Instagram Login" (enabled)
6. **VERIFY:** No stuck "Logging in..." state

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 1.2: Wrong Credentials
**Steps:**
1. Click "Instagram Login"
2. Enter invalid username/password
3. Click OK
4. Wait for authentication to fail
5. **EXPECTED:** 
   - Button resets to "Instagram Login"
   - Error dialog appears ONCE with auth failure message
   - Status bar shows "Instagram authentication failed"
6. **VERIFY:** No duplicate error messages

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 1.3: Network Error During Auth
**Steps:**
1. Disconnect internet
2. Click "Instagram Login"
3. Enter credentials
4. Wait for timeout
5. **EXPECTED:**
   - Button resets to "Instagram Login"
   - Error dialog appears ONCE
   - No stuck state

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 1.4: Successful Authentication
**Steps:**
1. Click "Instagram Login"
2. Enter valid credentials
3. Complete any 2FA if required
4. **EXPECTED:**
   - Button changes to "Instagram: Logged In" (disabled)
   - Status bar shows "Instagram authenticated successfully"
   - Success message appears ONCE

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🎵 YouTube Music Auto-Download

### Test 2.1: Regular YouTube Video
**Steps:**
1. Paste regular YouTube URL: `https://www.youtube.com/watch?v=dQw4w9WgXcQ`
2. Click Add
3. **EXPECTED:**
   - Cookie selector dialog appears
   - YouTube downloader dialog appears after cookie selection
   - Options available (quality, format, etc.)

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 2.2: YouTube Music URL Auto-Download
**Steps:**
1. Paste YouTube Music URL: `https://music.youtube.com/watch?v=dQw4w9WgXcQ`
2. Click Add
3. **EXPECTED:**
   - NO dialog appears
   - Download automatically added to list
   - Name shows proper track title (fetched from metadata)
   - Format is audio-only
   - Quality is set to "best"

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 2.3: YouTube Music Metadata Fetch
**Steps:**
1. Paste YouTube Music URL
2. Watch download list
3. **EXPECTED:**
   - Track name appears with proper title (not just "YouTube Music")
   - If metadata fetch fails, shows "YouTube Music" as fallback

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 2.4: YouTube Music Download Execution
**Steps:**
1. Add YouTube Music URL
2. Click "Download All"
3. Wait for completion
4. **EXPECTED:**
   - Downloads as audio file (.mp3, .m4a, etc.)
   - NOT video file
   - Metadata embedded in file
   - Thumbnail embedded (if available)

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🎶 SoundCloud Premium Detection

### Test 3.1: Public SoundCloud Track
**Steps:**
1. Paste public SoundCloud URL
2. Click Add
3. **EXPECTED:**
   - Track added to download list successfully
   - Name shows "Artist - Title"
   - No premium error

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 3.2: SoundCloud Go+ Premium Track
**Steps:**
1. Paste SoundCloud Go+ track URL (premium only)
2. Click Add
3. **EXPECTED:**
   - Error dialog appears immediately
   - Title: "SoundCloud Go+ Required"
   - Message: "This track requires Go+ subscription..."
   - Track NOT added to download list
   - Error shown ONCE (not duplicated)

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 3.3: Private/Unavailable SoundCloud Track
**Steps:**
1. Paste private/deleted SoundCloud URL
2. Click Add
3. **EXPECTED:**
   - Error dialog with appropriate message
   - Track not added to queue

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🚀 UI Startup Performance

### Test 4.1: No Startup Freeze
**Steps:**
1. Launch application
2. Observe UI rendering
3. **EXPECTED:**
   - UI appears immediately (< 500ms)
   - No freeze or hang
   - Status shows "Checking network connectivity..."
   - After 1-3 seconds, status updates to "Ready - All services connected"

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 4.2: Network Check in Background
**Steps:**
1. Launch app
2. Try clicking buttons immediately
3. **EXPECTED:**
   - UI is responsive during network check
   - Can interact with components while checking
   - Network check doesn't block main thread

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 4.3: Network Check Failure
**Steps:**
1. Disconnect internet
2. Launch app
3. Wait for network check
4. **EXPECTED:**
   - Error dialog appears after check
   - Title: "Network Connectivity Issue"
   - Status bar shows error
   - Error shown ONCE via message queue

**Status:** ⬜ PASS | ⬜ FAIL

---

## 💾 Download Error Handling

### Test 5.1: Download Failure
**Steps:**
1. Add invalid URL or URL that will fail
2. Click "Download All"
3. Wait for failure
4. **EXPECTED:**
   - Error dialog appears ONCE
   - Title: "Download Failed"
   - Message includes specific error
   - Status bar shows "Download failed: [name]" (simple message)
   - Download marked as failed in list
   - Buttons re-enabled

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 5.2: No Duplicate Error Messages
**Steps:**
1. Trigger any download error
2. Count error displays
3. **EXPECTED:**
   - Error dialog: 1 time
   - Status bar: 1 simple message (not red error)
   - NO duplicate showing

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🔄 State Management

### Test 6.1: Component State Persistence
**Steps:**
1. Authenticate Instagram
2. Check ComponentStateManager state
3. **EXPECTED:**
   - State stored in ComponentStateManager
   - options_bar displays correct state
   - State consistent across components

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 6.2: State Reset After Errors
**Steps:**
1. Trigger any error (Instagram auth, download, etc.)
2. Verify state resets correctly
3. **EXPECTED:**
   - All error paths reset state properly
   - No "stuck" states
   - UI returns to correct state

**Status:** ⬜ PASS | ⬜ FAIL

---

## 📋 Integration Tests

### Test 7.1: Full YouTube Music Workflow
**Steps:**
1. Launch app
2. Wait for network check
3. Paste YouTube Music URL
4. Download automatically added
5. Click "Download All"
6. Wait for completion
7. **EXPECTED:**
   - No errors
   - Audio file downloaded
   - Proper metadata
   - UI state correct throughout

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 7.2: Full SoundCloud Workflow
**Steps:**
1. Paste public SoundCloud URL
2. Verify track info fetched
3. Download added to list
4. Click "Download All"
5. Wait for completion
6. **EXPECTED:**
   - Audio file downloaded
   - Proper naming
   - No errors

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 7.3: Mixed Downloads
**Steps:**
1. Add YouTube video (with dialog)
2. Add YouTube Music (auto)
3. Add SoundCloud track
4. Try adding SoundCloud Go+ track (should fail)
5. Click "Download All"
6. **EXPECTED:**
   - All valid downloads complete
   - Premium track rejected
   - Errors shown appropriately

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🎨 UI Component Tests

### Test 8.1: Button State Updates
**Steps:**
1. Start download
2. Verify buttons disabled
3. Wait for completion
4. Verify buttons re-enabled
5. **EXPECTED:**
   - Buttons disabled during download
   - Buttons enabled after completion
   - State managed by ComponentStateManager

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 8.2: Status Bar Updates
**Steps:**
1. Perform various actions
2. Watch status bar
3. **EXPECTED:**
   - Status updates for each action
   - No duplicate messages
   - Clear, concise messages

**Status:** ⬜ PASS | ⬜ FAIL

---

## 🐛 Edge Cases

### Test 9.1: Rapid Button Clicking
**Steps:**
1. Click "Instagram Login" multiple times rapidly
2. **EXPECTED:**
   - Only one dialog appears
   - State doesn't get confused
   - Button state correct after cancellation

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 9.2: Cancel Mid-Download
**Steps:**
1. Start downloads
2. Close application mid-download
3. Re-open application
4. **EXPECTED:**
   - Clean shutdown
   - No stuck states on restart
   - Download list cleared or shows failed

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 9.3: Multiple Error Conditions
**Steps:**
1. Trigger network error
2. Immediately try Instagram login
3. Cancel dialog
4. Add invalid URL
5. **EXPECTED:**
   - Each error handled properly
   - No error accumulation
   - UI state consistent

**Status:** ⬜ PASS | ⬜ FAIL

---

## 📊 Performance Tests

### Test 10.1: Regex Pattern Performance
**Steps:**
1. Add 10+ SoundCloud URLs (mix of premium/public)
2. Measure premium detection time
3. **EXPECTED:**
   - Detection instant (< 100ms per track)
   - Regex patterns compiled once
   - No performance degradation

**Status:** ⬜ PASS | ⬜ FAIL

---

### Test 10.2: State Manager Performance
**Steps:**
1. Trigger 100+ state updates
2. Monitor memory and CPU
3. **EXPECTED:**
   - No memory leaks
   - State updates instant
   - No performance issues

**Status:** ⬜ PASS | ⬜ FAIL

---

## ✅ Test Summary

Total Tests: 28

| Category | Passed | Failed | Skipped |
|----------|--------|--------|---------|
| Instagram Auth | _/4 | _/4 | _/4 |
| YouTube Music | _/4 | _/4 | _/4 |
| SoundCloud Premium | _/3 | _/3 | _/3 |
| UI Startup | _/3 | _/3 | _/3 |
| Download Errors | _/2 | _/2 | _/2 |
| State Management | _/2 | _/2 | _/2 |
| Integration | _/3 | _/3 | _/3 |
| UI Components | _/2 | _/2 | _/2 |
| Edge Cases | _/3 | _/3 | _/3 |
| Performance | _/2 | _/2 | _/2 |

---

## 🚨 Critical Tests (Must Pass)

These tests are CRITICAL and must pass before merge:

1. ✅ Instagram button resets after cancellation (Test 1.1)
2. ✅ Instagram button resets after auth failure (Test 1.2)
3. ✅ YouTube Music auto-downloads without dialog (Test 2.2)
4. ✅ SoundCloud premium tracks rejected immediately (Test 3.2)
5. ✅ No UI freeze on startup (Test 4.1)
6. ✅ No duplicate error messages (Test 5.2)

---

## 📝 Test Execution Notes

**Tester Name:** _________________  
**Date:** _________________  
**Branch:** feature/soundcloud-support-and-error-fixes  
**Commit:** 5b3abc9  

**Environment:**
- OS: _________________
- Python Version: _________________
- Screen Resolution: _________________

**Notes:**
```
[Add any observations, issues found, or recommendations here]
```

---

## 🔍 Debugging Commands

If issues found, use these for debugging:

```python
# Check component state
component_state_manager.log_current_states()

# Check event bus
logger.setLevel(logging.DEBUG)

# Monitor state changes
grep "COMPONENT_STATE_MANAGER.*Setting" logs/app.log
```

---

**Status:** ⬜ ALL TESTS PASSED | ⬜ ISSUES FOUND  
**Ready for Merge:** ⬜ YES | ⬜ NO  
**Reviewer:** _________________