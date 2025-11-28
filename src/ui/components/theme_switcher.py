"""Theme switcher component with modern UI/UX design."""

from typing import Optional

import customtkinter as ctk

from src.core.enums.appearance_mode import AppearanceMode
from src.core.enums.color_theme import ColorTheme
from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import get_theme_manager, ThemeManager
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
        self._theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        
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
        
        # Color theme dropdown - modern combobox (read-only)
        self.color_label = ctk.CTkLabel(
            container, text="Theme:", font=("Roboto", 11)
        )
        self.color_label.grid(row=0, column=1, padx=(0, 5), sticky="w")
        
        # Create theme options with emoji indicators - expanded color palette
        theme_options = {
            "Blue": "🔵",
            "Green": "🟢", 
            "Purple": "🟣",
            "Orange": "🟠",
            "Teal": "🔷",
            "Pink": "🌸",
            "Indigo": "💙",
            "Amber": "🟡",
            "Red": "🔴",
            "Cyan": "🔵",
            "Emerald": "💚",
            "Rose": "🌹",
            "Violet": "🟣",
            "Slate": "⚫",
        }
        
        color_values = [f"{emoji} {name}" for name, emoji in theme_options.items()]
        current_color = self._theme_manager.get_color_theme()
        current_display = f"{theme_options.get(current_color.value.capitalize(), '🔵')} {current_color.value.capitalize()}"
        
        # Use CTkComboBox - modern look, prevent text editing
        self.color_dropdown = ctk.CTkComboBox(
            container,
            values=color_values,
            command=self._on_color_change,
            font=("Roboto", 11),
            width=130,
            height=30,
            dropdown_font=("Roboto", 11),
        )
        self.color_dropdown.set(current_display)
        self.color_dropdown.grid(row=0, column=2, padx=(0, 0))
        
        # Prevent text editing by binding events
        self._make_combobox_readonly()
        
        # Apply initial theme colors
        self._apply_theme_colors()
    
    def _make_combobox_readonly(self):
        """Make combobox read-only by binding events to prevent editing."""
        def prevent_edit(event):
            # Allow dropdown to open, but prevent text editing
            if event.keysym not in ("Return", "Escape", "Up", "Down"):
                return "break"
        
        def prevent_selection(event):
            # Prevent text selection
            return "break"
        
        # Get the entry widget inside the combobox and prevent editing
        try:
            entry = self.color_dropdown._entry
            # Prevent typing
            entry.bind("<Key>", prevent_edit)
            # Prevent text selection
            entry.bind("<Button-1>", lambda e: self.color_dropdown._open_dropdown_menu())
            entry.bind("<Control-a>", prevent_selection)
            entry.bind("<Button-3>", prevent_selection)  # Right click
        except Exception:
            pass  # If we can't access the entry, that's okay
    
    def _apply_theme_colors(self):
        """Apply theme colors to switcher components."""
        theme_json = self._theme_manager.get_theme_json()
        
        # Apply colors to switch
        button_config = theme_json.get("CTkButton", {})
        if button_config:
            self.appearance_switch.configure(
                progress_color=button_config.get("fg_color"),
                button_color=button_config.get("fg_color"),
                button_hover_color=button_config.get("hover_color"),
            )
        
        # Apply colors to combobox
        entry_config = theme_json.get("CTkEntry", {})
        if entry_config:
            self.color_dropdown.configure(
                fg_color=entry_config.get("fg_color"),
                border_color=entry_config.get("border_color"),
                button_color=button_config.get("fg_color") if button_config else None,
                button_hover_color=button_config.get("hover_color") if button_config else None,
            )
        
        # Apply colors to label
        label_config = theme_json.get("CTkLabel", {})
        if label_config:
            self.color_label.configure(text_color=label_config.get("text_color"))

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
    
    def _on_theme_changed(self, appearance, color):
        """Handle theme change event - update component colors."""
        self._apply_theme_colors()
        
        # Update dropdown display value
        theme_options = {
            "Blue": "🔵", "Green": "🟢", "Purple": "🟣", "Orange": "🟠",
            "Teal": "🔷", "Pink": "🌸", "Indigo": "💙", "Amber": "🟡",
        }
        current_display = f"{theme_options.get(color.value.capitalize(), '🔵')} {color.value.capitalize()}"
        self.color_dropdown.set(current_display)
