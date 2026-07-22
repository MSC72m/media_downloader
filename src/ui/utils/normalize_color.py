from __future__ import annotations

from typing import Any


def normalize_color(color: Any) -> str | None:
    if not color:
        return None
    if isinstance(color, list | tuple):
        return str(color[0]) if color else None
    return str(color)
