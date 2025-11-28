"""Interface for parsing and validating media content."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IParser(Protocol):
    def validate(self, url: str, context: dict[str, Any] | None = None) -> bool: ...

    def parse(
        self, data: dict[str, Any], context: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]: ...
