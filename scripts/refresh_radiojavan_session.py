#!/usr/bin/env python3
"""Refresh persisted RadioJavan browser cookie state."""

from src.core.config import get_config
from src.services.cookies import RadioJavanCookieManager


def main() -> int:
    manager = RadioJavanCookieManager(config=get_config())
    success = manager.refresh_if_needed()
    state = manager.get_state()
    print("refresh_success:", success)
    print("state:", state)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
