"""Thread-safe theme manager using generic EventBus pattern."""

from functools import cache
from typing import Any, Dict, Optional

import customtkinter as ctk

from src.core.config import get_config, AppConfig
from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.core.enums.theme_event import ThemeEvent
from src.services.events.event_bus import EventBus
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Module-level cached theme manager instance
_theme_manager_instance: Optional["ThemeManager"] = None


class ThemeManager(EventBus[ThemeEvent]):
    """Thread-safe theme manager using EventBus for observer pattern.
    
    Manages CustomTkinter theme appearance mode and color schemes.
    All theme changes are published via EventBus for real-time updates.
    """

    def __init__(self, root: Optional[Any] = None, config: AppConfig = get_config()):
        """Initialize theme manager.
        
        Args:
            root: Root window for main thread processing
            config: Application configuration (injected with get_config() default)
        """
        super().__init__(ThemeEvent, root)
        self.config = config
        self._current_appearance: AppearanceMode = config.ui.theme.appearance_mode_enum
        self._current_color: ColorTheme = config.ui.theme.color_theme_enum
        self._current_colors: Dict[str, Any] = {}
        self._theme_json: Dict[str, Any] = {}
        
        # Initialize CTK with current theme - must be done before creating widgets
        self._apply_theme(self._current_appearance, self._current_color)
        
        logger.info(
            f"[THEME_MANAGER] Initialized with {self._current_appearance.value}/{self._current_color.value}"
        )

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
        # This must happen before publishing event so widgets get updated
        self._apply_theme(appearance, color)
        
        # Force CTK to update all widgets - critical for dark mode
        if self._root:
            self._root.update()

        # Persist if requested
        if persist and self.config.ui.theme.theme_persistence:
            self._persist_theme()

        # Publish theme change event via EventBus (thread-safe)
        self.publish(ThemeEvent.THEME_CHANGED, appearance=appearance, color=color)
        logger.info(
            f"[THEME_MANAGER] Theme changed to {appearance.value}/{color.value}"
        )

    def _apply_theme(self, appearance: AppearanceMode, color: ColorTheme) -> None:
        """Apply theme to CustomTkinter with custom color schemes."""
        # Set appearance mode first - this is critical for dark/light mode
        # Must be called before any widgets are created for proper initialization
        ctk.set_appearance_mode(appearance.value)
        
        # Get theme JSON and color scheme from config
        self._theme_json = self.config.ui.theme.get_theme_json(appearance, color)
        color_scheme = self._get_color_scheme(appearance, color)
        self._current_colors = color_scheme
        
        logger.debug("[THEME_MANAGER] Applied theme and color scheme")

    def _get_color_scheme(
        self, appearance: AppearanceMode, color: ColorTheme
    ) -> Dict[str, Any]:
        """Get color scheme dictionary for appearance and color combination."""
        schemes = self.config.ui.theme.get_color_schemes()
        key = f"{appearance.value}_{color.value}"
        return schemes.get(key, schemes[f"{appearance.value}_blue"])

    def get_colors(self) -> Dict[str, Any]:
        """Get current color scheme."""
        return self._get_color_scheme(self._current_appearance, self._current_color)
    
    def get_theme_json(self) -> Dict[str, Any]:
        """Get current theme JSON structure."""
        return self._theme_json

    def get_appearance(self) -> AppearanceMode:
        """Get current appearance mode."""
        return self._current_appearance

    def get_color_theme(self) -> ColorTheme:
        """Get current color theme."""
        return self._current_color

    def _persist_theme(self) -> None:
        """Persist theme to config file using config object."""
        try:
            # Update config object with enum values (not strings)
            self.config.ui.theme.appearance_mode = self._current_appearance
            self.config.ui.theme.color_theme = self._current_color
            
            # Save using config object's save method
            self.config.save_to_file()
            logger.info("[THEME_MANAGER] Theme persisted to config file")
        except Exception as e:
            logger.error(f"[THEME_MANAGER] Failed to persist theme: {e}", exc_info=True)


@cache
def get_theme_manager(root: Optional[Any] = None) -> ThemeManager:
    """Get cached theme manager instance.
    
    Uses module-level caching to ensure single instance per root window.
    
    Args:
        root: Optional root window for main thread processing
        
    Returns:
        ThemeManager instance (cached per root)
    """
    global _theme_manager_instance
    
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager(root)
    elif root and _theme_manager_instance._root != root:
        _theme_manager_instance.set_root(root)
    
    return _theme_manager_instance
