"""Theme switcher component for changing UI themes."""

from typing import Optional

import customtkinter as ctk

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.ui.utils.theme_manager import ThemeManager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeSwitcher(ctk.CTkFrame):
    """Theme switcher component with appearance and color selection."""

    def __init__(self, master, theme_manager: Optional[ThemeManager] = None):
        """Initialize theme switcher.
        
        Args:
            master: Parent widget
            theme_manager: Theme manager instance (creates singleton if None)
        """
        super().__init__(master, fg_color="transparent")
        
        self._theme_manager = theme_manager or ThemeManager.get_instance(master.winfo_toplevel())
        
        # Configure grid
        self.grid_columnconfigure((0, 1), weight=1)
        
        # Appearance mode switcher
        self.appearance_label = ctk.CTkLabel(
            self, text="Mode:", font=("Roboto", 12)
        )
        self.appearance_label.grid(row=0, column=0, padx=(0, 5), sticky="w")
        
        self.appearance_switch = ctk.CTkSegmentedButton(
            self,
            values=["Dark", "Light"],
            command=self._on_appearance_change,
            font=("Roboto", 11),
            height=28,
        )
        # Set initial value
        current_mode = self._theme_manager.get_appearance()
        self.appearance_switch.set("Dark" if current_mode == AppearanceMode.DARK else "Light")
        self.appearance_switch.grid(row=0, column=1, padx=(0, 10), sticky="ew")
        
        # Color theme switcher
        self.color_label = ctk.CTkLabel(
            self, text="Theme:", font=("Roboto", 12)
        )
        self.color_label.grid(row=0, column=2, padx=(10, 5), sticky="w")
        
        color_values = [theme.value.capitalize() for theme in ColorTheme]
        self.color_switch = ctk.CTkSegmentedButton(
            self,
            values=color_values,
            command=self._on_color_change,
            font=("Roboto", 11),
            height=28,
        )
        # Set initial value
        current_color = self._theme_manager.get_color_theme()
        self.color_switch.set(current_color.value.capitalize())
        self.color_switch.grid(row=0, column=3, padx=(0, 0), sticky="ew")
        
        # Update column weights
        self.grid_columnconfigure(3, weight=2)

    def _on_appearance_change(self, value: str) -> None:
        """Handle appearance mode change."""
        appearance = AppearanceMode.DARK if value == "Dark" else AppearanceMode.LIGHT
        current_color = self._theme_manager.get_color_theme()
        
        logger.info(f"[THEME_SWITCHER] Changing appearance to {appearance.value}")
        self._theme_manager.set_theme(appearance, current_color)

    def _on_color_change(self, value: str) -> None:
        """Handle color theme change."""
        try:
            color = ColorTheme(value.lower())
            current_appearance = self._theme_manager.get_appearance()
            
            logger.info(f"[THEME_SWITCHER] Changing color to {color.value}")
            self._theme_manager.set_theme(current_appearance, color)
        except ValueError:
            logger.error(f"[THEME_SWITCHER] Invalid color theme: {value}")

