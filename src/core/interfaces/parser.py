from typing import Protocol, runtime_checkable

from src.core.type_defs import JSONDict


@runtime_checkable
class IParser(Protocol):
    def validate(self, url: str, context: JSONDict | None = None) -> bool: ...

    def parse(self, data: JSONDict, context: JSONDict | None = None) -> list[JSONDict]: ...
