import re
import threading
import time
from collections.abc import Callable
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue, YouTubeMetadata
from src.core.models import Download
from src.services.events.queue import Message

from ...utils.logger import get_logger
from ...utils.window import WindowCenterMixin, close_loading_dialog
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
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
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

        self.title("YouTube Video Downloader")
        self.geometry("700x900")
        self.resizable(True, True)
        self.minsize(600, 700)

        self.transient(parent)

        self.attributes("-topmost", True)
        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks in __init__: {e}")
        self.attributes("-topmost", False)

        try:
            self.center_window()
        except Exception as e:
            logger.warning(f"Could not center window: {e}")
            import contextlib

            with contextlib.suppress(Exception):
                self.geometry("700x900")

        self.after(10, self._start_metadata_fetch)

        self._poll_metadata_completion()

    def _poll_metadata_completion(self):
        """Poll for metadata completion from the main thread."""
        if self.video_metadata and self.video_metadata.error and not self._metadata_handler_called:
            logger.info("Metadata error detected - calling error handler")
            try:
                self._handle_metadata_error()
                self._metadata_handler_called = True
                return
            except Exception as e:
                logger.error(f"Error in metadata error handler: {e}", exc_info=True)

        if self._metadata_ready and not self._metadata_handler_called:
            logger.info("Metadata ready flag detected - calling handler")
            try:
                self._handle_metadata_fetched()
            except Exception as e:
                logger.error(f"Error in metadata handler: {e}", exc_info=True)
        elif not self._metadata_handler_called:
            self.after(100, self._poll_metadata_completion)

    def _safe_deiconify(self):
        """Safely deiconify the window, handling CustomTkinter race conditions."""
        try:
            self.update_idletasks()
            self.deiconify()
        except Exception as e:
            logger.warning(f"Error during deiconify (retrying): {e}")
            try:
                self.update()
                self.deiconify()
            except Exception as e2:
                logger.error(f"Failed to deiconify window: {e2}")

    def _start_metadata_fetch_with_cookie(self):
        """Start metadata fetching with auto-generated cookies."""
        self._start_metadata_fetch()

    def _start_metadata_fetch(self):
        """Start metadata fetching after cookie selection."""
        logger.debug("Starting metadata fetch process")

        self.withdraw()

        self._create_loading_overlay()
        self._fetch_metadata_async()

    def _create_loading_overlay(self):
        """Create loading overlay for metadata fetching using centralized component."""
        logger.debug("Creating loading overlay")

        try:
            self.loading_overlay = LoadingDialog(
                self.master,
                message="Fetching YouTube metadata...",
                timeout=self.config.ui.metadata_fetch_timeout,
                max_dots=self.config.ui.loading_dialog_max_dots,
                dot_animation_interval=self.config.ui.loading_dialog_animation_interval,
            )
            logger.debug("Loading overlay created successfully")

            self.loading_overlay.lift()
            self.loading_overlay.attributes("-topmost", True)
            self.loading_overlay.focus_force()

        except Exception as e:
            logger.error(f"Failed to create loading overlay: {e}", exc_info=True)
            self.loading_overlay = None

    def _fetch_metadata_with_timeout(self, cookie_path: str) -> tuple[Any, Exception | None]:
        """Fetch metadata with timeout protection.

        Args:
            cookie_path: Cookie file path

        Returns:
            Tuple of (metadata_result, error)
        """
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

        fetch_thread = threading.Thread(target=fetch_with_timeout, daemon=True)
        fetch_thread.start()

        timeout_seconds = 60
        start_time = time.time()

        while not fetch_completed[0] and (time.time() - start_time) < timeout_seconds:
            time.sleep(self.config.ui.metadata_poll_interval)

        if not fetch_completed[0]:
            raise TimeoutError(f"Metadata fetch timed out after {timeout_seconds} seconds")

        if metadata_error[0]:
            raise metadata_error[0]

        return metadata_result[0], None

    def _normalize_error_message(self, error_msg: str) -> str:
        """Normalize error message for user display.

        Args:
            error_msg: Raw error message

        Returns:
            Normalized error message
        """
        error_map = {
            "429": "YouTube rate limit exceeded. Please try again later or use browser cookies.",
            "403": "Access forbidden. This video may require age verification or cookies.",
        }

        error_code_pattern = re.compile(r"(429|403)")
        timeout_pattern = re.compile(r"timeout", re.IGNORECASE)

        code_match = error_code_pattern.search(error_msg)
        if code_match:
            code = code_match.group(1)
            return error_map.get(code, error_msg)
        if timeout_pattern.search(error_msg):
            return "Connection timed out. Please check your internet connection and try again."
        return error_msg

    def _fetch_metadata_async(self):
        """Fetch metadata asynchronously."""

        def fetch_worker():
            try:
                if not self.metadata_service:
                    error_msg = "No metadata service available"
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "YouTube", "metadata fetch", error_msg, self.url
                        )
                    self._schedule_ui_update(self._handle_metadata_error)
                    return

                cookie_path = self.selected_cookie_path
                logger.debug(f"YouTube dialog fetch_metadata - url: {self.url}")
                logger.debug(f"YouTube dialog fetch_metadata - cookie_path: {cookie_path}")

                logger.info("Calling metadata_service.fetch_metadata...")
                metadata, error = self._fetch_metadata_with_timeout(cookie_path)

                if error:
                    raise error

                self.video_metadata = metadata
                logger.info(f"Metadata fetch completed. Result: {self.video_metadata}")
                logger.info(f"Metadata type: {type(self.video_metadata)}")

                if self.video_metadata and self.video_metadata.error:
                    error_msg = self.video_metadata.error
                    logger.error(f"Metadata fetch failed with error: {error_msg}")
                    if self.error_handler:
                        self.error_handler.handle_service_failure(
                            "YouTube", "metadata fetch", error_msg, self.url
                        )
                    self._schedule_ui_update(self._handle_metadata_error)
                    return

                logger.info("Setting metadata ready flag for main thread polling")
                self._metadata_ready = True
                logger.debug("Metadata ready flag set, main thread polling will detect this")

            except Exception as e:
                logger.error(f"Error fetching metadata: {e}", exc_info=True)
                error_msg = self._normalize_error_message(str(e))

                if not self.video_metadata:
                    self.video_metadata = YouTubeMetadata(
                        video_id=None, title=None, error=error_msg
                    )

                if self.error_handler:
                    self.error_handler.handle_exception(e, "YouTube metadata fetch", "YouTube")

                self._schedule_ui_update(self._handle_metadata_error)

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _handle_metadata_error(self):
        """Handle metadata fetch error by closing the dialog."""
        if self.loading_overlay:
            close_loading_dialog(self.loading_overlay, error_path=True)
            self.loading_overlay = None

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

        if self.error_handler:
            self.error_handler.handle_service_failure(
                "YouTube", "metadata fetch", error_msg, self.url
            )
        elif self.message_queue:
            self.message_queue.add_message(
                Message(
                    text=error_msg,
                    level=MessageLevel.ERROR,
                    title="YouTube Metadata Error",
                )
            )

        try:
            self.destroy()
        except Exception as e:
            logger.error(f"Error destroying dialog: {e}")

    def _close_loading_and_show_dialog(self) -> None:
        """Close loading overlay and show main dialog."""
        if self.loading_overlay:
            logger.info("Closing loading overlay")
            close_loading_dialog(self.loading_overlay, error_path=False)
            self.loading_overlay = None

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

        try:
            self.after(100, lambda: self.grab_set() if self.winfo_exists() else None)
            logger.debug("Dialog grab scheduled - will be modal after UI renders")
        except Exception as e:
            logger.warning(f"Could not schedule grab: {e}")

    def _create_widgets_if_needed(self) -> bool:
        """Create widgets if not already created.

        Returns:
            True if widgets created successfully, False otherwise
        """
        if self.widgets_created:
            return True

        logger.info("Creating widgets")
        try:
            for widget in self.winfo_children():
                widget.destroy()

            self._create_widgets()
            logger.info("Widgets created successfully")
            self.widgets_created = True
            return True
        except Exception as e:
            logger.error(f"Error creating widgets: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(
                    e, "Creating download options", "YouTube Dialog"
                )
            elif self.message_queue:
                self.message_queue.add_message(
                    Message(
                        text=f"Failed to create download options: {e!s}",
                        level=MessageLevel.ERROR,
                        title="Dialog Error",
                    )
                )
            return False

    def _show_main_interface(self) -> bool:
        """Show main interface.

        Returns:
            True if successful, False otherwise
        """
        if not hasattr(self, "main_frame"):
            logger.error("Main frame not found - widget creation may have failed")
            return False

        logger.debug("Packing main frame")
        try:
            self.main_frame.pack(fill="both", expand=True)
            logger.debug("Main frame packed successfully")
        except Exception as e:
            logger.error(f"Error packing main frame: {e}", exc_info=True)
            return False

        try:
            self.minsize(500, 400)
            logger.debug("Dialog size updated")
        except Exception as e:
            logger.warning(f"Error updating dialog size: {e}")

        try:
            self.update_idletasks()
        except Exception as e:
            logger.warning(f"Could not update idletasks for geometry: {e}")

        logger.debug("Showing main window")
        try:
            self._show_main_window()
        except Exception as e:
            logger.error(f"Error showing main window: {e}", exc_info=True)
            return False

        return True

    def _handle_metadata_fetched(self):
        """Handle metadata fetch completion - ONLY SHOWS DIALOG AFTER FETCH COMPLETE."""
        logger.info("=== _handle_metadata_fetched called ===")
        logger.info("Handling metadata fetch completion")
        self._metadata_handler_called = True
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
                self.error_handler.handle_service_failure(
                    "YouTube", "metadata fetch", error_msg, self.url
                )
            self._handle_metadata_error()
            return

        self._close_loading_and_show_dialog()

        if not self._create_widgets_if_needed():
            return

        if not self._show_main_interface():
            return

    def _schedule_main_window_show(self):
        """Schedule showing main window after loading overlay is completely gone."""
        self.after(100, self._show_main_window)

    def _show_main_window(self):
        """Show the main window after loading is complete."""
        logger.debug("Showing main window - ensuring visibility")
        try:
            self.lift()
            self.focus_force()  # Force focus to this window

            logger.debug("Updating UI with metadata")
            self._update_ui_with_metadata()

            try:
                self.update_idletasks()
            except Exception as e:
                logger.warning(f"Could not update idletasks in show_main_window: {e}")

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

        if self.video_metadata.title:
            self.name_entry.delete(0, "end")
            self.name_entry.insert(0, self.video_metadata.title)

        if self.video_metadata.available_qualities:
            self.quality_var.set(self.video_metadata.available_qualities[0])
            self.quality_menu.configure(values=self.video_metadata.available_qualities)

        if self.video_metadata.available_formats:
            self.format_var.set(self.video_metadata.available_formats[0])
            self.format_menu.configure(values=self.video_metadata.available_formats)

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

        self._on_format_change()

    def _create_widgets(self):
        """Create dialog widgets with scrolling support."""
        self.title("YouTube Downloader")
        self.geometry("600x700")
        self.minsize(500, 400)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")

        title_label = ctk.CTkLabel(
            self.main_frame,
            text="YouTube Video Downloader",
            font=("Roboto", 24, "bold"),
        )
        title_label.pack(pady=(0, 20))

        url_frame = ctk.CTkFrame(self.main_frame)
        url_frame.pack(fill="x", pady=(0, 20))

        url_label = ctk.CTkLabel(url_frame, text="URL:", font=("Roboto", 12, "bold"))
        url_label.pack(anchor="w", padx=(10, 5))

        url_display = ctk.CTkEntry(url_frame, font=("Roboto", 10))
        url_display.insert(0, self.url)
        url_display.configure(state="disabled")
        url_display.pack(fill="x", padx=10, pady=(0, 10))

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

        options_frame = ctk.CTkFrame(self.main_frame)
        options_frame.pack(fill="x", pady=(0, 20))

        options_label = ctk.CTkLabel(
            options_frame, text="Download Options:", font=("Roboto", 12, "bold")
        )
        options_label.pack(anchor="w", padx=(10, 5))

        quality_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        quality_frame.pack(fill="x", padx=10, pady=8)

        quality_label = ctk.CTkLabel(quality_frame, text="Quality:", font=("Roboto", 11))
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

        format_label = ctk.CTkLabel(quality_frame, text="Format:", font=("Roboto", 11))
        format_label.pack(side="left", padx=(0, 10))

        self.format_var = ctk.StringVar(value=self.config.ui.format_options[0])
        format_options = self.config.ui.format_options

        self.format_map = {
            "Video + Audio": "video",  # Combined video+audio file
            "Audio Only": "audio",  # Audio track only (MP3)
            "Video Only": "video_only",  # Video track only, no audio (M4V)
        }

        self.format_menu = ctk.CTkOptionMenu(
            quality_frame,
            variable=self.format_var,
            values=format_options,
            width=120,
            font=("Roboto", 10),
            command=lambda _x: self._on_format_change(),
        )
        self.format_menu.pack(side="left")

        self.format_frame = quality_frame

        self.subtitle_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        self.subtitle_frame.pack(fill="x", padx=10, pady=8)

        subtitle_label = ctk.CTkLabel(self.subtitle_frame, text="Subtitles:", font=("Roboto", 11))
        subtitle_label.pack(anchor="w", pady=(0, 5))

        self.subtitle_dropdown = SubtitleChecklist(
            self.subtitle_frame,
            placeholder="No subtitles available",
            height=120,
            on_change=self._on_subtitle_change,
        )
        self.subtitle_dropdown.pack(fill="both", expand=True)

        advanced_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        advanced_frame.pack(fill="x", padx=10, pady=5)

        self.playlist_var = ctk.BooleanVar(value=False)
        playlist_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Playlist (if URL is a playlist)",
            variable=self.playlist_var,
            font=("Roboto", 11),
        )
        playlist_check.pack(anchor="w", pady=2)

        self.thumbnail_var = ctk.BooleanVar(value=True)
        thumbnail_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Download Thumbnail",
            variable=self.thumbnail_var,
            font=("Roboto", 11),
        )
        thumbnail_check.pack(anchor="w", pady=2)

        self.metadata_var = ctk.BooleanVar(value=True)
        metadata_check = ctk.CTkCheckBox(
            advanced_frame,
            text="Embed Metadata",
            variable=self.metadata_var,
            font=("Roboto", 11),
        )
        metadata_check.pack(anchor="w", pady=2)

        advanced_options_frame = ctk.CTkFrame(self.main_frame)
        advanced_options_frame.pack(fill="x", pady=(0, 20))

        advanced_label = ctk.CTkLabel(
            advanced_options_frame,
            text="Advanced Options:",
            font=("Roboto", 12, "bold"),
        )
        advanced_label.pack(anchor="w", padx=(10, 5))

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
            font=("Roboto", 10),
        )
        speed_entry.pack(side="left")

        retry_frame = ctk.CTkFrame(advanced_options_frame, fg_color="transparent")
        retry_frame.pack(fill="x", padx=10, pady=5)

        retry_label = ctk.CTkLabel(retry_frame, text="Retries:", font=("Roboto", 10))
        retry_label.pack(side="left", padx=(0, 10))

        self.retries_var = ctk.StringVar(value="3")
        retry_entry = ctk.CTkEntry(
            retry_frame, textvariable=self.retries_var, width=50, font=("Roboto", 10)
        )
        retry_entry.pack(side="left", padx=(0, 20))

        concurrent_label = ctk.CTkLabel(retry_frame, text="Concurrent:", font=("Roboto", 10))
        concurrent_label.pack(side="left", padx=(0, 10))

        self.concurrent_var = ctk.StringVar(value="1")
        concurrent_entry = ctk.CTkEntry(
            retry_frame, textvariable=self.concurrent_var, width=50, font=("Roboto", 10)
        )
        concurrent_entry.pack(side="left")

        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(30, 0))

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

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            height=40,
            font=("Roboto", 12),
        )
        cancel_button.pack(side="right", padx=5)

        self.name_entry.focus()

    def _on_subtitle_change(self, selected_subtitles: list) -> None:
        """Handle subtitle selection change."""
        logger.debug(f"Subtitle selection: {len(selected_subtitles)} selected")
        self.selected_subtitles = selected_subtitles

    def _on_format_change(self) -> None:
        """Handle format selection change."""
        format_display = self.format_var.get()

        format_value = self.format_map.get(format_display, "video")

        self._update_quality_options_for_format(format_value)
        logger.debug(f"Format: {format_display} ({format_value})")

    def _update_quality_options_for_format(self, format_value: str) -> None:
        """Update available quality options based on format selection."""
        if format_value == "audio":
            audio_qualities = ["best", "high", "medium", "low"]
            if hasattr(self, "quality_menu"):
                current_quality = self.quality_var.get()
                self.quality_menu.configure(values=audio_qualities)
                if current_quality not in audio_qualities:
                    self.quality_var.set("high")
        else:
            video_qualities = self.config.youtube.video_qualities
            if hasattr(self, "quality_menu"):
                current_quality = self.quality_var.get()
                self.quality_menu.configure(values=video_qualities)
                if current_quality not in video_qualities:
                    self.quality_var.set(self.config.youtube.default_quality)

    def _handle_add_to_downloads(self):
        """Handle add to downloads button click."""
        try:
            self.add_button.configure(state="disabled")

            self.after(10, self._process_add_to_downloads)

        except Exception as e:
            logger.error(f"Error in add to downloads: {e}")
            import traceback

            traceback.print_exc()
            if hasattr(self, "add_button"):
                self.add_button.configure(state="normal")

    def _process_add_to_downloads(self):
        """Process add to downloads in a non-blocking way."""
        try:
            name = self.name_entry.get().strip()
            if not name:
                self._show_error("Please enter a name for this download")
                return

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

            format_display = self.format_var.get()
            format_value = self.format_map.get(format_display, "video")
            audio_only = format_value == "audio"
            video_only = format_value == "video_only"

            selected_subtitles = self.subtitle_dropdown.get_selected_subtitles()

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

            if self.on_download:
                self.on_download(download)

            self.after(100, self.destroy)

        except Exception as e:
            logger.error(f"Error processing add to downloads: {e}")
            import traceback

            traceback.print_exc()
        finally:
            if self.winfo_exists() and hasattr(self, "add_button"):
                self.add_button.configure(state="normal")

    def _schedule_ui_update(self, update_func: Callable) -> None:
        """Schedule UI update on main thread using centralized queue from MediaDownloaderApp."""
        root = self.winfo_toplevel()
        if hasattr(root, "run_on_main_thread"):
            root.run_on_main_thread(update_func)
        else:
            self.after(0, update_func)

    def _show_error(self, message: str):
        """Show error message temporarily."""
        error_label = ctk.CTkLabel(
            self, text=message, text_color="red", font=("Roboto", 11, "bold")
        )
        error_label.pack(pady=5)
        self.after(4000, error_label.destroy)
