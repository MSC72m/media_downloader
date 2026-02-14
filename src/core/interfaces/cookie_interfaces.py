from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from src.core.type_defs import JSONDict


@runtime_checkable
class ICookieManager(Protocol):
    def get_cookie_info_for_ytdlp(self) -> JSONDict | None: ...

    def get_current_cookie_path(self) -> str | None: ...

    def get_cookies(self, domain: str) -> Mapping[str, str]: ...

    def needs_regeneration(self, domain: str, max_age_hours: int) -> bool: ...

    def get_cookie_file_path(self, domain: str) -> str | None: ...
