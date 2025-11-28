import sys
import queue
from pathlib import Path

from src.utils.common import ensure_gui_available
from src.utils.logger import get_logger

sys.path.append(str(Path(__file__).parent.parent))

logger = get_logger(__name__)


# Only import GUI modules after confirming tkinter is available
ensure_gui_available()
import customtkinter as ctk  # noqa: E402
from tkinter import Menu  # noqa: E402

from src.core import get_application_orchestrator  # noqa: E402
from src.core.interfaces import IMessageQueue  # noqa: E402
from src.services.events.queue import MessageQueue  # noqa: E402
from src.ui.components.download_list import DownloadListView  # noqa: E402
from src.ui.components.main_action_buttons import ActionButtonBar  # noqa: E402
from src.ui.components.options_bar import OptionsBar  # noqa: E402
from src.ui.components.status_bar import StatusBar  # noqa: E402
from src.ui.components.url_entry import URLEntryFrame  # noqa: E402

# Set theme after successful import
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _check_playwright_installation():
    """Check if Playwright is installed and show critical error if not.

    Returns:
        True if Playwright is installed or user chose to continue
        Does NOT return if user chose to exit (calls os._exit instead)
    """
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

        message_label = ctk.CTkLabel(
            error_frame, text=message, font=("Arial", 12), justify="left"
        )
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

            # Print clear instructions to terminal FIRST
            # We dont want this to have structured logging!
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
            raise SystemExit(1)

        # If we reach here, user clicked Continue Anyway
        logger.warning("[MAIN_APP] Continuing without Playwright as user requested")
        raise original_error


class MediaDownloaderApp(ctk.CTk):
    """Main application window - just UI setup and delegation."""

    def __init__(self):
        super().__init__()

        self.title("Media Downloader")
        self.geometry("1000x700")

        # Thread-safe UI update queue
        self.thread_queue = queue.Queue()
        self.after(100, self._process_thread_queue)

        ApplicationOrchestrator = get_application_orchestrator()
        self.orchestrator = ApplicationOrchestrator(self)

        # Note: MessageQueue will be created after status_bar is available
        # See _create_ui() for message_queue registration

        # Create UI
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._create_ui()
        self._setup_layout()
        self._setup_menu()

        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info("Media Downloader initialized")

        # Start connectivity check after UI is fully initialized
        # Use after() to ensure UI is ready to receive updates
        self.after(100, self.orchestrator.check_connectivity)

    def _process_thread_queue(self):
        """Process callbacks queued from background threads."""
        try:
            while not self.thread_queue.empty():
                try:
                    func = self.thread_queue.get_nowait()
                    func()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"[MAIN_APP] Error executing queued task: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[MAIN_APP] Error in event loop: {e}", exc_info=True)
        finally:
            self.after(50, self._process_thread_queue)

    def run_on_main_thread(self, func):
        """Schedule a function to run on the main thread."""
        self.thread_queue.put(func)

    def _create_ui(self):
        """Create all UI components."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame, text="Media Downloader", font=("Roboto", 32, "bold")
        )

        # Get coordinator for direct wiring
        coord = self.orchestrator.event_coordinator

        # URL Entry - wire directly to link detector
        def on_add_url(url: str, name: str) -> None:
            # Try to detect platform-specific handler first
            handler_found = self.orchestrator.link_detector.detect_and_handle(
                url, coord
            )

            # If no handler found, treat as generic download
            if not handler_found:
                logger.info(
                    f"[MAIN_APP] No handler found for {url}, treating as generic download"
                )
                coord.platform_download("generic", url, name)

        def on_youtube_detected(url: str) -> None:
            self.orchestrator.link_detector.detect_and_handle(url, coord)

        self.url_entry = URLEntryFrame(
            self.main_frame,
            on_add=on_add_url,
            on_youtube_detected=on_youtube_detected,
        )

        # Options Bar
        self.options_bar = OptionsBar(self.main_frame)

        # Download List
        self.download_list = DownloadListView(
            self.main_frame,
            on_selection_change=lambda sel: self.action_buttons.update_button_states(
                has_selection=len(sel) > 0,
                has_items=len(coord.downloads.get_downloads()) > 0
            ),
        )

        # Action Buttons - wire directly to coordinator
        logger.info("[MAIN_APP] Creating ActionButtonBar")

        def on_remove() -> None:
            coord.downloads.remove_downloads(self.download_list.get_selected_indices())

        def on_clear() -> None:
            coord.downloads.clear_downloads()

        def on_clear_completed() -> None:
            coord.downloads.clear_downloads()

        def on_download() -> None:
            downloads = coord.downloads.get_downloads()
            # Filter for pending downloads if needed, but start_downloads usually handles status check
            coord.downloads.start_downloads(downloads, coord.downloads_folder)

        def on_manage_files() -> None:
            coord.show_file_manager()

        self.action_buttons = ActionButtonBar(
            self.main_frame,
            on_remove=on_remove,
            on_clear=on_clear,
            on_clear_completed=on_clear_completed,
            on_download=on_download,
            on_manage_files=on_manage_files,
        )
        logger.info("[MAIN_APP] ActionButtonBar created successfully")

        # Status Bar
        self.status_bar = StatusBar(self.main_frame)
        logger.info("[MAIN_APP] StatusBar created")

        # Pass UI components to orchestrator
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
        """Configure the main layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(2, weight=1)  # Download list row

        # Arrange widgets
        self.title_label.grid(row=0, column=0, pady=(0, 20))
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        # OptionsBar is empty (no content) - skip gridding to avoid empty space
        # self.options_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.download_list.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self.action_buttons.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.status_bar.grid(row=4, column=0, sticky="ew")

    def _setup_menu(self):
        """Set up application menu."""

        menubar = Menu(self)
        self.configure(menu=menubar)

        tools_menu = Menu(menubar, tearoff=0)
        tools_menu.add_command(
            label="Network Status",
            command=self.orchestrator.event_coordinator.show_network_status,
        )
        menubar.add_cascade(label="Tools", menu=tools_menu)

    def _on_closing(self):
        """Handle application closing."""
        logger.info("[MAIN_APP] Application closing - cleaning up")

        # Cleanup orchestrator first
        try:
            self.orchestrator.cleanup()
            logger.info("[MAIN_APP] Orchestrator cleanup complete")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during orchestrator cleanup: {e}")

        # Destroy the window - this will handle cleanup automatically
        # Don't call quit() first, just destroy()
        try:
            self.destroy()
            logger.info("[MAIN_APP] Application closed")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during window destruction: {e}")


if __name__ == "__main__":
    # Will return True if Playwright is installed or user chose to continue
    try:
        _check_playwright_installation()
        # Only create app if we should continue
        logger.info("[MAIN_APP] Starting Media Downloader application")
        app = MediaDownloaderApp()
        app.mainloop()
        
    except (SystemExit, ImportError) as e:
        logger.error(f"[MAIN_APP] Missing dependencies: {e}", exc_info=True)
        sys.exit(1)

    except Exception as e:
        logger.error(f"[MAIN_APP] Unexpected error - exiting: {e}", exc_info=True)
        sys.exit(1)
