"""Portable gradient and depth rendering helper.

Provides utilities for rendering gradients and depth effects with opaque fallbacks
for cross-platform safety and performance.
"""

from __future__ import annotations


class GradientHelper:
    """Helper for portable gradient and depth rendering.

    Provides utilities to render gradients with automatic fallback to opaque
    colours for cross-platform safety and performance optimization.
    """

    @staticmethod
    def interpolate_color(
        start_color: str,
        end_color: str,
        steps: int = 10,
    ) -> list[str]:
        """Interpolate between two hex colours.

        Args:
            start_color: Starting colour in hex format (e.g., "#FF0000")
            end_color: Ending colour in hex format (e.g., "#0000FF")
            steps: Number of interpolation steps

        Returns:
            List of hex colours interpolating from start to end
        """
        # Parse hex colours
        start_rgb = GradientHelper._hex_to_rgb(start_color)
        end_rgb = GradientHelper._hex_to_rgb(end_color)

        colours = []
        for i in range(steps):
            # Linear interpolation
            ratio = i / (steps - 1) if steps > 1 else 0
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * ratio)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * ratio)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * ratio)

            colours.append(GradientHelper._rgb_to_hex(r, g, b))

        return colours

    @staticmethod
    def lighten_color(hex_color: str, factor: float = 0.2) -> str:
        """Lighten a hex colour by a given factor.

        Args:
            hex_color: Colour in hex format (e.g., "#FF0000")
            factor: Lightening factor (0.0-1.0, where 1.0 is white)

        Returns:
            Lightened hex colour
        """
        rgb = GradientHelper._hex_to_rgb(hex_color)

        r = int(rgb[0] + (255 - rgb[0]) * factor)
        g = int(rgb[1] + (255 - rgb[1]) * factor)
        b = int(rgb[2] + (255 - rgb[2]) * factor)

        return GradientHelper._rgb_to_hex(r, g, b)

    @staticmethod
    def darken_color(hex_color: str, factor: float = 0.2) -> str:
        """Darken a hex colour by a given factor.

        Args:
            hex_color: Colour in hex format (e.g., "#FF0000")
            factor: Darkening factor (0.0-1.0, where 1.0 is black)

        Returns:
            Darkened hex colour
        """
        rgb = GradientHelper._hex_to_rgb(hex_color)

        r = int(rgb[0] * (1 - factor))
        g = int(rgb[1] * (1 - factor))
        b = int(rgb[2] * (1 - factor))

        return GradientHelper._rgb_to_hex(r, g, b)

    @staticmethod
    def get_depth_colour(
        base_color: str,
        depth_level: int = 1,
        max_depth: int = 3,
    ) -> str:
        """Get a depth-adjusted colour (for layering visual hierarchy).

        Args:
            base_color: Base colour in hex format
            depth_level: Current depth level (1-based)
            max_depth: Maximum depth levels

        Returns:
            Depth-adjusted hex colour
        """
        if depth_level <= 0 or max_depth <= 0:
            return base_color

        # Progressive darkening based on depth
        factor = (depth_level / max_depth) * 0.3
        return GradientHelper.darken_color(base_color, factor)

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        """Convert hex colour to RGB tuple.

        Args:
            hex_color: Colour in hex format (e.g., "#FF0000")

        Returns:
            Tuple of (R, G, B) values (0-255)
        """
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore

    @staticmethod
    def _rgb_to_hex(r: int, g: int, b: int) -> str:
        """Convert RGB values to hex colour.

        Args:
            r: Red value (0-255)
            g: Green value (0-255)
            b: Blue value (0-255)

        Returns:
            Colour in hex format
        """
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def create_depth_gradient(
        base_color: str,
        depth_levels: int = 3,
    ) -> dict[int, str]:
        """Create a gradient of depth colours from a base colour.

        Args:
            base_color: Base colour in hex format
            depth_levels: Number of depth levels to generate

        Returns:
            Dictionary mapping depth level (1-based) to hex colour
        """
        return {
            i + 1: GradientHelper.get_depth_colour(base_color, i + 1, depth_levels)
            for i in range(depth_levels)
        }

    @staticmethod
    def get_opaque_fallback(hex_color: str) -> str:
        """Get opaque fallback for a colour (ensures cross-platform safety).

        For components that need to work across platforms with various
        transparency support levels, this returns an opaque version.

        Args:
            hex_color: Colour (may contain alpha channel)

        Returns:
            Opaque hex colour
        """
        # Simply return the hex if it's already opaque
        if hex_color.startswith("#"):
            return hex_color[:7]  # Return first 7 chars (no alpha)
        return hex_color
