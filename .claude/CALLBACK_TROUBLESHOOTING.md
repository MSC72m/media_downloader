# Callback Troubleshooting Guide

## Quick Diagnostics

### Issue: Download Status Not Updating

**Symptoms**:
- Download stays in "Downloading" state forever
- UI shows "Downloading (0.0%)" even after failure
- Buttons remain disabled after download

**Check**:
1. Look for these log messages:
   ```
   [EVENT_COORDINATOR] Completion callback: success=False
   [EVENT_COORDINATOR] Scheduling completion UI update
   [EVENT_COORDINATOR] _handle_completion_ui CALLED
   [EVENT_COORDINATOR] Refreshing download list
   ```

2. If missing `_handle_completion_ui CALLED`:
   - Window might have closed before callback
   - `root.after()` might not be available
   - Exception in callback scheduling

**Fix**:
```python
# Ensure window exists
if not hasattr(self.root, "after"):
    logger.error("root.after not available")
    return

# Check window is still valid
try:
    self.root.winfo_exists()
except tk.TclError:
    logger.warning("Window closed")
    return
```

### Issue: Download Object Status Not Updated

**Symptoms**:
- Completion callback fires but status still "Downloading"
- Database shows wrong status
- Retry doesn't work because status not marked failed

**Check**:
1. Look for these log messages:
   ```
   [DOWNLOAD_HANDLER] Failed to download: VideoName
   ```
   Should be followed by:
   ```python
   download.mark_failed(msg)  # Sets status to FAILED
   ```

2. If missing, the download status update is missing

**Fix**:
```python
# In download_handler.py _download_worker
if not success:
    # MUST update status before callback
    download.mark_failed(f"Failed to download: {download.name}")
    if completion_callback:
        completion_callback(False, msg)
    return

# On success
download.update_progress(100.0)  # Sets status to COMPLETED
if completion_callback:
    completion_callback(True, f"Downloaded: {download.name}")
```

### Issue: Progress Callback Not Firing

**Symptoms**:
- Download starts but no progress updates
- Progress bar stuck at 0%
- No progress logs

**Check**:
1. Look for progress wrapper logs:
   ```
   [DOWNLOAD_HANDLER] Progress: VideoName - 25.0% - 1234.56 bytes/s
   ```

2. If missing, check:
   - Is progress_callback passed to downloader?
   - Is downloader calling the callback?
   - Is progress_wrapper correctly wrapping the callback?

**Fix**:
```python
# In download_handler.py
def _create_progress_wrapper(self, download, progress_callback):
    def progress_wrapper(progress, speed):
        logger.info(f"Progress: {download.name} - {progress:.1f}%")
        if progress_callback:  # Always check if callback exists
            progress_callback(download, int(progress))
    return progress_wrapper
```

### Issue: Nested Callbacks Not Working

**Symptoms**:
- Outer callback works, inner doesn't
- Some downloads update, others don't
- Race conditions

**Check**:
1. Lambda capture issue:
   ```python
   # WRONG - will capture last value
   for d in downloads:
       callback = lambda: process(d)
   
   # CORRECT - capture value immediately
   for d in downloads:
       callback = lambda d=d: process(d)
   ```

**Fix**:
```python
# Use default arguments in lambda
self.root.after(0, lambda d=download: self._update_ui(d))

# Or use functools.partial
from functools import partial
self.root.after(0, partial(self._update_ui, download))
```

## Common Error Patterns

### Pattern 1: Missing Early Return
```python
# BAD - callback still invoked even after error
if error:
    logger.error("Error occurred")
    download.mark_failed("Error")
completion_callback(True, "Success")  # WRONG!

# GOOD - early return prevents further execution
if error:
    logger.error("Error occurred")
    download.mark_failed("Error")
    completion_callback(False, "Error")
    return  # STOP HERE

completion_callback(True, "Success")
```

### Pattern 2: Callback Before State Update
```python
# BAD - callback fires before state updated
completion_callback(False, "Failed")
download.mark_failed("Failed")  # Too late!

# GOOD - update state first
download.mark_failed("Failed")
completion_callback(False, "Failed")
```

### Pattern 3: Swallowed Exceptions
```python
# BAD - error hidden
try:
    risky_operation()
    callback(True, "Done")
except Exception:
    pass  # Silently fails!

# GOOD - log and handle
try:
    risky_operation()
    callback(True, "Done")
except Exception as e:
    logger.error(f"Error: {e}", exc_info=True)
    callback(False, str(e))
```

### Pattern 4: Forgetting Thread Context
```python
# BAD - UI update from worker thread
def worker_thread():
    download_file()
    self.label.configure(text="Done")  # CRASH on macOS!

# GOOD - schedule on main thread
def worker_thread():
    download_file()
    self.root.after(0, lambda: self.label.configure(text="Done"))
```

## Debugging Checklist

### When Download Fails But UI Doesn't Update

- [ ] Check if `download.mark_failed()` is called before completion callback
- [ ] Check if completion callback is invoked
- [ ] Check if `root.after()` scheduling succeeds
- [ ] Check if `_handle_completion_ui()` executes
- [ ] Check if `_refresh_download_list()` is called
- [ ] Check if download list has the download object
- [ ] Check if window is still open

### When Progress Doesn't Update

