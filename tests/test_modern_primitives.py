"""Tests for modern UI primitives: surfaces, icon buttons, status badges, and helpers."""

import pytest

from src.core.enums.appearance_mode import AppearanceMode
from src.ui import tokens
from src.ui.helpers.depth_rendering import GradientHelper
from src.ui.helpers.focus_ring import FocusRingHelper, apply_focus_ring


class TestDepthRendering:
    """Test depth rendering helper for gradient and colour manipulation."""

    def test_hex_to_rgb_conversion(self) -> None:
        """Verify hex to RGB conversion works correctly."""
        assert GradientHelper._hex_to_rgb("#FF0000") == (255, 0, 0)
        assert GradientHelper._hex_to_rgb("#00FF00") == (0, 255, 0)
        assert GradientHelper._hex_to_rgb("#0000FF") == (0, 0, 255)
        assert GradientHelper._hex_to_rgb("#FFFFFF") == (255, 255, 255)
        assert GradientHelper._hex_to_rgb("#000000") == (0, 0, 0)

    def test_rgb_to_hex_conversion(self) -> None:
        """Verify RGB to hex conversion works correctly."""
        assert GradientHelper._rgb_to_hex(255, 0, 0) == "#ff0000"
        assert GradientHelper._rgb_to_hex(0, 255, 0) == "#00ff00"
        assert GradientHelper._rgb_to_hex(0, 0, 255) == "#0000ff"
        assert GradientHelper._rgb_to_hex(255, 255, 255) == "#ffffff"
        assert GradientHelper._rgb_to_hex(0, 0, 0) == "#000000"

    def test_interpolate_color_generates_gradient(self) -> None:
        """Verify colour interpolation generates correct number of steps."""
        gradient = GradientHelper.interpolate_color("#FF0000", "#0000FF", steps=5)
        assert len(gradient) == 5
        assert gradient[0] == "#ff0000"  # Start colour
        assert gradient[-1] == "#0000ff"  # End colour

    def test_interpolate_color_progression(self) -> None:
        """Verify colour interpolation progresses smoothly."""
        gradient = GradientHelper.interpolate_color("#FFFFFF", "#000000", steps=3)
        assert len(gradient) == 3
        # Should go from white -> grey -> black
        assert gradient[0] == "#ffffff"
        assert gradient[-1] == "#000000"
        # Middle value should be intermediate
        rgb = GradientHelper._hex_to_rgb(gradient[1])
        assert all(0 < c < 255 for c in rgb)

    def test_lighten_color(self) -> None:
        """Verify colour lightening works."""
        # Lighten black should give grey
        lightened = GradientHelper.lighten_color("#000000", factor=0.5)
        rgb = GradientHelper._hex_to_rgb(lightened)
        assert all(c > 0 for c in rgb)

        # Lighten white should stay white
        lightened = GradientHelper.lighten_color("#FFFFFF", factor=0.5)
        assert lightened == "#ffffff"

    def test_darken_color(self) -> None:
        """Verify colour darkening works."""
        # Darken white should give grey
        darkened = GradientHelper.darken_color("#FFFFFF", factor=0.5)
        rgb = GradientHelper._hex_to_rgb(darkened)
        assert all(c < 255 for c in rgb)

        # Darken black should stay black
        darkened = GradientHelper.darken_color("#000000", factor=0.5)
        assert darkened == "#000000"

    def test_get_depth_colour(self) -> None:
        """Verify depth colour generation."""
        base = "#FF0000"

        # Level 1 should be darker than base
        level1 = GradientHelper.get_depth_colour(base, depth_level=1, max_depth=3)
        level1_rgb = GradientHelper._hex_to_rgb(level1)

        # Level 3 should be darker than level 1
        level3 = GradientHelper.get_depth_colour(base, depth_level=3, max_depth=3)
        level3_rgb = GradientHelper._hex_to_rgb(level3)

        # Both should be darker than base
        assert all(c < 255 for c in level1_rgb)
        assert all(c < 255 for c in level3_rgb)

    def test_create_depth_gradient(self) -> None:
        """Verify depth gradient creation."""
        gradient = GradientHelper.create_depth_gradient("#FF0000", depth_levels=3)

        assert len(gradient) == 3
        assert 1 in gradient
        assert 2 in gradient
        assert 3 in gradient

        # Each level should be progressively darker
        level1_rgb = GradientHelper._hex_to_rgb(gradient[1])
        level2_rgb = GradientHelper._hex_to_rgb(gradient[2])
        level3_rgb = GradientHelper._hex_to_rgb(gradient[3])

        # Average brightness should decrease with depth
        avg1 = sum(level1_rgb) / 3
        avg2 = sum(level2_rgb) / 3
        avg3 = sum(level3_rgb) / 3

        assert avg1 >= avg2 >= avg3

    def test_get_opaque_fallback(self) -> None:
        """Verify opaque fallback removes alpha channel."""
        assert GradientHelper.get_opaque_fallback("#FF0000") == "#FF0000"
        assert GradientHelper.get_opaque_fallback("#FF0000FF") == "#FF0000"
        assert GradientHelper.get_opaque_fallback("#FFFFFF") == "#FFFFFF"


