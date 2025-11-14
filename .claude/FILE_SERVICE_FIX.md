# FileService Registration Fix

## Issue
Download handler was failing with error:
```
AttributeError: 'NoneType' object has no attribute 'sanitize_filename'
```

## Root Cause
The `file_service` was never registered in the dependency injection container, so when `download_handler` tried to get it via `self.container.get("file_service")`, it returned `None`.

## Fix Applied

### 1. Registered FileService in Container
**File**: `src/core/application/orchestrator.py`

Added FileService to the service factory registrations:

```python
# In _initialize_services() method
self.container.register_factory("file_service", lambda: FileService())
```

Added import:
```python
from ...services.file import FileService
```

### 2. Added Fallback Sanitization
**File**: `src/handlers/download_handler.py`

Added defensive check with fallback in `_prepare_download_path()`:

```python
# Get file service with fallback
file_service = self.container.get("file_service")

if file_service:
    base_name = file_service.sanitize_filename(download.name or "download")
else:
    # Fallback sanitization if file_service not available
    logger.warning(
        "[DOWNLOAD_HANDLER] file_service not available, using fallback sanitization"
    )
    base_name = download.name or "download"
    # Remove invalid filename characters
    base_name = re.sub(r'[<>:"/\\|?*]', "_", base_name)
    base_name = base_name.strip()[:200]  # Limit length
```

## Why This Happened
The FileService was imported and used in other downloaders (TwitterDownloader, InstagramDownloader, PinterestDownloader) by creating new instances directly:
```python
file_service = FileService()
```

But the refactored DownloadHandler uses dependency injection via the container, expecting all services to be pre-registered. The FileService was simply never added to the container registration list.

## Testing
After restart, downloads should:
1. Successfully sanitize filenames using FileService
2. If FileService somehow unavailable, fallback to regex-based sanitization
3. No more `NoneType` errors

## Prevention
When refactoring code to use dependency injection:
1. Always register all services in the container
2. Add defensive checks for critical services
3. Provide fallback implementations where possible
4. Test that container has all required services at startup

## Related Services
All services now registered in container:
- ✅ `file_service` - NEW
- ✅ `cookie_manager`
- ✅ `service_factory`
- ✅ `download_service`
- ✅ `cookie_handler`
- ✅ `auth_handler`
- ✅ `download_handler`
- ✅ `network_checker`
- ✅ `service_detector`
- ✅ `service_controller`
- ✅ `event_coordinator`
