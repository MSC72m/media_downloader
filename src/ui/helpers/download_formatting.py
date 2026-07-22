"""Formatting helpers for download metadata display."""

from __future__ import annotations


def format_file_size(bytes_value: int | None) -> str:
    """Format bytes into human-readable size (KB, MB, GB)."""
    if bytes_value is None or bytes_value < 0:
        return "Unknown"

    value = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024:
            return f"{value:.1f} {unit}".rstrip(".0 ").replace(" ", "")
        value /= 1024

    return f"{value:.1f} TB"


def format_speed(speed_mbps: float | None) -> str:
    """Format speed in MB/s into human-readable format."""
    if speed_mbps is None or speed_mbps < 0:
        return "—"

    if speed_mbps < 1:
        kbps = speed_mbps * 1000
        return f"{kbps:.0f} KB/s"

    return f"{speed_mbps:.1f} MB/s"


def format_eta(seconds: int | None) -> str:
    """Format ETA in seconds into human-readable format."""
    if seconds is None or seconds < 0:
        return "—"

    if seconds < 60:
        return f"{seconds} sec"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} min"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours}h {minutes}m"


def truncate_url(url: str, max_length: int = 60) -> str:
    """Truncate long URLs for display while maintaining readability."""
    if len(url) <= max_length:
        return url

    # Keep scheme + domain, truncate path
    if "://" in url:
        scheme_domain = url.split("/", 3)[:3]
        scheme_domain = "/".join(scheme_domain)
        remaining = max_length - len(scheme_domain) - 3
        path = url[len(scheme_domain) :]
        if remaining > 0 and len(path) > remaining:
            return scheme_domain + path[: remaining - 1] + "…"
        return scheme_domain + path

    return url[: max_length - 1] + "…"


def get_quality_label(quality_str: str | None) -> str:
    """Get human-readable quality label."""
    if not quality_str:
        return "Unknown"

    quality_map = {
        "best": "Best",
        "worst": "Worst",
        "audio": "Audio Only",
        "video": "Video Only",
    }

    # Handle resolution formats like "720p", "1080p", "4K"
    if quality_str.endswith("p"):
        return quality_str.upper()

    return quality_map.get(quality_str.lower(), quality_str)
