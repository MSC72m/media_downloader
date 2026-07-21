"""Focus ring styling helper for keyboard accessibility.

Provides focus ring styling for keyboard navigation and accessibility.
"""

from __future__ import annotations

import customtkinter as ctk

from src.ui import tokens


class FocusRingHelper:
    """Helper for managing focus ring styling on widgets.

    Focus rings are essential for keyboard accessibility. This helper provides
    utilities to apply consistent focus styling across all components.
    """

    @staticmethod
    def apply_focus_ring(
        widget: ctk.CTkWidget,
        ring_color: str = tokens.FOCUS_RING,
        ring_width: int = tokens.FOCUS_WIDTH,
    ) -> None:
        """Apply focus ring styling to a widget.

        Args:
            widget: Widget to apply focus ring to
            ring_color: Colour for the focus ring
            ring_width: Width of the focus ring in pixels
        """
        # Store focus ring properties on widget for retrieval
        widget._focus_ring_color = ring_color
        widget._focus_ring_width = ring_width

    @staticmethod
    def get_focus_ring_color(widget: ctk.CTkWidget) -> str:
        """Get the focus ring colour for a widget.

        Args:
            widget: Widget to get focus ring colour from

        Returns:
            Focus ring colour hex string
        """
        return getattr(widget, "_focus_ring_color", tokens.FOCUS_RING)

    @staticmethod
    def get_focus_ring_width(widget: ctk.CTkWidget) -> int:
        """Get the focus ring width for a widget.

        Args:
            widget: Widget to get focus ring width from

        Returns:
            Focus ring width in pixels
        """
        return getattr(widget, "_focus_ring_width", tokens.FOCUS_WIDTH)


def apply_focus_ring(
    widget: ctk.CTkWidget,
    ring_color: str = tokens.FOCUS_RING,
    ring_width: int = tokens.FOCUS_WIDTH,
) -> None:
    """Apply focus ring styling to a widget (module-level function).

    Args:
        widget: Widget to apply focus ring to
        ring_color: Colour for the focus ring
        ring_width: Width of the focus ring in pixels
    """
    FocusRingHelper.apply_focus_ring(widget, ring_color, ring_width)
