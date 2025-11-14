# Data Flow Documentation - Single Source of Truth

This document shows the **SINGLE PATH** for each type of update in the application. There are **NO DUPLICATE FLOWS**.

---

## 🎯 Instagram Authentication Flow

### SINGLE PATH: platform_dialog_coordinator ONLY

```
User clicks "Instagram Login"
    ↓
options_bar._handle_instagram_login()
    → Just calls callback, NO state management
    ↓
platform_dialog_coordinator.authenticate_instagram()
    → Sets state to LOGGING_IN via component_state_manager ✅ ONLY HERE
    ↓
orchestrator.auth_manager.authenticate_instagram()
    → Shows login dialog
    → Performs authentication (network I/O in background thread)
    → NO UI updates, NO state management
    → Returns: callback(success, error_message)
    ↓
platform_dialog_coordinator.on_auth_complete()
    → Updates state via component_state_manager ✅ ONLY HERE
    → Updates status bar (single update)
    → Shows error dialog IF error (single dialog)
    ↓
component_state_manager.set_instagram_[authenticated|failed]()
    → Updates options_bar button display
    ↓
options_bar.set_instagram_status()
    → Updates button text and state (display only, no logic)
```

**KEY POINTS:**
- ✅ State set to LOGGING_IN: **1 place** (platform_dialog_coordinator before auth)
- ✅ State set to SUCCESS/FAILED: **1 place** (platform_dialog_coordinator callback)
- ✅ Status bar update: **1 place** (platform_dialog_coordinator callback)
- ✅ Error dialog: **1 place** (platform_dialog_coordinator callback)
- ❌ orchestrator does **ZERO** UI updates (auth logic only)

---

## 📥 Download Failure Flow

### SINGLE PATH: download_coordinator via event bus

```
Download fails in yt-dlp/downloader
    ↓
download.mark_failed(error_message)
    → Publishes DownloadEvent.FAILED via event_bus
    ↓
download_coordinator._on_failed_event()
    → Refreshes download list
    → Enables buttons
    → Updates status bar (simple message, not error style)
    → Shows error dialog via message_queue ✅ ONLY HERE
    ↓
component_state_manager (if needed)
    → Updates button states
```

**KEY POINTS:**
- ✅ Error dialog shown: **1 place** (download_coordinator._on_failed_event)
- ✅ Status bar updated: **1 place** (download_coordinator._on_failed_event)
- ❌ NO duplicate error showing in status bar AND dialog
- ❌ NO duplicate state updates

---

## 🌐 Network Connectivity Check Flow

### SINGLE PATH: orchestrator background thread → message_queue

```
App starts
    ↓
main.py: self.after(100, orchestrator.check_connectivity)
    ↓
orchestrator.check_connectivity()
    → Sets status: "Checking network connectivity..."
    → Starts background thread (no UI freeze)
    ↓
connectivity_worker() [background thread]
    → Performs network I/O
    → Schedules UI update via root.after(0, update_ui)
    ↓
orchestrator._handle_connectivity_check() [main thread]
    → Updates status bar (single update)
    → Shows error via message_queue IF error ✅ ONLY HERE
    ↓
message_queue.add_message()
    → Shows error dialog on main thread
```

**KEY POINTS:**
- ✅ Network I/O in background thread (no UI freeze)
- ✅ UI updates on main thread via root.after()
- ✅ Error dialog: **1 place** (via message_queue)
- ❌ NO blocking messagebox.showerror()

---

## 🎵 YouTube Music Auto-Download Flow

### SINGLE PATH: youtube_handler detects → auto-creates download

```
User pastes music.youtube.com URL
    ↓
youtube_handler.can_handle(url)
    → Detects YouTube Music URL
    → metadata['is_music'] = True
    ↓
youtube_handler.get_ui_callback()
    ↓
youtube_callback(url, ui_context)
    → Checks: if _is_youtube_music(url)
    → YES: Skip dialog, auto-download
    ↓
create_music_download()
    → Fetches metadata for track name
    → Creates Download object with:
        - audio_only = True
        - format = "audio"
        - quality = "best"
    → Calls download_callback(download)
    ↓
event_coordinator.add_download(download)
    → Adds to download list
    → No dialog shown
```

**KEY POINTS:**
- ✅ Music URL detection: **1 place** (_is_youtube_music checks domain)
- ✅ Auto-download: **1 place** (youtube_handler callback)
- ✅ No options dialog for music URLs
- ✅ Metadata fetched before adding to queue

---

## 🎶 SoundCloud Premium Track Rejection Flow

### SINGLE PATH: platform_dialog_coordinator checks before adding

