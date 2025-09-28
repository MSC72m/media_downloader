"""Browser cookie selection dialog that matches YouTube options window style."""

import customtkinter as ctk
import os
from typing import Optional, Callable
from ...utils.window import WindowCenterMixin
from ...interfaces.cookie_detection import BrowserType
from ...utils.logger import get_logger

logger = get_logger(__name__)


class BrowserCookieDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Dialog for selecting browser cookies that matches YouTube options style."""

    def __init__(self, parent, on_cookie_selected: Callable[[Optional[str], Optional[str]], None], **kwargs):
        super().__init__(parent, **kwargs)

        self.on_cookie_selected = on_cookie_selected
        self.cookie_path: Optional[str] = None
        self.selected_browser: Optional[str] = None

        # Configure window to match YouTube options style
        self.title("Select Cookie Source")
        self.geometry("500x500")
        self.resizable(False, False)  # Fixed size like YouTube options
        self.transient(parent)
        self.grab_set()

        # Center the window
        self.center_window()

        # Create content
        self._create_content()

    def _create_content(self):
        """Create the cookie selection dialog content."""
        # Main container with scrollable frame
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Title
        title_label = ctk.CTkLabel(
            self.main_container,
            text="Cookie Source Selection",
            font=("Roboto", 20, "bold")
        )
        title_label.pack(pady=(0, 20))

        # Description
        desc_label = ctk.CTkLabel(
            self.main_container,
            text="Choose how to provide cookies for YouTube access:",
            font=("Roboto", 12),
            wraplength=450
        )
        desc_label.pack(pady=(0, 25))

        # Scrollable frame for browser options
        scrollable_frame = ctk.CTkScrollableFrame(
            self.main_container,
            height=250,
            fg_color="transparent",
            corner_radius=8
        )
        scrollable_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Browser selection section
        self._create_browser_section(scrollable_frame)

        # Manual path section
        self._create_manual_section(scrollable_frame)

        # Button frame
        button_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        button_frame.pack(fill="x", pady=(30, 0))

        # Center button container
        button_container = ctk.CTkFrame(button_frame, fg_color="transparent")
        button_container.pack(expand=True)

        # Skip button
        skip_btn = ctk.CTkButton(
            button_container,
            text="Skip (No Cookies)",
            command=self._on_skip,
            width=150,
            height=40,
            font=("Roboto", 12, "bold"),
            fg_color=("gray60", "gray40"),
            hover_color=("gray70", "gray30"),
            corner_radius=8
        )
        skip_btn.pack(side="left", padx=(0, 20))

        # Continue button
        continue_btn = ctk.CTkButton(
            button_container,
            text="Continue",
            command=self._on_continue,
            width=150,
            height=40,
            font=("Roboto", 12, "bold"),
            fg_color="#2196F3",
            hover_color="#1976D2",
            corner_radius=8
        )
        continue_btn.pack(side="left")

    def _create_browser_section(self, parent):
        """Create browser selection section."""
        # Browser section title
        browser_title = ctk.CTkLabel(
            parent,
            text="Select Browser",
            font=("Roboto", 14, "bold")
        )
        browser_title.pack(anchor="w", pady=(10, 10))

        # Browser options with colors matching YouTube dialog
        browsers = [
            ("Chrome", "chrome", "#4285F4", "#FFA500"),
            ("Firefox", "firefox", "#4169E1", "#FFA500"),
            ("Safari", "safari", "#007AFF", "#FFA500")
        ]

        self.browser_var = ctk.StringVar(value="none")
        self.browser_buttons = {}

        for name, value, color, selected_color in browsers:
            button_frame = ctk.CTkFrame(parent, fg_color="transparent")
            button_frame.pack(fill="x", pady=5)

            radio = ctk.CTkRadioButton(
                button_frame,
                text=name,
                variable=self.browser_var,
                value=value,
                command=self._on_browser_selected,
                font=("Roboto", 12)
            )
            radio.pack(side="left", padx=(0, 10))

            # Status indicator
            status_label = ctk.CTkLabel(
                button_frame,
                text="",
                font=("Roboto", 10),
                width=100,
                text_color="gray"
            )
            status_label.pack(side="right")

            self.browser_buttons[value] = (radio, status_label)

        # None option
        none_frame = ctk.CTkFrame(parent, fg_color="transparent")
        none_frame.pack(fill="x", pady=5)

        none_radio = ctk.CTkRadioButton(
            none_frame,
            text="None",
            variable=self.browser_var,
            value="none",
            command=self._on_browser_selected,
            font=("Roboto", 12)
        )
        none_radio.pack(side="left")

    def _create_manual_section(self, parent):
        """Create manual path section."""
        # Manual section title
        manual_title = ctk.CTkLabel(
            parent,
            text="Or Enter Cookie File Path",
            font=("Roboto", 14, "bold")
        )
        manual_title.pack(anchor="w", pady=(20, 10))

        # Manual path frame
        manual_frame = ctk.CTkFrame(parent, fg_color="transparent")
        manual_frame.pack(fill="x", pady=5)

        # Path entry
        self.manual_path_var = ctk.StringVar()
        self.manual_entry = ctk.CTkEntry(
            manual_frame,
            textvariable=self.manual_path_var,
            placeholder_text="Enter path to cookie file...",
            width=300,
            height=35,
            font=("Roboto", 11)
        )
        self.manual_entry.pack(side="left", padx=(0, 10))

        # Browse button
        browse_btn = ctk.CTkButton(
            manual_frame,
            text="Browse...",
            command=self._browse_file,
            width=80,
            height=35,
            font=("Roboto", 10, "bold"),
            fg_color="#6C757D",
            hover_color="#5A6268"
        )
        browse_btn.pack(side="left")

        # Bind entry changes
        self.manual_entry.bind("<KeyRelease>", self._on_manual_path_changed)

    def _on_browser_selected(self):
        """Handle browser selection."""
        browser = self.browser_var.get()
        if browser != "none":
            # Clear manual entry when browser is selected
            self.manual_path_var.set("")
            # Update button colors
            self._update_browser_selection(browser)

    def _on_manual_path_changed(self, event=None):
        """Handle manual path entry changes."""
        if self.manual_path_var.get().strip():
            # Clear browser selection when manual path is entered
            self.browser_var.set("none")
            self._update_browser_selection("none")

    def _update_browser_selection(self, selected_browser: str):
        """Update browser button selection colors."""
        for browser_value, (radio, status) in self.browser_buttons.items():
            if browser_value == selected_browser and selected_browser != "none":
                radio.configure(text_color="white")
                status.configure(text="Selected", text_color="#4CAF50")
            else:
                radio.configure(text_color="gray")
                status.configure(text="", text_color="gray")

    def _browse_file(self):
        """Browse for cookie file."""
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            title="Select Cookie File",
            filetypes=[
                ("Cookie files", "*.txt *.cookies"),
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ]
        )
        if file_path:
            self.manual_path_var.set(file_path)
            self._on_manual_path_changed()

    def _on_continue(self):
        """Handle continue button click."""
        manual_path = self.manual_path_var.get().strip()
        browser = self.browser_var.get()

        print(f"Continue clicked: manual_path='{manual_path}', browser='{browser}'")

        if manual_path:
            # Use manual path
            if os.path.exists(manual_path):
                print(f"Using manual path: {manual_path}")
                self.cookie_path = manual_path
                self.selected_browser = None
                self._finish()
            else:
                print(f"Manual path not found: {manual_path}")
                self._show_error("Cookie file not found: " + manual_path)
        elif browser != "none":
            # Use browser selection
            print(f"Using browser: {browser}")
            self.selected_browser = browser
            self.cookie_path = None
            self._finish()
        else:
            print("No selection made")
            self._show_error("Please select a browser or enter a cookie file path")

    def _on_skip(self):
        """Handle skip button click."""
        self.cookie_path = None
        self.selected_browser = None
        self._finish()

    def _finish(self):
        """Finish the dialog and call callback."""
        logger.info(f"Finishing dialog: cookie_path={self.cookie_path}, browser={self.selected_browser}")
        # Store callback and parameters before destroying the window
        callback = self.on_cookie_selected
        cookie_path = self.cookie_path
        selected_browser = self.selected_browser
        parent = self.master
        
        # Release grab set before destroying
        self.grab_release()
        logger.info("Grab released, destroying dialog...")
        self.destroy()
        logger.info("Dialog destroyed, calling callback...")
        
        # Call callback after window is destroyed using parent window
        if callback and parent:
            parent.after(100, lambda: callback(cookie_path, selected_browser))
            logger.info("Callback scheduled successfully")
        elif callback:
            # Fallback: call immediately if no parent
            callback(cookie_path, selected_browser)
            logger.info("Callback called immediately")

    def _show_error(self, message: str):
        """Show error message."""
        # Remove previous error messages
        for widget in self.main_container.winfo_children():
            if isinstance(widget, ctk.CTkLabel) and widget.cget("text_color") == "red":
                widget.destroy()

        error_label = ctk.CTkLabel(
            self.main_container,
            text=message,
            text_color="red",
            font=("Roboto", 10)
        )
        error_label.pack(pady=(10, 0))
        # Remove error message after 3 seconds
        self.after(3000, error_label.destroy)