"""Enhanced dialog for YouTube video downloads with metadata fetching."""

import threading
import time
from collections.abc import Callable
from typing import Optional

import customtkinter as ctk

from src.core.config import get_config, AppConfig
from src.core.enums.message_level import MessageLevel
from src.core.models import Download
from src.interfaces.service_interfaces import IErrorHandler, IMessageQueue
from src.services.events.queue import Message
from ...interfaces.youtube_metadata import YouTubeMetadata
from ...utils.logger import get_logger
from ...utils.window import WindowCenterMixin
from ..components.loading_dialog import LoadingDialog
from ..components.subtitle_checklist import SubtitleChecklist

logger = get_logger(__name__)


class YouTubeDownloaderDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Enhanced dialog for downloading YouTube videos with metadata support."""

    def __init__(
        self,
        parent,
        url: str,
        cookie_handler,
        on_download: Callable | None = None,
        metadata_service=None,
        pre_fetched_metadata: YouTubeMetadata | None = None,
        initial_cookie_path: str | None = None,
        error_handler: Optional[IErrorHandler] = None,
        message_queue: Optional[IMessageQueue] = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(parent)

        self.config = config
        self.url = url
        self.cookie_handler = cookie_handler
        self.on_download = on_download
        self.metadata_service = metadata_service
        self.video_metadata = pre_fetched_metadata
        self.error_handler = error_handler
        self.message_queue = message_queue
        self.loading_overlay: LoadingDialog | None = None
        self.selected_cookie_path = initial_cookie_path
        self.widgets_created = False
        self._metadata_handler_called = False
        self._metadata_ready = False
        self.selected_subtitles = []

        # Configure window
        self.title("YouTube Video Downloader")
        self.geometry("700x900")
        self.resizable(True, True)
        self.minsize(600, 700)

        # Make window modal
        self.transient(parent)
        # Note: Don't grab_set() yet - wait until after metadata is fetched
        # Otherwise event callbacks won't process properly

        # Ensure dialog appears on top
        self.attributes("-topmost", True)
        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks in __init__: {e}")
        self.attributes("-topmost", False)

        # Center the window using mixin
        try:
            self.center_window()
        except Exception as e:
            logger.warning(f"Could not center window: {e}")
            # Set a default geometry if centering fails
            try:
                self.geometry("700x900")
            except Exception:
                pass

        # Don't hide dialog yet - loading overlay needs visible parent
        # Show loading overlay immediately, then start fetch
        self.after(10, self._start_metadata_fetch)

        # Start polling for metadata completion from main thread
        self._poll_metadata_completion()

    def _poll_metadata_completion(self):
        """Poll for metadata completion from the main thread."""
        # Check for errors first
        if self.video_metadata and self.video_metadata.error and not self._metadata_handler_called:
            logger.info("Metadata error detected - calling error handler")
            try:
                self._handle_metadata_error()
                self._metadata_handler_called = True
                return
            except Exception as e:
                logger.error(f"Error in metadata error handler: {e}", exc_info=True)
        
        # Check for successful completion
        if self._metadata_ready and not self._metadata_handler_called:
            logger.info("Metadata ready flag detected - calling handler")
            try:
                self._handle_metadata_fetched()
            except Exception as e:
                logger.error(f"Error in metadata handler: {e}", exc_info=True)
        elif not self._metadata_handler_called:
            # Continue polling every 100ms until metadata is ready or error occurs
            self.after(100, self._poll_metadata_completion)

    def _safe_deiconify(self):
        """Safely deiconify the window, handling CustomTkinter race conditions."""
        try:
            # Ensure geometry is set before deiconifying
            self.update_idletasks()
            self.deiconify()
        except Exception as e:
            # Handle the "expected integer but got a list" error from CustomTkinter
            logger.warning(f"Error during deiconify (retrying): {e}")
            try:
                # Try again after a brief update
                self.update()
                self.deiconify()
            except Exception as e2:
                logger.error(f"Failed to deiconify window: {e2}")
                # Last resort - just continue, window may already be visible

    def _start_metadata_fetch_with_cookie(self):
        """Start metadata fetching with auto-generated cookies."""
        # Auto cookie manager handles cookies, just start fetch
        self._start_metadata_fetch()

    def _start_metadata_fetch(self):
        """Start metadata fetching after cookie selection."""
        logger.debug("Starting metadata fetch process")

        # Keep dialog hidden during metadata fetch
        # The loading overlay will be created as a standalone dialog
        self.withdraw()

        self._create_loading_overlay()
        self._fetch_metadata_async()

    def _create_loading_overlay(self):
        """Create loading overlay for metadata fetching."""
        logger.debug("Creating loading overlay")

        try:
            # Create overlay with root window as parent so it shows independently
            # This allows the main dialog to stay hidden during fetch
            self.loading_overlay = LoadingDialog(
                self.master, "Fetching YouTube metadata...", timeout=self.config.ui.metadata_fetch_timeout
            )
            logger.debug("Loading overlay created successfully")

            # Make sure it's visible and on top
            self.loading_overlay.lift()
            self.loading_overlay.attributes("-topmost", True)
            self.loading_overlay.focus_force()

        except Exception as e:
            logger.error(f"Failed to create loading overlay: {e}", exc_info=True)
            # Continue without overlay
            self.loading_overlay = None

    def _fetch_metadata_async(self):
        """Fetch metadata asynchronously."""

        def fetch_worker():
            try:
                if self.metadata_service:
                    # Use selected cookie path
                    cookie_path = self.selected_cookie_path

                    # Debug output
                    logger.debug(f"YouTube dialog fetch_metadata - url: {self.url}")
                    logger.debug(
                        f"YouTube dialog fetch_metadata - cookie_path: {cookie_path}"
                    )

                    # Fetch metadata with cookies and timeout protection
                    logger.info("Calling metadata_service.fetch_metadata...")

                    # Set a timeout for metadata fetch
                    metadata_result = [None]
                    metadata_error = [None]
                    fetch_completed = [False]

                    def fetch_with_timeout():
                        try:
                            metadata_result[0] = self.metadata_service.fetch_metadata(
                                self.url, cookie_path, None
                            )
                            fetch_completed[0] = True
                        except Exception as e:
                            metadata_error[0] = e
                            fetch_completed[0] = True

                    # Start fetch thread
                    fetch_thread = threading.Thread(
                        target=fetch_with_timeout, daemon=True
                    )
                    fetch_thread.start()

                    # Wait for completion or timeout
                    timeout_seconds = 60  # 1 minute timeout
                    start_time = time.time()

                    while (
                        not fetch_completed[0]
                        and (time.time() - start_time) < timeout_seconds
                    ):
                        time.sleep(self.config.ui.metadata_poll_interval)

                    # Check result
                    if not fetch_completed[0]:
                        logger.error(
                            f"Metadata fetch timed out after {timeout_seconds} seconds"
                        )
                        raise TimeoutError(
                            f"Metadata fetch timed out after {timeout_seconds} seconds"
                        )

                    if metadata_error[0]:
                        raise metadata_error[0]

                    self.video_metadata = metadata_result[0]
                    logger.info(
                        f"Metadata fetch completed. Result: {self.video_metadata}"
                    )
                    logger.info(f"Metadata type: {type(self.video_metadata)}")

                    if self.video_metadata and self.video_metadata.error:
                        error_msg = self.video_metadata.error
                        logger.error(f"Metadata fetch failed with error: {error_msg}")
                        if self.error_handler:
                            self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, self.url)
                        self.after(0, self._handle_metadata_error)
                        return

                    # Signal that metadata is ready - the main thread polling will detect this
                    logger.info("Setting metadata ready flag for main thread polling")
                    self._metadata_ready = True
                    logger.debug(
                        "Metadata ready flag set, main thread polling will detect this"
                    )
                else:
                    error_msg = "No metadata service available"
                    if self.error_handler:
                        self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, self.url)
                    self.after(0, self._handle_metadata_error)
                    return

            except Exception as e:
                logger.error(f"Error fetching metadata: {e}", exc_info=True)
                error_msg = str(e)
                
                error_map = {
                    "429": "YouTube rate limit exceeded. Please try again later or use browser cookies.",
                    "403": "Access forbidden. This video may require age verification or cookies.",
                }
                
                if any(code in error_msg for code in error_map.keys()):
                    for code, msg in error_map.items():
                        if code in error_msg:
                            error_msg = msg
                            break
                elif "timeout" in error_msg.lower():
                    error_msg = "Connection timed out. Please check your internet connection and try again."

                if not hasattr(self, "video_metadata") or not self.video_metadata:
                    self.video_metadata = YouTubeMetadata(video_id=None, title=None, error=error_msg)

                if self.error_handler:
                    self.error_handler.handle_exception(e, "YouTube metadata fetch", "YouTube")

                self.after(0, self._handle_metadata_error)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _handle_metadata_error(self):
        """Handle metadata fetch error by closing the dialog."""
        # Hide loading overlay
        if self.loading_overlay:
            try:
                self.loading_overlay.close()
            except Exception as e:
                logger.warning(f"Error closing loading overlay: {e}")
            finally:
                self.loading_overlay = None  # Clear reference

        # Ensure dialog is visible for error message
        try:
            self.lift()
            self.focus_force()
        except Exception as e:
            logger.warning(f"Error making dialog visible for error message: {e}")

        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks in error handler: {e}")

        error_msg = "Failed to fetch video metadata. Please check the URL and try again."
        if self.video_metadata and self.video_metadata.error:
            error_msg = f"Failed to fetch video metadata: {self.video_metadata.error}"

        # Show error via status bar only - no popup dialogs
        if self.error_handler:
            self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, self.url)
        elif self.message_queue:
            self.message_queue.add_message(
                Message(text=error_msg, level=MessageLevel.ERROR, title="YouTube Metadata Error")
            )

        try:
            self.destroy()
        except Exception as e:
            logger.error(f"Error destroying dialog: {e}")

    def _handle_metadata_fetched(self):
        """Handle metadata fetch completion - ONLY SHOWS DIALOG AFTER FETCH COMPLETE."""
        logger.info("=== _handle_metadata_fetched called ===")
        logger.info("Handling metadata fetch completion")
        self._metadata_handler_called = True  # Set flag to prevent timeout fallback
        logger.info(f"Video metadata: {self.video_metadata}")
        logger.info(f"Video metadata type: {type(self.video_metadata)}")
        if self.video_metadata:
            logger.info(
                f"Video metadata title: {getattr(self.video_metadata, 'title', 'No title')}"
            )
            logger.info(
                f"Video metadata error: {getattr(self.video_metadata, 'error', 'No error')}"
            )

        if self.video_metadata and self.video_metadata.error:
            error_msg = self.video_metadata.error
            logger.error(f"Metadata fetch error: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure("YouTube", "metadata fetch", error_msg, self.url)
            self._handle_metadata_error()
            return

        # CRITICAL: Close loading overlay FIRST, THEN show main dialog
        if self.loading_overlay:
            logger.info("Closing loading overlay")
            try:
                if hasattr(self, "loading_overlay") and self.loading_overlay:
                    self.loading_overlay.close()
                    self.loading_overlay = None
            except Exception as e:
                logger.error(f"Error closing loading overlay: {e}")
            finally:
                self.loading_overlay = None  # Clear reference

        # IMPORTANT: Only NOW show the main options dialog after loading is complete
        logger.info("Showing YouTube options dialog after metadata fetch complete")
        try:
            self.deiconify()
            self.lift()
            self.focus_force()
            logger.info("Dialog shown and focused")
        except Exception as e:
            logger.warning(f"Error showing dialog: {e}")

        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks after metadata fetch: {e}")

        # Now that metadata is loaded, make the dialog modal
        try:
            self.grab_set()
            logger.debug("Dialog grab set - now modal")
        except Exception as e:
            logger.warning(f"Could not set grab: {e}")

        # Create main interface only after metadata is successfully fetched
        if not self.widgets_created:
            logger.info("Creating widgets")
            try:
                # Clear any existing widgets first (like placeholder)
                for widget in self.winfo_children():
                    widget.destroy()

                self._create_widgets()
                logger.info("Widgets created successfully")
                self.widgets_created = True
            except Exception as e:
                logger.error(f"Error creating widgets: {e}", exc_info=True)
                # Show error via status bar only
                if self.error_handler:
                    self.error_handler.handle_exception(e, "Creating download options", "YouTube Dialog")
                elif self.message_queue:
                    self.message_queue.add_message(
                        Message(text=f"Failed to create download options: {str(e)}", level=MessageLevel.ERROR, title="Dialog Error")
                )
                return

        # Show main interface
        if hasattr(self, "main_frame"):
            logger.debug("Packing main frame")
            try:
                self.main_frame.pack(fill="both", expand=True)
                logger.debug("Main frame packed successfully")
            except Exception as e:
                logger.error(f"Error packing main frame: {e}", exc_info=True)
                return
        else:
            logger.error("Main frame not found - widget creation may have failed")
            return

        # Force geometry update to ensure proper sizing
        try:
            # Set a minimum size to ensure dialog is visible
            self.minsize(500, 400)
            logger.debug("Dialog size updated")
        except Exception as e:
            logger.warning(f"Error updating dialog size: {e}")

        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks for geometry: {e}")

        # Show main window immediately
        logger.debug("Showing main window")
        try:
            self._show_main_window()
        except Exception as e:
            logger.error(f"Error showing main window: {e}", exc_info=True)

    def _schedule_main_window_show(self):
        """Schedule showing main window after loading overlay is completely gone."""
        # Give a small delay to ensure loading overlay is properly closed
        self.after(100, self._show_main_window)

    def _show_main_window(self):
        """Show the main window after loading is complete."""
        logger.debug("Showing main window - ensuring visibility")
        # Show the main window now that everything is ready
        try:
            self.lift()
            self.focus_force()  # Force focus to this window

            # Update UI with metadata
            logger.debug("Updating UI with metadata")
            self._update_ui_with_metadata()

            # Ensure window is visible by updating it
            try:
                self.update_idletasks()
            except Exception as e:
                logger.warning(f"Could not update idletasks in show_main_window: {e}")

            # Force another update to ensure visibility
            try:
                self.update()
            except Exception as e:
                logger.warning(f"Could not update in show_main_window: {e}")

            logger.debug("Main window shown")
        except Exception as e:
            logger.error(f"Error showing main window: {e}", exc_info=True)

    def _update_ui_with_metadata(self) -> None:
        """Update UI components with fetched metadata."""
        if not self.video_metadata:
            return

        # Auto-fill name with video title
        if self.video_metadata.title:
            self.name_entry.delete(0, "end")
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
                    "id": sub["language_code"],  # Use language code as ID
                    "display": sub["language_name"],  # Use language name for display
                    "language_code": sub["language_code"],
                    "language_name": sub["language_name"],
                    "is_auto": sub["is_auto_generated"],
                    "is_auto_generated": sub["is_auto_generated"],
                    "url": sub["url"],
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
        # Configure window properties
        self.title("YouTube Downloader")
        self.geometry("600x700")
        self.minsize(500, 400)

        # Create scrollable frame using grid
        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Main container
        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")

        # Title
        title_label = ctk.CTkLabel(
            self.main_frame,
            text="YouTube Video Downloader",
            font=("Roboto", 24, "bold"),
        )
        title_label.pack(pady=(0, 20))

        # URL display
        url_frame = ctk.CTkFrame(self.main_frame)
        url_frame.pack(fill="x", pady=(0, 20))

        url_label = ctk.CTkLabel(url_frame, text="URL:", font=("Roboto", 12, "bold"))
        url_label.pack(anchor="w", padx=(10, 5))

        url_display = ctk.CTkEntry(url_frame, font=("Roboto", 10))
        url_display.insert(0, self.url)
        url_display.configure(state="disabled")
        url_display.pack(fill="x", padx=10, pady=(0, 10))

        # Video name input
        name_frame = ctk.CTkFrame(self.main_frame)
        name_frame.pack(fill="x", pady=(0, 20))

        name_label = ctk.CTkLabel(
            name_frame, text="Video/Playlist Name:", font=("Roboto", 12, "bold")
        )
        name_label.pack(anchor="w", padx=(10, 5))

        self.name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Enter name for this download",
            font=("Roboto", 12),
        )
        self.name_entry.pack(fill="x", padx=10, pady=(0, 10))

        # Cookie selection
        cookie_frame = ctk.CTkFrame(self.main_frame)
        cookie_frame.pack(fill="x", pady=(0, 20))

        cookie_label = ctk.CTkLabel(
            cookie_frame,
            text="Cookies Status:",
            font=("Roboto", 12, "bold"),
        )
        cookie_label.pack(anchor="w", padx=10, pady=(10, 5))

        cookie_info_label = ctk.CTkLabel(
            cookie_frame,
            text="Cookies are automatically managed for age-restricted content",
            font=("Roboto", 10),
            text_color="gray",
        )
        cookie_info_label.pack(anchor="w", padx=(10, 0))

        self.cookie_status_label = ctk.CTkLabel(
            cookie_frame, text="No cookies selected", font=("Roboto", 10)
        )
        self.cookie_status_label.pack(anchor="w", padx=10, pady=5)

        # Download options
        options_frame = ctk.CTkFrame(self.main_frame)
        options_frame.pack(fill="x", pady=(0, 20))

        options_label = ctk.CTkLabel(
            options_frame, text="Download Options:", font=("Roboto", 12, "bold")
        )
        options_label.pack(anchor="w", padx=(10, 5))

        # Quality selection
        quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=10, pady=8)

        quality_label = ctk.CTkLabel(
            quality_frame, text="Quality:", font=("Roboto", 11)
        )
        quality_label.pack(side="left", padx=(0, 10))

        self.quality_var = ctk.StringVar(value=self.config.youtube.default_quality)
        quality_options = self.config.youtube.supported_qualities

        self.quality_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.quality_var,
            values=quality_options,
            width=120,
            font=("Roboto", 10),
        )
        self.quality_menu.pack(side="left", padx=(0, 20))

        # Format selection (controls audio/video)
        format_label = ctk.CTkLabel(quality_frame, text="Format:", font=("Roboto", 11))
        format_label.pack(side="left", padx=(0, 10))

        self.format_var = ctk.StringVar(value=self.config.ui.format_options[0])
        format_options = self.config.ui.format_options

        # Map user-friendly names to internal values
        self.format_map = {
            "Video + Audio": "video",
            "Audio Only": "audio",
            "Video Only": "video_only",
        }

        self.format_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.format_var,
            values=format_options,
            width=120,
            font=("Roboto", 10),
            command=lambda x: self._on_format_change(),
        )
        self.format_menu.pack(side="left")

        # Store reference for later updates
        self.format_frame = quality_frame

        # Subtitle selection (initially hidden)
        self.subtitle_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.subtitle_frame.pack(fill="x", padx=10, pady=8)

        subtitle_label = ctk.CTkLabel(
            self.subtitle_frame, text="Subtitles:", font=("Roboto", 11)
        )
        subtitle_label.pack(anchor="w", pady=(0, 5))

        self.subtitle_dropdown = SubtitleChecklist(
            self.subtitle_frame,
            placeholder="No subtitles available",
            height=120,
            on_change=self._on_subtitle_change,
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
            font=("Roboto", 11),
        )
        playlist_check.pack(anchor="w", pady=2)

        # Subtitle selection is handled by the dropdown above

        # Thumbnail options
        self.thumbnail_var = ctk.BooleanVar(value=True)
        thumbnail_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Thumbnail",
            variable=self.thumbnail_var,
            font=("Roboto", 11),
        )
        thumbnail_check.pack(anchor="w", pady=2)

        # Embed metadata
        self.metadata_var = ctk.BooleanVar(value=True)
        metadata_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Embed Metadata",
            variable=self.metadata_var,
            font=("Roboto", 11),
        )
        metadata_check.pack(anchor="w", pady=2)

        # Advanced yt-dlp options
        advanced_options_frame = ctk.CTkFrame(self.main_frame)
        advanced_options_frame.pack(fill="x", pady=(0, 20))

        advanced_label = ctk.CTkLabel(
            advanced_options_frame,
            text="Advanced Options:",
            font=("Roboto", 12, "bold"),
        )
        advanced_label.pack(anchor="w", padx=(10, 5))

        # Speed limit
        speed_frame = ctk.CTkFrame(advanced_options_frame, fg_color="transparent")
        speed_frame.pack(fill="x", padx=10, pady=5)

        speed_label = ctk.CTkLabel(
            speed_frame, text="Speed Limit (KB/s):", font=("Roboto", 10)
        )
        speed_label.pack(side="left", padx=(0, 10))

        self.speed_limit_var = ctk.StringVar(value="")
        speed_entry = ctk.CTkEntry(
            speed_frame,
            textvariable=self.speed_limit_var,
            width=100,
            placeholder_text="No limit",
            font=("Roboto", 10),
        )
        speed_entry.pack(side="left")

        # Retry options
        retry_frame = ctk.CTkFrame(advanced_options_frame, fg_color="transparent")
        retry_frame.pack(fill="x", padx=10, pady=5)

        retry_label = ctk.CTkLabel(retry_frame, text="Retries:", font=("Roboto", 10))
        retry_label.pack(side="left", padx=(0, 10))

        self.retries_var = ctk.StringVar(value="3")
        retry_entry = ctk.CTkEntry(
            retry_frame, textvariable=self.retries_var, width=50, font=("Roboto", 10)
        )
        retry_entry.pack(side="left", padx=(0, 20))

        # Concurrent downloads
        concurrent_label = ctk.CTkLabel(
            retry_frame, text="Concurrent:", font=("Roboto", 10)
        )
        concurrent_label.pack(side="left", padx=(0, 10))

        self.concurrent_var = ctk.StringVar(value="1")
        concurrent_entry = ctk.CTkEntry(
            retry_frame, textvariable=self.concurrent_var, width=50, font=("Roboto", 10)
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
            hover_color="#218838",
        )
        self.add_button.pack(side="right", padx=5)

        # Cancel button
        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            height=40,
            font=("Roboto", 12),
        )
        cancel_button.pack(side="right", padx=5)

        # Set focus
        self.name_entry.focus()

    def _on_subtitle_change(self, selected_subtitles: list) -> None:
        """Handle subtitle selection change."""
        logger.debug(f"Subtitle selection: {len(selected_subtitles)} selected")
        # Store the selected subtitles for later use
        self.selected_subtitles = selected_subtitles

    def _on_format_change(self) -> None:
        """Handle format selection change."""
        format_display = self.format_var.get()

        # Convert display name to internal value
        format_value = self.format_map.get(format_display, "video")

        # Update UI based on format selection
        format_descriptions = {
            "video": "Video + Audio (MP4)",
            "audio": "Audio Only (MP3)",
            "video_only": "Video Only (M4V)",
        }

        # Update the quality options based on format
        self._update_quality_options_for_format(format_value)
        logger.debug(f"Format: {format_display} ({format_value})")

    def _update_quality_options_for_format(self, format_value: str) -> None:
        """Update available quality options based on format selection."""
        if format_value == "audio":
            # For audio only, show audio quality options
            audio_qualities = ["best", "high", "medium", "low"]
            if hasattr(self, "quality_menu"):
                current_quality = self.quality_var.get()
                self.quality_menu.configure(values=audio_qualities)
                # Set a sensible default if current quality is not in audio options
                if current_quality not in audio_qualities:
                    self.quality_var.set("high")
        else:
            # For video formats, show video quality options
            video_qualities = self.config.youtube.video_qualities
            if hasattr(self, "quality_menu"):
                current_quality = self.quality_var.get()
                self.quality_menu.configure(values=video_qualities)
                # Set a sensible default if current quality is not in video options
                if current_quality not in video_qualities:
                    self.quality_var.set(self.config.youtube.default_quality)

    def _handle_add_to_downloads(self):
        """Handle add to downloads button click."""
        try:
            # Disable button to prevent multiple clicks
            self.add_button.configure(state="disabled")

            # Use after to prevent UI blocking
            self.after(10, self._process_add_to_downloads)

        except Exception as e:
            logger.error(f"Error in add to downloads: {e}")
            import traceback

            traceback.print_exc()
            # Re-enable button on error
            if hasattr(self, "add_button"):
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
            format_display = self.format_var.get()
            format_value = self.format_map.get(format_display, "video")
            audio_only = format_value == "audio"
            video_only = format_value == "video_only"

            # Get selected subtitles
            selected_subtitles = self.subtitle_dropdown.get_selected_subtitles()

            # Create Download object with all options
            download = Download(
                url=self.url,
                name=name,
                service_type="youtube",
                quality=self.quality_var.get(),
                download_playlist=self.playlist_var.get(),
                audio_only=audio_only,
                video_only=video_only,
                format=format_value,
                download_subtitles=bool(selected_subtitles),
                selected_subtitles=selected_subtitles,
                download_thumbnail=self.thumbnail_var.get(),
                embed_metadata=self.metadata_var.get(),
                cookie_path=getattr(self, "selected_cookie_path", None),
                speed_limit=self.speed_limit_var.get() or None,
                retries=int(self.retries_var.get()) if self.retries_var.get() else 3,
                concurrent_downloads=int(self.concurrent_var.get())
                if self.concurrent_var.get()
                else 1,
            )

            # Call download callback with Download object
            if self.on_download:
                self.on_download(download)

            # Close dialog after a small delay
            self.after(100, self.destroy)

        except Exception as e:
            logger.error(f"Error processing add to downloads: {e}")
            import traceback

            traceback.print_exc()
        finally:
            # Re-enable button if dialog still exists
            if hasattr(self, "add_button") and self.winfo_exists():
                self.add_button.configure(state="normal")

    def _show_error(self, message: str):
        """Show error message temporarily."""
        error_label = ctk.CTkLabel(
            self, text=message, text_color="red", font=("Roboto", 11, "bold")
        )
        error_label.pack(pady=5)
        self.after(4000, error_label.destroy)
