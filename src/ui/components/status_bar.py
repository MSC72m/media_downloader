from __future__ import annotations

import contextlib
import queue
import re
import time

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StatusBar(ctk.CTkFrame):
    _SUCCESS_MESSAGE_PATTERN = re.compile(r"Download completed", re.IGNORECASE)
    _CONNECTION_CONFIRMED_PATTERN = re.compile(r"Connection confirmed", re.IGNORECASE)

    def __init__(
        self,
        master,
        config: AppConfig = get_config(),
        theme_manager: ThemeManager | None = None,
    ):
        super().__init__(master, fg_color="transparent")

        self._root_window = self._get_root_window()
        self._update_queue = queue.Queue(maxsize=50)
        self._message_queue = queue.Queue(maxsize=20)
        self._running = True
        self._current_message: str | None = None
        self._message_timeout: float | None = None
        self._is_error_message: bool = False
        self._config = config

        self._theme_manager = theme_manager or get_theme_manager(self._root_window)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)

        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0, sticky="nsew")
        self.center_frame.grid_columnconfigure(0, weight=1)

        self.status_label = ctk.CTkLabel(
            self.center_frame, text="Initializing...", font=("Roboto", 12)
        )
        self.status_label.grid(row=0, column=0, pady=(0, 2))

        self.progress_bar = ctk.CTkProgressBar(
            self.center_frame,
            height=22,
            corner_radius=8,
            border_width=0,
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 0), padx=0)
        self.progress_bar.set(0)

        self._apply_theme_colors()

        self._process_queue()
        self._process_messages()

    def _get_root_window(self):
        try:
            return self.winfo_toplevel()
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error getting root window: {e}")
            return self

    def _process_queue(self):
        if not self._running:
            return

        try:
            max_updates_per_cycle = 3
            updates_processed = 0

            while updates_processed < max_updates_per_cycle and not self._update_queue.empty():
                try:
                    update_func = self._update_queue.get_nowait()
                    update_func()
                    updates_processed += 1
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"[STATUS_BAR] Error processing update: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error in _process_queue: {e}", exc_info=True)

        if self._running and self._root_window:
            try:
                self._root_window.after(33, self._process_queue)
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error scheduling next queue check: {e}")

    def _queue_update(self, update_func):
        try:
            if self._update_queue.full():
                with contextlib.suppress(queue.Empty):
                    self._update_queue.get_nowait()
            self._update_queue.put_nowait(update_func)
        except queue.Full:
            pass
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error queuing update: {e}", exc_info=True)

    def show_message(self, message: str):
        self._add_message(message)

    def show_error(self, message: str):
        error_text = f"Error: {message}"
        self._add_message(error_text, is_error=True)

    def show_warning(self, message: str):
        warning_text = f"Warning: {message}"
        self._add_message(warning_text)

    def _add_message(self, message: str, is_error: bool = False) -> None:
        def _update():
            try:
                is_success_message = bool(self._SUCCESS_MESSAGE_PATTERN.search(message))
                is_connection_confirmed = bool(self._CONNECTION_CONFIRMED_PATTERN.search(message))

                if is_connection_confirmed:
                    self._connection_confirmed_shown = True

                if not self._current_message:
                    self._current_message = message
                    self._is_error_message = is_error
                    current_time = time.time()
                    timeout_seconds = (
                        self._config.ui.error_message_timeout_seconds
                        if is_error
                        else self._config.ui.message_timeout_seconds
                    )
                    self._message_timeout = current_time + timeout_seconds
                    self.status_label.configure(text=message)
                    return

                if is_success_message:
                    self._current_message = message
                    self._is_error_message = is_error
                    current_time = time.time()
                    timeout_seconds = self._config.ui.message_timeout_seconds
                    self._message_timeout = current_time + timeout_seconds
                    self.status_label.configure(text=message)
                    return

                self._message_queue.put((message, is_error))
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error adding message: {e}", exc_info=True)

        self._queue_update(_update)

    def _check_message_timeout(self, current_time: float) -> None:
        if (
            self._current_message
            and self._message_timeout
            and current_time >= self._message_timeout
        ):
            self._current_message = None
            self._message_timeout = None
            self._is_error_message = False

    def _get_next_message(self, current_time: float) -> None:
        if self._current_message or self._message_queue.empty():
            return

        try:
            message_data = self._message_queue.get_nowait()
            if isinstance(message_data, tuple):
                self._current_message, self._is_error_message = message_data
            else:
                self._current_message = message_data
                self._is_error_message = False

            timeout_seconds = (
                self._config.ui.error_message_timeout_seconds
                if self._is_error_message
                else self._config.ui.message_timeout_seconds
            )

            self._message_timeout = current_time + timeout_seconds
            self.status_label.configure(text=self._current_message)
        except queue.Empty:
            pass

    def _show_ready_if_no_message(self) -> None:
        if not self._current_message:
            self.status_label.configure(text="Ready")
            if hasattr(self, "_connection_confirmed_shown"):
                self._connection_confirmed_shown = False

    def _process_messages(self):
        if not self._running:
            return

        try:
            current_time = time.time()
            self._check_message_timeout(current_time)
            self._get_next_message(current_time)
            self._show_ready_if_no_message()

        except Exception as e:
            logger.error(f"[STATUS_BAR] Error processing messages: {e}", exc_info=True)

        if self._running and self._root_window:
            try:
                self._root_window.after(100, self._process_messages)
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error scheduling message check: {e}")

    def update_progress(self, progress: float):
        def _update():
            try:
                self.progress_bar.set(progress / 100)
                if progress >= 100:
                    self.status_label.configure(text="Download Complete")
                    self._current_message = None
                    self._message_timeout = None
                else:
                    self.status_label.configure(text=f"Downloading... {progress:.1f}%")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error updating progress: {e}", exc_info=True)

        if progress >= 100:
            try:
                _update()
                if self._running and self._root_window:
                    self._root_window.after_idle(self._process_queue)
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error in immediate progress update: {e}")
        else:
            self._queue_update(_update)

    def reset(self):
        def _update():
            try:
                self.progress_bar.set(0)
                self.status_label.configure(text="Ready")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error resetting: {e}", exc_info=True)

        self._queue_update(_update)

    def _on_theme_changed(self, appearance, color):
        self._apply_theme_colors()

    def _apply_theme_colors(self):
        if not hasattr(self, "progress_bar"):
            return

        self._theme_manager.get_colors()
        theme_json = self._theme_manager.get_theme_json()

        button_config = theme_json.get("CTkButton", {})
        if button_config:
            progress_color = button_config.get("fg_color")
            if progress_color:
                self.progress_bar.configure(progress_color=progress_color)

    def destroy(self):
        self._running = False
        if self._theme_manager:
            self._theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
