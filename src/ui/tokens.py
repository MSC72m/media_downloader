"""Design tokens: the single source of truth for spacing, sizing, radius,
typography, semantic colours, and surface elevations across the UI.

Why this exists
---------------
Before this module, spacing/padding literals (35, 25, 15, 10, ...), font
tuples (``("Roboto", 26, "bold")``) and widget dimensions were duplicated
across ``main.py`` and every component/dialog with no shared scale. That made
the UI visually inconsistent and impossible to retune coherently.

The redesigned token system adds semantic surface/elevation roles, focus
indicators, density settings, and a complete contract for what theme values
must be supplied. This ensures the modern design remains coherent and theme-safe.

DPI / scaling note
------------------
CustomTkinter already multiplies widget sizes *and* font sizes by its internal
widget-scaling factor (which it derives from the OS DPI once we stop forcing it
to 1.0). Therefore tokens are expressed in **logical pixels** and we must NOT
apply any manual DPI multiplier here — doing so would double-scale. Keep this
module free of ``winfo_fpixels`` / screen math; that belongs in the windowing
helper, not in the token scale.

Usage
-----
    from src.ui import tokens

    frame.grid(padx=tokens.SPACE_LG, pady=tokens.SPACE_MD)
    label.configure(font=tokens.font("title"))
    button.configure(height=tokens.CONTROL_H, corner_radius=tokens.RADIUS_MD)

    # Semantic colour and surface roles are resolved via ThemeManager:
    theme_json = theme_manager.get_theme_json()
    media_downloader = theme_json.get("MediaDownloader", {})
    accent_color = media_downloader.get(tokens.ACCENT_PRIMARY, "#0000FF")

``font()`` returns a ``CTkFont`` and therefore must be called *after* a Tk root
exists (i.e. from within widget construction), never at import time.

Visual system contract
----------------------
Every theme JSON must supply the following keys under "light" and "dark" sections
to satisfy the complete semantic contract:

  Surface & Elevation:
    surface: base window background
    surface_elevated: raised cards, panels
    surface_overlay: dialogs, overlays

  Text & Semantics:
    text_on_surface: primary text
    text_muted: secondary/disabled text

  Status (always paired with icon/text for accessibility):
    status_success, status_error, status_warning, status_pending, status_active

  Accent & Controls:
    accent: primary action colour
    button_success, button_success_hover

  Focus & Borders:
    focus_ring: keyboard focus indicator (optional; defaults to accent)
    card_border: card/container borders

This policy ensures all 22 themes provide consistent, accessible components.
"""

from __future__ import annotations

from typing import Literal

import customtkinter as ctk

# --------------------------------------------------------------------------- #
# Spacing scale (4pt base, 8pt rhythm). Use these instead of ad-hoc literals.  #
# --------------------------------------------------------------------------- #
SPACE_XXS = 2
SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32

# --------------------------------------------------------------------------- #
# Density & padding for different content zones.                              #
# --------------------------------------------------------------------------- #
DENSITY_COMPACT = SPACE_SM  # condensed lists, tool bars
DENSITY_NORMAL = SPACE_MD  # standard spacing
DENSITY_SPACIOUS = SPACE_LG  # cards, sections, breathing room

# --------------------------------------------------------------------------- #
# Corner radius scale.                                                         #
# --------------------------------------------------------------------------- #
RADIUS_SM = 6
RADIUS_MD = 10
RADIUS_LG = 14
RADIUS_FULL = 999  # pill/circle

# --------------------------------------------------------------------------- #
# Standard control dimensions (logical px). CTk scales these for DPI.          #
# --------------------------------------------------------------------------- #
CONTROL_H = 36  # default height for buttons / entries / option menus
CONTROL_H_SM = 28
CONTROL_H_LG = 44
ICON_SM = 16
ICON_MD = 20
ICON_LG = 24

# --------------------------------------------------------------------------- #
# Focus & borders for keyboard accessibility.                                  #
# --------------------------------------------------------------------------- #
FOCUS_WIDTH = 2  # keyboard focus ring width
BORDER_WIDTH_DEFAULT = 1
BORDER_WIDTH_HOVER = 1
BORDER_WIDTH_FOCUS = FOCUS_WIDTH

# --------------------------------------------------------------------------- #
# Typography. Sizes are logical point sizes; CTk scales them for DPI.          #
# One family, a small type scale, semantic roles keyed by name.                #
# --------------------------------------------------------------------------- #
FONT_FAMILY = "Roboto"
FONT_FAMILY_MONO = "Roboto Mono"

FontRole = Literal[
    "caption",  # secondary / metadata text
    "body",  # default UI text
    "subtitle",  # emphasised body / section labels
    "title",  # dialog + section titles
    "display",  # app / header title
]

# role -> (size, weight)
_TYPE_SCALE: dict[FontRole, tuple[int, Literal["normal", "bold"]]] = {
    "caption": (11, "normal"),
    "body": (13, "normal"),
    "subtitle": (15, "bold"),
    "title": (20, "bold"),
    "display": (26, "bold"),
}


def font(
    role: FontRole = "body",
    *,
    weight: Literal["normal", "bold"] | None = None,
) -> ctk.CTkFont:
    """Return a ``CTkFont`` for a semantic role.

    ``weight`` overrides the role default when provided ("normal"/"bold").
    Must be called after a Tk root exists (i.e. during widget construction).
    """
    size, default_weight = _TYPE_SCALE[role]
    return ctk.CTkFont(family=FONT_FAMILY, size=size, weight=weight or default_weight)


# --------------------------------------------------------------------------- #
# Semantic colour role names.                                                  #
#                                                                              #
# These are the *names* of the roles the UI uses; concrete hex values live in  #
# the theme JSONs (see themes/*.json) so they follow the active theme and      #
# light/dark mode. Kept here as constants so call sites never hard-code a       #
# colour or status indicator.                                                  #
#                                                                              #
# Components MUST use these names + ThemeManager.get_theme_json() to resolve   #
# actual colours at runtime. No hard-coded hex or theme-specific colours.      #
# --------------------------------------------------------------------------- #

# Surface elevation
SURFACE_BASE = "surface"  # window background
SURFACE_RAISED = "surface_elevated"  # cards / panels / raised containers
SURFACE_OVERLAY = "surface_overlay"  # dialogs / modals / overlays

# Text & content
TEXT_PRIMARY = "text_on_surface"  # primary text on surfaces
TEXT_MUTED = "text_muted"  # secondary / disabled / hint text

# Status indicators (always paired with icon/text, never colour-only)
STATUS_PENDING = "status_pending"
STATUS_ACTIVE = "status_active"
STATUS_SUCCESS = "status_success"
STATUS_ERROR = "status_error"
STATUS_WARNING = "status_warning"

# Accent & interaction
ACCENT_PRIMARY = "accent"  # primary action, active state, focus
BUTTON_SUCCESS = "button_success"
BUTTON_SUCCESS_HOVER = "button_success_hover"

# Focus & borders
FOCUS_RING = "focus_ring"  # keyboard focus ring (falls back to accent)
CARD_BORDER = "card_border"  # card/container borders
