"""Thread-safe theme manager using generic EventBus pattern."""

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

import customtkinter as ctk

from src.core.config import get_config, AppConfig
from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.core.enums.theme_event import ThemeEvent
from src.services.events.event_bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeManager(EventBus[ThemeEvent]):
    """Thread-safe theme manager using EventBus for observer pattern.
    
    Manages CustomTkinter theme appearance mode and color schemes.
    All theme changes are published via EventBus for real-time updates.
    """

    _instance: Optional["ThemeManager"] = None

    def __init__(self, root: Optional[Any] = None, config: AppConfig = get_config()):
        """Initialize theme manager.
        
        Args:
            root: Root window for main thread processing
            config: Application configuration
        """
        super().__init__(ThemeEvent, root)
        self._config = config
        self._current_appearance: AppearanceMode = config.ui.theme.appearance_mode_enum
        self._current_color: ColorTheme = config.ui.theme.color_theme_enum
        self._current_colors: Dict[str, Any] = {}
        
        # Initialize CTK with current theme
        self._apply_theme(self._current_appearance, self._current_color)
        
        logger.info(
            f"[THEME_MANAGER] Initialized with {self._current_appearance.value}/{self._current_color.value}"
        )

    @classmethod
    def get_instance(cls, root: Optional[Any] = None) -> "ThemeManager":
        """Get singleton instance of theme manager."""
        if cls._instance is None:
            cls._instance = cls(root)
        elif root and cls._instance._root != root:
            cls._instance.set_root(root)
        return cls._instance

    def set_theme(
        self, appearance: AppearanceMode, color: ColorTheme, persist: bool = True
    ) -> None:
        """Set theme - publishes event via EventBus for thread-safe updates.
        
        Args:
            appearance: Appearance mode (dark/light)
            color: Color theme
            persist: Whether to persist to config file
        """
        if appearance == self._current_appearance and color == self._current_color:
            logger.debug("[THEME_MANAGER] Theme unchanged, skipping")
            return

        self._current_appearance = appearance
        self._current_color = color

        # Apply theme immediately (on main thread)
        self._apply_theme(appearance, color)

        # Persist if requested
        if persist and self._config.ui.theme.theme_persistence:
            self._persist_theme()

        # Publish theme change event via EventBus (thread-safe)
        self.publish(ThemeEvent.THEME_CHANGED, appearance=appearance, color=color)
        logger.info(
            f"[THEME_MANAGER] Theme changed to {appearance.value}/{color.value}"
        )

    def _apply_theme(self, appearance: AppearanceMode, color: ColorTheme) -> None:
        """Apply theme to CustomTkinter."""
        # Set appearance mode
        ctk.set_appearance_mode(appearance.value)

        # Map our color themes to CTK built-in themes
        # CTK supports: "blue", "green", "dark-blue"
        ctk_theme_map = {
            ColorTheme.BLUE: "blue",
            ColorTheme.GREEN: "green",
            ColorTheme.PURPLE: "blue",  # Fallback to blue
            ColorTheme.ORANGE: "blue",  # Fallback to blue
            ColorTheme.TEAL: "green",  # Fallback to green
            ColorTheme.PINK: "blue",  # Fallback to blue
            ColorTheme.INDIGO: "blue",  # Fallback to blue
            ColorTheme.AMBER: "blue",  # Fallback to blue
        }
        
        ctk_theme = ctk_theme_map.get(color, "blue")
        ctk.set_default_color_theme(ctk_theme)

        # Store custom color scheme for components that want to use them
        color_scheme = self._get_color_scheme(appearance, color)
        self._apply_custom_colors(color_scheme)

    def _get_color_scheme(
        self, appearance: AppearanceMode, color: ColorTheme
    ) -> Dict[str, str]:
        """Get color scheme dictionary for appearance and color combination."""
        schemes = self._get_all_schemes()
        key = f"{appearance.value}_{color.value}"
        return schemes.get(key, schemes[f"{appearance.value}_blue"])

    def _get_all_schemes(self) -> Dict[str, Dict[str, str]]:
        """Get all color schemes."""
        return {
            # Dark themes
            "dark_blue": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#1f538d",
                "button_hover_color": "#14375e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_green": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#2d8659",
                "button_hover_color": "#1f5c3f",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_purple": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#7b2cbf",
                "button_hover_color": "#5a1f8f",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_orange": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#d97706",
                "button_hover_color": "#92400e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_teal": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#0d9488",
                "button_hover_color": "#0f766e",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_pink": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#db2777",
                "button_hover_color": "#be185d",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_indigo": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#4f46e5",
                "button_hover_color": "#4338ca",
                "text_color": ["#ffffff", "#ffffff"],
            },
            "dark_amber": {
                "fg_color": ["#1a1a1a", "#2b2b2b"],
                "hover_color": ["#3a3a3a", "#4a4a4a"],
                "border_color": ["#3a3a3a", "#4a4a4a"],
                "button_color": "#f59e0b",
                "button_hover_color": "#d97706",
                "text_color": ["#ffffff", "#ffffff"],
            },
            # Light themes
            "light_blue": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#3b82f6",
                "button_hover_color": "#2563eb",
                "text_color": ["#000000", "#000000"],
            },
            "light_green": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#10b981",
                "button_hover_color": "#059669",
                "text_color": ["#000000", "#000000"],
            },
            "light_purple": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#8b5cf6",
                "button_hover_color": "#7c3aed",
                "text_color": ["#000000", "#000000"],
            },
            "light_orange": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#f97316",
                "button_hover_color": "#ea580c",
                "text_color": ["#000000", "#000000"],
            },
            "light_teal": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#14b8a6",
                "button_hover_color": "#0d9488",
                "text_color": ["#000000", "#000000"],
            },
            "light_pink": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#ec4899",
                "button_hover_color": "#db2777",
                "text_color": ["#000000", "#000000"],
            },
            "light_indigo": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#6366f1",
                "button_hover_color": "#4f46e5",
                "text_color": ["#000000", "#000000"],
            },
            "light_amber": {
                "fg_color": ["#f0f0f0", "#ffffff"],
                "hover_color": ["#e0e0e0", "#f5f5f5"],
                "border_color": ["#d0d0d0", "#e0e0e0"],
                "button_color": "#fbbf24",
                "button_hover_color": "#f59e0b",
                "text_color": ["#000000", "#000000"],
            },
        }

    def _apply_custom_colors(self, color_scheme: Dict[str, Any]) -> None:
        """Apply custom colors to CTK widgets.
        
        Note: CustomTkinter doesn't have a direct API for custom color schemes,
        so we'll need to set colors per widget. For now, we set the default theme
        and widgets will need to use theme manager colors.
        """
        # CTK uses a theme system, but we can't directly override it
        # Instead, we'll store the colors and components will query them
        self._current_colors = color_scheme
        logger.debug(f"[THEME_MANAGER] Applied color scheme: {color_scheme}")

    def get_colors(self) -> Dict[str, Any]:
        """Get current color scheme."""
        return self._get_color_scheme(self._current_appearance, self._current_color)

    def get_appearance(self) -> AppearanceMode:
        """Get current appearance mode."""
        return self._current_appearance

    def get_color_theme(self) -> ColorTheme:
        """Get current color theme."""
        return self._current_color

    def _persist_theme(self) -> None:
        """Persist theme to config file."""
        try:
            config_file = Path.home() / ".media_downloader" / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Load existing config or create new
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
            else:
                config_data = {}

            # Update theme config
            if "ui" not in config_data:
                config_data["ui"] = {}
            if "theme" not in config_data["ui"]:
                config_data["ui"]["theme"] = {}

            config_data["ui"]["theme"]["appearance_mode"] = self._current_appearance.value
            config_data["ui"]["theme"]["color_theme"] = self._current_color.value

            # Write back
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            logger.info("[THEME_MANAGER] Theme persisted to config file")
        except Exception as e:
            logger.error(f"[THEME_MANAGER] Failed to persist theme: {e}", exc_info=True)

