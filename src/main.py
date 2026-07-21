import atexit
import contextlib
import importlib.util
import queue
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, cast

from src.utils.common import ensure_gui_available, resource_path, set_windows_dpi_awareness
from src.utils.logger import get_logger

sys.path.append(str(Path(__file__).parent.parent))

logger = get_logger(__name__)

# Windows DPI awareness must be set before ANY tkinter/CTk window is created
set_windows_dpi_awareness()

ensure_gui_available()
from tkinter import Menu  # noqa: E402

import customtkinter as ctk  # noqa: E402

# Initialize CTK's built-in theme so ThemeManager.theme is populated.
# This MUST happen before any CTk widget is created.
ctk.set_default_color_theme("blue")
ctk.set_appearance_mode("System")
# Cap widget scaling so Retina displays don't balloon everything.
# CustomTkinter auto-detects OS DPI and can go as high as 1.5-1.7x on
# Retina, which makes padded=16 render as 24-27 points — too loose.
# Pinning to a moderate value keeps the UI compact on all screens.
ctk.set_widget_scaling(1.15)

from src.core import Download, get_application_orchestrator  # noqa: E402
from src.core.config import AppConfig, get_config  # noqa: E402
from src.core.enums.download_status import DownloadStatus  # noqa: E402
from src.core.interfaces import DynamicUIContextProtocol  # noqa: E402
from src.ui.components.download_card_list import DownloadCardList  # noqa: E402
from src.ui.components.footer import AppFooter  # noqa: E402
from src.ui.components.header import AppHeader  # noqa: E402
from src.ui.components.url_entry import URLEntryFrame  # noqa: E402
from src.ui.utils.theme_manager import get_theme_manager  # noqa: E402
from src.ui.visual_system import GradientBackdrop, resolve_palette  # noqa: E402

if TYPE_CHECKING:
    from src.application.orchestrator import ApplicationOrchestrator


