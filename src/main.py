"""Media downloader application entrypoint."""

import sys
from src.utils.logger import get_logger
from pathlib import Path
import customtkinter as ctk

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Import UI components
from src.ui.components.url_entry import URLEntryFrame
from src.ui.components.options_bar import OptionsBar
from src.ui.components.download_list import DownloadListView
from src.ui.components.status_bar import StatusBar
from src.ui.components.main_action_buttons import ActionButtonBar
from src.ui.components.cookie_selector import CookieSelectorFrame

from src.core import ApplicationOrchestrator

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = get_logger(__name__)

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MediaDownloaderApp(ctk.CTk):
    """Main application window - just UI setup and delegation."""

    def __init__(self):
        super().__init__()

        self.title("Media Downloader")
        self.geometry("1000x700")

        self.orchestrator = ApplicationOrchestrator(self)

        # Create UI
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._create_ui()
        self._setup_layout()
        self._setup_menu()

        # Bind close handler
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        logger.info("Media Downloader initialized")

        # Start connectivity check
        self.orchestrator.check_connectivity()

    def _create_ui(self):
        """Create all UI components."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Media Downloader",
            font=("Roboto", 32, "bold")
        )

        # URL Entry
        self.url_entry = URLEntryFrame(
            self.main_frame,
            on_add=self.orchestrator.handle_add_url,
            on_youtube_detected=self.orchestrator.handle_youtube_detected
        )

        # Options Bar
        self.options_bar = OptionsBar(
            self.main_frame,
            on_instagram_login=self.orchestrator.handle_instagram_login
        )

        # Download List
        self.download_list = DownloadListView(
            self.main_frame,
            on_selection_change=self.orchestrator.handle_selection_change
        )

        # Action Buttons
        logger.info("[MAIN_APP] Creating ActionButtonBar")
        logger.info(f"[MAIN_APP] on_download callback: {self.orchestrator.handle_download}")
        self.action_buttons = ActionButtonBar(
            self.main_frame,
            on_remove=self.orchestrator.handle_remove,
            on_clear=self.orchestrator.handle_clear,
            on_download=self.orchestrator.handle_download,
            on_manage_files=self.orchestrator.handle_manage_files
        )
        logger.info("[MAIN_APP] ActionButtonBar created successfully")

        # Status Bar
        self.status_bar = StatusBar(self.main_frame)

        # Cookie Selector (initially hidden)
        self.cookie_selector = CookieSelectorFrame(
            self.main_frame,
            cookie_handler=self.orchestrator.get_service('cookie_handler'),
            on_cookie_detected=lambda success: self.orchestrator.handle_cookie_detected("chrome", "/tmp/cookies") if success else None,
            on_manual_select=self.orchestrator.handle_cookie_manual_select
        )

        # Pass UI components to orchestrator
        logger.info("[MAIN_APP] Passing UI components to orchestrator")
        self.orchestrator.set_ui_components(
            url_entry=self.url_entry,
            options_bar=self.options_bar,
            download_list=self.download_list,
            action_buttons=self.action_buttons,
            status_bar=self.status_bar,
            cookie_selector=self.cookie_selector
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
        tools_menu.add_command(label="Network Status", command=self.orchestrator.show_network_status)
        menubar.add_cascade(label="Tools", menu=tools_menu)

    def _on_closing(self):
        """Handle application closing."""
        self.orchestrator.cleanup()
        self.destroy()


if __name__ == "__main__":
    app = MediaDownloaderApp()
    app.mainloop()