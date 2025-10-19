"""Enhanced dialog for YouTube video downloads with metadata fetching."""

import customtkinter as ctk
from typing import Optional, Callable, Dict, Any, List
import json
import os
import threading
from pathlib import Path
from ...interfaces.youtube_metadata import YouTubeMetadata
from ...interfaces.cookie_detection import BrowserType
from ...utils.window import WindowCenterMixin
from ...utils.logger import get_logger
from ..components.simple_loading_dialog import SimpleLoadingDialog
from ..components.subtitle_checklist import SubtitleChecklist
from .browser_cookie_dialog import BrowserCookieDialog

logger = get_logger(__name__)


class YouTubeDownloaderDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Enhanced dialog for downloading YouTube videos with metadata support."""

    # Class variables for cookie caching
    _cached_cookies = {}
    _selected_browser = None

    def __init__(
        self,
        parent,
        url: str,
        cookie_handler,
        on_download: Optional[Callable[[str, str, Dict[str, Any]], None]] = None,
        metadata_service=None,
        pre_fetched_metadata: Optional[YouTubeMetadata] = None,
        initial_cookie_path: Optional[str] = None,
        initial_browser: Optional[str] = None
    ):
        super().__init__(parent)

        self.url = url
        self.cookie_handler = cookie_handler
        self.on_download = on_download
        self.metadata_service = metadata_service
        self.browser_buttons = {}
        self.video_metadata = pre_fetched_metadata  # Use pre-fetched metadata if provided
        self.loading_overlay: Optional[SimpleLoadingDialog] = None
        self.selected_cookie_path = initial_cookie_path
        self.selected_browser = initial_browser
        self.widgets_created = False

        # Configure window
        self.title("YouTube Video Downloader")
        self.geometry("700x900")
        self.resizable(True, True)
        self.minsize(600, 700)

        # Make window modal
        self.transient(parent)
        self.grab_set()

        # Center the window using mixin
        self.center_window()

        # Hide the main window initially
        self.withdraw()

        # Start metadata fetch directly since cookie selection is already handled
        self._start_metadata_fetch()

    def _start_metadata_fetch_with_cookie(self):
        """Start metadata fetching with the provided cookie information."""
        if self.selected_browser:
            # If browser was selected, get cookies from browser
            self._get_browser_cookies(self.selected_browser)
        else:
            # Use manual cookie path or proceed without cookies
            self._start_metadata_fetch()

    def _show_cookie_selection(self):
        """Show cookie selection dialog before metadata fetching."""
        logger.info("Showing cookie selection dialog")

        def on_cookie_selected(cookie_path: Optional[str], browser: Optional[str]):
            logger.info(f"Cookie selection callback: path={cookie_path}, browser={browser}")
            self.selected_cookie_path = cookie_path
            self.selected_browser = browser

            # If manual path was provided, use it directly
            if cookie_path:
                logger.info("Starting metadata fetch with manual cookie path")
                self._start_metadata_fetch()
            elif browser:
                logger.info(f"Getting cookies from browser: {browser}")
                # If browser was selected, get cookies from browser
                self._get_browser_cookies(browser)
            else:
                logger.info("No cookies selected, proceeding without cookies")
                # No cookies selected, proceed without
                self._start_metadata_fetch()

        try:
            logger.info("Creating BrowserCookieDialog")
            BrowserCookieDialog(self, on_cookie_selected)
            logger.info("BrowserCookieDialog created successfully")
            # No need to wait_window() as the callback will be called after the dialog is destroyed
        except Exception as e:
            logger.error(f"Error showing cookie dialog: {e}")
            # If cookie dialog fails, proceed without cookies
            self._start_metadata_fetch()

    def _get_browser_cookies(self, browser: str):
        """Handle browser cookie selection - just pass browser type to yt-dlp."""
        # yt-dlp handles cookie extraction directly, no manual extraction needed
        logger.debug(f"Using browser cookies: {browser}")

        # Start metadata fetching immediately
        self.after(0, self._start_metadata_fetch)

    def _start_metadata_fetch(self):
        """Start metadata fetching after cookie selection."""
        logger.info("Starting metadata fetch process")
        self._create_loading_overlay()
        self._fetch_metadata_async()

    def _create_loading_overlay(self):
        """Create loading overlay for metadata fetching."""
        logger.info("Creating loading overlay")
        self.loading_overlay = SimpleLoadingDialog(self, "Fetching YouTube metadata", timeout=90)
        logger.info("Loading overlay created successfully")

    def _fetch_metadata_async(self):
        """Fetch metadata asynchronously."""
        def fetch_worker():
            try:
                if self.metadata_service:
                    # Use selected cookie path
                    cookie_path = self.selected_cookie_path

                    # Debug output
                    print(f"DEBUG: YouTube dialog fetch_metadata - url: {self.url}")
                    print(f"DEBUG: YouTube dialog fetch_metadata - cookie_path: {cookie_path}")
                    print(f"DEBUG: YouTube dialog fetch_metadata - selected_browser: {self.selected_browser}")

                    # Fetch metadata with cookies
                    self.video_metadata = self.metadata_service.fetch_metadata(self.url, cookie_path, self.selected_browser)

                    # Check if metadata fetch failed
                    if self.video_metadata and self.video_metadata.error:
                        self.after(0, self._handle_metadata_error)
                        return
                else:
                    # No metadata service available
                    self.after(0, self._handle_metadata_error)
                    return

                # Update UI in main thread
                self.after(0, self._handle_metadata_fetched)

            except Exception as e:
                logger.error(f"Error fetching metadata: {e}")
                # Close the dialog if metadata fetch fails
                self.after(0, self._handle_metadata_error)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _handle_metadata_error(self):
        """Handle metadata fetch error by closing the dialog."""
        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.close()

        # Show error message and close dialog
        from tkinter import messagebox

        error_msg = "Failed to fetch video metadata. Please check the URL and try again."
        if self.video_metadata and self.video_metadata.error:
            error_msg = f"Failed to fetch video metadata: {self.video_metadata.error}"

        messagebox.showerror("Metadata Error", error_msg)
        self.destroy()

    def _handle_metadata_fetched(self):
        """Handle metadata fetch completion."""
        # Check if metadata has an error
        if self.video_metadata and self.video_metadata.error:
            self._handle_metadata_error()
            return

        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.close()

        # Create main interface only after metadata is successfully fetched
        if not self.widgets_created:
            self._create_widgets()
            self._load_cached_selections()
            self.widgets_created = True

        # Show main interface
        if hasattr(self, 'main_frame'):
            self.main_frame.pack(fill="both", expand=True)

        # Wait for loading overlay to close completely, then show main window
        self._schedule_main_window_show()

    def _schedule_main_window_show(self):
        """Schedule showing main window after loading overlay is completely gone."""
        if self.loading_overlay and hasattr(self.loading_overlay, 'winfo_exists') and self.loading_overlay.winfo_exists():
            # Loading overlay still exists, wait a bit more
            self.after(100, self._schedule_main_window_show)
        else:
            # Loading overlay is gone, show main window
            self.after(200, self._show_main_window)

    def _show_main_window(self):
        """Show the main window after loading is complete."""
        # Show the main window now that everything is ready
        self.deiconify()
        self.lift()

        # Update UI with metadata
        self._update_ui_with_metadata()

    def _update_ui_with_metadata(self):
        """Update UI components with fetched metadata."""
        if not self.video_metadata:
            return

        # Auto-fill name with video title
        if self.video_metadata.title:
            self.name_entry.delete(0, 'end')
            self.name_entry.insert(0, self.video_metadata.title)

        # Update quality options
        if self.video_metadata.available_qualities:
            self.quality_var.set(self.video_metadata.available_qualities[0])
            self.quality_menu.configure(values=self.video_metadata.available_qualities)

        # Update format options
        if self.video_metadata.available_formats:
            self.format_var.set(self.video_metadata.available_formats[0])
            self.format_menu.configure(values=self.video_metadata.available_formats)

        # Update subtitle options
        if self.video_metadata.available_subtitles:
            subtitle_options = [
                {
                    'id': sub['language_code'],  # Use language code as ID
                    'display': sub['language_name'],  # Use language name for display
                    'language_code': sub['language_code'],
                    'language_name': sub['language_name'],
                    'is_auto': sub['is_auto_generated'],
                    'is_auto_generated': sub['is_auto_generated'],
                    'url': sub['url']
                }
                for sub in self.video_metadata.available_subtitles
            ]
            self.subtitle_dropdown.set_subtitle_options(subtitle_options)
            self.subtitle_frame.pack(fill="x", pady=(0, 20), after=self.format_frame)
        else:
            self.subtitle_frame.pack_forget()

        # Update format callback
        self._on_format_change()

    def _create_widgets(self):
        """Create dialog widgets with scrolling support."""
        # Create scrollable frame using grid
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main container (initially hidden)
        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")

        # Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="YouTube Video Downloader",
            font=("Roboto", 24, "bold")
        )
        title_label.pack(pady=(0, 20))

        # URL display
        url_frame = ctk.CTkFrame(self.main_frame)
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
        name_frame = ctk.CTkFrame(self.main_frame)
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
        cookie_frame = ctk.CTkFrame(self.main_frame)
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
            BrowserType.CHROME: ("Chrome", "#4285F4", "#FFA500"),
            BrowserType.FIREFOX: ("Firefox", "#4169E1", "#FFA500"),
            BrowserType.SAFARI: ("Safari", "#007AFF", "#FFA500")
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
        options_frame = ctk.CTkFrame(self.main_frame)
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

        self.quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.quality_var,
            values=quality_options,
            width=120,
            font=("Roboto", 10)
        )
        self.quality_menu.pack(side="left", padx=(0, 20))

        # Format selection (controls audio/video)
        format_label = ctk.CTkLabel(quality_frame, text="Format:", font=("Roboto", 11))
        format_label.pack(side="left", padx=(0, 10))

        self.format_var = ctk.StringVar(value="video")
        format_options = ["video", "audio", "video_only"]

        self.format_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.format_var,
            values=format_options,
            width=100,
            font=("Roboto", 10),
            command=lambda x: self._on_format_change()
        )
        self.format_menu.pack(side="left")

        # Store reference for later updates
        self.format_frame = quality_frame

        # Subtitle selection (initially hidden)
        self.subtitle_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.subtitle_frame.pack(fill="x", padx=10, pady=8)

        subtitle_label = ctk.CTkLabel(self.subtitle_frame, text="Subtitles:", font=("Roboto", 11))
        subtitle_label.pack(anchor="w", pady=(0, 5))

        self.subtitle_dropdown = SubtitleChecklist(
            self.subtitle_frame,
            placeholder="No subtitles available",
            height=120,
            on_change=self._on_subtitle_change
        )
        self.subtitle_dropdown.pack(fill="both", expand=True)

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

        # Subtitle selection is handled by the dropdown above

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
        advanced_options_frame = ctk.CTkFrame(self.main_frame)
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
        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(30, 0))

        # Add to downloads button
        self.add_button = ctk.CTkButton(
            button_frame,
            text="Add to Downloads",
            command=self._handle_add_to_downloads,
            width=150,
            height=40,
            font=("Roboto", 12, "bold"),
            fg_color="#28a745",
            hover_color="#218838"
        )
        self.add_button.pack(side="right", padx=5)

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

        # Set focus
        self.name_entry.focus()

    def _on_subtitle_change(self, selected_subtitles: List[str]):
        """Handle subtitle selection change."""
        # This method is called when subtitle selection changes
        # You can add custom logic here if needed
        pass

    def _on_format_change(self):
        """Handle format selection change."""
        format_value = self.format_var.get()

        # Update format label text to show what it means
        # format_descriptions = {
        #     "video": "Video + Audio",
        #     "audio": "Audio Only",
        #     "video_only": "Video Only"
        # }

        # Update audio_only checkbox based on format
        if format_value == "audio":
            # Audio format means audio only
            pass  # No checkbox anymore
        else:
            # Video or video_only means include video
            pass

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
                button.configure(fg_color="#4169E1")
            elif btn_browser == BrowserType.SAFARI:
                button.configure(fg_color="#007AFF")

        # Set selected button to orange
        if browser in self.browser_buttons:
            self.browser_buttons[browser].configure(fg_color="#FFA500")

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
        except Exception:
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
        except Exception:
            pass  # Fail silently if cache can't be saved

    def _handle_add_to_downloads(self):
        """Handle add to downloads button click."""
        try:
            # Disable button to prevent multiple clicks
            self.add_button.configure(state="disabled")

            # Use after to prevent UI blocking
            self.after(10, self._process_add_to_downloads)

        except Exception as e:
            print(f"Error in add to downloads: {e}")
            import traceback
            traceback.print_exc()
            # Re-enable button on error
            if hasattr(self, 'add_button'):
                self.add_button.configure(state="normal")

    def _process_add_to_downloads(self):
        """Process add to downloads in a non-blocking way."""
        try:
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

            # Get format-specific settings
            format_value = self.format_var.get()
            audio_only = format_value == "audio"
            video_only = format_value == "video_only"

            # Get selected subtitles
            selected_subtitles = self.subtitle_dropdown.get_selected_subtitles()

            # Create comprehensive download options
            download_options = {
                'quality': self.quality_var.get(),
                'format': format_value,
                'audio_only': audio_only,
                'video_only': video_only,
                'download_playlist': self.playlist_var.get(),
                'download_subtitles': bool(selected_subtitles),
                'selected_subtitles': selected_subtitles,
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

            # Close dialog after a small delay
            self.after(100, self.destroy)

        except Exception as e:
            print(f"Error processing add to downloads: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Re-enable button if dialog still exists
            if hasattr(self, 'add_button') and self.winfo_exists():
                self.add_button.configure(state="normal")

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