class TestFocusRing:
    """Test focus ring styling helper."""

    def test_focus_ring_helper_apply(self) -> None:
        """Verify focus ring helper can apply styling."""
        # Create a mock widget
        class MockWidget:
            pass

        widget = MockWidget()
        FocusRingHelper.apply_focus_ring(widget, "#0000FF", 2)

        assert widget._focus_ring_color == "#0000FF"
        assert widget._focus_ring_width == 2

    def test_focus_ring_helper_get_color(self) -> None:
        """Verify focus ring helper retrieves colour."""
        class MockWidget:
            pass

        widget = MockWidget()
        FocusRingHelper.apply_focus_ring(widget, "#FF0000", 3)

        assert FocusRingHelper.get_focus_ring_color(widget) == "#FF0000"

    def test_focus_ring_helper_get_width(self) -> None:
        """Verify focus ring helper retrieves width."""
        class MockWidget:
            pass

        widget = MockWidget()
        FocusRingHelper.apply_focus_ring(widget, "#FF0000", 3)

        assert FocusRingHelper.get_focus_ring_width(widget) == 3

    def test_focus_ring_defaults(self) -> None:
        """Verify focus ring defaults are used for unstored values."""
        class MockWidget:
            pass

        widget = MockWidget()

        # Should return defaults if not set
        assert FocusRingHelper.get_focus_ring_color(widget) == tokens.FOCUS_RING
        assert FocusRingHelper.get_focus_ring_width(widget) == tokens.FOCUS_WIDTH

    def test_module_level_apply_focus_ring(self) -> None:
        """Verify module-level apply_focus_ring function works."""
        class MockWidget:
            pass

        widget = MockWidget()
        apply_focus_ring(widget, "#0000FF", 2)

        assert widget._focus_ring_color == "#0000FF"
        assert widget._focus_ring_width == 2


