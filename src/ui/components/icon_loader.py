"""Platform badges and status/action icons rendered as styled text or CTkImage.

This module maps platform names and statuses to display characters and
theme-aware colors.  It avoids bundling raster/SVG assets by using Unicode
characters and inline CTkImage generation where an actual icon is needed.
"""

from __future__ import annotations

import customtkinter as ctk

from src.core.enums.download_status import DownloadStatus
from src.ui import tokens

# ── Platform badges ────────────────────────────────────────────────────────

PlatformBadge = tuple[str, str]  # (label, hex_color)


def platform_badge(service_type: str | None) -> PlatformBadge:
    """Return a (label, hex_color) pair for the given service type."""
    badges: dict[str, PlatformBadge] = {
        "youtube": ("YT", "#FF0000"),
        "youtube_music": ("YM", "#FF0000"),
        "spotify": ("SP", "#1DB954"),
        "soundcloud": ("SC", "#FF7700"),
        "tiktok": ("TK", "#000000"),
        "instagram": ("IG", "#E4405F"),
        "twitter": ("TW", "#1DA1F2"),
        "pinterest": ("PI", "#E60023"),
        "radiojavan": ("RJ", "#00A0E0"),
    }
    return badges.get(service_type or "", ("", ""))


# ── Status indicators ──────────────────────────────────────────────────────

StatusIcon = tuple[str, str]  # (emoji/unicode, hex_color)


def status_icon(status: DownloadStatus) -> StatusIcon:
    """Return a (character, hex_color) pair for download status."""
    icons: dict[DownloadStatus, StatusIcon] = {
        DownloadStatus.PENDING: ("\u25cb", tokens.STATUS_PENDING),
        DownloadStatus.DOWNLOADING: ("\u25d4", tokens.STATUS_ACTIVE),
        DownloadStatus.COMPLETED: ("\u2713", tokens.STATUS_SUCCESS),
        DownloadStatus.FAILED: ("\u2717", tokens.STATUS_ERROR),
        DownloadStatus.PAUSED: ("\u23f8", tokens.STATUS_WARNING),
        DownloadStatus.CANCELLED: ("\u2717", tokens.STATUS_WARNING),
    }
    return icons.get(status, ("?", tokens.STATUS_PENDING))


def status_label(status: DownloadStatus) -> str:
    """Return a human-readable label for the status."""
    labels = {
        DownloadStatus.PENDING: "Pending",
        DownloadStatus.DOWNLOADING: "Downloading",
        DownloadStatus.COMPLETED: "Completed",
        DownloadStatus.FAILED: "Failed",
        DownloadStatus.PAUSED: "Paused",
        DownloadStatus.CANCELLED: "Cancelled",
    }
    return labels.get(status, "Unknown")


# ── Theme-coloured canvas icon (for platform badge images) ─────────────────


def create_platform_image(
    service_type: str | None,
    size: int = tokens.ICON_MD,
) -> ctk.CTkImage | None:
    """Create a coloured square ``CTkImage`` as a platform badge.

    Falls back to ``None`` when PIL is unavailable.
    """
    label, color = platform_badge(service_type)
    if not label or not color:
        return None
    try:
        from PIL import Image, ImageDraw

        im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        hex_color = color.lstrip("#")
        rgb = tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
        draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=size // 4, fill=rgb)
        return ctk.CTkImage(im, size=(size, size))
    except ImportError:
        return None
