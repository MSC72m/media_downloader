from __future__ import annotations

from functools import cache
from typing import Any

import customtkinter as ctk

from src.core.config import AppConfig, get_config
from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.core.enums.theme_event import ThemeEvent
from src.services.events.event_bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)

_theme_manager_instance: ThemeManager | None = None


class ThemeManager(EventBus[ThemeEvent]):
    def __init__(self, root: Any | None = None, config: AppConfig = get_config()):
        super().__init__(ThemeEvent, root)
        self.config = config
        self._current_appearance: AppearanceMode = config.ui.theme.appearance_mode_enum
        self._current_color: ColorTheme = config.ui.theme.color_theme_enum
        self._current_colors: dict[str, Any] = {}
        self._theme_json: dict[str, Any] = {}

        self._apply_theme(self._current_appearance, self._current_color)

        logger.info(
            f"[THEME_MANAGER] Initialized with {self._current_appearance.value}/{self._current_color.value}"
        )

    def set_theme(
        self, appearance: AppearanceMode, color: ColorTheme, persist: bool = True
    ) -> None:
        if appearance == self._current_appearance and color == self._current_color:
            logger.debug("[THEME_MANAGER] Theme unchanged, skipping")
            return

        self._current_appearance = appearance
        self._current_color = color

        self._apply_theme(appearance, color)

        if self._root:
            self._root.update()

        if persist and self.config.ui.theme.theme_persistence:
            self._persist_theme()

        self.publish(ThemeEvent.THEME_CHANGED, appearance=appearance, color=color)
        logger.info(f"[THEME_MANAGER] Theme changed to {appearance.value}/{color.value}")

    def _apply_theme(self, appearance: AppearanceMode, color: ColorTheme) -> None:
        ctk.set_appearance_mode(appearance.value)

        self._theme_json = self.config.ui.theme.get_theme_json(appearance, color)
        color_scheme = self._get_color_scheme(appearance, color)
        self._current_colors = color_scheme

        logger.debug("[THEME_MANAGER] Applied theme and color scheme")

    def _get_color_scheme(self, appearance: AppearanceMode, color: ColorTheme) -> dict[str, Any]:
        schemes = self.config.ui.theme.get_color_schemes()
        key = f"{appearance.value}_{color.value}"
        return schemes.get(key, schemes[f"{appearance.value}_blue"])

    def get_colors(self) -> dict[str, Any]:
        return self._get_color_scheme(self._current_appearance, self._current_color)

    def get_theme_json(self) -> dict[str, Any]:
        return self._theme_json

    def get_appearance(self) -> AppearanceMode:
        return self._current_appearance

    def get_color_theme(self) -> ColorTheme:
        return self._current_color

    def _persist_theme(self) -> None:
        try:
            self.config.ui.theme.appearance_mode = self._current_appearance
            self.config.ui.theme.color_theme = self._current_color

            self.config.save_to_file()
            logger.info("[THEME_MANAGER] Theme persisted to config file")
        except Exception as e:
            logger.error(f"[THEME_MANAGER] Failed to persist theme: {e}", exc_info=True)


@cache
def get_theme_manager(root: Any | None = None) -> ThemeManager:
    global _theme_manager_instance  # noqa: PLW0603

    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager(root)
    elif root and _theme_manager_instance._root != root:
        _theme_manager_instance.set_root(root)

    return _theme_manager_instance
