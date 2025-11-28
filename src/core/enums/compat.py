"""Python version compatibility utilities for enums."""

import sys

# Python 3.10 compatibility for StrEnum
if sys.version_info >= (3, 11):
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        """Fallback StrEnum implementation for Python < 3.11"""

        def _generate_next_value_(name, start, count, last_values):
            return name.lower()
