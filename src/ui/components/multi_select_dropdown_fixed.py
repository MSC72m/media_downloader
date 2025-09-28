"""Fixed multi-select dropdown component that doesn't block UI."""

import customtkinter as ctk
from typing import List, Dict, Any, Callable, Optional, Tuple
import threading


class SubtitleMultiSelect(ctk.CTkFrame):
    """Fixed multi-select dropdown that doesn't block the UI."""

    def __init__(
        self,
        master,
        placeholder: str = "Select subtitles...",
        options: List[Dict[str, Any]] = None,
        on_change: Optional[Callable[[List[str]], None]] = None,
        width: int = 200,
        height: int = 30,
        **kwargs
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.placeholder = placeholder
        self.options = options or []
        self.on_change = on_change
        self.width = width
        self.height = height
        self.selected_options: List[str] = []
        self.dropdown_window: Optional[ctk.CTkToplevel] = None
        self.is_open = False
        self._main_thread_id = threading.get_ident()

        self._create_widgets()
        self._bind_events()

    def _create_widgets(self):
        """Create the dropdown widgets."""
        # Main frame
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        # Main button
        self.main_button = ctk.CTkButton(
            self.main_frame,
            text=self.placeholder,
            command=self._toggle_dropdown,
            width=self.width,
            height=self.height,
            font=("Roboto", 11),
            anchor="w",
            fg_color=("gray90", "gray30"),
            hover_color=("gray80", "gray40")
        )
        self.main_button.pack(fill="x")

        # Dropdown arrow
        self.arrow_label = ctk.CTkLabel(
            self.main_button,
            text="▼",
            font=("Roboto", 12)
        )
        self.arrow_label.place(relx=0.95, rely=0.5, anchor="e")

    def _bind_events(self):
        """Bind window events."""
        # Bind escape key to close dropdown
        self.bind("<Escape>", lambda e: self._close_dropdown())

        # Bind focus out to close dropdown
        self.bind("<FocusOut>", self._handle_focus_out)

    def _toggle_dropdown(self):
        """Toggle dropdown visibility without blocking."""
        if self.is_open:
            self._close_dropdown()
        else:
            # Use after to prevent blocking
            self.after(1, self._open_dropdown)

    def _open_dropdown(self):
        """Open dropdown in a non-blocking way."""
        if self.is_open:
            return

        try:
            # Get button position
            self.main_button.update_idletasks()
            x = self.main_button.winfo_rootx()
            y = self.main_button.winfo_rooty() + self.main_button.winfo_height()

            # Create dropdown window
            self.dropdown_window = ctk.CTkToplevel(self.winfo_toplevel())
            self.dropdown_window.overrideredirect(True)
            self.dropdown_window.attributes('-topmost', True)
            self.dropdown_window.transient(self.winfo_toplevel())
            self.dropdown_window.geometry(f"{self.width}x250+{x}+{y}")

            # Main frame for dropdown
            main_frame = ctk.CTkFrame(self.dropdown_window, fg_color=("gray95", "gray25"))
            main_frame.pack(fill="both", expand=True, padx=2, pady=2)

            # Header
            header_label = ctk.CTkLabel(
                main_frame,
                text="Select Subtitles",
                font=("Roboto", 12, "bold")
            )
            header_label.pack(pady=(8, 4))

            # Scrollable frame for options
            scrollable_frame = ctk.CTkScrollableFrame(
                main_frame,
                width=self.width - 20,
                height=160,
                fg_color="transparent"
            )
            scrollable_frame.pack(fill="both", expand=True, padx=8, pady=4)

            # Create options
            self._create_options(scrollable_frame)

            # Button frame
            button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
            button_frame.pack(fill="x", pady=(4, 8))

            # Buttons
            done_btn = ctk.CTkButton(
                button_frame,
                text="Done",
                command=self._close_dropdown,
                width=60,
                height=25,
                font=("Roboto", 9)
            )
            done_btn.pack(side="right", padx=(4, 8))

            clear_btn = ctk.CTkButton(
                button_frame,
                text="Clear",
                command=self._clear_selection,
                width=60,
                height=25,
                font=("Roboto", 9)
            )
            clear_btn.pack(side="right")

            # Bind events to dropdown window
            self.dropdown_window.bind("<Escape>", lambda e: self._close_dropdown())
            self.dropdown_window.bind("<FocusOut>", self._handle_dropdown_focus_out)

            # Focus the dropdown
            self.dropdown_window.focus_set()
            self.is_open = True

        except Exception as e:
            print(f"Error opening dropdown: {e}")
            self._cleanup_dropdown()

    def _create_options(self, parent):
        """Create checkbox options."""
        self.checkboxes = {}

        for i, option in enumerate(self.options):
            try:
                option_frame = ctk.CTkFrame(parent, fg_color="transparent")
                option_frame.pack(fill="x", pady=1)

                option_id = option.get('id', str(i))
                display_text = option.get('display', option_id)
                is_auto = option.get('is_auto', False)

                # Checkbox
                var = ctk.BooleanVar(value=option_id in self.selected_options)
                checkbox = ctk.CTkCheckBox(
                    option_frame,
                    text=display_text + (" (Auto)" if is_auto else ""),
                    variable=var,
                    font=("Roboto", 10),
                    command=lambda oid=option_id, v=var: self._handle_option_change(oid, v.get())
                )
                checkbox.pack(anchor="w", padx=5, pady=2)

                self.checkboxes[option_id] = var

            except Exception as e:
                print(f"Error creating option {i}: {e}")

    def _handle_option_change(self, option_id: str, is_selected: bool):
        """Handle option selection change."""
        try:
            if is_selected and option_id not in self.selected_options:
                self.selected_options.append(option_id)
            elif not is_selected and option_id in self.selected_options:
                self.selected_options.remove(option_id)

            self._update_display_text()
            if self.on_change:
                self.on_change(self.selected_options.copy())

        except Exception as e:
            print(f"Error handling option change: {e}")

    def _update_display_text(self):
        """Update the button display text."""
        try:
            if not self.selected_options:
                display_text = self.placeholder
            elif len(self.selected_options) == 1:
                display_text = f"1 subtitle selected"
            else:
                display_text = f"{len(self.selected_options)} subtitles selected"

            self.main_button.configure(text=display_text)

        except Exception as e:
            print(f"Error updating display text: {e}")

    def _close_dropdown(self):
        """Close dropdown safely."""
        if self.dropdown_window:
            try:
                self.dropdown_window.destroy()
            except:
                pass
            self.dropdown_window = None

        self.checkboxes = {}
        self.is_open = False

    def _cleanup_dropdown(self):
        """Clean up dropdown resources."""
        self._close_dropdown()

    def _clear_selection(self):
        """Clear all selections."""
        try:
            self.selected_options.clear()
            for var in self.checkboxes.values():
                var.set(False)
            self._update_display_text()
            if self.on_change:
                self.on_change([])

        except Exception as e:
            print(f"Error clearing selection: {e}")

    def _handle_focus_out(self, event):
        """Handle focus out event."""
        # Small delay to allow checkbox clicks
        self.after(100, self._check_focus_and_close)

    def _handle_dropdown_focus_out(self, event):
        """Handle dropdown focus out."""
        self.after(50, self._check_focus_and_close)

    def _check_focus_and_close(self):
        """Check if we should close the dropdown."""
        if not self.is_open:
            return

        try:
            # Check if dropdown or any of its children have focus
            focused_widget = self.focus_get()
            if focused_widget is None or not self._is_widget_in_dropdown(focused_widget):
                self._close_dropdown()

        except Exception as e:
            print(f"Error checking focus: {e}")
            # Close on error
            self._close_dropdown()

    def _is_widget_in_dropdown(self, widget):
        """Check if widget is part of the dropdown."""
        if not self.dropdown_window:
            return False

        try:
            while widget:
                if widget == self.dropdown_window:
                    return True
                widget = widget.master
            return False
        except:
            return False

    def set_options(self, options: List[Dict[str, Any]]):
        """Set new options for the dropdown."""
        try:
            self.options = options or []
            self.selected_options.clear()
            self._update_display_text()

            # If dropdown is open, refresh it
            if self.is_open:
                self._close_dropdown()
                self.after(10, self._open_dropdown)

        except Exception as e:
            print(f"Error setting options: {e}")

    def set_subtitle_options(self, options: List[Dict[str, Any]]):
        """Set subtitle options (alias for set_options)."""
        return self.set_options(options)

    def get_selected_subtitles(self) -> List[str]:
        """Get currently selected subtitle IDs."""
        return self.selected_options.copy()

    def set_selected_subtitles(self, selected_ids: List[str]):
        """Set currently selected subtitle IDs."""
        try:
            self.selected_options = list(selected_ids)
            self._update_display_text()

            # Update checkboxes if dropdown is open
            for option_id, var in self.checkboxes.items():
                var.set(option_id in self.selected_options)

        except Exception as e:
            print(f"Error setting selected subtitles: {e}")

    def destroy(self):
        """Clean up when widget is destroyed."""
        self._cleanup_dropdown()
        super().destroy()