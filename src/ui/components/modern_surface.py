"""Canonical surface aliases backed by the centralized visual system."""

from __future__ import annotations

from typing import Any

from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassFrame


class BaseSurface(GlassFrame):
    def __init__(
        self,
        master: Any,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            elevation="base",
            **kwargs,
        )


class RaisedSurface(GlassFrame):
    def __init__(
        self,
        master: Any,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            elevation="raised",
            **kwargs,
        )