- [ ] Check if progress callback passed to downloader
- [ ] Check if downloader calls progress callback
- [ ] Check if progress_wrapper is created
- [ ] Check if coordinator's on_progress receives calls
- [ ] Check if `_update_progress_ui()` is scheduled
- [ ] Check if `_update_progress_ui()` executes
- [ ] Check if download_list widget exists

### When Callbacks Fire Multiple Times

- [ ] Check for duplicate callback registrations
- [ ] Check if download started multiple times
- [ ] Check for callback in loop without proper capture
- [ ] Check thread cleanup (threads might not be stopping)

## Log Analysis

### Successful Download Flow
```
[DOWNLOAD_HANDLER] Worker started for: VideoName
[DOWNLOAD_HANDLER] Detected service type: youtube
[DOWNLOAD_HANDLER] Created YouTubeDownloader
[DOWNLOAD_HANDLER] Starting download...
[DOWNLOAD_HANDLER] Progress: VideoName - 25.0% - 1234.56 bytes/s
[EVENT_COORDINATOR] Progress callback: VideoName - 25%
[EVENT_COORDINATOR] _update_progress_ui called for VideoName
[DOWNLOAD_HANDLER] Progress: VideoName - 50.0% - 1234.56 bytes/s
[DOWNLOAD_HANDLER] Progress: VideoName - 75.0% - 1234.56 bytes/s
[DOWNLOAD_HANDLER] Progress: VideoName - 100.0% - 1234.56 bytes/s
[DOWNLOAD_HANDLER] Download completed with success: True
[DOWNLOAD_HANDLER] Successfully downloaded: VideoName
[EVENT_COORDINATOR] Completion callback: success=True
[EVENT_COORDINATOR] Scheduling completion UI update
[EVENT_COORDINATOR] _handle_completion_ui CALLED: success=True
[EVENT_COORDINATOR] Re-enabling action buttons
[EVENT_COORDINATOR] Refreshing download list
[EVENT_COORDINATOR] Refreshing 1 downloads
[EVENT_COORDINATOR] Download list refreshed successfully
[EVENT_COORDINATOR] Success status displayed
[EVENT_COORDINATOR] _handle_completion_ui COMPLETED
```

### Failed Download Flow
```
[DOWNLOAD_HANDLER] Worker started for: VideoName
[DOWNLOAD_HANDLER] Starting download...
[youtube] Downloading from YouTube: https://...
ERROR: [youtube] Requested format is not available
[DOWNLOAD_HANDLER] Download completed with success: False
[DOWNLOAD_HANDLER] Failed to download: VideoName
[EVENT_COORDINATOR] Completion callback: success=False, message=Failed...
[EVENT_COORDINATOR] Scheduling completion UI update
[EVENT_COORDINATOR] _handle_completion_ui CALLED: success=False
[EVENT_COORDINATOR] Re-enabling action buttons
[EVENT_COORDINATOR] Refreshing download list
[EVENT_COORDINATOR] Got 1 downloads to refresh
[EVENT_COORDINATOR] Download list refreshed successfully
[EVENT_COORDINATOR] Failure status displayed
[EVENT_COORDINATOR] _handle_completion_ui COMPLETED
```

## Emergency Fixes

### Force UI Refresh
```python
# If UI not updating, manually refresh
if self.download_list:
    downloads = self.download_list.get_downloads()
    self.download_list.refresh_items(downloads)
```

### Force Button Re-enable
```python
# If buttons stuck disabled
if self.action_buttons:
    self.action_buttons.set_enabled(True)
```

### Force Status Update
```python
# If download stuck in wrong state
download.status = DownloadStatus.FAILED
download.error_message = "Forced failure"
download.completed_at = datetime.now()
```

### Clear Python Cache
```bash
# If changes not taking effect
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
find . -name "*.pyc" -delete 2>/dev/null
```

## Prevention

### Always Do This
1. **Update state before callbacks**
   ```python
   download.mark_failed("Error")  # First
   callback(False, "Error")        # Then
   ```

2. **Use early returns**
   ```python
   if not valid:
       return
   # Continue only if valid
   ```

3. **Log at decision points**
   ```python
   logger.info("About to call callback")
   callback(success, message)
   logger.info("Callback called successfully")
   ```

4. **Validate before scheduling**
   ```python
   if not hasattr(self.root, "after"):
       return
   try:
       self.root.winfo_exists()
   except tk.TclError:
       return
   ```

### Never Do This
1. **Don't skip state updates**
   ```python
   # NO!
   callback(False, "Error")
   # Where's download.mark_failed()?
   ```

2. **Don't ignore exceptions**
   ```python
   # NO!
   try:
       callback()
   except:
       pass  # Silent failure!
   ```

3. **Don't update UI from worker threads**
   ```python
   # NO!
   def worker():
       self.label.configure(text="Done")  # CRASH!
   ```

4. **Don't create circular callbacks**
   ```python
   # NO!
   def callback_a():
       callback_b()
   
   def callback_b():
       callback_a()  # Infinite loop!
   ```

## Getting Help

If issue persists after following this guide:

1. **Collect logs** - Run with full logging enabled
2. **Check thread IDs** - Ensure UI updates on main thread
3. **Verify window state** - Window might be closed/destroyed
4. **Test in isolation** - Create minimal reproduction
5. **Check Python version** - Some features require Python 3.8+

For specific issues, see:
- `CALLBACK_REFACTORING.md` - Complete refactoring details
- `DIALOG_THREADING_FIXES.md` - Thread-safety patterns
- GitHub Issues - Known problems and solutions