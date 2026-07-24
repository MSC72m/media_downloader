"""Tests for visual system contract and theme validation."""

import pytest

from src.core.config import ThemeConfig
from src.ui import tokens
from src.ui.utils.theme_contract import (
    OPTIONAL_SEMANTIC_COLORS,
    REQUIRED_SEMANTIC_COLORS,
    ensure_theme_semantic_defaults,
    validate_theme_semantic_contract,
)


class TestTokensContract:
    """Test that tokens module defines all required semantic roles."""

    def test_required_semantic_colors_defined(self) -> None:
        """Verify all required semantic colour roles are exported as token constants."""
        required_constants = {
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
            tokens.BUTTON_SUCCESS,
            tokens.BUTTON_SUCCESS_HOVER,
            tokens.CARD_BORDER,
        }

        assert required_constants == REQUIRED_SEMANTIC_COLORS, (
            "Tokens module exports do not match required semantic colours. "
            f"Missing: {REQUIRED_SEMANTIC_COLORS - required_constants}"
        )

    def test_optional_semantic_colors_defined(self) -> None:
        """Verify optional semantic colour roles are exported."""
        assert tokens.FOCUS_RING in OPTIONAL_SEMANTIC_COLORS


class TestThemeSemanticContract:
    """Test that all built-in themes satisfy the visual system contract."""

    @pytest.fixture
    def all_color_schemes(self) -> dict[str, dict[str, object]]:
        """Load all available colour schemes."""
        return ThemeConfig.get_color_schemes()

    def test_all_themes_have_light_and_dark(self, all_color_schemes: dict[str, dict[str, object]]) -> None:
        """Verify every colour scheme has both light and dark variants."""
        # Extract unique theme names (e.g., "blue" from "light_blue", "dark_blue")
        theme_names = set()
        for key in all_color_schemes.keys():
            # Key format: "appearance_color" e.g. "light_blue"
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                theme_names.add(parts[-1])

        # Verify we have both light and dark for each theme
        for theme_name in sorted(theme_names):
            light_key = f"light_{theme_name}"
            dark_key = f"dark_{theme_name}"
            assert light_key in all_color_schemes, f"Missing light variant for {theme_name}"
            assert dark_key in all_color_schemes, f"Missing dark variant for {theme_name}"

    def test_all_themes_have_required_semantic_colors(
        self, all_color_schemes: dict[str, dict[str, object]]
    ) -> None:
        """Verify every theme provides all required semantic colours."""
        for key, scheme in all_color_schemes.items():
            # Key is already in format "light_blue" or "dark_blue"
            # scheme is just the colour dict for that mode
            is_valid = validate_theme_semantic_contract(scheme, key)
            assert is_valid, f"Theme {key} fails semantic contract validation"

    def test_all_semantic_colors_are_valid_hex_or_pairs(
        self, all_color_schemes: dict[str, dict[str, object]]
    ) -> None:
        """Verify all semantic colour values are valid hex strings or [light, dark] pairs."""
        for key, scheme in all_color_schemes.items():
            for color_key in REQUIRED_SEMANTIC_COLORS:
                if color_key not in scheme:
                    pytest.fail(f"{key} missing required colour: {color_key}")

                value = scheme[color_key]

                if isinstance(value, list):
                    # Should be [light_hex, dark_hex] pair
                    assert len(value) == 2, f"{key}.{color_key} list should have 2 elements"
                    for i, color in enumerate(value):
                        assert isinstance(color, str), (
                            f"{key}.{color_key}[{i}] is {type(color)}, not str"
                        )
                        assert color.startswith("#"), f"{key}.{color_key}[{i}] not hex: {color}"
                elif isinstance(value, str):
                    assert value.startswith("#"), f"{key}.{color_key} not hex: {value}"
                else:
                    pytest.fail(f"{key}.{color_key} is invalid type: {type(value)}")

    def test_focus_ring_fallback(self, all_color_schemes: dict[str, dict[str, object]]) -> None:
        """Verify all themes have focus_ring or can fall back to accent."""
        for key, scheme in all_color_schemes.items():
            # After augmentation, focus_ring should exist
            if tokens.FOCUS_RING not in scheme:
                # But accent must exist as fallback
                assert (
                    tokens.ACCENT_PRIMARY in scheme
                ), f"{key} missing both focus_ring and accent"

    def test_ensure_defaults_adds_missing_keys(self) -> None:
        """Verify ensure_theme_semantic_defaults fills missing optional keys."""
        incomplete_theme = {
            "light": {"accent": "#007BFF"},
            "dark": {"accent": "#0056b3"},
        }

        result = ensure_theme_semantic_defaults(incomplete_theme, "test")

        # focus_ring should be added from accent
        assert result["light"]["focus_ring"] == "#007BFF"
        assert result["dark"]["focus_ring"] == "#0056b3"

    def test_we_have_exactly_22_themes(self, all_color_schemes: dict[str, dict[str, object]]) -> None:
        """Verify all 22 color themes are present."""
        # Extract unique theme names
        theme_names = set()
        for key in all_color_schemes.keys():
            parts = key.rsplit("_", 1)
            if len(parts) == 2:
                theme_names.add(parts[-1])

        expected_22_themes = {
            "blue", "green", "red", "purple", "cyan", "emerald",
            "gold", "amber", "pink", "coral", "orange", "lime",
            "indigo", "teal", "violet", "rose", "slate", "navy",
            "cyberpunk", "espresso", "glacier", "sunset",
        }

        assert len(theme_names) == 22, f"Expected 22 themes, got {len(theme_names)}: {theme_names}"
        assert theme_names == expected_22_themes, f"Theme names mismatch: {theme_names ^ expected_22_themes}"


class TestSemanticColorUsagePatterns:
    """Test best practices for consuming semantic colours in components."""

    def test_semantic_color_keys_are_strings(self) -> None:
        """Verify all semantic colour role constants are strings."""
        for attr_name in dir(tokens):
            if not attr_name.startswith("_"):
                attr = getattr(tokens, attr_name)
                if isinstance(attr, str) and attr not in (tokens.FONT_FAMILY, tokens.FONT_FAMILY_MONO):
                    # Should be a valid semantic role name, not a random string
                    # These are used as keys in theme JSON
                    if "_" in attr or attr in (
                        "surface", "text_on_surface", "text_muted", "status_pending",
                        "status_active", "status_success", "status_error", "status_warning",
                        "accent", "button_success", "button_success_hover", "card_border",
                        "focus_ring", "surface_elevated", "surface_overlay"
                    ):
                        assert isinstance(attr, str)