```
User pastes SoundCloud URL
    ↓
soundcloud_handler → platform_dialog_coordinator.show_soundcloud_dialog()
    ↓
Gets track info: downloader.get_info(url)
    ↓
Checks: downloader._is_premium_track(info)
    → Uses compiled regex patterns (efficient)
    → Checks: policy, availability, keywords
    ↓
IF premium:
    → Shows error dialog via _show_error_dialog() ✅ ONLY HERE
    → Returns (does NOT add to download queue)
    ↓
IF not premium:
    → Creates Download object
    → Calls on_download_callback(download)
```

**KEY POINTS:**
- ✅ Premium check: **1 place** (before download creation)
- ✅ Error shown: **1 place** (via message_queue)
- ✅ Uses regex for efficient pattern matching
- ❌ NO download added if premium detected

---

## 🔄 Component State Management

### SINGLE SOURCE OF TRUTH: ComponentStateManager

```
ANY component wants to update state
    ↓
component_state_manager.set_[state_name]()
    → Updates internal state dictionary
    → Calls appropriate UI component update method
    ↓
UI Component (options_bar, action_buttons, etc.)
    → Receives state update
    → Updates display (no logic, just rendering)
```

**State Types Managed:**
1. **instagram_auth** → InstagramAuthStatus (LOGGING_IN, AUTHENTICATED, FAILED)
2. **download_in_progress** → bool
3. **buttons_enabled** → bool
4. **network_status** → string

**KEY POINTS:**
- ✅ All state changes go through ComponentStateManager
- ✅ UI components only display state, don't manage it
- ✅ No duplicate state in multiple places
- ✅ Single source of truth for all states

---

## ⚠️ Error Display Strategy

### SINGLE PATH: message_queue for all user-facing errors

```
Error occurs anywhere in application
    ↓
Create Message object:
    - text: error message
    - level: MessageLevel.ERROR
    - title: error dialog title
    ↓
message_queue.add_message(message)
    ↓
MessageQueue processes on main thread
    → Shows messagebox.showerror()
    → Non-blocking, integrates with app lifecycle
```

**Rules:**
- ✅ ALL user-facing errors use message_queue
- ❌ NO direct messagebox.showerror() calls
- ❌ NO duplicate error showing in status bar + dialog
- ✅ Status bar shows simple info, dialog shows detailed error

---

## 📊 Summary of Single Paths

| Update Type | Single Source | Method |
|-------------|---------------|--------|
| Instagram State | platform_dialog_coordinator | component_state_manager.set_instagram_*() |
| Download Errors | download_coordinator | message_queue.add_message() |
| Network Errors | orchestrator | message_queue.add_message() |
| Button States | component_state_manager | set_buttons_enabled() |
| Status Bar | event_coordinator | update_status() |
| Music Auto-DL | youtube_handler | Detects + auto-creates Download |
| Premium Check | platform_dialog_coordinator | Checks before adding to queue |

---

## 🚫 Anti-Patterns (REMOVED)

### ❌ What We DON'T Do Anymore:

1. **Duplicate State Updates**
   ```python
   # OLD (WRONG):
   options_bar.set_instagram_status(LOGGING_IN)  # Place 1
   auth_manager._update_instagram_status("logging_in")  # Place 2
   
   # NEW (CORRECT):
   component_state_manager.set_instagram_logging_in()  # ONLY place
   ```

2. **Duplicate Error Showing**
   ```python
   # OLD (WRONG):
   self.ui_state.show_error(error)  # Place 1
   self._show_error_dialog(title, error)  # Place 2
   
   # NEW (CORRECT):
   self._show_error_dialog(title, error)  # ONLY place
   ```

3. **UI Updates in Multiple Layers**
   ```python
   # OLD (WRONG):
   orchestrator: updates state + status bar + shows error
   coordinator: ALSO updates state + status bar + shows error
   
   # NEW (CORRECT):
   orchestrator: performs auth logic ONLY
   coordinator: ALL UI updates in ONE place
   ```

---

## ✅ Verification Checklist

To verify single path data flow:

- [ ] Instagram auth failure → Button resets → Error shows ONCE
- [ ] Download failure → Error dialog shows ONCE (not + status bar error)
- [ ] Network error → Error dialog shows ONCE via message queue
- [ ] YouTube Music URL → Auto-downloads, no dialog
- [ ] SoundCloud premium → Error shows ONCE, not added to queue
- [ ] Any state change → Logged from component_state_manager ONLY

---

## 🔍 Debugging State Issues

If state gets "stuck":

1. Check `component_state_manager.log_current_states()`
2. Verify only ONE place is calling `set_[state_name]()`
3. Check all error paths have proper state reset
4. Ensure main thread scheduling is correct (use `root.after()`)

---

**Last Updated:** 2024-11-14  
**Maintainer:** Development Team  
**Status:** ✅ All duplicate flows removed