def _check_playwright_installation() -> None:
    try:
        if not importlib.util.find_spec("playwright"):
            raise ImportError("playwright module not found")
        logger.info("[MAIN_APP] Playwright is installed")
    except ImportError as original_error:
        logger.error("[MAIN_APP] Playwright is NOT installed - showing critical error")

        # Create a minimal window to show the error
        error_window = ctk.CTk()
        error_window.title("CRITICAL: Playwright Not Installed")
        screen_w = error_window.winfo_screenwidth()
        screen_h = error_window.winfo_screenheight()
        w = min(600, int(screen_w * 0.9))
        h = min(400, int(screen_h * 0.9))
        error_window.geometry(f"{w}x{h}")

        # Center the window
        error_window.update_idletasks()
        width = error_window.winfo_width()
        height = error_window.winfo_height()
        x = (error_window.winfo_screenwidth() // 2) - (width // 2)
        y = (error_window.winfo_screenheight() // 2) - (height // 2)
        error_window.geometry(f"{width}x{height}+{x}+{y}")

        # Error message
        error_frame = ctk.CTkFrame(error_window, fg_color="transparent")
        error_frame.pack(fill="both", expand=True, padx=20, pady=20)

        title_label = ctk.CTkLabel(
            error_frame,
            text="PLAYWRIGHT NOT INSTALLED",
            font=("Arial", 20, "bold"),
            text_color="red",
        )
        title_label.pack(pady=(0, 20))

        message = (
            "The auto-cookie generation system requires Playwright.\n\n"
            "Without it, age-restricted YouTube videos will FAIL to download.\n\n"
            "To fix this, run these commands in your terminal:\n\n"
            "   pip install playwright\n"
            "   playwright install chromium\n\n"
            "Then restart the application.\n\n"
            "Click 'Continue Anyway' to run without cookies (NOT RECOMMENDED)\n"
            "or 'Exit' to close and install Playwright first."
        )

        message_label = ctk.CTkLabel(error_frame, text=message, font=("Arial", 12), justify="left")
        message_label.pack(pady=10)

        # Buttons
        button_frame = ctk.CTkFrame(error_frame, fg_color="transparent")
        button_frame.pack(pady=20)

        # Track which button was clicked
        exit_clicked = {"value": False}

        def continue_anyway() -> None:
            logger.warning("[MAIN_APP] User chose to continue without Playwright")
            error_window.destroy()

        def exit_app() -> None:
            logger.info("[MAIN_APP] User chose to exit and install Playwright")
            exit_clicked["value"] = True

            print("\n" + "=" * 70)
            print("  PLAYWRIGHT INSTALLATION REQUIRED")
            print("=" * 70)
            print("\nTo install Playwright and Chromium, run these commands:\n")
            print("  pip install playwright")
            print("  playwright install chromium")
            print("\nAfter installation, restart the application:")
            print("  uv run -m src.main")
            print("\n" + "=" * 70 + "\n")

            # Destroy window to exit mainloop
            error_window.destroy()

        # Exit button - recommended action
        exit_button = ctk.CTkButton(
            button_frame,
            text="Exit",
            command=exit_app,
            fg_color="red",
            hover_color="darkred",
            width=150,
        )
        exit_button.pack(side="left", padx=10)

        # Continue button - not recommended
        continue_button = ctk.CTkButton(
            button_frame,
            text="Continue Without Playwright",
            command=continue_anyway,
            fg_color="gray",
            hover_color="darkgray",
            width=250,
        )
        continue_button.pack(side="left", padx=10)

        # Prevent window from being closed without clicking a button
        error_window.protocol("WM_DELETE_WINDOW", exit_app)

        # Run the error window - this BLOCKS until user clicks a button
        error_window.mainloop()

        # Check which button was clicked
        if exit_clicked["value"]:
            logger.info("[MAIN_APP] Exiting program as user requested")
            raise SystemExit(1) from None

        # If we reach here, user clicked Continue Anyway
        logger.warning("[MAIN_APP] Continuing without Playwright as user requested")
        raise original_error


class MediaDownloaderApp(ctk.CTk):
    def __init__(self, config: AppConfig | None = None) -> None:
        super().__init__()

        self.config = config or get_config()

        self.title(self.config.ui.app_title)

        # Screen-aware initial geometry (90% of screen, capped at 1200x800)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        init_w = min(int(screen_w * 0.9), 1200)
        init_h = min(int(screen_h * 0.9), 800)
        self.geometry(f"{init_w}x{init_h}")
        self.minsize(700, 500)

        # Set window icon
        icon_path = resource_path("assets/media_downloader.ico")
        if icon_path.exists():
            self.after(100, lambda: self.iconbitmap(str(icon_path)))

        self.thread_queue = queue.Queue(maxsize=100)
        self._queue_processor_running = True
        self.after(100, self._process_thread_queue)

        application_orchestrator = cast(
            type["ApplicationOrchestrator"],
            get_application_orchestrator(),
        )
        self.orchestrator = application_orchestrator(self, config=self.config)

        self.theme_manager = get_theme_manager(self, config=self.config)
        palette = resolve_palette(self.theme_manager)
        self.configure(fg_color=palette.background_mid)

        self.update_idletasks()

        # One real gradient canvas owns the window background.  The four
        # production regions are direct children so spacing reveals it.
        self.background = GradientBackdrop(self, theme_manager=self.theme_manager)
        self.main_frame = self.background
        self._create_ui()
        self._setup_layout()
        self._setup_menu()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        atexit.register(self._graceful_shutdown)

        logger.info("Media Downloader initialized")

        self.after(100, self.orchestrator.check_connectivity)

    def _process_thread_queue(self) -> None:
        if not self._queue_processor_running:
            return
        try:
            max_tasks_per_cycle = 10
            tasks_processed = 0

            while tasks_processed < max_tasks_per_cycle and not self.thread_queue.empty():
                try:
                    func = self.thread_queue.get_nowait()
                    func()
                    tasks_processed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"[MAIN_APP] Error executing queued task: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[MAIN_APP] Error in event loop: {e}", exc_info=True)
        finally:
            if self._queue_processor_running:
                self.after(33, self._process_thread_queue)

    def run_on_main_thread(self, func: Callable[[], None]) -> None:
        try:
            if self.thread_queue.full():
                with contextlib.suppress(queue.Empty):
                    self.thread_queue.get_nowait()
            self.thread_queue.put_nowait(func)
        except queue.Full:
            pass

    def _create_ui(self) -> None:
        from src.ui.components.settings_panel import SettingsPanel

        coord = self.orchestrator.event_coordinator

        self.header_frame = AppHeader(
            self.main_frame,
            self.theme_manager,
            self.config,
            title=self.config.ui.app_title,
        )

        def on_add_url(url: str, name: str) -> None:
            if not self.orchestrator.link_detector.detect_and_handle(
                url, cast(DynamicUIContextProtocol, coord)
            ):
                logger.info(f"[MAIN_APP] No handler found for {url}, treating as generic download")
                coord.platform_download("generic", url, name)

        def on_youtube_detected(url: str) -> None:
            self.orchestrator.link_detector.detect_and_handle(
                url, cast(DynamicUIContextProtocol, coord)
            )

        self.url_entry = URLEntryFrame(
            self.main_frame,
            on_add=on_add_url,
            on_youtube_detected=on_youtube_detected,
            theme_manager=self.theme_manager,
        )

        def on_clear() -> None:
            coord.downloads.clear_downloads()

        def on_download() -> None:
            downloads = coord.downloads.get_downloads()
            coord.downloads.start_downloads(downloads, coord.downloads_folder)

        def on_manage_files() -> None:
            coord.show_file_manager()

        self.footer = AppFooter(
            self.main_frame,
            on_clear=on_clear,
            on_download=on_download,
            on_manage_files=on_manage_files,
            theme_manager=self.theme_manager,
        )

        def on_remove(download: Download) -> None:
            downloads = coord.downloads.get_downloads()
            for index, candidate in enumerate(downloads):
                if candidate is download or (
                    candidate.url == download.url and candidate.name == download.name
                ):
                    coord.downloads.remove_downloads([index])
                    return

        def on_queue_summary(downloads: Sequence[Download]) -> None:
            self.footer.update_queue(downloads)
            active = sum(
                item.status
                in {DownloadStatus.PENDING, DownloadStatus.DOWNLOADING, DownloadStatus.PAUSED}
                for item in downloads
            )
            self.header_frame.set_count(active, len(downloads))

        self.download_list = DownloadCardList(
            self.main_frame,
            on_remove=on_remove,
            on_summary=on_queue_summary,
            theme_manager=self.theme_manager,
        )

        # Preserve the existing orchestrator component keys while presenting a
        # single cohesive footer in the UI.
        self.action_buttons = self.footer
        self.status_bar = self.footer

        self.settings_panel = SettingsPanel(
            self.main_frame,
            theme_manager=self.theme_manager,
            config=self.config,
        )
        self.header_frame.settings_button.configure(command=self.settings_panel.toggle)

        self.orchestrator.set_ui_components(
            url_entry=self.url_entry,
            download_list=self.download_list,
            action_buttons=self.footer,
            status_bar=self.footer,
        )
        logger.info("[MAIN_APP] Queue-first UI connected to orchestrator")

    def _setup_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.background.grid(row=0, column=0, sticky="nsew")

        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=0)
        self.main_frame.grid_rowconfigure(2, weight=1)

        # Four regions: compact header, link input, expanding queue, footer.
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=18, pady=(14, 8))
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 9))
        self.download_list.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 9))
        self.footer.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 14))

    def _setup_menu(self) -> None:
        menubar = Menu(self)
        self.configure(menu=menubar)

        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Network Status",
            command=self.orchestrator.event_coordinator.show_network_status,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

    def _graceful_shutdown(self) -> None:
        try:
            logger.info("[MAIN_APP] Graceful shutdown - persisting settings")

            if hasattr(self, "theme_manager"):
                try:
                    self.theme_manager._persist_theme()
                except Exception as e:
                    logger.error(f"[MAIN_APP] Failed to persist theme: {e}", exc_info=True)

            if hasattr(self, "orchestrator"):
                try:
                    self.orchestrator.cleanup()
                except Exception as e:
                    logger.error(
                        f"[MAIN_APP] Error during orchestrator cleanup: {e}",
                        exc_info=True,
                    )

            logger.info("[MAIN_APP] Graceful shutdown complete")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during graceful shutdown: {e}", exc_info=True)

    def _on_closing(self) -> None:
        logger.info("[MAIN_APP] Application closing - cleaning up")
        self._queue_processor_running = False
        self._graceful_shutdown()

        try:
            self.destroy()
            logger.info("[MAIN_APP] Application closed")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during window destruction: {e}")


