from collections.abc import Callable, Iterator
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, resolve_palette
from src.utils.logger import get_logger

logger = get_logger(__name__)


class SubtitleChecklist(GlassFrame):
    """Simple scrollable checklist for subtitle selection."""

    def __init__(
        self,
        master,
        placeholder: str = "No subtitles available",
        on_change: Callable[[list[str]], None] | None = None,
        height: int = 120,
        config: AppConfig = get_config(),
        theme_manager: ThemeManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, theme_manager=theme_manager, **kwargs)

        self.placeholder = placeholder
        self.on_change = on_change
        self.height = height
        self.app_config = config
        self.selected_options: list[str] = []
        self.options: list[dict[str, Any]] = []
        self.checkboxes: dict[str, ctk.CTkCheckBox] = {}
        self.option_vars: dict[str, ctk.BooleanVar] = {}
        self._subtitle_generator: Iterator[tuple[dict[str, Any], int]] | None = None
        self._batch_size: int = self.app_config.ui.subtitle_batch_size
        self._current_index: int = 0
        self._batch_after_id: str | None = None

        self._create_widgets()

    def _create_widgets(self) -> None:
        """Create the checklist widgets."""
        palette = resolve_palette(self.theme_manager)
        self.title_label = ctk.CTkLabel(
            self,
            text="Available Subtitles:",
            font=("Roboto", 11, "bold"),
            text_color=palette.text,
        )
        self.title_label.pack(anchor="w", pady=(0, 5))

        self.scrollable_frame = ctk.CTkScrollableFrame(
            self,
            height=self.height,
            fg_color=palette.surface,
            border_color=palette.border,
            border_width=1,
        )
        self.scrollable_frame.pack(fill="both", expand=True)

        self.placeholder_label = ctk.CTkLabel(
            self.scrollable_frame,
            text=self.placeholder,
            font=("Roboto", 10),
            text_color=palette.text_muted,
        )
        self.placeholder_label.pack(pady=20)

        self.button_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.button_frame.pack(fill="x", pady=(5, 0))

        self.select_all_btn = GlassButton(
            self.button_frame,
            text="Select All",
            command=self._select_all,
            theme_manager=self.theme_manager,
            variant="secondary",
            width=80,
            height=25,
            font=("Roboto", 9),
        )
        self.select_all_btn.pack(side="left", padx=(0, 5))

        self.clear_all_btn = GlassButton(
            self.button_frame,
            text="Clear All",
            command=self._clear_all,
            theme_manager=self.theme_manager,
            variant="ghost",
            width=80,
            height=25,
            font=("Roboto", 9),
        )
        self.clear_all_btn.pack(side="left")

        self.status_label = ctk.CTkLabel(
            self.button_frame,
            text="0 selected",
            font=("Roboto", 9),
            text_color=palette.text_muted,
        )
        self.status_label.pack(side="right")

    def set_subtitle_options(self, subtitles: list[dict[str, Any]]) -> None:
        """Set subtitle options with generator-based batch loading to prevent UI freeze.

        Uses a generator with offset/indexing for efficient batch loading.
        Batch size is configurable via config.ui.subtitle_batch_size.
        """
        try:
            self.options = subtitles or []

            self._clear_existing_options()

            if not subtitles:
                self.placeholder_label.pack(pady=20)
                self.button_frame.pack_forget()
                return

            self.placeholder_label.pack_forget()
            self.button_frame.pack(fill="x", pady=(5, 0))

            self._subtitle_generator = self._subtitle_batch_generator(subtitles)
            self._current_index = 0

            self._load_next_batch()

        except Exception as e:
            logger.error(f"Error setting subtitle options: {e}", exc_info=True)

    def _subtitle_batch_generator(
        self, subtitles: list[dict[str, Any]]
    ) -> Iterator[tuple[dict[str, Any], int]]:
        """Generator that yields subtitles in batches with offset/indexing.

        Args:
            subtitles: Full list of subtitles to process

        Yields:
            Tuples of (subtitle_dict, index) for efficient batch processing
        """
        offset = 0
        while offset < len(subtitles):
            for i, subtitle in enumerate(
                subtitles[offset : offset + self._batch_size], start=offset
            ):
                yield subtitle, i
            offset += self._batch_size

    def _load_next_batch(self) -> None:
        """Load next batch of subtitles using generator with offset/indexing."""
        self._batch_after_id = None
        if not self._subtitle_generator:
            self._update_status()
            return

        try:
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

            [self._create_option_item(subtitle, index) for subtitle, index in batch_items]

            self._current_index += len(batch_items)

            if len(batch_items) == self._batch_size:
                self._batch_after_id = self.after(10, self._load_next_batch)
            else:
                self._update_status()

        except StopIteration:
            self._update_status()
        except Exception as e:
            logger.error(f"Error loading subtitle batch: {e}", exc_info=True)
            self._update_status()

    def _clear_existing_options(self) -> None:
        """Clear existing option widgets."""
        if self._batch_after_id is not None:
            self.after_cancel(self._batch_after_id)
            self._batch_after_id = None
        self._subtitle_generator = None
        self._current_index = 0

        [checkbox.destroy() for checkbox in self.checkboxes.values()]
        self.checkboxes.clear()

        self.option_vars.clear()

        self.selected_options.clear()

    def _create_option_item(self, option: dict[str, Any], index: int) -> None:
        """Create a single option item."""
        try:
            option_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            option_frame.pack(fill="x", pady=2, padx=5)

            option_id = option.get("id", str(index))
            display_text = option.get("display", option_id)

            var = ctk.BooleanVar(value=False)
            self.option_vars[option_id] = var

            palette = resolve_palette(self.theme_manager)
            checkbox = ctk.CTkCheckBox(
                option_frame,
                text=display_text,
                variable=var,
                font=("Roboto", 10),
                text_color=palette.text,
                fg_color=palette.accent,
                hover_color=palette.accent_hover,
                command=lambda oid=option_id, v=var: self._handle_option_change(oid, v.get()),
            )
            checkbox.pack(anchor="w")

            self.checkboxes[option_id] = checkbox

        except Exception as e:
            logger.error(f"Error creating option item {index}: {e}")

    def _handle_option_change(self, option_id: str, is_selected: bool) -> None:
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

    def _update_status(self) -> None:
        """Update the status label."""
        try:
            if (count := len(self.selected_options)) == 0:
                text = "0 selected"
            elif count == 1:
                text = "1 selected"
            else:
                text = f"{count} selected"

            self.status_label.configure(text=text)

        except Exception as e:
            logger.error(f"Error updating status: {e}")

    def _select_all(self) -> None:
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

    def _clear_all(self) -> None:
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

    def set_selected_subtitles(self, selected_ids: list[str]) -> None:
        """Set currently selected subtitle IDs."""
        try:
            self.selected_options = list(selected_ids)

            for option_id, var in self.option_vars.items():
                var.set(option_id in self.selected_options)

            self._update_status()

        except Exception as e:
            logger.error(f"Error setting selected subtitles: {e}")

    def clear_selection(self) -> None:
        """Clear all selections (alias for _clear_all)."""
        self._clear_all()

    def _handle_visual_theme_changed(self, appearance: str, color: str) -> None:
        super()._handle_visual_theme_changed(appearance, color)
        palette = resolve_palette(self.theme_manager)
        self.title_label.configure(text_color=palette.text)
        self.placeholder_label.configure(text_color=palette.text_muted)
        self.status_label.configure(text_color=palette.text_muted)
        self.scrollable_frame.configure(
            fg_color=palette.surface,
            border_color=palette.border,
        )
        for checkbox in self.checkboxes.values():
            checkbox.configure(
                text_color=palette.text,
                fg_color=palette.accent,
                hover_color=palette.accent_hover,
            )

    def destroy(self) -> None:
        if self._batch_after_id is not None:
            self.after_cancel(self._batch_after_id)
            self._batch_after_id = None
        super().destroy()
