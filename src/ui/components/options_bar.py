from __future__ import annotations

import queue
from typing import TYPE_CHECKING

import customtkinter as ctk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import get_theme_manager
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.ui.utils.theme_manager import ThemeManager

logger = get_logger(__name__)


class OptionsBar(ctk.CTkFrame):
    def __init__(self, master, theme_manager: ThemeManager | None = None):
        super().__init__(master, fg_color="transparent")

        self._update_queue = queue.Queue()
        self._running = True
        self._root_window = self._get_root_window()

        self._theme_manager = theme_manager or get_theme_manager(self._root_window)
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

        self._process_queue()

    def _on_theme_changed(self, appearance, color):
        pass

    def _get_root_window(self):
        try:
            return self.winfo_toplevel()
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error getting root window: {e}")
            return self

    def _process_queue(self):
        if not self._running:
            return

        try:
            while not self._update_queue.empty():
                try:
                    update_func = self._update_queue.get_nowait()
                    update_func()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"[OPTIONS_BAR] Error processing update: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error in _process_queue: {e}", exc_info=True)

        if self._running and self._root_window:
            try:
                self._root_window.after(50, self._process_queue)
            except Exception as e:
                logger.error(f"[OPTIONS_BAR] Error scheduling next queue check: {e}")

    def _queue_update(self, update_func):
        try:
            self._update_queue.put(update_func)
        except Exception as e:
            logger.error(f"[OPTIONS_BAR] Error queuing update: {e}", exc_info=True)

    def destroy(self):
        self._running = False
        super().destroy()
