#!/usr/bin/env python3
"""Theme augmentation script: ensure all themes have the complete semantic contract."""

import json
from pathlib import Path
from typing import Any

THEMES_DIR = Path(__file__).parent.parent / "themes"

REQUIRED_LIGHT_DARK = {
    "surface",
    "surface_elevated",
    "surface_overlay",
    "text_on_surface",
    "text_muted",
    "status_pending",
    "status_active",
    "status_success",
    "status_error",
    "status_warning",
    "accent",
    "button_success",
    "button_success_hover",
    "card_border",
}

OPTIONAL_WITH_FALLBACK = {
    "focus_ring",  # falls back to accent
}


def augment_theme(theme_data: dict[str, Any]) -> dict[str, Any]:  # noqa: PLR0912
    """Augment theme with missing semantic keys using defaults or fallbacks."""
    for appearance in ("light", "dark"):
        if appearance not in theme_data:
            continue

        section = theme_data[appearance]
        if not isinstance(section, dict):
            continue

        # Ensure all required keys are present
        for key in REQUIRED_LIGHT_DARK:
            if key not in section:
                # Provide sensible defaults based on key
                if key == "surface":
                    section[key] = "#FFFFFF" if appearance == "light" else "#1A1A1A"
                elif key == "surface_elevated":
                    section[key] = "#F5F5F5" if appearance == "light" else "#2B2B2B"
                elif key == "surface_overlay":
                    section[key] = "#FFFFFF" if appearance == "light" else "#1A1A1A"
                elif key == "text_on_surface":
                    section[key] = "#1A1A1A" if appearance == "light" else "#FFFFFF"
                elif key == "text_muted":
                    section[key] = "#999999" if appearance == "light" else "#888888"
                elif key == "status_pending":
                    section[key] = "#6B7280" if appearance == "light" else "#9AA0A6"
                elif key == "status_active":
                    section[key] = section.get("accent", "#007BFF")
                elif key == "status_success":
                    section[key] = "#28a745" if appearance == "light" else "#4CAF50"
                elif key == "status_error":
                    section[key] = "#dc3545" if appearance == "light" else "#F44336"
                elif key == "status_warning":
                    section[key] = "#B45309" if appearance == "light" else "#F59E0B"
                elif key == "accent":
                    section[key] = "#007BFF"
                elif key == "button_success":
                    section[key] = "#28a745" if appearance == "light" else "#4CAF50"
                elif key == "button_success_hover":
                    section[key] = "#218838" if appearance == "light" else "#388E3C"
                elif key == "card_border":
                    section[key] = "#CCCCCC" if appearance == "light" else "#4a4a4a"

        # Handle optional keys with fallbacks
        if "focus_ring" not in section and "accent" in section:
            section["focus_ring"] = section["accent"]

    return theme_data


def main() -> None:
    """Augment all theme files."""
    if not THEMES_DIR.exists():
        print(f"Themes directory not found: {THEMES_DIR}")
        return

    theme_files = sorted(THEMES_DIR.glob("*.json"))
    print(f"Found {len(theme_files)} theme files")

    for theme_file in theme_files:
        print(f"\nProcessing {theme_file.name}...")
        try:
            with open(theme_file, encoding="utf-8") as f:
                theme_data = json.load(f)

            # Augment with missing keys
            augmented = augment_theme(theme_data)

            # Write back
            with open(theme_file, "w", encoding="utf-8") as f:
                json.dump(augmented, f, indent=2, ensure_ascii=False)

            print(f"  ✓ Updated {theme_file.name}")

        except Exception as e:
            print(f"  ✗ Error processing {theme_file.name}: {e}")


if __name__ == "__main__":
    main()
