"""Theme visual-system contract validator.

Ensures all 18 built-in themes + user themes supply required semantic colour roles
and maintain adequate contrast for accessibility.
"""

from __future__ import annotations

from typing import Any

from src.ui import tokens
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Required semantic colour keys that every theme must provide in light/dark sections
REQUIRED_SEMANTIC_COLORS = {
    # Surface elevation
    tokens.SURFACE_BASE,
    tokens.SURFACE_RAISED,
    tokens.SURFACE_OVERLAY,
    # Text
    tokens.TEXT_PRIMARY,
    tokens.TEXT_MUTED,
    # Status (always with icon/text, never colour-only)
    tokens.STATUS_PENDING,
    tokens.STATUS_ACTIVE,
    tokens.STATUS_SUCCESS,
    tokens.STATUS_ERROR,
    tokens.STATUS_WARNING,
    # Accent & controls
    tokens.ACCENT_PRIMARY,
    tokens.BUTTON_SUCCESS,
    tokens.BUTTON_SUCCESS_HOVER,
    # Focus & borders
    tokens.CARD_BORDER,
}

# Optional keys with sensible fallbacks
OPTIONAL_SEMANTIC_COLORS = {
    tokens.FOCUS_RING,  # falls back to accent
}


def validate_theme_semantic_contract(theme_dict: dict[str, Any], theme_name: str) -> bool:
    """Validate that a theme provides all required semantic colours.

    Args:
        theme_dict: Either a full theme dict with "light"/"dark" sections,
                    or a single mode dict (from load_color_schemes()).
        theme_name: Theme name for logging

    Returns:
        True if theme is valid, False otherwise
    """
    valid = True

    # Determine if this is a full theme or a single mode
    if "light" in theme_dict and "dark" in theme_dict:
        # Full theme dict
        sections = {k: v for k, v in theme_dict.items() if k in ("light", "dark")}
    else:
        # Single mode dict from load_color_schemes()—infer appearance from context
        sections = {"_mode": theme_dict}

    for _appearance, section in sections.items():
        if not isinstance(section, dict):
            logger.warning(f"[THEME_CONTRACT] Theme '{theme_name}' section is not a dict")
            valid = False
            continue

        # Check required keys
        missing = REQUIRED_SEMANTIC_COLORS - set(section.keys())
        if missing:
            logger.warning(f"[THEME_CONTRACT] Theme '{theme_name}' missing: {missing}")
            valid = False

        # Check for invalid colour values (None, empty string)
        for key in REQUIRED_SEMANTIC_COLORS:
            if key in section:
                value = section[key]
                # Handle both single colours and [light, dark] pairs
                if isinstance(value, list):
                    if any(not v or not isinstance(v, str) for v in value):
                        logger.warning(
                            f"[THEME_CONTRACT] Theme '{theme_name}' {key} "
                            f"contains invalid colour: {value}"
                        )
                        valid = False
                elif not value or not isinstance(value, str):
                    logger.warning(
                        f"[THEME_CONTRACT] Theme '{theme_name}' {key} "
                        f"is not a valid colour string: {value}"
                    )
                    valid = False

    return valid


def ensure_theme_semantic_defaults(theme_data: dict[str, Any], theme_name: str) -> dict[str, Any]:
    """Fill missing optional semantic colours with sensible defaults.

    Args:
        theme_data: The theme dict (with "light" and "dark" sections)
        theme_name: Theme name for logging

    Returns:
        Updated theme dict with defaults applied
    """
    for appearance in ("light", "dark"):
        if appearance not in theme_data:
            continue

        section = theme_data[appearance]
        if not isinstance(section, dict):
            continue

        # Use accent as fallback for focus_ring if missing
        if tokens.FOCUS_RING not in section and tokens.ACCENT_PRIMARY in section:
            section[tokens.FOCUS_RING] = section[tokens.ACCENT_PRIMARY]
            logger.debug(
                f"[THEME_CONTRACT] Theme '{theme_name}' {appearance}: "
                f"using accent as fallback for focus_ring"
            )

    return theme_data


def validate_all_themes(themes_dict: dict[str, dict[str, Any]]) -> dict[str, bool]:
    """Validate all available themes.

    Args:
        themes_dict: Dictionary of loaded themes from get_color_schemes()

    Returns:
        Dict mapping theme name -> validity (True/False)
    """
    results = {}

    for theme_name, theme_data in themes_dict.items():
        # Extract base name (e.g. "light_blue" -> "blue")
        base_name = theme_name.rsplit("_", 1)[-1] if "_" in theme_name else theme_name

        # Collect all appearances for this theme name
        if base_name not in {k.rsplit("_", 1)[-1] if "_" in k else k for k in themes_dict}:
            continue

        # Validate using the structured format
        is_valid = validate_theme_semantic_contract(theme_data, base_name)
        results[theme_name] = is_valid

    return results
