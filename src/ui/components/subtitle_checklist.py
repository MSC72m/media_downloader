"""Simple subtitle selection component using a scrollable checklist."""

"""Subtitle checklist component for YouTube downloads."""

from collections.abc import Callable
from typing import Any, Dict, List

import customtkinter as ctk


class SubtitleChecklist(ctk.CTkFrame):
    """Simple scrollable checklist for subtitle selection."""

    def __init__(
        self,
        master,
        placeholder: str = "No subtitles available",
        on_change: Callable[[List[Dict[str, str]]], None] | None = None,
        height: int = 120,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.placeholder = placeholder
        self.on_change = on_change
        self.height = height
        self.selected_options: List[str] = []
        self.options: List[Dict[str, Any]] = []
        self.checkboxes: Dict[str, ctk.CTkCheckBox] = {}
        self.option_vars: Dict[str, ctk.BooleanVar] = {}

        self._create_widgets()

    def _create_widgets(self):
        """Create the checklist widgets."""
        # Title label
        self.title_label = ctk.CTkLabel(
            self, text="Available Subtitles:", font=("Roboto", 11, "bold")
        )
        self.title_label.pack(anchor="w", pady=(0, 5))

        # Scrollable frame for options
        self.scrollable_frame = ctk.CTkScrollableFrame(
            self, height=self.height, fg_color=("gray95", "gray25")
        )
        self.scrollable_frame.pack(fill="both", expand=True)

        # Placeholder label
        self.placeholder_label = ctk.CTkLabel(
            self.scrollable_frame,
            text=self.placeholder,
            font=("Roboto", 10),
            text_color="gray",
        )
        self.placeholder_label.pack(pady=20)

        # Button frame
        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=(5, 0))

        # Select/Clear buttons
        self.select_all_btn = ctk.CTkButton(
            self.button_frame,
            text="Select All",
            command=self._select_all,
            width=80,
            height=25,
            font=("Roboto", 9),
        )
        self.select_all_btn.pack(side="left", padx=(0, 5))

        self.clear_all_btn = ctk.CTkButton(
            self.button_frame,
            text="Clear All",
            command=self._clear_all,
            width=80,
            height=25,
            font=("Roboto", 9),
        )
        self.clear_all_btn.pack(side="left")

        # Status label
        self.status_label = ctk.CTkLabel(
            self.button_frame, text="0 selected", font=("Roboto", 9), text_color="gray"
        )
        self.status_label.pack(side="right")

    def set_subtitle_options(self, subtitles: list[dict[str, Any]]) -> None:
        """Set subtitle options."""
        try:
            # Store the options
            self.options = options or []

            # Clear existing options
            self._clear_existing_options()

            if not options:
                self.placeholder_label.pack(pady=20)
                self.button_frame.pack_forget()
                return

            # Hide placeholder
            self.placeholder_label.pack_forget()
            self.button_frame.pack(fill="x", pady=(5, 0))

            # Create new options
            for i, option in enumerate(options):
                self._create_option_item(option, i)

            self._update_status()

        except Exception as e:
            print(f"Error setting subtitle options: {e}")

    def _clear_existing_options(self):
        """Clear existing option widgets."""
        # Clear checkboxes
        for checkbox in self.checkboxes.values():
            checkbox.destroy()
        self.checkboxes.clear()

        # Clear variables
        for var in self.option_vars.values():
            del var
        self.option_vars.clear()

        # Clear selections
        self.selected_options.clear()

    def _create_option_item(self, option: Dict[str, Any], index: int):
        """Create a single option item."""
        try:
            option_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            option_frame.pack(fill="x", pady=2, padx=5)

            option_id = option.get("id", str(index))
            display_text = option.get("display", option_id)
            is_auto = option.get("is_auto", False)

            # Add (Auto) suffix for auto-generated subtitles
            if is_auto:
                display_text += " (Auto)"

            # Create boolean variable
            var = ctk.BooleanVar(value=False)
            self.option_vars[option_id] = var

            # Create checkbox
            checkbox = ctk.CTkCheckBox(
                option_frame,
                text=display_text,
                variable=var,
                font=("Roboto", 10),
                command=lambda oid=option_id, v=var: self._handle_option_change(
                    oid, v.get()
                ),
            )
            checkbox.pack(anchor="w")

            self.checkboxes[option_id] = checkbox

        except Exception as e:
            print(f"Error creating option item {index}: {e}")

    def _handle_option_change(self, option_id: str, is_selected: bool):
        """Handle option selection change."""
        try:
            if is_selected and option_id not in self.selected_options:
                self.selected_options.append(option_id)
            elif not is_selected and option_id in self.selected_options:
                self.selected_options.remove(option_id)

            self._update_status()

            if self.on_change:
                self.on_change(self.selected_options.copy())

        except Exception as e:
            print(f"Error handling option change: {e}")

    def _update_status(self):
        """Update the status label."""
        try:
            count = len(self.selected_options)
            if count == 0:
                text = "0 selected"
            elif count == 1:
                text = "1 selected"
            else:
                text = f"{count} selected"

            self.status_label.configure(text=text)

        except Exception as e:
            print(f"Error updating status: {e}")

    def _select_all(self):
        """Select all options."""
        try:
            self.selected_options.clear()
            for option_id, var in self.option_vars.items():
                var.set(True)
                self.selected_options.append(option_id)

            self._update_status()

            if self.on_change:
                self.on_change(self.selected_options.copy())

        except Exception as e:
            print(f"Error selecting all: {e}")

    def _clear_all(self):
        """Clear all selections."""
        try:
            self.selected_options.clear()
            for var in self.option_vars.values():
                var.set(False)

            self._update_status()

            if self.on_change:
                self.on_change([])

        except Exception as e:
            print(f"Error clearing all: {e}")

    def get_selected_subtitles(self) -> list[dict[str, str]]:
        """Get currently selected subtitle dictionaries."""
        selected_dicts = []
        for option_id in self.selected_options:
            # Find the option details for this ID
            for option in self.options:
                if option.get("id") == option_id:
                    selected_dicts.append(
                        {
                            "language_code": option.get("language_code", option_id),
                            "language_name": option.get("display", option_id),
                            "is_auto_generated": str(option.get("is_auto", False)),
                            "url": option.get("url", ""),
                        }
                    )
                    break
        return selected_dicts

    def set_selected_subtitles(self, selected_ids: List[str]):
        """Set currently selected subtitle IDs."""
        try:
            self.selected_options = list(selected_ids)

            for option_id, var in self.option_vars.items():
                var.set(option_id in self.selected_options)

            self._update_status()

        except Exception as e:
            print(f"Error setting selected subtitles: {e}")

    def clear_selection(self):
        """Clear all selections (alias for _clear_all)."""
        self._clear_all()
