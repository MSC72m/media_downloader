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

        # Note: YouTube-specific options are handled in the YouTube download dialog
        # Instagram Login Button
        self.insta_login_button = ctk.CTkButton(
            self,
            text="Instagram Login",
            command=self._handle_instagram_login,
            font=("Roboto", 12),
        )
        self.insta_login_button.pack(side=tk.LEFT, padx=(0, 0))

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
        """Update Instagram button state based on auth status.

        This is called by ComponentStateManager ONLY - no local state management.
        """
        logger.info(f"[OPTIONS_BAR] Setting Instagram status to: {status}")
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
            InstagramAuthStatus.FAILED: {"text": "Instagram Login", "state": "normal"},
        }

        config = status_config.get(status)
        if config:
            logger.info(f"[OPTIONS_BAR] Configuring button with: {config}")
            self.insta_login_button.configure(**config)
        else:
            logger.warning(f"[OPTIONS_BAR] Unknown status: {status}")

    # Keeping this for backward compatibility
    def set_instagram_authenticated(self, authenticated: bool):
        """Update Instagram button state - legacy method."""
        if authenticated:
            self.set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
        else:
            self.set_instagram_status(InstagramAuthStatus.FAILED)

    # Note: YouTube options are now handled individually per download item in the YouTube dialog
