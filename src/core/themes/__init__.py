"""Dynamic theme loader.

Scans for .json theme files in two locations (in priority order):
1. ``themes/`` directory at the project root  (bundled themes)
2. ``~/.media_downloader/themes/`` directory  (user-added themes)

Users can add custom themes by dropping a JSON file into either directory.
User themes override bundled themes when names collide.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Directory discovery
# ---------------------------------------------------------------------------

_DEFAULT_THEME = "blue"


def _get_project_themes_dir() -> Path:
    """Return the ``themes/`` directory at the project root."""
    # Walk up from this file (src/core/themes/__init__.py) to find project root.
    # Fall back to cwd-based lookup and sys.path inspection.
    candidate = Path(__file__).resolve().parent.parent.parent.parent / "themes"
    if candidate.is_dir():
        return candidate

    # Fallback: check cwd
    cwd_candidate = Path.cwd() / "themes"
    if cwd_candidate.is_dir():
        return cwd_candidate

    # Fallback: check sys.path entries (e.g. when installed as package)
    for p in sys.path:
        sp = Path(p) / "themes"
        if sp.is_dir():
            return sp

    return candidate  # return expected path even if missing


def _get_user_themes_dir() -> Path:
    """Return ``~/.media_downloader/themes/``."""
    return Path.home() / ".media_downloader" / "themes"


# ---------------------------------------------------------------------------
# Low-level loading helpers
# ---------------------------------------------------------------------------


def _load_theme_file(path: Path) -> dict[str, Any] | None:
    """Read and parse a single theme JSON file. Returns *None* on error."""
    try:
        with open(path, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        # Minimal validation: must have a name and at least one mode
        if not isinstance(data, dict) or "name" not in data:
            logger.warning("Theme file %s missing 'name' key, skipping", path)
            return None
        if "light" not in data and "dark" not in data:
            logger.warning("Theme file %s has no 'light' or 'dark' section, skipping", path)
            return None
        if "emoji" not in data:
            logger.warning("Theme file %s missing 'emoji' key, using default", path)
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load theme file %s: %s", path, exc)
        return None


def _collect_json_files(*dirs: Path) -> list[Path]:
    """Gather ``*.json`` files from *dirs*, later dirs win on name collision."""
    seen: dict[str, Path] = {}
    for d in dirs:
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            seen[f.stem] = f  # last write wins → user overrides bundled
    return list(seen.values())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_schemes_cache: dict[str, dict[str, Any]] | None = None
_themes_cache: list[dict[str, str]] | None = None


def load_color_schemes() -> dict[str, dict[str, Any]]:
    """Load all color schemes from JSON theme files.

    Returns a dict keyed ``"{mode}_{name}"`` (e.g. ``"dark_blue"``) whose
    values are the raw colour-palette dicts.  This is a drop-in replacement
    for the old ``ThemeConfig.get_color_schemes()`` static method.

    Results are cached after the first call.  Use :func:`reload_themes` to
    force a refresh.
    """
    global _schemes_cache  # noqa: PLW0603
    if _schemes_cache is not None:
        return _schemes_cache

    schemes: dict[str, dict[str, Any]] = {}
    files = _collect_json_files(_get_project_themes_dir(), _get_user_themes_dir())

    for path in files:
        if (theme_data := _load_theme_file(path)) is None:
            continue
        name = theme_data["name"]
        for mode in ("light", "dark"):
            if mode_data := theme_data.get(mode):
                schemes[f"{mode}_{name}"] = mode_data

    if not schemes:
        logger.error("No theme files found – UI will use hard-coded fallback colours")

    _schemes_cache = schemes
    return schemes


def get_available_themes() -> list[dict[str, str]]:
    """Return metadata for every discovered theme.

    Each entry is ``{"name": "<theme>", "emoji": "<emoji>"}``, sorted
    alphabetically by name.  The list is built from the same JSON files
    that :func:`load_color_schemes` reads.
    """
    global _themes_cache  # noqa: PLW0603
    if _themes_cache is not None:
        return _themes_cache

    themes: list[dict[str, str]] = []
    files = _collect_json_files(_get_project_themes_dir(), _get_user_themes_dir())

    for path in files:
        if (theme_data := _load_theme_file(path)) is None:
            continue
        themes.append(
            {
                "name": theme_data.get("name", path.stem),
                "emoji": theme_data.get("emoji", "\U0001f535"),  # default 🔵
            }
        )

    themes.sort(key=lambda t: t["name"])
    _themes_cache = themes
    return themes


def get_available_theme_names() -> set[str]:
    """Return a set of all discovered theme names (lowercase)."""
    return {t["name"] for t in get_available_themes()}


def get_default_theme() -> str:
    """Return the default theme name."""
    return _DEFAULT_THEME


def reload_themes() -> dict[str, dict[str, Any]]:
    """Clear caches and re-read all theme files from disk."""
    global _schemes_cache, _themes_cache  # noqa: PLW0603
    _schemes_cache = None
    _themes_cache = None
    return load_color_schemes()
