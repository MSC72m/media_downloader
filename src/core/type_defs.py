from __future__ import annotations

from collections.abc import Mapping
from typing import TypeAlias

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONDict: TypeAlias = dict[str, JSONValue]
ReadonlyJSONDict: TypeAlias = Mapping[str, JSONValue]
