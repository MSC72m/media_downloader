"""Multi-select dropdown component with checkbox support."""

from collections.abc import Callable
from typing import Any, Dict, List

import customtkinter as ctk

from src.utils.logger import get_logger

logger = get_logger(__name__)


class MultiSelectDropdown(ctk.CTkFrame):
    """Multi-select dropdown with checkboxes for subtitle selection."""

    def __init__(
        self,
        master,
        placeholder: str = "Select items...",
        options: List[Dict[str, Any]] = None,
        on_change: Callable[[List[str]], None] | None = None,
        width: int = 200,
        height: int = 30,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.placeholder = placeholder
        self.options = options or []
        self.on_change = on_change
        self.width = width
        self.height = height

        self.selected_options: List[str] = []
        self.dropdown_window: ctk.CTkToplevel | None = None
        self.is_open = False
        self.checkboxes: Dict[str, ctk.CTkCheckBox] = {}

        self._create_widgets()

    def _create_widgets(self):
        """Create the dropdown widgets."""
        # Main button
        self.main_button = ctk.CTkButton(
            self,
            text=self.placeholder,
            command=self._toggle_dropdown,
            width=self.width,
            height=self.height,
            font=("Roboto", 11),
            anchor="w",
        )
        self.main_button.pack(fill="x")

        # Dropdown arrow
        self.arrow_label = ctk.CTkLabel(self.main_button, text="▼", font=("Roboto", 12))
        self.arrow_label.place(relx=0.95, rely=0.5, anchor="e")

    def _toggle_dropdown(self):
        """Toggle dropdown visibility."""
        if self.is_open:
            self._close_dropdown()
        else:
            # Use after to prevent UI blocking
            self.after(10, self._open_dropdown)

    def _open_dropdown(self):
        """Open the dropdown menu."""
        if self.is_open:
            return

        try:
            # Create dropdown window
            self.dropdown_window = ctk.CTkToplevel(self.winfo_toplevel())
            self.dropdown_window.overrideredirect(True)  # Remove window decorations
            self.dropdown_window.attributes("-topmost", True)
            self.dropdown_window.transient(self.winfo_toplevel())

            # Position dropdown below main button
            x = self.main_button.winfo_rootx()
            y = self.main_button.winfo_rooty() + self.main_button.winfo_height()
            self.dropdown_window.geometry(f"{self.width}x300+{x}+{y}")

            # Create scrollable frame for options
            scrollable_frame = ctk.CTkScrollableFrame(
                self.dropdown_window, width=self.width - 10, height=280
            )
            scrollable_frame.pack(fill="both", expand=True, padx=5, pady=5)

            # Create option checkboxes
            self.checkboxes = {}
            for i, option in enumerate(self.options):
                self._create_option_item(scrollable_frame, option, i)

            # Select all / Deselect all buttons
            button_frame = ctk.CTkFrame(scrollable_frame, fg_color="transparent")
            button_frame.pack(fill="x", pady=(10, 5))

            select_all_btn = ctk.CTkButton(
                button_frame,
                text="Select All",
                command=self._select_all,
                width=80,
                height=25,
                font=("Roboto", 9),
            )
            select_all_btn.pack(side="left", padx=(0, 5))

            deselect_all_btn = ctk.CTkButton(
                button_frame,
                text="Deselect All",
                command=self._deselect_all,
                width=80,
                height=25,
                font=("Roboto", 9),
            )
            deselect_all_btn.pack(side="left")

            # Bind click outside to close - only bind to dropdown window
            self.dropdown_window.bind("<Button-1>", self._handle_outside_click)
            self.dropdown_window.bind("<FocusOut>", self._handle_focus_out)
            self.dropdown_window.bind("<Escape>", lambda e: self._close_dropdown())

            # Focus the dropdown window
            self.dropdown_window.focus_set()
            self.is_open = True

        except Exception:
            # If anything goes wrong, ensure we clean up
            if hasattr(self, "dropdown_window") and self.dropdown_window:
                try:
                    self.dropdown_window.destroy()
                except Exception:
                    pass
                self.dropdown_window = None
            self.is_open = False

    def _create_option_item(self, parent, option: Dict[str, Any], index: int):
        """Create a single option item with checkbox."""
        try:
            option_frame = ctk.CTkFrame(parent, fg_color="transparent")
            option_frame.pack(fill="x", pady=2, padx=5)

            # Get option details
            option_id = option.get("id", str(index))
            display_text = option.get("display", option_id)
            subtitle = option.get("subtitle", "")
            is_auto = option.get("is_auto", False)

            # Checkbox
            var = ctk.BooleanVar(value=option_id in self.selected_options)
            checkbox = ctk.CTkCheckBox(
                option_frame,
                text="",
                variable=var,
                width=20,
                command=lambda oid=option_id, v=var: self._handle_option_change(
                    oid, v.get()
                ),
            )
            checkbox.pack(side="left", padx=(0, 10))

            # Store reference to clean up later
            if not hasattr(self, "_checkbox_vars"):
                self._checkbox_vars = {}
            self._checkbox_vars[option_id] = var

            # Option details
            details_frame = ctk.CTkFrame(option_frame, fg_color="transparent")
            details_frame.pack(side="left", fill="x", expand=True)

            # Main text
            main_text = display_text
            if is_auto:
                main_text += " (Auto)"

            text_label = ctk.CTkLabel(
                details_frame,
                text=main_text,
                font=("Roboto", 10, "bold" if not is_auto else "normal"),
                anchor="w",
            )
            text_label.pack(anchor="w")

            # Subtitle text if available
            if subtitle:
                subtitle_label = ctk.CTkLabel(
                    details_frame,
                    text=subtitle,
                    font=("Roboto", 8),
                    text_color="gray",
                    anchor="w",
                )
                subtitle_label.pack(anchor="w")

            self.checkboxes[option_id] = var

        except Exception as e:
            logger.error(f"Error creating option item: {e}", exc_info=True)
            # Don't let one broken option break the whole dropdown

    def _handle_option_change(self, option_id: str, is_selected: bool):
        """Handle option selection change."""
        if is_selected and option_id not in self.selected_options:
            self.selected_options.append(option_id)
        elif not is_selected and option_id in self.selected_options:
            self.selected_options.remove(option_id)

        self._update_display_text()
        if self.on_change:
            self.on_change(self.selected_options)

    def _select_all(self):
        """Select all options."""
        for option_id, var in self.checkboxes.items():
            var.set(True)
            if option_id not in self.selected_options:
                self.selected_options.append(option_id)

        self._update_display_text()
        if self.on_change:
            self.on_change(self.selected_options)

    def _deselect_all(self):
        """Deselect all options."""
        for option_id, var in self.checkboxes.items():
            var.set(False)

        self.selected_options.clear()
        self._update_display_text()
        if self.on_change:
            self.on_change(self.selected_options)

    def _update_display_text(self):
        """Update the display text on the main button."""
        if not self.selected_options:
            display_text = self.placeholder
        elif len(self.selected_options) == 1:
            display_text = "1 item selected"
        else:
            display_text = f"{len(self.selected_options)} items selected"

        self.main_button.configure(text=display_text)

    def _close_dropdown(self):
        """Close the dropdown menu."""
        if self.dropdown_window:
            try:
                self.dropdown_window.destroy()
            except Exception:
                pass
            self.dropdown_window = None

        # Clean up references
        self.checkboxes.clear()
        if hasattr(self, "_checkbox_vars"):
            self._checkbox_vars.clear()
        self.is_open = False

    def _handle_outside_click(self, event):
        """Handle clicks outside the dropdown."""
        if self.is_open and self.dropdown_window:
            # Check if click is outside dropdown window
            widget = event.widget
            while widget:
                if widget == self.dropdown_window:
                    return  # Click is inside dropdown
                widget = widget.master

            self._close_dropdown()

    def _handle_focus_out(self, event):
        """Handle focus out event to close dropdown."""
        if self.is_open and self.dropdown_window:
            # Small delay to allow checkbox clicks to process
            self.after(100, self._check_focus_and_close)

    def _check_focus_and_close(self):
        """Check if dropdown still has focus and close if not."""
        if self.is_open and self.dropdown_window:
            try:
                # Check if dropdown window still has focus
                focused_widget = self.focus_get()
                if focused_widget != self.dropdown_window and not self._is_descendant(
                    focused_widget, self.dropdown_window
                ):
                    self._close_dropdown()
            except Exception:
                # If we can't check focus, close it
                self._close_dropdown()

    def _is_descendant(self, widget, parent):
        """Check if widget is a descendant of parent."""
        while widget:
            if widget == parent:
                return True
            widget = widget.master
        return False

    def set_options(self, options: list[dict[str, Any]]) -> None:
        """Set new options for the dropdown."""
        self.options = options
        self.selected_options.clear()
        self._update_display_text()

    def get_selected(self) -> list[str]:
        """Get currently selected option IDs."""
        return self.selected_options.copy()

    def set_selected_options(self, selected_ids: List[str]):
        """Set currently selected option IDs."""
        self.selected_options = selected_ids.copy()
        self._update_display_text()

    def destroy(self):
        """Clean up the dropdown."""
        self._close_dropdown()
        super().destroy()


class SubtitleMultiSelect(MultiSelectDropdown):
    """Specialized multi-select dropdown for subtitle selection."""

    def __init__(
        self,
        master,
        placeholder: str = "Select subtitles...",
        width: int = 300,
        height: int = 35,
        **kwargs,
    ):
        super().__init__(
            master, placeholder=placeholder, width=width, height=height, **kwargs
        )

        # Group options by auto/manual
        self.auto_options: List[Dict[str, Any]] = []
        self.manual_options: List[Dict[str, Any]] = []

    def set_subtitle_options(self, subtitles: List[Dict[str, Any]]):
        """Set subtitle options from metadata."""
        options = []
        self.auto_options = []
        self.manual_options = []

        # Group subtitles
        for subtitle in subtitles:
            option = {
                "id": subtitle["language_code"],
                "display": subtitle["language_name"],
                "subtitle": subtitle["language_code"],
                "is_auto": subtitle["is_auto_generated"],
            }

            if subtitle["is_auto_generated"]:
                self.auto_options.append(option)
            else:
                self.manual_options.append(option)

        # Add manual subtitles first, then auto-generated
        if self.manual_options:
            options.extend(self.manual_options)

        if self.auto_options:
            # Add separator if we have both types
            if self.manual_options:
                options.append(
                    {
                        "id": "separator",
                        "display": "─────────────────",
                        "subtitle": "",
                        "is_auto": False,
                        "is_separator": True,
                    }
                )

            options.extend(self.auto_options)

        self.set_options(options)

    def _create_option_item(self, parent, option: Dict[str, Any], index: int):
        """Override to handle separator items."""
        if option.get("is_separator"):
            # Create separator line
            separator_label = ctk.CTkLabel(
                parent, text=option["display"], font=("Roboto", 8), text_color="gray"
            )
            separator_label.pack(fill="x", pady=(5, 2))
            return

        super()._create_option_item(parent, option, index)

    def get_selected_subtitles(self) -> List[Dict[str, str]]:
        """Get selected subtitles as list of language codes and types."""
        selected = []
        for option_id in self.selected_options:
            # Find the option to determine if it's auto or manual
            for option in self.options:
                if option["id"] == option_id and not option.get("is_separator"):
                    selected.append(
                        {
                            "language_code": option["id"],
                            "type": "auto" if option.get("is_auto") else "manual",
                        }
                    )
                    break

        return selected
