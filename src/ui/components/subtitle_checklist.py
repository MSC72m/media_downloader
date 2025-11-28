"""Subtitle checklist component for YouTube downloads."""

from collections.abc import Callable, Iterator
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SubtitleChecklist(ctk.CTkFrame):
    """Simple scrollable checklist for subtitle selection."""

    def __init__(
        self,
        master,
        placeholder: str = "No subtitles available",
        on_change: Callable[[list[dict[str, str]]], None] | None = None,
        height: int = 120,
        config: AppConfig = get_config(),
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self.placeholder = placeholder
        self.on_change = on_change
        self.height = height
        self.config = config
        self.selected_options: list[str] = []
        self.options: list[dict[str, Any]] = []
        self.checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self.option_vars: dict[str, ctk.BooleanVar] = {}
        self._subtitle_generator: Iterator[dict[str, Any]] | None = None
        self._batch_size: int = self.config.ui.subtitle_batch_size
        self._current_index: int = 0

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
        """Set subtitle options with generator-based batch loading to prevent UI freeze.

        Uses a generator with offset/indexing for efficient batch loading.
        Batch size is configurable via config.ui.subtitle_batch_size.
        """
        try:
            # Store all options
            self.options = subtitles or []

            # Clear existing options
            self._clear_existing_options()

            if not subtitles:
                self.placeholder_label.pack(pady=20)
                self.button_frame.pack_forget()
                return

            # Hide placeholder and show buttons
            self.placeholder_label.pack_forget()
            self.button_frame.pack(fill="x", pady=(5, 0))

            # Create generator for efficient batch loading with offset/indexing
            self._subtitle_generator = self._subtitle_batch_generator(subtitles)
            self._current_index = 0

            # Load first batch immediately
            self._load_next_batch()

        except Exception as e:
            logger.error(f"Error setting subtitle options: {e}", exc_info=True)

    def _subtitle_batch_generator(
        self, subtitles: list[dict[str, Any]]
    ) -> Iterator[dict[str, Any]]:
        """Generator that yields subtitles in batches with offset/indexing.

        Args:
            subtitles: Full list of subtitles to process

        Yields:
            Tuples of (subtitle_dict, index) for efficient batch processing
        """
        offset = 0
        while offset < len(subtitles):
            # Yield batch with indexing
            for i, subtitle in enumerate(
                subtitles[offset : offset + self._batch_size], start=offset
            ):
                yield subtitle, i
            offset += self._batch_size

    def _load_next_batch(self) -> None:
        """Load next batch of subtitles using generator with offset/indexing."""
        if not self._subtitle_generator:
            self._update_status()
            return

        try:
            # Load batch using generator - efficient with offset/indexing
            batch_items = []
            for _ in range(self._batch_size):
                try:
                    subtitle, index = next(self._subtitle_generator)
                    batch_items.append((subtitle, index))
                except StopIteration:
                    break

            if not batch_items:
                self._update_status()
                return

            # Create options for this batch using list comprehension
            [self._create_option_item(subtitle, index) for subtitle, index in batch_items]

            self._current_index += len(batch_items)

            # Schedule next batch if generator has more (check if we got full batch)
            if len(batch_items) == self._batch_size:
                self.after(10, self._load_next_batch)  # Small delay to keep UI responsive
            else:
                self._update_status()

        except StopIteration:
            self._update_status()
        except Exception as e:
            logger.error(f"Error loading subtitle batch: {e}", exc_info=True)
            self._update_status()

    def _clear_existing_options(self):
        """Clear existing option widgets."""
        # Cancel any pending batch loads
        self._subtitle_generator = None
        self._current_index = 0

        # Clear checkboxes using list comprehension
        [checkbox.destroy() for checkbox in self.checkboxes.values()]
        self.checkboxes.clear()

        # Clear variables
        self.option_vars.clear()

        # Clear selections
        self.selected_options.clear()

    def _create_option_item(self, option: dict[str, Any], index: int):
        """Create a single option item."""
        try:
            option_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            option_frame.pack(fill="x", pady=2, padx=5)

            option_id = option.get("id", str(index))
            display_text = option.get("display", option_id)
            # Note: display_text already contains "(Auto)" suffix if it's auto-generated
            # (added in metadata_parser), so we don't add it again here

            # Create boolean variable
            var = ctk.BooleanVar(value=False)
            self.option_vars[option_id] = var

            # Create checkbox
            checkbox = ctk.CTkCheckBox(
                option_frame,
                text=display_text,
                variable=var,
                font=("Roboto", 10),
                command=lambda oid=option_id, v=var: self._handle_option_change(oid, v.get()),
            )
            checkbox.pack(anchor="w")

            self.checkboxes[option_id] = checkbox

        except Exception as e:
            logger.error(f"Error creating option item {index}: {e}")

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
            logger.error(f"Error handling option change: {e}")

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
            logger.error(f"Error updating status: {e}")

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
            logger.error(f"Error selecting all: {e}")

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
            logger.error(f"Error clearing all: {e}")

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

    def set_selected_subtitles(self, selected_ids: list[str]):
        """Set currently selected subtitle IDs."""
        try:
            self.selected_options = list(selected_ids)

            for option_id, var in self.option_vars.items():
                var.set(option_id in self.selected_options)

            self._update_status()

        except Exception as e:
            logger.error(f"Error setting selected subtitles: {e}")

    def clear_selection(self):
        """Clear all selections (alias for _clear_all)."""
        self._clear_all()
