import customtkinter as ctk
import tkinter as tk
from typing import Callable

from src.core.enums import InstagramAuthStatus


class OptionsBar(ctk.CTkFrame):
    """Frame for download options and controls."""

    def __init__(
            self,
            master,
            on_instagram_login: Callable,
            on_quality_change: Callable = None,
            on_option_change: Callable = None
    ):
        super().__init__(master, fg_color="transparent")

        self.on_instagram_login = on_instagram_login
        self.on_quality_change = on_quality_change
        self.on_option_change = on_option_change
        
        # Current Instagram auth status
        self.instagram_status = InstagramAuthStatus.FAILED

        # Note: YouTube options (playlist, audio only, quality) have been moved to the YouTube-specific dialog
        # Instagram Login Button
        self.insta_login_button = ctk.CTkButton(
            self,
            text="Instagram Login",
            command=self._handle_instagram_login,
            font=("Roboto", 12)
        )
        self.insta_login_button.pack(side=tk.LEFT, padx=(0, 0))

    def _handle_instagram_login(self):
        """Handle Instagram login button state and callback."""
        self.set_instagram_status(InstagramAuthStatus.LOGGING_IN)
        self.on_instagram_login()

    def set_instagram_status(self, status: InstagramAuthStatus):
        """Update Instagram button state based on auth status."""
        self.instagram_status = status
        
        if status == InstagramAuthStatus.LOGGING_IN:
            self.insta_login_button.configure(
                text="Logging in...",
                state="disabled"
            )
        elif status == InstagramAuthStatus.AUTHENTICATED:
            self.insta_login_button.configure(
                text="Instagram: Logged In",
                state="disabled"
            )
        elif status == InstagramAuthStatus.FAILED:
            self.insta_login_button.configure(
                text="Instagram Login",
                state="normal"
            )

    # Keeping this for backward compatibility
    def set_instagram_authenticated(self, authenticated: bool):
        """Update Instagram button state - legacy method."""
        if authenticated:
            self.set_instagram_status(InstagramAuthStatus.AUTHENTICATED)
        else:
            self.set_instagram_status(InstagramAuthStatus.FAILED)

    # Note: YouTube options are now handled individually per download item in the YouTube dialog
