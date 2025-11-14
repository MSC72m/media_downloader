# Auto-Cleanup Completed Downloads Feature

## Overview

Implemented automatic and manual cleanup of completed downloads to keep the UI clean and organized. When new downloads are added, completed ones are automatically removed from the list.

---

## Problem Statement

**User Request:**
> "If another link is inserted and tried to be downloaded it should reset the completed ones and remove them from url entries and the ui"

**User Need:**
- Keep download list clean by removing completed items
- Automatic cleanup when adding new downloads
- Manual cleanup option for user control
- Better UX by not cluttering the interface with finished downloads

---

## Implementation

### 1. Download List Methods (`src/ui/components/download_list.py`)

#### `remove_completed_downloads() -> int`
```python
"""Remove all completed downloads from the list.

Returns:
    Number of downloads removed
"""
```

**Logic:**
1. Iterate through `_downloads` list
2. Find all downloads with `status == DownloadStatus.COMPLETED`
3. Collect their indices
4. Call `remove_downloads(indices)` to remove them
5. Refresh UI to reflect changes
6. Return count of removed items

**Example:**
```python
# Before
_downloads = [
    Download(name="Video1", status=COMPLETED),    # index 0
    Download(name="Video2", status=DOWNLOADING),  # index 1
    Download(name="Video3", status=COMPLETED),    # index 2
]

# After remove_completed_downloads()
_downloads = [
    Download(name="Video2", status=DOWNLOADING),  # index 0 (re-indexed)
]
# Returns: 2 (removed Video1 and Video3)
```

#### `has_completed_downloads() -> bool`
```python
"""Check if there are any completed downloads in the list."""
```

**Returns:**
- `True` if any download has `status == DownloadStatus.COMPLETED`
- `False` otherwise

---

### 2. Event Coordinator Helper Method (`src/services/events/coordinator.py`)

#### `_auto_clear_completed_downloads() -> int`
```python
"""Auto-clear completed downloads from the list.

Returns:
    Number of downloads cleared
"""
```

**Logic:**
1. **Check download_list exists:** Return 0 if None
2. **Check methods exist:** Verify `has_completed_downloads()` and `remove_completed_downloads()` are available
3. **Check if any completed:** Return 0 if no completed downloads
4. **Remove completed:** Call `remove_completed_downloads()`
5. **Update status bar:** Show "Cleared N completed download(s)" message
6. **Return count:** Number of items removed

**Key Features:**
- ✅ Safe: Checks for existence of download_list and methods
- ✅ Non-disruptive: Returns 0 if nothing to clear
- ✅ Logged: Info level logging for tracking
- ✅ User feedback: Updates status bar when items are cleared

**Called From:**
- `add_download()` - Automatically before adding new download
- `handle_clear_completed()` - Manual button click

---

### 3. Automatic Cleanup in `add_download()`

**Location:** `src/services/events/coordinator.py`

```python
def add_download(self, download: Download) -> bool:
    """Add a download to the system."""
    if not self.download_list:
        return False
    
    try:
        # Auto-clear completed downloads before adding new one
        self._auto_clear_completed_downloads()  # ← AUTOMATIC CLEANUP
        
        # Add new download
        download.set_event_bus(self.event_bus)
        self.download_list.add_download(download)
        self.update_status(f"Download added: {download.name}")
        return True
    except Exception as e:
        logger.error(f"Failed to add download: {e}", exc_info=True)
        return False
```

**Flow:**
```
User pastes new URL
    ↓
Handler detects platform (YouTube/Twitter/etc)
    ↓
EventCoordinator.handle_<platform>_download()
    ↓
EventCoordinator.add_download()
    ↓
_auto_clear_completed_downloads() ← AUTOMATIC CLEANUP
    ↓
download_list.add_download(new_download)
    ↓
UI shows only active + new downloads
```

---

### 4. Manual Cleanup via "Clear Completed" Button

#### UI Component (`src/ui/components/main_action_buttons.py`)

**Added Button:**
```python
self.clear_completed_button = ctk.CTkButton(
    self,
    text="Clear Completed",
    command=on_clear_completed,
    **self.button_style,
)
```

**Button States:**
- **Enabled:** When `has_items == True` (any downloads in list)
- **Disabled:** When list is empty or download is in progress

**Layout:**
```
[Remove Selected] [Clear All] [Clear Completed] [Download All] [Manage Files]
       ↑               ↑              ↑               ↑              ↑
  Selected items   All items    Completed only    Start all     File manager
```

#### Orchestrator Handler (`src/core/application/orchestrator.py`)

```python
def handle_clear_completed(self):
    """Handle clearing only completed downloads."""
    removed_count = self.event_coordinator._auto_clear_completed_downloads()
    logger.info(f"[ORCHESTRATOR] Cleared {removed_count} completed downloads")
```

**Wiring in main.py:**
```python
self.action_buttons = ActionButtonBar(
    self.main_frame,
    on_remove=self.orchestrator.handle_remove,
    on_clear=self.orchestrator.handle_clear,
    on_clear_completed=self.orchestrator.handle_clear_completed,  # ← NEW
    on_download=self.orchestrator.handle_download,
    on_manage_files=self.orchestrator.handle_manage_files,
)
```

