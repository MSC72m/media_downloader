"""Appearance mode enum for theme system."""

from .compat import StrEnum


class AppearanceMode(StrEnum):
    """Appearance mode options for the UI theme."""

    DARK = "dark"
    LIGHT = "light"
