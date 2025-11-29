import contextlib
import queue
import sys
from pathlib import Path

from src.utils.common import ensure_gui_available
from src.utils.logger import get_logger

sys.path.append(str(Path(__file__).parent.parent))

logger = get_logger(__name__)


ensure_gui_available()
from tkinter import Menu  # noqa: E402

import customtkinter as ctk  # noqa: E402

from src.core import get_application_orchestrator  # noqa: E402
from src.core.config import get_config  # noqa: E402
from src.ui.components.download_list import DownloadListView  # noqa: E402
from src.ui.components.main_action_buttons import ActionButtonBar  # noqa: E402
from src.ui.components.options_bar import OptionsBar  # noqa: E402
from src.ui.components.status_bar import StatusBar  # noqa: E402
from src.ui.components.theme_switcher import ThemeSwitcher  # noqa: E402
from src.ui.components.url_entry import URLEntryFrame  # noqa: E402
from src.ui.utils.theme_manager import get_theme_manager  # noqa: E402


def _check_playwright_installation():
    try:
        import playwright  # noqa: F401

        logger.info("[MAIN_APP] Playwright is installed")
    except ImportError as original_error:
        logger.error("[MAIN_APP] Playwright is NOT installed - showing critical error")

        # Create a minimal window to show the error
        error_window = ctk.CTk()
        error_window.title("CRITICAL: Playwright Not Installed")
        error_window.geometry("600x400")

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
            text="⚠️  PLAYWRIGHT NOT INSTALLED  ⚠️",
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

        def continue_anyway():
            logger.warning("[MAIN_APP] User chose to continue without Playwright")
            error_window.destroy()

        def exit_app():
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
    def __init__(self):
        super().__init__()

        self.config = get_config()

        self.title(self.config.ui.app_title)
        self.geometry("1000x700")

        self.thread_queue = queue.Queue(maxsize=100)
        self.after(100, self._process_thread_queue)

        application_orchestrator = get_application_orchestrator()
        self.orchestrator = application_orchestrator(self)

        self.theme_manager = get_theme_manager(self)

        self.update()

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._create_ui()
        self._setup_layout()
        self._setup_menu()

        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        import atexit

        atexit.register(self._graceful_shutdown)

        logger.info("Media Downloader initialized")

        self.after(100, self.orchestrator.check_connectivity)

    def _process_thread_queue(self):
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
            self.after(33, self._process_thread_queue)

    def run_on_main_thread(self, func):
        try:
            if self.thread_queue.full():
                with contextlib.suppress(queue.Empty):
                    self.thread_queue.get_nowait()
            self.thread_queue.put_nowait(func)
        except queue.Full:
            pass

    def _create_ui(self):
        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent", corner_radius=0)
        self.header_frame.grid_columnconfigure(0, weight=1)
        self.header_frame.grid_columnconfigure(1, weight=0)

        app_title = self.config.ui.app_title
        self.title_label = ctk.CTkLabel(
            self.header_frame, text=app_title, font=("Roboto", 26, "bold")
        )
        self.title_label.grid(row=0, column=0, sticky="w", pady=8)

        self.theme_switcher = ThemeSwitcher(self.header_frame, self.theme_manager)
        self.theme_switcher.grid(row=0, column=1, sticky="e", pady=8, padx=(20, 0))

        coord = self.orchestrator.event_coordinator

        def on_add_url(url: str, name: str) -> None:
            handler_found = self.orchestrator.link_detector.detect_and_handle(url, coord)

            if not handler_found:
                logger.info(f"[MAIN_APP] No handler found for {url}, treating as generic download")
                coord.platform_download("generic", url, name)

        def on_youtube_detected(url: str) -> None:
            self.orchestrator.link_detector.detect_and_handle(url, coord)

        self.url_entry = URLEntryFrame(
            self.main_frame,
            on_add=on_add_url,
            on_youtube_detected=on_youtube_detected,
            theme_manager=self.theme_manager,
        )

        self.options_bar = OptionsBar(self.main_frame, theme_manager=self.theme_manager)

        self.download_list = DownloadListView(
            self.main_frame,
            on_selection_change=lambda sel: self.action_buttons.update_button_states(
                has_selection=len(sel) > 0,
                has_items=len(coord.downloads.get_downloads()) > 0,
            ),
            theme_manager=self.theme_manager,
        )

        logger.info("[MAIN_APP] Creating ActionButtonBar")

        def on_remove() -> None:
            coord.downloads.remove_downloads(self.download_list.get_selected_indices())

        def on_clear() -> None:
            coord.downloads.clear_downloads()

        def on_download() -> None:
            downloads = coord.downloads.get_downloads()
            coord.downloads.start_downloads(downloads, coord.downloads_folder)

        def on_manage_files() -> None:
            coord.show_file_manager()

        self.action_buttons = ActionButtonBar(
            self.main_frame,
            on_remove=on_remove,
            on_clear=on_clear,
            on_download=on_download,
            on_manage_files=on_manage_files,
            theme_manager=self.theme_manager,
        )
        logger.info("[MAIN_APP] ActionButtonBar created successfully")

        self.status_bar = StatusBar(self.main_frame, theme_manager=self.theme_manager)
        logger.info("[MAIN_APP] StatusBar created")

        logger.info("[MAIN_APP] Passing UI components to orchestrator")
        self.orchestrator.set_ui_components(
            url_entry=self.url_entry,
            options_bar=self.options_bar,
            download_list=self.download_list,
            action_buttons=self.action_buttons,
            status_bar=self.status_bar,
        )
        logger.info("[MAIN_APP] UI components passed to orchestrator successfully")

    def _setup_layout(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=30, pady=(20, 25))
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)
        self.main_frame.grid_rowconfigure(5, weight=0)

        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 35))
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 25))
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 15))
        self.action_buttons.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.status_bar.grid(row=5, column=0, sticky="ew", pady=(0, 0))

    def _setup_menu(self):
        menubar = Menu(self)
        self.configure(menu=menubar)

        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Network Status",
            command=self.orchestrator.event_coordinator.show_network_status,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

    def _graceful_shutdown(self):
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

    def _on_closing(self):
        logger.info("[MAIN_APP] Application closing - cleaning up")
        self._graceful_shutdown()

        try:
            self.destroy()
            logger.info("[MAIN_APP] Application closed")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during window destruction: {e}")


if __name__ == "__main__":
    try:
        _check_playwright_installation()
        logger.info("[MAIN_APP] Starting Media Downloader application")
        app = MediaDownloaderApp()
        app.mainloop()

    except (SystemExit, ImportError) as e:
        logger.error(f"[MAIN_APP] Missing dependencies: {e}", exc_info=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"[MAIN_APP] Unexpected error - exiting: {e}", exc_info=True)
        sys.exit(1)
