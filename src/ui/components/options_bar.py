import customtkinter as ctk
import tkinter as tk
from typing import Callable

from src.models.enums.status import InstagramAuthStatus


class OptionsBar(ctk.CTkFrame):
    """Frame for download options and controls."""

    def __init__(
            self,
            master,
            on_instagram_login: Callable,
            on_quality_change: Callable,
            on_option_change: Callable
    ):
        super().__init__(master, fg_color="transparent")

        self.on_instagram_login = on_instagram_login
        self.on_quality_change = on_quality_change
        self.on_option_change = on_option_change
        
        # Current Instagram auth status
        self.instagram_status = InstagramAuthStatus.FAILED

        # YouTube Playlist Option
        self.playlist_var = ctk.StringVar(value="off")
        self.playlist_checkbox = ctk.CTkCheckBox(
            self,
            text="Download YouTube Playlist",
            variable=self.playlist_var,
            onvalue="on",
            offvalue="off",
            font=("Roboto", 12),
            command=lambda: self.on_option_change("playlist", self.playlist_var.get() == "on")
        )
        self.playlist_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        # Audio Only Option
        self.audio_var = ctk.StringVar(value="off")
        self.audio_checkbox = ctk.CTkCheckBox(
            self,
            text="Audio Only",
            variable=self.audio_var,
            onvalue="on",
            offvalue="off",
            font=("Roboto", 12),
            command=lambda: self.on_option_change("audio_only", self.audio_var.get() == "on")
        )
        self.audio_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        # Quality Selection
        self.quality_var = ctk.StringVar(value="720p")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self,
            values=["360p", "480p", "720p", "1080p"],
            variable=self.quality_var,
            font=("Roboto", 12),
            command=self.on_quality_change
        )
        self.quality_dropdown.pack(side=tk.LEFT)

        # Instagram Login Button
        self.insta_login_button = ctk.CTkButton(
            self,
            text="Instagram Login",
            command=self._handle_instagram_login,
            font=("Roboto", 12)
        )
        self.insta_login_button.pack(side=tk.LEFT, padx=(20, 0))

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

    def get_youtube_options(self) -> dict:
        """Get current YouTube download options."""
        return {
            'quality': self.quality_var.get(),
            'playlist': self.playlist_var.get() == "on",
            'audio_only': self.audio_var.get() == "on"
        }
