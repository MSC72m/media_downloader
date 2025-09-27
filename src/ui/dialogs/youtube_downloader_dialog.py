"""Dialog for YouTube video downloads."""

import customtkinter as ctk
from typing import Optional, Callable, Dict, Any
import json
import os
from pathlib import Path
from ...interfaces.cookie_detection import BrowserType
from ...utils.window import WindowCenterMixin


class YouTubeDownloaderDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Enhanced dialog for downloading YouTube videos with comprehensive options."""

    # Class variables for cookie caching
    _cached_cookies = {}
    _selected_browser = None

    def __init__(
        self,
        parent,
        url: str,
        cookie_handler,
        on_download: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
    ):
        super().__init__(parent)

        self.url = url
        self.cookie_handler = cookie_handler
        self.on_download = on_download
        self.browser_buttons = {}

        # Configure window
        self.title("YouTube Video Downloader")
        self.geometry("700x800")
        self.resizable(True, True)
        self.minsize(600, 600)

        # Make window modal
        self.transient(parent)
        self.grab_set()

        # Center the window using mixin
        self.center_window()

        self._create_widgets()
        self._load_cached_selections()

    def _create_widgets(self):
        """Create dialog widgets with scrolling support."""
        # Create scrollable frame
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Main container
        main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ctk.CTkLabel(
            main_frame,
            text="YouTube Video Downloader",
            font=("Roboto", 24, "bold")
        )
        title_label.pack(pady=(0, 20))

        # URL display
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.pack(fill="x", pady=(0, 20))

        url_label = ctk.CTkLabel(
            url_frame,
            text="URL:",
            font=("Roboto", 12, "bold")
        )
        url_label.pack(anchor="w", padx=(10, 5))

        url_display = ctk.CTkEntry(
            url_frame,
            font=("Roboto", 10)
        )
        url_display.insert(0, self.url)
        url_display.configure(state="disabled")
        url_display.pack(fill="x", padx=10, pady=(0, 10))

        # Video name input
        name_frame = ctk.CTkFrame(main_frame)
        name_frame.pack(fill="x", pady=(0, 20))

        name_label = ctk.CTkLabel(
            name_frame,
            text="Video/Playlist Name:",
            font=("Roboto", 12, "bold")
        )
        name_label.pack(anchor="w", padx=(10, 5))

        self.name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Enter name for this download",
            font=("Roboto", 12)
        )
        self.name_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Cookie selection
        cookie_frame = ctk.CTkFrame(main_frame)
        cookie_frame.pack(fill="x", pady=(0, 20))

        cookie_label = ctk.CTkLabel(
            cookie_frame,
            text="Browser Cookies (to bypass YouTube restrictions):",
            font=("Roboto", 12, "bold")
        )
        cookie_label.pack(anchor="w", padx=(10, 5))

        cookie_info_label = ctk.CTkLabel(
            cookie_frame,
            text="Select a browser to use its cookies for age-restricted or region-locked content",
            font=("Roboto", 10),
            text_color="gray"
        )
        cookie_info_label.pack(anchor="w", padx=(10, 0))

        # Browser buttons
        browser_button_frame = ctk.CTkFrame(cookie_frame, fg_color="transparent")
        browser_button_frame.pack(fill="x", padx=10, pady=10)

        browser_info = {
            BrowserType.CHROME: ("Chrome", "#4285F4", "#FFD700"),
            BrowserType.FIREFOX: ("Firefox", "#FF9500", "#FFD700"),
            BrowserType.SAFARI: ("Safari", "#007AFF", "#FFD700")
        }

        for browser, (name, color, selected_color) in browser_info.items():
            button = ctk.CTkButton(
                browser_button_frame,
                text=f"Use {name}",
                command=lambda b=browser: self._handle_browser_select(b),
                width=140,
                height=35,
                font=("Roboto", 11, "bold"),
                fg_color=color,
                hover_color=self._darken_color(color)
            )
            button.pack(side="left", padx=5)
            self.browser_buttons[browser] = button

        self.cookie_status_label = ctk.CTkLabel(
            cookie_frame,
            text="No cookies selected",
            font=("Roboto", 10)
        )
        self.cookie_status_label.pack(anchor="w", padx=10, pady=5)

        # Download options
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(fill="x", pady=(0, 20))

        options_label = ctk.CTkLabel(
            options_frame,
            text="Download Options:",
            font=("Roboto", 12, "bold")
        )
        options_label.pack(anchor="w", padx=(10, 5))

        # Quality selection
        quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=10, pady=8)

        quality_label = ctk.CTkLabel(quality_frame, text="Quality:", font=("Roboto", 11))
        quality_label.pack(side="left", padx=(0, 10))

        self.quality_var = ctk.StringVar(value="720p")
        quality_options = ["144p", "240p", "360p", "480p", "720p", "1080p", "1440p", "4K", "8K"]

        quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.quality_var,
            values=quality_options,
            width=120,
            font=("Roboto", 10)
        )
        quality_menu.pack(side="left", padx=(0, 20))

        # Format selection
        format_label = ctk.CTkLabel(quality_frame, text="Format:", font=("Roboto", 11))
        format_label.pack(side="left", padx=(0, 10))

        self.format_var = ctk.StringVar(value="video")
        format_options = ["video", "audio", "both"]

        format_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.format_var,
            values=format_options,
            width=100,
            font=("Roboto", 10)
        )
        format_menu.pack(side="left")

        # Advanced options
        advanced_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        advanced_frame.pack(fill="x", padx=10, pady=5)

        # Playlist download
        self.playlist_var = ctk.BooleanVar(value=False)
        playlist_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Playlist (if URL is a playlist)",
            variable=self.playlist_var,
            font=("Roboto", 11)
        )
        playlist_check.pack(anchor="w", pady=2)

        # Audio only option
        self.audio_only_var = ctk.BooleanVar(value=False)
        audio_only_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Audio Only (extract audio)",
            variable=self.audio_only_var,
            font=("Roboto", 11)
        )
        audio_only_check.pack(anchor="w", pady=2)

        # Subtitle options
        self.subtitle_var = ctk.BooleanVar(value=False)
        subtitle_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Subtitles",
            variable=self.subtitle_var,
            font=("Roboto", 11)
        )
        subtitle_check.pack(anchor="w", pady=2)

        # Thumbnail options
        self.thumbnail_var = ctk.BooleanVar(value=True)
        thumbnail_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Thumbnail",
            variable=self.thumbnail_var,
            font=("Roboto", 11)
        )
        thumbnail_check.pack(anchor="w", pady=2)

        # Embed metadata
        self.metadata_var = ctk.BooleanVar(value=True)
        metadata_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Embed Metadata",
            variable=self.metadata_var,
            font=("Roboto", 11)
        )
        metadata_check.pack(anchor="w", pady=2)

        # Advanced yt-dlp options
        advanced_options_frame = ctk.CTkFrame(main_frame)
        advanced_options_frame.pack(fill="x", pady=(0, 20))

        advanced_label = ctk.CTkLabel(
            advanced_options_frame,
            text="Advanced Options:",
            font=("Roboto", 12, "bold")
        )
        advanced_label.pack(anchor="w", padx=(10, 5))

        # Speed limit
        speed_frame = ctk.CTkFrame(advanced_options_frame, fg_color="transparent")
        speed_frame.pack(fill="x", padx=10, pady=5)

        speed_label = ctk.CTkLabel(speed_frame, text="Speed Limit (KB/s):", font=("Roboto", 10))
        speed_label.pack(side="left", padx=(0, 10))

        self.speed_limit_var = ctk.StringVar(value="")
        speed_entry = ctk.CTkEntry(
            speed_frame,
            textvariable=self.speed_limit_var,
            width=100,
            placeholder_text="No limit",
            font=("Roboto", 10)
        )
        speed_entry.pack(side="left")

        # Retry options
        retry_frame = ctk.CTkFrame(advanced_options_frame, fg_color="transparent")
        retry_frame.pack(fill="x", padx=10, pady=5)

        retry_label = ctk.CTkLabel(retry_frame, text="Retries:", font=("Roboto", 10))
        retry_label.pack(side="left", padx=(0, 10))

        self.retries_var = ctk.StringVar(value="3")
        retry_entry = ctk.CTkEntry(
            retry_frame,
            textvariable=self.retries_var,
            width=50,
            font=("Roboto", 10)
        )
        retry_entry.pack(side="left", padx=(0, 20))

        # Concurrent downloads
        concurrent_label = ctk.CTkLabel(retry_frame, text="Concurrent:", font=("Roboto", 10))
        concurrent_label.pack(side="left", padx=(0, 10))

        self.concurrent_var = ctk.StringVar(value="1")
        concurrent_entry = ctk.CTkEntry(
            retry_frame,
            textvariable=self.concurrent_var,
            width=50,
            font=("Roboto", 10)
        )
        concurrent_entry.pack(side="left")

        # Buttons
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(30, 0))

        # Add to downloads button
        add_button = ctk.CTkButton(
            button_frame,
            text="Add to Downloads",
            command=self._handle_add_to_downloads,
            width=150,
            height=40,
            font=("Roboto", 12, "bold"),
            fg_color="#28a745",
            hover_color="#218838"
        )
        add_button.pack(side="right", padx=5)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            height=40,
            font=("Roboto", 12)
        )
        cancel_button.pack(side="right", padx=5)

        # Set focus and auto-detect name
        self.name_entry.focus()
        self._auto_fill_name()

    def _auto_fill_name(self):
        """Auto-fill the name based on URL."""
        try:
            if "youtube.com" in self.url:
                if "watch?v=" in self.url:
                    # Single video
                    video_id = self.url.split("watch?v=")[1].split("&")[0]
                    self.name_entry.insert(0, f"YouTube Video ({video_id[:8]}...)")
                elif "playlist" in self.url:
                    # Playlist
                    playlist_id = self.url.split("list=")[1].split("&")[0]
                    self.name_entry.insert(0, f"YouTube Playlist ({playlist_id[:8]}...)")
            elif "youtu.be" in self.url:
                # Shortened URL
                video_id = self.url.split("/")[-1].split("?")[0]
                self.name_entry.insert(0, f"YouTube Video ({video_id[:8]}...)")
        except:
            self.name_entry.insert(0, "YouTube Media")

    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color for hover effect."""
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, c - 30) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def _handle_browser_select(self, browser: BrowserType):
        """Handle browser selection for cookies with caching."""
        # Reset all buttons to default color
        for btn_browser, button in self.browser_buttons.items():
            if btn_browser == BrowserType.CHROME:
                button.configure(fg_color="#4285F4")
            elif btn_browser == BrowserType.FIREFOX:
                button.configure(fg_color="#FF9500")
            elif btn_browser == BrowserType.SAFARI:
                button.configure(fg_color="#007AFF")

        # Set selected button to yellow
        if browser in self.browser_buttons:
            self.browser_buttons[browser].configure(fg_color="#FFD700")

        # Try to use cached cookies first
        if browser in self._cached_cookies:
            cookie_path = self._cached_cookies[browser]
            if os.path.exists(cookie_path):
                self._set_cookie_success(browser, cookie_path)
                return

        # Detect cookies if not cached
        try:
            cookie_path = self.cookie_handler.detect_cookies_for_browser(browser)
            if cookie_path:
                # Cache the cookie path
                self._cached_cookies[browser] = cookie_path
                self._selected_browser = browser
                self._save_cached_selections()
                self._set_cookie_success(browser, cookie_path)
            else:
                self._set_cookie_failure(browser)
        except Exception as e:
            self._set_cookie_error(browser, str(e))

    def _set_cookie_success(self, browser: BrowserType, cookie_path: str):
        """Set successful cookie detection."""
        self.cookie_status_label.configure(
            text=f"✓ Using {browser.value} cookies (cached)",
            text_color="green"
        )
        self.selected_cookie_path = cookie_path

    def _set_cookie_failure(self, browser: BrowserType):
        """Set failed cookie detection."""
        self.cookie_status_label.configure(
            text=f"✗ No {browser.value} cookies found",
            text_color="red"
        )
        self.selected_cookie_path = None

    def _set_cookie_error(self, browser: BrowserType, error: str):
        """Set cookie detection error."""
        self.cookie_status_label.configure(
            text=f"✗ Error with {browser.value} cookies: {error[:50]}...",
            text_color="red"
        )
        self.selected_cookie_path = None

    def _load_cached_selections(self):
        """Load cached browser selection."""
        try:
            cache_file = Path.home() / ".media_downloader" / "youtube_cache.json"
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    self._cached_cookies = cache_data.get('cookies', {})
                    self._selected_browser = cache_data.get('selected_browser')

                    # Restore selected button state
                    if self._selected_browser and self._selected_browser in self.browser_buttons:
                        self._handle_browser_select(self._selected_browser)
        except Exception as e:
            pass  # Fail silently if cache can't be loaded

    def _save_cached_selections(self):
        """Save cached browser selection."""
        try:
            cache_dir = Path.home() / ".media_downloader"
            cache_dir.mkdir(exist_ok=True)

            cache_file = cache_dir / "youtube_cache.json"
            cache_data = {
                'cookies': self._cached_cookies,
                'selected_browser': self._selected_browser
            }

            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            pass  # Fail silently if cache can't be saved

    def _handle_add_to_downloads(self):
        """Handle add to downloads button click."""
        name = self.name_entry.get().strip()
        if not name:
            self._show_error("Please enter a name for this download")
            return

        # Validate options
        try:
            if self.speed_limit_var.get():
                int(self.speed_limit_var.get())
            if self.retries_var.get():
                int(self.retries_var.get())
            if self.concurrent_var.get():
                int(self.concurrent_var.get())
        except ValueError:
            self._show_error("Please enter valid numbers for advanced options")
            return

        # Create comprehensive download options
        download_options = {
            'quality': self.quality_var.get(),
            'format': self.format_var.get(),
            'audio_only': self.audio_only_var.get(),
            'download_playlist': self.playlist_var.get(),
            'download_subtitles': self.subtitle_var.get(),
            'download_thumbnail': self.thumbnail_var.get(),
            'embed_metadata': self.metadata_var.get(),
            'cookie_path': getattr(self, 'selected_cookie_path', None),
            'selected_browser': self._selected_browser,
            'speed_limit': self.speed_limit_var.get() or None,
            'retries': int(self.retries_var.get()) if self.retries_var.get() else 3,
            'concurrent_downloads': int(self.concurrent_var.get()) if self.concurrent_var.get() else 1
        }

        # Call download callback
        if self.on_download:
            self.on_download(self.url, name, download_options)

        # Close dialog
        self.destroy()

    def _show_error(self, message: str):
        """Show error message temporarily."""
        error_label = ctk.CTkLabel(
            self,
            text=message,
            text_color="red",
            font=("Roboto", 11, "bold")
        )
        error_label.pack(pady=5)
        self.after(4000, error_label.destroy)