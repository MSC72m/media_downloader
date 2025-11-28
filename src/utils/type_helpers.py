from typing import Any, Callable, Optional, TypeVar
from src.core.interfaces import (
    HasCleanupProtocol,
    HasClearProtocol,
    HasCompletedDownloadsProtocol,
    TkRootProtocol,
    UIContextProtocol,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


def get_ui_context(ui_context: Any) -> Optional[UIContextProtocol]:
    """Safely extract UI context (orchestrator or event coordinator).

    Args:
        ui_context: Either an orchestrator or event coordinator

    Returns:
        UIContextProtocol if valid, None otherwise
    """
    # Check if it has the required attributes (root and download methods)
    # Note: container attribute is optional as EventCoordinator might not have it
    if hasattr(ui_context, "root"):
        # Check for explicit methods or dynamic dispatch capability
        if hasattr(ui_context, "platform_download") or hasattr(
            ui_context, "youtube_download"
        ):
            return ui_context

        # Check if it has container (Orchestrator case) which might delegate
        if hasattr(ui_context, "container"):
            # If orchestrator doesn't have download methods, checking event_coordinator
            if hasattr(ui_context, "event_coordinator"):
                return ui_context.event_coordinator
            return ui_context

    # Check if it has an event_coordinator attribute (Orchestrator wrapper case)
    if hasattr(ui_context, "event_coordinator"):
        return ui_context.event_coordinator

    logger.warning(
        f"[TYPE_HELPER] ui_context is not a valid UIContextProtocol: {type(ui_context)}"
    )
    return None


def get_root(ui_context: Any) -> Optional[TkRootProtocol]:
    """Safely extract Tk root from UI context.

    Args:
        ui_context: UI context object

    Returns:
        TkRootProtocol if available, None otherwise
    """
    ctx = get_ui_context(ui_context)
    if ctx and hasattr(ctx, "root"):
        return ctx.root
    return None


def get_platform_callback(
    ui_context: Any, platform: str
) -> Optional[Callable[[str], None]]:
    """Get platform-specific download callback.

    Args:
        ui_context: UI context object
        platform: Platform name (youtube, twitter, instagram, pinterest, generic)

    Returns:
        Callback function if available, None otherwise
    """
    ctx = get_ui_context(ui_context)
    if not ctx:
        return None

    callback_map = {
        "youtube": ctx.youtube_download,
        "twitter": ctx.twitter_download,
        "instagram": ctx.instagram_download,
        "pinterest": ctx.pinterest_download,
        "generic": ctx.generic_download,
    }

    return callback_map.get(platform)


def schedule_on_main_thread(
    root: Any, func: Callable[[], Any], immediate: bool = False
) -> None:
    """Schedule function on main thread if possible, otherwise execute immediately.

    Args:
        root: Tk root window
        func: Function to execute
        immediate: If True and root doesn't have after, execute immediately
    """
    if isinstance(root, TkRootProtocol):
        try:
            root.after(0, func)
        except Exception as e:
            logger.error(f"[TYPE_HELPER] Failed to schedule on main thread: {e}")
            if immediate:
                func()
    elif immediate:
        func()


def safe_cleanup(obj: Any) -> None:
    """Safely call cleanup method if it exists.

    Args:
        obj: Object to clean up
    """
    if isinstance(obj, HasCleanupProtocol):
        try:
            obj.cleanup()
        except Exception as e:
            logger.error(f"[TYPE_HELPER] Cleanup failed for {type(obj).__name__}: {e}")


def safe_clear(obj: Any) -> None:
    """Safely call clear method if it exists.

    Args:
        obj: Object to clear
    """
    if isinstance(obj, HasClearProtocol):
        try:
            obj.clear()
        except Exception as e:
            logger.error(f"[TYPE_HELPER] Clear failed for {type(obj).__name__}: {e}")


def has_completed_downloads(download_list: Any) -> bool:
    """Check if download list has completed downloads.

    Args:
        download_list: Download list component

    Returns:
        True if has completed downloads, False otherwise
    """
    if isinstance(download_list, HasCompletedDownloadsProtocol):
        try:
            return download_list.has_completed_downloads()
        except Exception:
            pass
    return False


def remove_completed_downloads(download_list: Any) -> int:
    """Remove completed downloads from list.

    Args:
        download_list: Download list component

    Returns:
        Number of downloads removed
    """
    if isinstance(download_list, HasCompletedDownloadsProtocol):
        try:
            return download_list.remove_completed_downloads()
        except Exception as e:
            logger.error(f"[TYPE_HELPER] Failed to remove completed downloads: {e}")
    return 0


def safe_getattr(obj: Any, attr: str, default: T) -> T:
    """Type-safe getattr with default value.

    Args:
        obj: Object to get attribute from
        attr: Attribute name
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default