---

## User Scenarios

### Scenario 1: Automatic Cleanup on New Download

**Steps:**
1. User downloads Video A → completes successfully
2. User downloads Video B → completes successfully
3. User pastes new URL for Video C
4. System automatically removes Video A and Video B
5. Only Video C appears in the download list

**Logs:**
```
[DOWNLOAD_LIST] Marking completed download for removal: Video A
[DOWNLOAD_LIST] Marking completed download for removal: Video B
[EVENT_COORDINATOR] Auto-cleared 2 completed downloads
[STATUS_BAR] Cleared 2 completed download(s)
[EVENT_COORDINATOR] Adding download to download_list
[STATUS_BAR] Download added: Video C
```

### Scenario 2: Manual Cleanup

**Steps:**
1. User has 5 downloads: 3 completed, 2 in progress
2. User clicks "Clear Completed" button
3. System removes only the 3 completed downloads
4. 2 in-progress downloads remain in the list

**Result:**
```
Before:
- Video1 | Completed
- Video2 | Downloading (45%)
- Video3 | Completed
- Video4 | Completed
- Video5 | Downloading (78%)

After clicking "Clear Completed":
- Video2 | Downloading (45%)
- Video5 | Downloading (78%)
```

### Scenario 3: No Completed Downloads

**Steps:**
1. User has 2 downloads: both in progress
2. User clicks "Clear Completed" button
3. Nothing happens (no completed downloads to remove)

**Logs:**
```
[DOWNLOAD_LIST] No completed downloads to remove
[EVENT_COORDINATOR] Auto-cleared 0 completed downloads
```

---

## Benefits

### User Experience
- ✅ **Cleaner UI**: Completed downloads don't clutter the interface
- ✅ **Automatic**: No manual intervention required
- ✅ **Flexible**: Manual button for user control
- ✅ **Intuitive**: Completed items are cleaned up naturally

### Performance
- ✅ **Efficient**: Only removes completed items, preserves active downloads
- ✅ **Non-blocking**: Quick operation, doesn't slow down new downloads
- ✅ **Scalable**: Works with any number of completed downloads

### Safety
- ✅ **Defensive**: Checks for existence of methods/objects before calling
- ✅ **Non-destructive**: Only removes completed downloads, never active ones
- ✅ **Logged**: All operations are logged for debugging

---

## Edge Cases Handled

### 1. No Download List
```python
if not self.download_list:
    return 0  # Safe return
```

### 2. Methods Not Available (Older Version)
```python
if not hasattr(self.download_list, "remove_completed_downloads"):
    return 0  # Graceful degradation
```

### 3. Empty List
```python
if not self.download_list.has_completed_downloads():
    return 0  # Nothing to do
```

### 4. All Downloads Completed
```python
# All downloads removed, list becomes empty
# UI shows empty state
# "Clear Completed" button becomes disabled
```

### 5. Mixed Status Downloads
```python
# COMPLETED removed
# DOWNLOADING preserved
# FAILED preserved (user may want to retry)
# PENDING preserved
```

---

## Configuration Options (Future Enhancement)

Could add user preferences:

```python
# Settings
AUTO_CLEAR_COMPLETED = True  # Auto-clear on new download
CLEAR_FAILED_DOWNLOADS = False  # Keep failed for review
CLEAR_AFTER_N_MINUTES = 60  # Auto-clear after 1 hour
SHOW_CONFIRMATION = True  # Ask before clearing
```

---

## Testing Checklist

- [x] Single completed download removed automatically
- [x] Multiple completed downloads removed automatically
- [x] Manual "Clear Completed" button works
- [x] In-progress downloads are NOT removed
- [x] Failed downloads are NOT removed
- [x] Pending downloads are NOT removed
- [x] Button states update correctly
- [x] Status bar shows feedback
- [x] Logs track operations
- [x] Empty list handled gracefully
- [x] No completed downloads handled gracefully

---

## Files Modified

### New Methods Added
1. **`src/ui/components/download_list.py`**
   - `remove_completed_downloads()` - Remove completed items
   - `has_completed_downloads()` - Check for completed items

2. **`src/services/events/coordinator.py`**
   - `_auto_clear_completed_downloads()` - Helper method for cleanup

3. **`src/core/application/orchestrator.py`**
   - `handle_clear_completed()` - Handler for button click

### Modified Components
1. **`src/ui/components/main_action_buttons.py`**
   - Added "Clear Completed" button
   - Updated grid layout (5 columns)
   - Added button state management

2. **`src/main.py`**
   - Wired `on_clear_completed` callback

3. **`src/services/events/coordinator.py`**
   - Auto-cleanup in `add_download()`

---

## Summary

✅ **Automatic cleanup** when new downloads are added  
✅ **Manual cleanup** via "Clear Completed" button  
✅ **Safe and defensive** with proper error handling  
✅ **User feedback** via status bar messages  
✅ **Preserves active downloads** (in-progress, failed, pending)  
✅ **Clean UX** without cluttering the interface  

The feature enhances the user experience by maintaining a clean, organized download list while preserving important information about active and failed downloads.