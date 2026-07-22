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

    def apply_min_size(self, min_width: int, min_height: int, screen_factor: float = 0.9) -> None:
        """Set ``minsize`` clamped so it never exceeds the usable screen.

        Tk enforces ``minsize`` over any geometry request, so a minimum larger
        than the display makes the window impossible to fit and pushes its
        lower content (e.g. the Download button) off-screen. Always clamp.
        """
        with contextlib.suppress(Exception):
            screen_w = self.winfo_screenwidth()  # type: ignore[attr-defined]
            screen_h = self.winfo_screenheight()  # type: ignore[attr-defined]
            self.minsize(  # type: ignore[attr-defined]
                min(min_width, int(screen_w * screen_factor)),
                min(min_height, int(screen_h * screen_factor)),
            )

    def apply_screen_aware_geometry(
        self,
        preferred_width: int,
        preferred_height: int,
        min_width: int,
        min_height: int,
        screen_factor: float = 0.9,
    ) -> None:
        """Size, constrain and centre a window so it always fits the display.

        Single source of truth for dialog sizing. Sets a screen-clamped
        ``minsize`` FIRST, then applies a preferred geometry (also clamped to
        ``screen_factor`` of the screen) and centres. Callers must not hand-roll
        ``min(fixed, screen*factor)`` maths — use this instead.
        """
        if not isinstance(self, tk.Tk | tk.Toplevel):
            raise TypeError("WindowCenterMixin must be used with Tk or Toplevel windows")

        with contextlib.suppress(Exception):
            self.update_idletasks()

        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        max_w = int(screen_w * screen_factor)
        max_h = int(screen_h * screen_factor)

        self.apply_min_size(min_width, min_height, screen_factor)

        width = max(min(preferred_width, max_w), min(min_width, max_w))
        height = max(min(preferred_height, max_h), min(min_height, max_h))
        # center_window re-clamps to screen and positions the window.
        self.center_window(width, height)
