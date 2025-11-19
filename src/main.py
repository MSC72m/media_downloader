import sys
from pathlib import Path

from src.utils.common import ensure_gui_available
from src.utils.logger import get_logger

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

logger = get_logger(__name__)


def _ensure_gui_available():
    try:
        import tkinter as _tk  # noqa: F401

        import customtkinter as _ctk  # noqa: F401

        return True
    except Exception as e:
        msg = (
            "Tkinter (GUI) is not available in this Python. "
            "Please install Tcl/Tk and a Python build with _tkinter.\n"
            "macOS with pyenv: brew install tcl-tk and reinstall Python with Tk support."
        )
        logger.error(msg)
        print(msg)
        raise SystemExit(1) from e


# Only import GUI modules after confirming tkinter is available
ensure_gui_available()
import customtkinter as ctk  # noqa: E402

from src.core import ApplicationOrchestrator  # noqa: E402
from src.services.events.queue import MessageQueue
from src.ui.components.download_list import DownloadListView  # noqa: E402
from src.ui.components.main_action_buttons import ActionButtonBar  # noqa: E402
from src.ui.components.options_bar import OptionsBar  # noqa: E402
from src.ui.components.status_bar import StatusBar  # noqa: E402
from src.ui.components.url_entry import URLEntryFrame  # noqa: E402

# Set theme after successful import
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def _check_playwright_installation():
    """Check if Playwright is installed and show critical error if not."""
    try:
        import playwright  # noqa: F401

        logger.info("[MAIN_APP] Playwright is installed")
        return True
    except ImportError:
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

        def continue_anyway():
            logger.warning("[MAIN_APP] User chose to continue without Playwright")
            # Cancel all pending after callbacks before destroying
            try:
                for after_id in error_window.tk.call("after", "info"):
                    error_window.after_cancel(after_id)
            except:
                pass
            error_window.quit()
            error_window.destroy()

        def exit_app():
            logger.info("[MAIN_APP] User chose to exit and install Playwright")

            # Cancel all pending after callbacks before destroying
            try:
                for after_id in error_window.tk.call("after", "info"):
                    error_window.after_cancel(after_id)
            except:
                pass

            error_window.quit()
            error_window.destroy()

            # Print clear instructions to terminal
            print("\n" + "=" * 70)
            print("  PLAYWRIGHT INSTALLATION REQUIRED")
            print("=" * 70)
            print("\nTo install Playwright and Chromium, run these commands:\n")
            print("  pip install playwright")
            print("  playwright install chromium")
            print("\nAfter installation, restart the application:")
            print("  uv run -m src.main")
            print("\n" + "=" * 70 + "\n")

            raise SystemExit(1)

        exit_button = ctk.CTkButton(
            button_frame,
            text="Exit (Recommended)",
            command=exit_app,
            fg_color="red",
            hover_color="darkred",
            width=200,
        )
        exit_button.pack(side="left", padx=10)

        continue_button = ctk.CTkButton(
            button_frame,
            text="Continue Anyway (Not Recommended)",
            command=continue_anyway,
            fg_color="orange",
            hover_color="darkorange",
            width=250,
        )
        continue_button.pack(side="left", padx=10)

        # Run the error window
        error_window.mainloop()
        return False


class MediaDownloaderApp(ctk.CTk):
    """Main application window - just UI setup and delegation."""

    def __init__(self):
        super().__init__()

        self.title("Media Downloader")
        self.geometry("1000x700")

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
        self.options_bar = OptionsBar(
            self.main_frame,
            on_instagram_login=lambda: coord.authenticate_instagram(self),
        )

        # Download List
        self.download_list = DownloadListView(
            self.main_frame,
            on_selection_change=lambda sel: self.action_buttons.set_enabled(True)
            if sel
            else None,
        )

        # Action Buttons - wire directly to coordinator
        logger.info("[MAIN_APP] Creating ActionButtonBar")

        def on_remove() -> None:
            coord.downloads.remove_downloads(self.download_list.get_selected_indices())

        def on_clear() -> None:
            coord.downloads.clear_downloads()

        def on_clear_completed() -> None:
            coord.downloads.clear_completed_downloads()

        def on_download() -> None:
            coord.downloads.start_downloads()

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

        # Register message queue now that status_bar exists
        message_queue = MessageQueue(self.status_bar)
        self.orchestrator.container.register(
            "message_queue", message_queue, singleton=True
        )
        logger.info("[MAIN_APP] MessageQueue registered with status_bar")

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
        self.main_frame.grid_rowconfigure(3, weight=1)

        # Arrange widgets
        self.title_label.grid(row=0, column=0, pady=(0, 20))
        self.url_entry.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.options_bar.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 10))
        self.action_buttons.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.status_bar.grid(row=5, column=0, sticky="ew")

    def _setup_menu(self):
        """Set up application menu."""
        from tkinter import Menu

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

        # Cancel all pending after callbacks to prevent "invalid command name" errors
        try:
            for after_id in self.tk.call("after", "info"):
                self.after_cancel(after_id)
            logger.info("[MAIN_APP] Canceled all pending after callbacks")
        except Exception as e:
            logger.warning(f"[MAIN_APP] Error canceling after callbacks: {e}")

        # Cleanup orchestrator
        try:
            self.orchestrator.cleanup()
            logger.info("[MAIN_APP] Orchestrator cleanup complete")
        except Exception as e:
            logger.error(f"[MAIN_APP] Error during orchestrator cleanup: {e}")

        # Destroy the window
        self.quit()
        self.destroy()
        logger.info("[MAIN_APP] Application closed")


if __name__ == "__main__":
    # Check Playwright installation before starting the app
    _check_playwright_installation()

    app = MediaDownloaderApp()
    app.mainloop()
