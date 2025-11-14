# 🚀 QUICK TEST INSTRUCTIONS

## Critical Tests - Do These First!

### ✅ Test 1: Instagram Button Reset (MOST CRITICAL)

1. **Launch the app**
2. **Click "Instagram Login"** button
3. **Watch the button** - it should change to "Logging in..."
4. **Immediately click "Cancel"** or click the X on the dialog
5. **VERIFY:** Button should **IMMEDIATELY** change back to "Instagram Login" (enabled)

**Expected:** ✅ Button resets instantly  
**If Failed:** ❌ Button stuck on "Logging in..." - STATE BUG STILL EXISTS

---

### ✅ Test 2: Instagram Auth Failure

1. Click "Instagram Login"
2. Enter **wrong username/password**
3. Click OK
4. Wait for auth to fail
5. **VERIFY:** 
   - Button resets to "Instagram Login"
   - Error dialog appears **ONCE** (not duplicated)

**Expected:** ✅ Button resets, error shows once  
**If Failed:** ❌ Button stuck or duplicate errors

---

### ✅ Test 3: App Startup (No Freeze)

1. **Close and relaunch** the app
2. **VERIFY:**
   - UI appears **immediately** (< 1 second)
   - No freeze or hang
   - Status bar shows "Initializing..." then "Checking network connectivity..."
   - After 2-3 seconds: "Ready - All services connected"

**Expected:** ✅ Instant UI, smooth startup  
**If Failed:** ❌ UI freezes for 2-3 seconds

---

### ✅ Test 4: YouTube Music Auto-Download

1. Paste this URL: `https://music.youtube.com/watch?v=dQw4w9WgXcQ`
2. Click "Add"
3. **VERIFY:**
   - **NO dialog appears** (important!)
   - Download **automatically added** to list
   - Name shows proper track title

**Expected:** ✅ Auto-adds, no dialog  
**If Failed:** ❌ Dialog shows or nothing added

---

### ✅ Test 5: SoundCloud Premium Rejection

1. Find a SoundCloud Go+ track (premium only)
2. Paste URL and click "Add"
3. **VERIFY:**
   - Error dialog appears: "SoundCloud Go+ Required"
   - Track **NOT added** to download list

**Expected:** ✅ Rejected with clear error  
**If Failed:** ❌ Added to queue or wrong error

---

## 🎯 What's Been Fixed

### Before ❌
- Instagram button stuck in "Logging in..." state
- UI froze for 2-3 seconds on startup
- Duplicate error messages everywhere
- No YouTube Music support
- No SoundCloud premium detection

### After ✅
- Instagram button **ALWAYS** resets (failsafe + primary path)
- UI starts **instantly** (network check in background)
- Errors shown **ONCE** via message queue
- YouTube Music **auto-downloads** as audio
- SoundCloud premium tracks **rejected immediately**

---

## 🔧 If Tests Fail

### Instagram Button Still Stuck?

Check logs for:
```
[COMPONENT_STATE_MANAGER] Instagram button initialized to FAILED
[PLATFORM_DIALOG_COORDINATOR] State set to FAILED
```

If missing, state manager not initializing.

### UI Still Freezes?

Check logs for:
```
[ORCHESTRATOR] Connectivity check started in background thread
```

If missing, threading not working.

### Errors Showing Twice?

Check logs - should only see:
```
[DOWNLOAD_COORDINATOR] Error dialog queued
```

NOT:
```
show_error() + _show_error_dialog()  <-- BAD, duplicate
```

---

## 📊 Quick Status Check

Run the app and check:

- [ ] Instagram button resets on cancel
- [ ] UI starts instantly (no freeze)
- [ ] YouTube Music auto-downloads
- [ ] SoundCloud premium rejected
- [ ] No duplicate errors

**All checked?** ✅ Ready to merge!  
**Any unchecked?** ❌ Report which test failed

---

## 🐛 Found Issues?

Report:
1. Which test failed
2. What you expected
3. What actually happened
4. Check logs in console

---

**Branch:** `feature/soundcloud-support-and-error-fixes`  
**Status:** Ready for testing  
**Priority:** Test Instagram button first!