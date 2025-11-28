"""Theme switcher component with modern UI/UX design."""

from typing import Optional

import customtkinter as ctk

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.ui.utils.theme_manager import get_theme_manager
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ThemeSwitcher(ctk.CTkFrame):
    """Modern theme switcher with dropdown menu for better UX."""

    def __init__(self, master, theme_manager: Optional["ThemeManager"] = None):
        """Initialize theme switcher with modern design.
        
        Args:
            master: Parent widget
            theme_manager: Theme manager instance (creates singleton if None)
        """
        super().__init__(master, fg_color="transparent")
        
        # Theme manager injected with default
        self._theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        
        # Configure grid - single row, compact design
        self.grid_columnconfigure(0, weight=1)
        
        # Create compact container
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=0, sticky="e")
        
        # Appearance mode toggle - compact switch with proper initialization
        current_mode = self._theme_manager.get_appearance()
        is_dark = current_mode == AppearanceMode.DARK
        
        self.appearance_switch = ctk.CTkSwitch(
            container,
            text="🌙 Dark" if is_dark else "☀️ Light",
            command=self._on_appearance_toggle,
            font=("Roboto", 11),
            width=90,
        )
        if is_dark:
            self.appearance_switch.select()
        self.appearance_switch.grid(row=0, column=0, padx=(0, 15))
        
        # Color theme dropdown - modern combobox
        self.color_label = ctk.CTkLabel(
            container, text="Theme:", font=("Roboto", 11)
        )
        self.color_label.grid(row=0, column=1, padx=(0, 5), sticky="w")
        
        # Create theme options with emoji indicators
        theme_options = {
            "Blue": "🔵",
            "Green": "🟢", 
            "Purple": "🟣",
            "Orange": "🟠",
            "Teal": "🔷",
            "Pink": "🌸",
            "Indigo": "💙",
            "Amber": "🟡",
        }
        
        color_values = [f"{emoji} {name}" for name, emoji in theme_options.items()]
        current_color = self._theme_manager.get_color_theme()
        current_display = f"{theme_options.get(current_color.value.capitalize(), '🔵')} {current_color.value.capitalize()}"
        
        # Use CTkOptionMenu instead of CTkComboBox - non-editable dropdown button
        self.color_dropdown = ctk.CTkOptionMenu(
            container,
            values=color_values,
            command=self._on_color_change,
            font=("Roboto", 11),
            width=120,
            height=28,
            dropdown_font=("Roboto", 11),
        )
        self.color_dropdown.set(current_display)
        self.color_dropdown.grid(row=0, column=2, padx=(0, 0))

    def _on_appearance_toggle(self) -> None:
        """Handle appearance mode toggle."""
        is_dark = self.appearance_switch.get()
        appearance = AppearanceMode.DARK if is_dark else AppearanceMode.LIGHT
        current_color = self._theme_manager.get_color_theme()
        
        logger.info(f"[THEME_SWITCHER] Changing appearance to {appearance.value}")
        self._theme_manager.set_theme(appearance, current_color)
        
        # Update switch text
        self.appearance_switch.configure(text="🌙 Dark" if is_dark else "☀️ Light")

    def _on_color_change(self, value: str) -> None:
        """Handle color theme change."""
        # Extract color name from display string (e.g., "🔵 Blue" -> "blue")
        color_name = value.split()[-1].lower()
        try:
            color = ColorTheme(color_name)
            current_appearance = self._theme_manager.get_appearance()
            
            logger.info(f"[THEME_SWITCHER] Changing color to {color.value}")
            self._theme_manager.set_theme(current_appearance, color)
        except ValueError:
            logger.error(f"[THEME_SWITCHER] Invalid color theme: {color_name}")
