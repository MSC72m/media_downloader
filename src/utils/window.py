import contextlib
import tkinter as tk
from typing import Protocol, runtime_checkable

from src.utils.logger import get_logger

logger = get_logger(__name__)


@runtime_checkable
class _LoadingDialogProtocol(Protocol):
    def winfo_exists(self) -> bool: ...

    def close(self) -> None: ...

    def update_idletasks(self) -> None: ...

    def destroy(self) -> None: ...


def close_loading_dialog(dialog: object | None, error_path: bool = False) -> None:
    """Close loading dialog with robust error handling - shared utility.

    Args:
        dialog: LoadingDialog instance to close (always has close/destroy/winfo_exists)
        error_path: Whether this is an error path (for logging)
    """
    path_suffix = " (error path)" if error_path else ""

    if not dialog or not isinstance(dialog, _LoadingDialogProtocol):
        logger.warning(f"[WINDOW_UTILS] No loading dialog to close{path_suffix}")
        return

    logger.info(f"[WINDOW_UTILS] Attempting to close loading dialog{path_suffix}")

    # LoadingDialog always has these methods - no hasattr needed
    try:
        # Check if dialog still exists
        if not dialog.winfo_exists():
            logger.debug(f"[WINDOW_UTILS] Loading dialog already destroyed{path_suffix}")
            return

        # Try close() first - this should release grab and destroy properly
        try:
            dialog.close()
            logger.info(f"[WINDOW_UTILS] Loading dialog closed via close(){path_suffix}")
            # Give it a moment to process
            dialog.update_idletasks()
            # Verify it's actually closed
            if not dialog.winfo_exists():
                return
        except Exception as close_error:
            logger.warning(f"[WINDOW_UTILS] close() failed{path_suffix}: {close_error}")
            # Fall through to destroy()

        # Fallback to destroy() if close() failed
        dialog.destroy()
        logger.info(f"[WINDOW_UTILS] Loading dialog destroyed via destroy(){path_suffix}")

    except Exception as e:
        logger.error(
            f"[WINDOW_UTILS] Error closing loading dialog{path_suffix}: {e}",
            exc_info=True,
        )
        # Ensure cleanup in exception handler
        try:
            if dialog.winfo_exists():
                dialog.destroy()
                logger.info(
                    f"[WINDOW_UTILS] Loading dialog force-destroyed in exception handler{path_suffix}"
                )
        except Exception:
            pass


class WindowCenterMixin:
    """Mixin class to provide window centering and screen-aware sizing."""

    def center_window(self, width: int | None = None, height: int | None = None) -> None:
        """Center the window on the screen or relative to parent.

        If width/height are provided, the window is resized to fit within
        90% of the screen (capped at the requested size) before centering.
        """
        if not isinstance(self, tk.Tk) and not isinstance(self, tk.Toplevel):
            raise TypeError("WindowCenterMixin must be used with Tk or Toplevel windows")

        with contextlib.suppress(Exception):
            self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # Clamp requested size to 90% of screen
        max_w = int(screen_width * 0.9)
        max_h = int(screen_height * 0.9)

        window_width = min(width, max_w) if width is not None else self.winfo_width() or 700
        window_height = min(height, max_h) if height is not None else self.winfo_height() or 900

        # Apply clamped geometry
        self.geometry(f"{window_width}x{window_height}")

        # Re-read after geometry set
        window_width = self.winfo_width()
        window_height = self.winfo_height()

        # Center relative to parent or screen
        if hasattr(self, "master") and self.master and self.master.winfo_exists():
            parent = self.master
            x = parent.winfo_x() + (parent.winfo_width() - window_width) // 2
            y = parent.winfo_y() + (parent.winfo_height() - window_height) // 2
        else:
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

        # Ensure fully visible
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        self.geometry(f"+{x}+{y}")
