"""Theme event enum for theme change notifications."""

from enum import Enum, auto


class ThemeEvent(Enum):
    """Theme change event types."""

    THEME_CHANGED = auto()
