"""Pydantic models for UI state management."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from src.models.enums.theme import UITheme
from src.models.enums.message import MessageLevel


class UIMessage(BaseModel):
    """Message to display in the UI."""
    text: str
    level: MessageLevel = Field(default=MessageLevel.INFO)
    duration: int = Field(default=5000, description="How long to display the message (ms)")
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class UIState(BaseModel):
    """Main UI state model."""
    theme: UITheme = Field(default=UITheme.DARK)
    download_directory: str = Field(default="~/Downloads")
    last_message: Optional[UIMessage] = Field(default=None)
    show_options_panel: bool = Field(default=False)
    selected_indices: List[int] = Field(default_factory=list)
    
    # Button states
    button_states: Dict[str, bool] = Field(
        default_factory=lambda: {
            "add": True,
            "remove": False,
            "clear": False,
            "download": False,
            "cancel": False,
            "pause": False,
            "resume": False,
            "settings": True,
            "instagram_login": True,
            "instagram_logout": False
        }
    )
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True

    def update_button_states(self, has_selection: bool, has_items: bool, is_downloading: bool = False):
        """Update button states based on app state."""
        self.button_states["remove"] = has_selection and not is_downloading
        self.button_states["clear"] = has_items and not is_downloading
        self.button_states["download"] = has_items and not is_downloading
        self.button_states["cancel"] = is_downloading
        self.button_states["pause"] = is_downloading
        self.button_states["resume"] = False  # Only enabled when specifically paused 