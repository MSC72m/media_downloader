import queue
import threading
import tkinter as tk
from collections.abc import Callable

import customtkinter as ctk

from src.core.enums import InstagramAuthStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class OptionsBar(ctk.CTkFrame):
    """Frame for download options and controls."""

    def __init__(self, master, on_instagram_login: Callable):
        super().__init__(master, fg_color="transparent")

        self.on_instagram_login = on_instagram_login

        # Current Instagram auth status
        self.instagram_status = InstagramAuthStatus.FAILED

        # Queue for thread-safe UI updates
        self._update_queue = queue.Queue()
        self._running = True
        self._root_window = self._get_root_window()

        # Note: YouTube-specific options are handled in the YouTube download dialog
        # Instagram Login Button
        self.insta_login_button = ctk.CTkButton(
            self,
            text="Instagram Login",
            command=self._handle_instagram_login,
            font=("Roboto", 12),
        )
        self.insta_login_button.pack(side=tk.LEFT, padx=(0, 0))

        # Start processing queue
        self._process_queue()

    def _get_root_window(self):
        """Get the root Tk window for scheduling."""
        try:
            widget = self
            while widget:
                master = getattr(widget, "master", None)
                if master is None:
                    return widget
                widget = master
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

    def _handle_instagram_login(self):
        """Handle Instagram login button click - just trigger callback.

        State management is handled by ComponentStateManager, not here.
        """
        logger.info("[OPTIONS_BAR] Instagram login button clicked")
        try:
            logger.info(f"[OPTIONS_BAR] Calling callback: {self.on_instagram_login}")
            self.on_instagram_login()
            logger.info("[OPTIONS_BAR] Callback completed")
        except Exception as e:
            logger.error(
                f"[OPTIONS_BAR] Error in Instagram login callback: {e}", exc_info=True
            )

    def set_instagram_status(self, status: InstagramAuthStatus):
        """Update Instagram button state based on auth status - thread-safe via queue.

        This is called by ComponentStateManager ONLY - no local state management.
        """
        logger.info(
            f"[OPTIONS_BAR] set_instagram_status called: {status}, thread={threading.current_thread().name}"
        )

        def _update():
            try:
                self.instagram_status = status

                # Map status to button configuration
                status_config = {
                    InstagramAuthStatus.LOGGING_IN: {
                        "text": "Logging in...",
                        "state": "disabled",
                    },
                    InstagramAuthStatus.AUTHENTICATED: {
                        "text": "Instagram: Logged In",
                        "state": "disabled",
                    },
                    InstagramAuthStatus.FAILED: {
                        "text": "Instagram Login",
                        "state": "normal",
                    },
                }

                config = status_config.get(status)
                if config:
                    logger.info(f"[OPTIONS_BAR] Configuring button with: {config}")
                    self.insta_login_button.configure(**config)
                    logger.info(
                        f"[OPTIONS_BAR] Button configured successfully to: {status}"
                    )
                else:
                    logger.warning(f"[OPTIONS_BAR] Unknown status: {status}")
            except Exception as e:
                logger.error(
                    f"[OPTIONS_BAR] Error updating Instagram status: {e}", exc_info=True
                )

        self._queue_update(_update)

    # Keeping this for backward compatibility
    def set_instagram_authenticated(self, authenticated: bool):
        """Update Instagram button state - legacy method."""
        if authenticated:
            self.set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
        else:
            self.set_instagram_status(InstagramAuthStatus.FAILED)

    def destroy(self):
        """Clean up resources."""
        self._running = False
        super().destroy()

    # Note: YouTube options are now handled individually per download item in the YouTube dialog
