from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast

from src.core.interfaces import (
    DynamicUIContextProtocol,
    HasCleanupProtocol,
    HasClearProtocol,
    HasCompletedDownloadsProtocol,
    HasEventCoordinatorProtocol,
    TkRootProtocol,
    UIContextProtocol,
)
from src.core.models import Download
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")
UIContextLike = UIContextProtocol | DynamicUIContextProtocol | HasEventCoordinatorProtocol
DownloadCallback = Callable[[str | Download], None]


def get_ui_context(ui_context: UIContextLike | None) -> UIContextProtocol | None:
    if ui_context is None:
        return None

    if isinstance(ui_context, UIContextProtocol):
        return ui_context

    if isinstance(ui_context, HasEventCoordinatorProtocol):
        return ui_context.event_coordinator

    required_attrs = ("root", "downloads", "platform_dialogs")
    if all(hasattr(ui_context, attr) for attr in required_attrs):
        return cast(UIContextProtocol, ui_context)

    logger.warning(
        "[TYPE_HELPER] ui_context is not a valid UIContextProtocol: %s", type(ui_context)
    )
    return None


def get_root(ui_context: UIContextLike | None) -> TkRootProtocol | None:
    if ctx := get_ui_context(ui_context):
        return ctx.root
    return None


def get_platform_callback(
    ui_context: UIContextLike | None, platform: str
) -> DownloadCallback | None:
    if not (ctx := get_ui_context(ui_context)):
        return None

    if platform in {"youtube", "spotify"} and hasattr(ctx, "downloads"):
        return cast(DownloadCallback, ctx.downloads.add_download)

    callback_map: dict[str, DownloadCallback] = {
        "youtube": cast(DownloadCallback, ctx.youtube_download),
        "twitter": cast(DownloadCallback, ctx.twitter_download),
        "instagram": cast(DownloadCallback, ctx.instagram_download),
        "pinterest": cast(DownloadCallback, ctx.pinterest_download),
        "spotify": cast(DownloadCallback, ctx.spotify_download),
        "tiktok": cast(DownloadCallback, ctx.tiktok_download),
        "radiojavan": cast(DownloadCallback, ctx.radiojavan_download),
        "soundcloud": cast(DownloadCallback, ctx.soundcloud_download),
        "generic": cast(DownloadCallback, ctx.generic_download),
    }

    return callback_map.get(platform)


def schedule_on_main_thread(
    root: TkRootProtocol | None,
    func: Callable[[], None],
    immediate: bool = False,
) -> None:
    if root is not None:
        try:
            root.after(0, func)
            return
        except Exception as e:
            logger.error(f"[TYPE_HELPER] Failed to schedule on main thread: {e}")
    if immediate:
        func()


def safe_cleanup(obj: HasCleanupProtocol | None) -> None:
    if obj is None:
        return
    try:
        obj.cleanup()
    except Exception as e:
        logger.error(f"[TYPE_HELPER] Cleanup failed for {type(obj).__name__}: {e}")


def safe_clear(obj: HasClearProtocol | None) -> None:
    if obj is None:
        return
    try:
        obj.clear()
    except Exception as e:
        logger.error(f"[TYPE_HELPER] Clear failed for {type(obj).__name__}: {e}")


def has_completed_downloads(download_list: HasCompletedDownloadsProtocol | None) -> bool:
    if download_list is None:
        return False
    try:
        return download_list.has_completed_downloads()
    except Exception:
        return False


def remove_completed_downloads(download_list: HasCompletedDownloadsProtocol | None) -> int:
    if download_list is None:
        return 0
    try:
        return download_list.remove_completed_downloads()
    except Exception as e:
        logger.error(f"[TYPE_HELPER] Failed to remove completed downloads: {e}")
        return 0


def safe_getattr(obj: object, attr: str, default: T) -> T:
    try:
        return getattr(obj, attr, default)
    except Exception:
        return default
