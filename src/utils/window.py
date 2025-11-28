import tkinter as tk
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


def close_loading_dialog(dialog: Optional[object], error_path: bool = False) -> None:
    """Close loading dialog with robust error handling - shared utility.

    Args:
        dialog: LoadingDialog instance to close (always has close/destroy/winfo_exists)
        error_path: Whether this is an error path (for logging)
    """
    path_suffix = " (error path)" if error_path else ""

    if not dialog:
        logger.warning(f"[WINDOW_UTILS] No loading dialog to close{path_suffix}")
        return

    logger.info(f"[WINDOW_UTILS] Attempting to close loading dialog{path_suffix}")

    # LoadingDialog always has these methods - no hasattr needed
    try:
        # Check if dialog still exists
        if not dialog.winfo_exists():
            logger.debug(
                f"[WINDOW_UTILS] Loading dialog already destroyed{path_suffix}"
            )
            return

        # Try close() first - this should release grab and destroy properly
        try:
            dialog.close()
            logger.info(
                f"[WINDOW_UTILS] Loading dialog closed via close(){path_suffix}"
            )
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
        logger.info(
            f"[WINDOW_UTILS] Loading dialog destroyed via destroy(){path_suffix}"
        )

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
    """Mixin class to provide window centering functionality."""

    def center_window(self) -> None:
        """Center the window on the screen or relative to parent."""
        if not isinstance(self, tk.Tk) and not isinstance(self, tk.Toplevel):
            raise TypeError(
                "WindowCenterMixin must be used with Tk or Toplevel windows"
            )

        # Update window geometry to get accurate dimensions
        try:
            self.update_idletasks()
        except Exception:
            # Handle CustomTkinter dimension event bug
            pass

        # Get window size
        try:
            window_width = self.winfo_width()
            window_height = self.winfo_height()
        except Exception:
            # If we can't get dimensions, use defaults from geometry string
            window_width = 700
            window_height = 900

        # Get screen dimensions
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        # If window has parent, center relative to parent
        if hasattr(self, "master") and self.master and self.master.winfo_exists():
            parent = self.master
            parent_x = parent.winfo_x()
            parent_y = parent.winfo_y()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()

            x = parent_x + (parent_width - window_width) // 2
            y = parent_y + (parent_height - window_height) // 2
        else:
            # Center on screen
            x = (screen_width - window_width) // 2
            y = (screen_height - window_height) // 2

        # Ensure window is fully visible
        x = max(0, min(x, screen_width - window_width))
        y = max(0, min(y, screen_height - window_height))

        # Set the position
        self.geometry(f"+{x}+{y}")