if __name__ == "__main__":
    try:
        # Step 1: Verify Playwright Python package is available
        logger.info("[MAIN_APP] Step 1/3: Checking Playwright installation...")
        _check_playwright_installation()

        # Step 2: Ensure Chromium browser is available (non-blocking).
        # Cookie init threads will wait on _chromium_ready event before launching browsers.
        logger.info("[MAIN_APP] Step 2/3: Checking Chromium availability...")
        try:
            from src.services.cookies.playwright_bootstrap import (
                is_chromium_installed,
            )

            if not is_chromium_installed():
                logger.info("[MAIN_APP] Chromium not found - will install on first launch")
        except Exception as e:
            logger.warning(f"[MAIN_APP] Playwright bootstrap check skipped: {e}")

        # Step 2b: Verify ffmpeg is available (no download — installer handles this).
        logger.info("[MAIN_APP] Step 2b: Checking ffmpeg availability...")
        try:
            from src.utils.ffmpeg import is_ffmpeg_available

            if not is_ffmpeg_available():
                logger.warning("[MAIN_APP] ffmpeg not found - video merging may not work")
        except Exception as e:
            logger.warning(f"[MAIN_APP] ffmpeg check skipped: {e}")

        # Step 3: Create and display the main application window
        logger.info("[MAIN_APP] Step 3/3: Initializing application window...")
        app = MediaDownloaderApp()

        # Start Chromium install in background after window is visible
        try:
            from src.services.cookies.playwright_bootstrap import (
                detect_system_chrome,
                ensure_playwright_ready,
                is_chromium_installed,
            )

            if not is_chromium_installed():
                system_chrome = detect_system_chrome()
                if system_chrome:
                    from src.services.cookies.playwright_bootstrap import _chromium_ready

                    _chromium_ready.set()
                    logger.info(f"[MAIN_APP] Using system browser: {system_chrome}")
                else:
                    app.status_bar.show_message("Setting up browser (first time only)...")
                    logger.info("[MAIN_APP] Chromium not found - installing in background...")

                    def _bg_install():
                        from src.services.cookies.playwright_bootstrap import _chromium_ready

                        ensure_playwright_ready(root_window=app)
                        if _chromium_ready.is_set():
                            app.run_on_main_thread(
                                lambda: app.status_bar.show_message("Browser ready")
                            )

                    import threading

                    threading.Thread(target=_bg_install, daemon=True).start()
            else:
                from src.services.cookies.playwright_bootstrap import _chromium_ready

                _chromium_ready.set()
                logger.info("[MAIN_APP] Browser already available")
        except Exception:
            pass

        app.mainloop()

    except (SystemExit, ImportError) as e:
        logger.error(f"[MAIN_APP] Missing dependencies: {e}", exc_info=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"[MAIN_APP] Unexpected error - exiting: {e}", exc_info=True)
        sys.exit(1)
