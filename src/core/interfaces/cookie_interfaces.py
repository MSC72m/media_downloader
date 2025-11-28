from typing import Optional, Dict, Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class ICookieManager(Protocol):
    def get_cookie_info_for_ytdlp(self) -> Optional[Dict[str, Any]]:
        ...

    def get_current_cookie_path(self) -> Optional[str]:
        ...

    def get_cookies(self, domain: str) -> Mapping[str, str]:
        ...

    def needs_regeneration(self, domain: str, max_age_hours: int) -> bool:
        ...

    def get_cookie_file_path(self, domain: str) -> str | None:
        ...
