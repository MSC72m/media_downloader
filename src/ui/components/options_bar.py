import queue
from typing import TYPE_CHECKING, Optional

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import get_theme_manager
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.ui.utils.theme_manager import ThemeManager

logger = get_logger(__name__)


class OptionsBar(ctk.CTkFrame):
    """Frame for download options and controls."""

    def __init__(self, master, theme_manager: Optional["ThemeManager"] = None):
        super().__init__(master, fg_color="transparent")

        # Queue for thread-safe UI updates
        self._update_queue = queue.Queue()
        self._running = True
        self._root_window = self._get_root_window()

        # Subscribe to theme manager - injected with default
        self._theme_manager = theme_manager or get_theme_manager(self._root_window)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        # Note: YouTube-specific options are handled in the YouTube download dialog
        # Instagram authentication is now handled automatically when Instagram URLs are detected
        # OptionsBar is currently empty - will be shown when content is added

        # Start processing queue
        self._process_queue()

    def _on_theme_changed(self, appearance, color):
        """Handle theme change event."""
        pass

    def _get_root_window(self):
        """Get the root Tk window for scheduling."""
        try:
            # Try to get the actual root window
            return self.winfo_toplevel()
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error getting root window: {e}")
            return self

    def _process_queue(self):
        """Process queued UI updates on main thread."""
        if not self._running:
            return

        try:
            # Process all pending updates
            while not self._update_queue.empty():
                try:
                    update_func = self._update_queue.get_nowait()
                    update_func()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(
                        f"[OPTIONS_BAR] Error processing update: {e}", exc_info=True
                    )
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error in _process_queue: {e}", exc_info=True)

        # Schedule next queue check
        if self._running and self._root_window:
            try:
                self._root_window.after(50, self._process_queue)
            except Exception as e:
                logger.error(f"[OPTIONS_BAR] Error scheduling next queue check: {e}")

    def _queue_update(self, update_func):
        """Queue an update to be processed on main thread."""
        try:
            self._update_queue.put(update_func)
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error queuing update: {e}", exc_info=True)

    def destroy(self):
        """Clean up resources."""
        self._running = False
        super().destroy()

    # Note: YouTube options are now handled individually per download item in the YouTube dialog
    # Note: Instagram authentication is now handled automatically when Instagram URLs are detected
