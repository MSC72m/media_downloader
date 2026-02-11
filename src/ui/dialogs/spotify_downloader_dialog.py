import threading
from collections.abc import Callable
from typing import Any

import customtkinter as ctk
import PIL.Image
import PIL.ImageTk

from src.core.config import AppConfig, get_config
from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.core.models import Download
from src.services.events.queue import Message

from ...utils.logger import get_logger
from ...utils.window import WindowCenterMixin, close_loading_dialog
from ..components.loading_dialog import LoadingDialog

logger = get_logger(__name__)


class SpotifyDownloaderDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Dialog for downloading Spotify content via YouTube matches.

    Follows YouTube dialog pattern for consistency:
    - Uses LoadingDialog for async operations
    - Shows Spotify metadata (thumbnail, title, type)
    - Shows YouTube search results for user selection
    - For playlists: Shows track list with YouTube match status
    - Uses same lifecycle: init → load metadata → show UI → user interaction
    """

    def __init__(
        self,
        parent,
        url: str,
        on_download: Callable | None = None,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        config: AppConfig = get_config(),
    ):
        super().__init__(parent)

        self.config = config
        self.url = url
        self.on_download = on_download
        self.error_handler = error_handler
        self.message_queue = message_queue
        self.loading_overlay: LoadingDialog | None = None
        self.widgets_created = False
        self._metadata_handler_called = False
        self._metadata_ready = False
        self.spotify_metadata = None
        self.youtube_results: list[dict[str, Any]] = []
        self.selected_youtube_result: dict[str, Any] | None = None
        self.selected_track_index: int | None = None

        self.title("Spotify Downloader")
        self.geometry("900x950")
        self.resizable(True, True)
        self.minsize(700, 800)

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
                self.geometry("900x950")

        self.after(10, self._start_metadata_fetch)

        self._poll_metadata_completion()

    def _poll_metadata_completion(self):
        """Poll for metadata completion from main thread (YouTube pattern)."""
        if (
            self.spotify_metadata
            and self.spotify_metadata.get("error")
            and not self._metadata_handler_called
        ):
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
        """Safely deiconify window (YouTube pattern)."""
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

    def _start_metadata_fetch(self):
        """Start metadata fetching (YouTube pattern)."""
        logger.debug("Starting metadata fetch process")

        self.withdraw()

        self._create_loading_overlay()
        self._fetch_metadata_async()

    def _create_loading_overlay(self):
        """Create loading overlay for metadata fetching (YouTube pattern)."""
        logger.debug("Creating loading overlay")

        try:
            self.loading_overlay = LoadingDialog(
                self.master,
                message="Extracting Spotify metadata...",
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

    def _fetch_metadata_async(self):
        """Fetch metadata asynchronously (YouTube pattern)."""

        def fetch_worker():
            try:
                from src.services.spotify.downloader import SpotifyDownloader

                downloader = SpotifyDownloader(
                    error_handler=self.error_handler,
                    config=self.config,
                )

                metadata = downloader.get_metadata(self.url)

                if not metadata or not metadata.get("title"):
                    self.spotify_metadata = {"error": "Failed to extract metadata"}
                    self._metadata_ready = True
                    return

                self.spotify_metadata = metadata
                logger.info("Metadata fetch completed")
                logger.info(f"Metadata type: {metadata.get('type', 'unknown')}")

                if metadata.get("type") in ("album", "playlist"):
                    tracks = metadata.get("tracks", [])
                    logger.info(f"Found {len(tracks)} tracks in playlist/album")
                    self._load_youtube_results_for_tracks(tracks, downloader)
                else:
                    self._load_youtube_result_for_single_track(metadata, downloader)

                self._metadata_ready = True

            except Exception as e:
                logger.error(f"Error fetching metadata: {e}", exc_info=True)
                self.spotify_metadata = {"error": str(e)}
                self._metadata_ready = True

        threading.Thread(target=fetch_worker, daemon=True).start()

    def _load_youtube_result_for_single_track(self, metadata: dict, downloader):
        """Load YouTube search results for single track."""
        artist, track = downloader._parse_artist_track(metadata["title"])

        logger.info(f"Searching YouTube for: {artist} - {track}")
        results = downloader.get_search_results(artist, track)
        self.youtube_results = results
        logger.info(f"Found {len(results)} YouTube results")

    def _load_youtube_results_for_tracks(self, tracks: list[dict], downloader):
        """Load YouTube search results for all tracks in playlist/album."""
        logger.info(f"Searching YouTube for {len(tracks)} tracks")

        for track_data in tracks:
            try:
                track_title = track_data.get("title", "")
                artist, track = downloader._parse_artist_track(track_title)

                results = downloader.get_search_results(artist, track)

                track_data["youtube_results"] = results
                track_data["best_match"] = (
                    downloader._select_best_match(track, results) if results else None
                )

            except Exception as e:
                logger.warning(
                    f"Error searching YouTube for track {track_data.get('position')}: {e}"
                )
                track_data["youtube_results"] = []
                track_data["best_match"] = None

        logger.info("YouTube search completed for all tracks")

    def _handle_metadata_error(self):
        """Handle metadata fetch error (YouTube pattern)."""
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

        error_msg = "Failed to extract Spotify metadata. Check URL and try again."
        if self.spotify_metadata and self.spotify_metadata.get("error"):
            error_msg = f"Failed to extract Spotify metadata: {self.spotify_metadata['error']}"

        if self.message_queue:
            self.message_queue.add_message(
                Message(
                    text=error_msg,
                    level=MessageLevel.ERROR,
                    title="Spotify Metadata Error",
                )
            )

        try:
            self.destroy()
        except Exception as e:
            logger.error(f"Error destroying dialog: {e}")

    def _close_loading_and_show_dialog(self) -> None:
        """Close loading overlay and show main dialog (YouTube pattern)."""
        if self.loading_overlay:
            logger.info("Closing loading overlay")
            close_loading_dialog(self.loading_overlay, error_path=False)
            self.loading_overlay = None

        logger.info("Showing Spotify options dialog after metadata fetch complete")
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
        """Create widgets if not already created (YouTube pattern)."""
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
                    e, "Creating download options", "Spotify Dialog"
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
        """Show main interface (YouTube pattern)."""
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
            self.minsize(700, 800)
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
        """Handle metadata fetch completion (YouTube pattern)."""
        logger.info("=== _handle_metadata_fetched called ===")
        logger.info("Handling metadata fetch completion")
        self._metadata_handler_called = True
        logger.info(f"Spotify metadata: {self.spotify_metadata}")
        logger.info(f"Spotify metadata type: {type(self.spotify_metadata)}")

        if self.spotify_metadata and self.spotify_metadata.get("error"):
            error_msg = self.spotify_metadata.get("error", "Unknown error")
            logger.error(f"Metadata fetch error: {error_msg}")
            if self.error_handler:
                self.error_handler.handle_service_failure(
                    "Spotify", "metadata fetch", error_msg, self.url
                )
            self._handle_metadata_error()
            return

        self._close_loading_and_show_dialog()

        if not self._create_widgets_if_needed():
            return

        if not self._show_main_interface():
            return

    def _show_main_window(self):
        """Show main window after loading is complete (YouTube pattern)."""
        logger.debug("Showing main window - ensuring visibility")
        try:
            self.lift()
            self.focus_force()

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
        """Update UI components with fetched metadata (YouTube pattern)."""
        if not self.spotify_metadata:
            return

        if self.spotify_metadata.get("title"):
            title = self.spotify_metadata["title"]
            logger.info(f"Updating UI with title: {title}")

    def _create_widgets(self):
        """Create dialog widgets with scrolling support (YouTube pattern)."""
        self.title("Spotify Downloader")
        self.geometry("900x950")
        self.minsize(700, 800)

        self.scrollable_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")

        title_label = ctk.CTkLabel(
            self.main_frame,
            text="Spotify Downloader",
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

        self._add_metadata_display()

        content_type = self.spotify_metadata.get("type", "unknown")
        if content_type in ("album", "playlist"):
            self._add_playlist_section()
        elif content_type == "track":
            self._add_single_track_section()

        button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(30, 0))

        self.download_button = ctk.CTkButton(
            button_frame,
            text="Download Selected",
            command=self._handle_download,
            width=150,
            height=40,
            font=("Roboto", 12, "bold"),
            fg_color="#1DB954",
            hover_color="#1ed760",
        )
        self.download_button.pack(side="right", padx=5)
        self.download_button.configure(state="disabled")

        cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            height=40,
            font=("Roboto", 12),
        )
        cancel_button.pack(side="right", padx=5)

    def _add_metadata_display(self):
        """Add Spotify metadata display with thumbnail (YouTube pattern)."""
        if not self.spotify_metadata:
            return

        metadata_frame = ctk.CTkFrame(self.main_frame)
        metadata_frame.pack(fill="x", pady=(0, 20))

        info_frame = ctk.CTkFrame(metadata_frame)
        info_frame.pack(fill="x", padx=10, pady=10)

        if self.spotify_metadata.get("thumbnail"):
            self._add_thumbnail_preview(info_frame)

        title = self.spotify_metadata.get("title", "Unknown")
        title_label = ctk.CTkLabel(
            info_frame,
            text=title,
            font=("Roboto", 18, "bold"),
        )
        title_label.pack(anchor="w", pady=(0, 10))

        content_type = self.spotify_metadata.get("type", "track")
        type_label = ctk.CTkLabel(
            info_frame,
            text=content_type.upper(),
            font=("Roboto", 10, "bold"),
            fg_color="#1DB954",
            corner_radius=4,
        )
        type_label.pack(anchor="w")

    def _add_thumbnail_preview(self, parent_frame):
        """Add thumbnail preview (YouTube pattern)."""
        if not self.spotify_metadata or not self.spotify_metadata.get("thumbnail"):
            return

        logger.debug("[SPOTIFY_DIALOG] Adding thumbnail preview")

        try:
            import io

            import requests

            thumbnail_url = self.spotify_metadata["thumbnail"]
            response = requests.get(thumbnail_url, timeout=10)
            response.raise_for_status()

            image = PIL.Image.open(io.BytesIO(response.content))
            image.thumbnail((200, 200))

            photo = PIL.ImageTk.PhotoImage(image)

            thumbnail_container = ctk.CTkFrame(
                parent_frame,
                corner_radius=12,
                fg_color=("#1DB954", "#191414"),
                border_width=2,
                border_color=("#1DB954", "#191414"),
            )
            thumbnail_container.pack(side="left", padx=(0, 15))

            thumbnail_label = ctk.CTkLabel(
                thumbnail_container,
                image=photo,
                text="",
            )
            thumbnail_label.pack(padx=10, pady=10)
            thumbnail_label.image = photo
            self._thumbnail_photo = photo

            logger.debug("[SPOTIFY_DIALOG] Thumbnail preview added successfully")

        except Exception as e:
            logger.warning(f"[SPOTIFY_DIALOG] Failed to load thumbnail: {e}")

    def _add_single_track_section(self):
        """Add single track YouTube search results section (YouTube pattern)."""
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", pady=(0, 20))

        section_label = ctk.CTkLabel(
            section_frame,
            text="YouTube Search Results - Select One:",
            font=("Roboto", 14, "bold"),
        )
        section_label.pack(anchor="w", padx=10, pady=(10, 10))

        self.result_radio_var = ctk.StringVar()
        self.result_checkboxes: dict[int, ctk.CTkCheckBox] = {}

        for i, result in enumerate(self.youtube_results):
            self._add_search_result_item(section_frame, result, i)

    def _add_search_result_item(self, parent_frame, result: dict, index: int):
        """Add a single YouTube search result item (YouTube pattern)."""
        result_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        result_frame.pack(fill="x", padx=10, pady=5)

        title = result.get("title", "Unknown")
        duration = result.get("duration", 0)
        duration_str = f"{int(duration // 60)}:{int(duration % 60):02d}" if duration else "Unknown"

        var = ctk.BooleanVar(value=False)
        self.result_checkboxes[index] = var

        checkbox = ctk.CTkCheckBox(
            result_frame,
            text=f"{title} ({duration_str})",
            variable=var,
            font=("Roboto", 11),
            command=lambda idx=index, v=var: self._on_result_selected(idx, v.get()),
        )
        checkbox.pack(fill="x")

    def _add_playlist_section(self):
        """Add playlist/album track list section (YouTube pattern)."""
        section_frame = ctk.CTkFrame(self.main_frame)
        section_frame.pack(fill="x", pady=(0, 20))

        info_label = ctk.CTkLabel(
            section_frame,
            text="Tracks - Select tracks to download:",
            font=("Roboto", 14, "bold"),
        )
        info_label.pack(anchor="w", padx=10, pady=(10, 5))

        count_label = ctk.CTkLabel(
            section_frame,
            text=f"{len(self.spotify_metadata.get('tracks', []))} tracks found",
            font=("Roboto", 11),
            text_color="gray",
        )
        count_label.pack(anchor="w", padx=10, pady=(0, 10))

        track_list_frame = ctk.CTkScrollableFrame(section_frame, height=400)
        track_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.track_checkboxes: dict[int, ctk.CTkCheckBox] = {}

        for track_data in self.spotify_metadata.get("tracks", []):
            position = track_data.get("position", 0)
            self._add_track_item(track_list_frame, track_data, position)

    def _add_track_item(self, parent_frame, track_data: dict, position: int):
        """Add a single track item with YouTube match info (YouTube pattern)."""
        track_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        track_frame.pack(fill="x", pady=5)

        title = track_data.get("title", "Unknown")

        var = ctk.BooleanVar(value=False)
        self.track_checkboxes[position] = var

        checkbox = ctk.CTkCheckBox(
            track_frame,
            text=title,
            variable=var,
            font=("Roboto", 11),
            command=lambda pos=position, v=var: self._on_track_selected(pos, v.get()),
        )
        checkbox.pack(fill="x")

        best_match = track_data.get("best_match")
        if best_match:
            match_label = ctk.CTkLabel(
                track_frame,
                text=f"✓ Match found: {best_match.get('title', 'Unknown')[:40]}...",
                font=("Roboto", 9),
                text_color="#28a745",
            )
            match_label.pack(anchor="w", padx=(30, 0), pady=(0, 5))
        else:
            no_match_label = ctk.CTkLabel(
                track_frame,
                text="✗ No match found",
                font=("Roboto", 9),
                text_color="#dc3545",
            )
            no_match_label.pack(anchor="w", padx=(30, 0), pady=(0, 5))

    def _on_result_selected(self, index: int, selected: bool):
        """Handle YouTube search result selection (YouTube pattern)."""
        if selected:
            for i, checkbox in self.result_checkboxes.items():
                if i != index:
                    checkbox.set(False)

            self.selected_youtube_result = self.youtube_results[index]
            logger.info(f"Selected YouTube result: {self.selected_youtube_result.get('title')}")

            if self.download_button:
                self.download_button.configure(state="normal")

        elif self.selected_youtube_result and index == self.youtube_results.index(
            self.selected_youtube_result
        ):
            self.selected_youtube_result = None

            if self.selected_track_index is None:
                self.download_button.configure(state="disabled")

    def _on_track_selected(self, position: int, selected: bool):
        """Handle track selection (YouTube pattern)."""
        if selected:
            for i, checkbox in self.track_checkboxes.items():
                if i != position:
                    checkbox.set(False)

            self.selected_track_index = position
            logger.info(f"Selected track at position: {position}")

            if self.download_button:
                self.download_button.configure(state="normal")
        elif self.selected_track_index == position:
            self.selected_track_index = None

            if not any(var.get() for var in self.track_checkboxes.values()):
                self.download_button.configure(state="disabled")

    def _handle_download(self):
        """Handle download button click (YouTube pattern)."""
        try:
            self.download_button.configure(state="disabled")

            self.after(10, self._process_download)

        except Exception as e:
            logger.error(f"Error in download button handler: {e}", exc_info=True)
            import traceback

            traceback.print_exc()
            if hasattr(self, "download_button"):
                self.download_button.configure(state="normal")

    def _process_download(self):
        """Process download in a non-blocking way (YouTube pattern)."""
        try:
            content_type = self.spotify_metadata.get("type", "unknown")

            if content_type == "track":
                self._process_single_track_download()
            elif content_type in ("album", "playlist"):
                self._process_playlist_download()
            else:
                self._show_error("Unsupported content type")

        except Exception as e:
            logger.error(f"Error processing download: {e}", exc_info=True)
            import traceback

            traceback.print_exc()
        finally:
            if self.winfo_exists() and hasattr(self, "download_button"):
                self.download_button.configure(state="normal")

    def _process_single_track_download(self):
        """Process single track download."""
        if not self.selected_youtube_result:
            self._show_error("Please select a YouTube video to download")
            return

        youtube_url = self.selected_youtube_result.get("webpage_url")
        title = self.selected_youtube_result.get("title", "Spotify Track")
        filename = f"{title}.mp3"

        download = Download(
            url=youtube_url,
            name=filename,
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
        )

        if self.on_download:
            self.on_download(download)

        logger.info(f"Added download: {filename}")
        self.after(100, self.destroy)

    def _process_playlist_download(self):
        """Process playlist/album download."""
        if self.selected_track_index is None:
            self._show_error("Please select at least one track to download")
            return

        tracks = self.spotify_metadata.get("tracks", [])
        track_data = tracks[self.selected_track_index]

        youtube_url = None
        title = None
        if track_data.get("best_match"):
            youtube_url = track_data["best_match"].get("webpage_url")
            title = track_data["best_match"].get("title", track_data.get("title", "Spotify Track"))

        if not youtube_url:
            self._show_error("No YouTube match found for selected track")
            return

        filename = f"{title}.mp3"

        download = Download(
            url=youtube_url,
            name=filename,
            service_type="spotify",
            audio_only=True,
            quality="best",
            format="audio",
        )

        if self.on_download:
            self.on_download(download)

        logger.info(f"Added download: {filename}")
        self.after(100, self.destroy)

    def _parse_track_name_for_file(self, track_title: str | None = None) -> tuple[str, str]:
        """Parse artist and track for filename."""
        title = track_title or self.spotify_metadata.get("title", "Unknown Track")

        from src.services.spotify.downloader import SpotifyDownloader

        return SpotifyDownloader._parse_artist_track(title)

    def _show_error(self, message: str):
        """Show error message temporarily (YouTube pattern)."""
        error_label = ctk.CTkLabel(
            self, text=message, text_color="red", font=("Roboto", 11, "bold")
        )
        error_label.pack(pady=5)
        self.after(4000, error_label.destroy)

    def _schedule_ui_update(self, update_func: Callable) -> None:
        """Schedule UI update on main thread (YouTube pattern)."""
        root = self.winfo_toplevel()
        if hasattr(root, "run_on_main_thread"):
            root.run_on_main_thread(update_func)
        else:
            self.after(0, update_func)
