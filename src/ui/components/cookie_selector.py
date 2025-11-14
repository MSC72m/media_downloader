"""UI component for selecting browser cookies."""

from tkinter import filedialog, messagebox
from collections.abc import Callable

import customtkinter as ctk

from src.utils.logger import get_logger

from ...handlers.cookie_handler import CookieHandler
from ...interfaces.cookie_detection import BrowserType

logger = get_logger(__name__)


class CookieSelectorFrame(ctk.CTkFrame):
    """Frame for selecting browser cookies."""

    def __init__(
        self,
        parent,
        cookie_handler: CookieHandler,
        on_cookie_detected: Callable[[bool], None] | None = None,
        on_manual_select: Callable[[], None] | None = None
    ):
        super().__init__(parent, fg_color="transparent")

        self.cookie_handler = cookie_handler
        self.on_cookie_detected = on_cookie_detected
        self.on_manual_select = on_manual_select
        self.platform = cookie_handler.get_platform()
        # Always show all three browser options
        from ...interfaces.cookie_detection import BrowserType
        self.supported_browsers = [BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.SAFARI]

        self.current_cookie_status = "No cookies detected"
        self._create_widgets()

    def _create_widgets(self):
        """Create the widget components."""
        # Main container
        self.main_container = ctk.CTkFrame(self, fg_color=("gray90", "gray20"))
        self.main_container.pack(fill="x", pady=5)

        # Title
        self.title_label = ctk.CTkLabel(
            self.main_container,
            text="Browser Cookies (for YouTube videos)",
            font=("Roboto", 12, "bold")
        )
        self.title_label.pack(pady=(10, 5))

        # Status
        self.status_label = ctk.CTkLabel(
            self.main_container,
            text=self.current_cookie_status,
            font=("Roboto", 10)
        )
        self.status_label.pack(pady=5)

        # Browser selection frame
        self.browser_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.browser_frame.pack(fill="x", padx=20, pady=10)

        # Browser buttons
        self._create_browser_buttons()

        # Manual selection button
        self.manual_button = ctk.CTkButton(
            self.main_container,
            text="Select Cookie File Manually",
            command=self._handle_manual_select,
            width=200
        )
        self.manual_button.pack(pady=5)

        # Refresh button
        self.refresh_button = ctk.CTkButton(
            self.main_container,
            text="Refresh Detection",
            command=self._refresh_detection,
            width=150
        )
        self.refresh_button.pack(pady=(0, 10))

    def _create_browser_buttons(self):
        """Create browser selection buttons based on platform."""
        # Clear existing buttons
        for widget in self.browser_frame.winfo_children():
            widget.destroy()

        browser_info = {
            BrowserType.CHROME: ("Chrome", "#4285F4"),
            BrowserType.FIREFOX: ("Firefox", "#FF9500"),
            BrowserType.SAFARI: ("Safari", "#007AFF")
        }

        for browser in self.supported_browsers:
            name, color = browser_info[browser]

            button = ctk.CTkButton(
                self.browser_frame,
                text=f"Use {name} Cookies",
                command=lambda b=browser: self._handle_browser_select(b),
                width=150,
                fg_color=color,
                hover_color=self._darken_color(color)
            )
            button.pack(side="left", padx=5)

    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color for hover effect."""
        # Simple darkening - subtract 20 from each RGB component
        hex_color = hex_color.lstrip('#')
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, c - 30) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"

    def _handle_browser_select(self, browser: BrowserType):
        """Handle browser selection."""
        try:
            self.status_label.configure(text=f"Detecting {browser.value} cookies...")

            cookie_path = self.cookie_handler.detect_cookies_for_browser(browser)
            if cookie_path:
                self.current_cookie_status = f"Using {browser.value} cookies"
                self.status_label.configure(text=self.current_cookie_status)
                self._show_success_message(f"Successfully detected {browser.value} cookies!")
                if self.on_cookie_detected:
                    self.on_cookie_detected(True)
            else:
                self.current_cookie_status = f"No {browser.value} cookies found"
                self.status_label.configure(text=self.current_cookie_status)
                self._show_warning_message(f"No {browser.value} cookies detected. Please ensure {browser.value} is installed and logged into YouTube.")

        except Exception as e:
            logger.error(f"Error detecting {browser.value} cookies: {e}")
            self.current_cookie_status = f"Error detecting {browser.value} cookies"
            self.status_label.configure(text=self.current_cookie_status)
            self._show_error_message(f"Error detecting {browser.value} cookies: {str(e)}")

    def _handle_manual_select(self):
        """Handle manual cookie file selection."""
        try:
            file_path = filedialog.askopenfilename(
                title="Select Cookie File",
                filetypes=[
                    ("Cookie files", "*.txt *.sqlite *.cookies *.binarycookies"),
                    ("Text files", "*.txt"),
                    ("SQLite files", "*.sqlite"),
                    ("All files", "*.*")
                ]
            )

            if file_path:
                success = self.cookie_handler.set_cookie_file(file_path)
                if success:
                    self.current_cookie_status = "Using manual cookie file"
                    self.status_label.configure(text=self.current_cookie_status)
                    self._show_success_message("Cookie file loaded successfully!")
                    if self.on_cookie_detected:
                        self.on_cookie_detected(True)
                    if self.on_manual_select:
                        self.on_manual_select()
                else:
                    self.current_cookie_status = "Invalid cookie file"
                    self.status_label.configure(text=self.current_cookie_status)
                    self._show_error_message("Invalid cookie file selected. Please select a valid cookie file.")

        except Exception as e:
            logger.error(f"Error in manual cookie selection: {e}")
            self._show_error_message(f"Error selecting cookie file: {str(e)}")

    def _refresh_detection(self):
        """Refresh cookie detection."""
        try:
            self.current_cookie_status = "Refreshing detection..."
            self.status_label.configure(text=self.current_cookie_status)

            # Update supported browsers
            self.supported_browsers = self.cookie_handler.get_supported_browsers()
            self._create_browser_buttons()

            # Check current status
            if self.cookie_handler.has_valid_cookies():
                self.current_cookie_status = "Cookies already loaded"
                self.status_label.configure(text=self.current_cookie_status)
                if self.on_cookie_detected:
                    self.on_cookie_detected(True)
            else:
                self.current_cookie_status = "No cookies detected"
                self.status_label.configure(text=self.current_cookie_status)
                if self.on_cookie_detected:
                    self.on_cookie_detected(False)

        except Exception as e:
            logger.error(f"Error refreshing detection: {e}")
            self.current_cookie_status = "Error refreshing detection"
            self.status_label.configure(text=self.current_cookie_status)

    def _show_success_message(self, message: str):
        """Show a success message."""
        messagebox.showinfo("Success", message)

    def _show_warning_message(self, message: str):
        """Show a warning message."""
        messagebox.showwarning("Warning", message)

    def _show_error_message(self, message: str):
        """Show an error message."""
        messagebox.showerror("Error", message)

    def update_status(self, has_cookies: bool):
        """Update the cookie status display."""
        if has_cookies:
            self.current_cookie_status = "Cookies loaded"
            self.status_label.configure(text=self.current_cookie_status)
        else:
            self.current_cookie_status = "No cookies detected"
            self.status_label.configure(text=self.current_cookie_status)

    def set_visible(self, visible: bool):
        """Set the visibility of the cookie selector frame."""
        if visible:
            self.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        else:
            self.grid_forget()
