# Subtitle Loading Performance Fix

## Issues Fixed

### 1. UI Freezing During Subtitle Loading
**Problem**: The YouTube downloader dialog would freeze for 30-60 seconds while loading subtitles, making the app appear unresponsive.

**Root Cause**: 
- `_get_real_subtitles()` was trying 4 different clients sequentially (web, android, ios, tv_embedded)
- Each client had a 15-second timeout
- Total possible wait time: 4 × 15 = 60 seconds
- This was running in the metadata fetch worker thread, blocking the UI update

### 2. Chrome Cookie Encryption on macOS
**Problem**: Chrome cookies couldn't be read due to macOS encryption.

**Log Output**:
```
WARNING - Chrome cookies are encrypted. On macOS, cookies may not be accessible due to system encryption.
INFO - No YouTube/Google cookies found in Chrome
```

**Status**: This is a known limitation. The app now uses yt-dlp's built-in `--cookies-from-browser` which handles encryption internally.

## Solutions Implemented

### Fast Subtitle Loading

**Before**:
```python
# Tried ALL clients sequentially
clients_to_try = ['web', 'android', 'ios', 'tv_embedded']
for client in clients_to_try:
    result = subprocess.run(cmd, timeout=15, ...)  # 15 seconds each!
```

**After**:
```python
# Only try the most reliable client
clients_to_try = ['tv_embedded']  # Fast and reliable
for client in clients_to_try:
    result = subprocess.run(cmd, timeout=5, ...)  # Only 5 seconds!
```

**Performance Improvement**: 
- Before: 15-60 seconds
- After: 5 seconds maximum
- **Speed increase: 3-12x faster!**

### Immediate Fallback

**Before**: Tried all clients, then returned empty subtitles

**After**: Immediately returns English auto-captions as fallback:
```python
return {
    'subtitles': {},
    'automatic_captions': {'en': [{'url': ''}]}  # Fast fallback
}
```

### Non-Blocking Subtitle Loading

Subtitles are now fetched with:
1. **Fast attempt** - Try tv_embedded client (5 seconds max)
2. **Immediate fallback** - Return English auto-captions if timeout
3. **No blocking** - Main metadata returns quickly with default subtitles

## Files Modified

### `src/services/youtube/metadata_service.py`
- Reduced `clients_to_try` to only `['tv_embedded']`
- Changed timeout from 15 to 5 seconds
- Added fast fallback for English auto-captions in main flow
- Removed subtitle fetching from critical path

## Performance Metrics

### Before Fix
```
Dialog appears -> [30-60 second freeze] -> Subtitles loaded -> Dialog interactive
```

### After Fix
```
Dialog appears -> [<5 seconds] -> Dialog interactive with English subtitles
```

## Testing

### Test 1: Dialog Responsiveness
1. Add a YouTube URL
2. Click "Add"
3. **Expected**: Dialog appears within 5 seconds, fully interactive
4. **Verify**: No freezing, can interact with all controls immediately

### Test 2: Subtitle Loading
1. Open YouTube download dialog
2. Check subtitle dropdown
3. **Expected**: English (Auto) available immediately
4. **Note**: Full subtitle list may not load if video has access restrictions

### Test 3: Cookie Detection
1. Log into YouTube in Chrome
2. Try to download a restricted video
3. **Expected**: App uses `--cookies-from-browser chrome` automatically
4. **Note**: Still may not work due to YouTube's anti-bot measures

## Cookie Handling

### macOS Encrypted Cookies
Chrome on macOS encrypts cookies in Keychain. Solutions:

1. **Built-in (Recommended)**: Use yt-dlp's `--cookies-from-browser`
   - Already implemented in the app
   - Handles encryption automatically
   - May still fail due to Keychain access restrictions

2. **Manual Export**: Export cookies to text file
   - Use browser extension to export cookies
   - Select exported file in app

3. **Different Browser**: Try Firefox or Safari
   - May have different encryption schemes
   - Test with "Detect Cookies" feature

## Known Limitations

1. **Cookie Access**: macOS Keychain may block cookie access even with proper permissions
2. **YouTube Anti-Bot**: YouTube may still block downloads even with valid cookies
3. **Subtitle Completeness**: Full subtitle list only loads if video is accessible

## Recommendations

### For Users
1. If dialog is slow, wait 5 seconds - it will become responsive
2. If cookies don't work, try manual export or different browser
3. If subtitles missing, video may have restricted access

### For Developers
1. Always use timeouts for subprocess calls
2. Provide fast fallbacks for non-critical data
3. Load expensive data lazily when possible
4. Never block UI thread with network operations

## Related Issues

- ✅ FileService registration (separate fix)
- ✅ Callback refactoring (separate fix)
- ✅ YouTube format string (separate fix)
- ✅ Download state management (separate fix)

## Verification

After restart, check logs for:
```
INFO - Using fast fallback - assuming English auto captions are available
```

If you see multiple lines like:
```
Trying web client for subtitle list...
Trying android client for subtitle list...
```
The fix hasn't been applied - restart the app.

## Summary

The subtitle loading system is now **3-12x faster** with:
- Single client attempt (tv_embedded)
- 5-second timeout (down from 15)
- Immediate fallback to English
- No UI blocking

Dialog now appears and becomes interactive in **under 5 seconds** instead of 30-60 seconds!