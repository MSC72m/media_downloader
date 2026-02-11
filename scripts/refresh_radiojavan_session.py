#!/usr/bin/env python3
"""Refresh persisted RadioJavan browser session state."""

from src.core.config import get_config
from src.services.cookies import RadioJavanSessionManager


def main() -> int:
    manager = RadioJavanSessionManager(config=get_config())
    success = manager.refresh_session()
    state = manager.get_state()
    print("refresh_success:", success)
    print("state:", state)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