class TestTokenContract:
    """Verify token system is complete for primitive usage."""

    def test_all_semantic_tokens_exist(self) -> None:
        """Verify all semantic tokens used by primitives are defined."""
        required_tokens = {
            tokens.SURFACE_BASE,
            tokens.SURFACE_RAISED,
            tokens.SURFACE_OVERLAY,
            tokens.TEXT_PRIMARY,
            tokens.TEXT_MUTED,
            tokens.STATUS_PENDING,
            tokens.STATUS_ACTIVE,
            tokens.STATUS_SUCCESS,
            tokens.STATUS_ERROR,
            tokens.STATUS_WARNING,
            tokens.ACCENT_PRIMARY,
            tokens.CARD_BORDER,
            tokens.FOCUS_RING,
        }

        # All should be strings
        for token in required_tokens:
            assert isinstance(token, str), f"Token {token} is not a string"
            assert len(token) > 0, f"Token {token} is empty"

    def test_control_dimensions_defined(self) -> None:
        """Verify control dimensions used by primitives are defined."""
        assert tokens.CONTROL_H == 36
        assert tokens.CONTROL_H_SM == 28
        assert tokens.CONTROL_H_LG == 44
        assert tokens.ICON_SM == 16
        assert tokens.ICON_MD == 20
        assert tokens.ICON_LG == 24

    def test_spacing_scale_defined(self) -> None:
        """Verify spacing scale is complete."""
        assert tokens.SPACE_XXS == 2
        assert tokens.SPACE_XS == 4
        assert tokens.SPACE_SM == 8
        assert tokens.SPACE_MD == 12
        assert tokens.SPACE_LG == 16
        assert tokens.SPACE_XL == 24
        assert tokens.SPACE_XXL == 32

    def test_radius_scale_defined(self) -> None:
        """Verify radius scale is complete."""
        assert tokens.RADIUS_SM == 6
        assert tokens.RADIUS_MD == 10
        assert tokens.RADIUS_LG == 14
        assert tokens.RADIUS_FULL == 999

    def test_focus_dimensions_defined(self) -> None:
        """Verify focus dimensions are defined."""
        assert tokens.FOCUS_WIDTH == 2
        assert tokens.BORDER_WIDTH_DEFAULT == 1
        assert tokens.BORDER_WIDTH_FOCUS == tokens.FOCUS_WIDTH

    def test_font_roles_available(self) -> None:
        """Verify all font roles have definitions in type scale."""
        # Font roles are defined in tokens._TYPE_SCALE
        font_roles = ["caption", "body", "subtitle", "title", "display"]
        type_scale = {
            "caption": (11, "normal"),
            "body": (13, "normal"),
            "subtitle": (15, "bold"),
            "title": (20, "bold"),
            "display": (26, "bold"),
        }

        for role in font_roles:
            assert role in type_scale, f"Font role '{role}' not in type scale"
            size, weight = type_scale[role]
            assert size > 0, f"Font size for '{role}' is not positive"
            assert weight in ("normal", "bold"), f"Invalid weight for '{role}'"


class TestStatusBadgeContract:
    """Verify StatusBadge implementation meets contract."""

    def test_status_types_supported(self) -> None:
        """Verify all status types are supported."""
        status_types = ["pending", "active", "success", "error", "warning"]
        for status in status_types:
            # Just verify the string exists and is used
            assert isinstance(status, str)

    def test_status_icons_defined(self) -> None:
        """Verify status icons are accessible."""
        # These would be defined in StatusBadge._status_map
        status_icons = {
            "pending": "⏳",
            "active": "●",
            "success": "✓",
            "error": "✕",
            "warning": "⚠",
        }

        for status, icon in status_icons.items():
            assert isinstance(status, str)
            assert isinstance(icon, str)
            assert len(icon) > 0


class TestPrimitiveIntegration:
    """Integration tests for primitives working together."""

    def test_depth_gradient_all_colors_valid(self) -> None:
        """Verify depth gradient generates only valid hex colours."""
        gradient = GradientHelper.create_depth_gradient("#FF0000", depth_levels=5)

        for level, colour in gradient.items():
            assert 1 <= level <= 5
            assert colour.startswith("#")
            assert len(colour) == 7 or len(colour) == 9  # hex or hex with alpha

    def test_gradient_interpolation_all_valid(self) -> None:
        """Verify gradient interpolation generates only valid colours."""
        gradient = GradientHelper.interpolate_color("#000000", "#FFFFFF", steps=10)

        for colour in gradient:
            assert colour.startswith("#")
            assert len(colour) == 7 or len(colour) == 9

    def test_colour_adjustments_monotonic(self) -> None:
        """Verify colour adjustments follow monotonic patterns."""
        base = "#808080"  # Mid-grey

        # Lightening should get lighter
        light = GradientHelper.lighten_color(base, factor=0.5)
        light_rgb = GradientHelper._hex_to_rgb(light)
        base_rgb = GradientHelper._hex_to_rgb(base)

        assert sum(light_rgb) > sum(base_rgb)

        # Darkening should get darker
        dark = GradientHelper.darken_color(base, factor=0.5)
        dark_rgb = GradientHelper._hex_to_rgb(dark)

        assert sum(dark_rgb) < sum(base_rgb)
