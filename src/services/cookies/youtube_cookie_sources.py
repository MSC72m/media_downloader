from __future__ import annotations

import json
import os
import shutil
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol
from urllib.parse import parse_qs, urlparse

import yt_dlp

from src.core.config import AppConfig, get_config
from src.services.ytdlp_logger import YTDLPLoggerBridge
from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.core.interfaces import IAutoCookieManager, ICookieHandler

logger = get_logger(__name__)


YOUTUBE_STRICT_PROBE_URLS = [
    "https://www.youtube.com/watch?v=8dcLBO7XFrc",
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",
]
YOUTUBE_EASY_PROBE_URL = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
YOUTUBE_ALL_PROBE_URLS = [*YOUTUBE_STRICT_PROBE_URLS, YOUTUBE_EASY_PROBE_URL]

_BROWSER_PROBE_TTL_HOURS = 12


@dataclass(slots=True)
class YouTubeAuthConfig:
    """Resolved auth source configuration for yt-dlp."""

    label: str
    source: str
    ytdlp_options: dict[str, Any]
    browser: str | None = None
    reason: str | None = None


@dataclass(slots=True)
class BrowserProbeResult:
    """Probe result for one browser candidate."""

    browser: str
    source_browser: str
    success: bool
    reason: str | None
    last_probe_at: str


@dataclass(slots=True)
class YouTubeCookieProbeState:
    """Persistent state for browser cookie probing."""

    preferred_source: str | None = None
    preferred_browser: str | None = None
    last_success_at: str | None = None
    ttl_expires_at: str | None = None
    per_browser_result: dict[str, dict[str, Any]] = field(default_factory=dict)
    last_probe_urls: list[str] = field(default_factory=list)
    last_failure_reason: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> YouTubeCookieProbeState:
        return cls(
            preferred_source=data.get("preferred_source"),
            preferred_browser=data.get("preferred_browser"),
            last_success_at=data.get("last_success_at"),
            ttl_expires_at=data.get("ttl_expires_at"),
            per_browser_result=data.get("per_browser_result", {}) or {},
            last_probe_urls=data.get("last_probe_urls", []) or [],
            last_failure_reason=data.get("last_failure_reason"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def is_cache_valid(self) -> bool:
        if not self.preferred_source or not self.ttl_expires_at:
            return False

        try:
            expires_at = datetime.fromisoformat(self.ttl_expires_at)
        except ValueError:
            return False

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return datetime.now(timezone.utc) < expires_at


@dataclass(slots=True)
class BrowserProbeCandidate:
    """Browser candidate for cookies-from-browser probing."""

    name: str
    ytdlp_browser: str
    profile_path: str | None = None

    def to_option_tuple(self) -> tuple[str, ...]:
        if not self.profile_path:
            return (self.ytdlp_browser,)
        return (self.ytdlp_browser, self.profile_path)


class YouTubeCookieSourceStrategy(Protocol):
    source_name: str

    def resolve(self) -> list[YouTubeAuthConfig]: ...


class _YouTubeProbeRunner:
    """Executes yt-dlp probe runs for cookie source health checks."""

    def __init__(self, config: AppConfig = get_config()) -> None:
        self.config = config

    def probe_browser(
        self,
        candidate: BrowserProbeCandidate,
        probe_urls: list[str],
    ) -> BrowserProbeResult:
        for probe_url in probe_urls:
            expected_id = _extract_video_id(probe_url)
            options = self._base_options()
            options["cookiesfrombrowser"] = candidate.to_option_tuple()

            success, reason = self._probe_url_with_options(probe_url, expected_id, options)
            if success:
                return BrowserProbeResult(
                    browser=candidate.name,
                    source_browser=candidate.ytdlp_browser,
                    success=True,
                    reason=None,
                    last_probe_at=_utc_now_iso(),
                )

            if reason and "could not find" in reason.lower():
                return BrowserProbeResult(
                    browser=candidate.name,
                    source_browser=candidate.ytdlp_browser,
                    success=False,
                    reason=reason,
                    last_probe_at=_utc_now_iso(),
                )

        return BrowserProbeResult(
            browser=candidate.name,
            source_browser=candidate.ytdlp_browser,
            success=False,
            reason="No probe URL succeeded",
            last_probe_at=_utc_now_iso(),
        )

    def probe_cookie_file(self, cookie_path: str, probe_urls: list[str]) -> tuple[bool, str | None]:
        cookie_file = Path(cookie_path)
        if not cookie_file.exists():
            return False, f"Cookie file does not exist: {cookie_path}"

        options = self._base_options()
        options["cookiefile"] = str(cookie_file)

        for probe_url in probe_urls:
            expected_id = _extract_video_id(probe_url)
            success, reason = self._probe_url_with_options(probe_url, expected_id, options)
            if success:
                return True, None

            if reason and "cookie" not in reason.lower() and "sign in" not in reason.lower():
                # Keep trying other probe URLs when failure does not look auth-specific.
                continue

        return False, "Cookie file failed strict YouTube probes"

    def _base_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "ignoreconfig": True,
            "skip_download": True,
            "noplaylist": True,
            "socket_timeout": self.config.downloads.socket_timeout,
            "extract_flat": False,
            "extractor_args": {"youtube": {"player_client": ["web"]}},
            "logger": YTDLPLoggerBridge("YOUTUBE_COOKIE_PROBE"),
        }

        if shutil.which("node"):
            options["js_runtimes"] = {"node": {}}
            options["remote_components"] = "ejs:github"

        return options

    def _probe_url_with_options(
        self,
        url: str,
        expected_video_id: str | None,
        options: dict[str, Any],
    ) -> tuple[bool, str | None]:
        try:
            with yt_dlp.YoutubeDL(options) as ydl:  # type: ignore[arg-type]
                info = ydl.extract_info(url, download=False)

            if not info or not isinstance(info, dict):
                return False, "Probe extraction returned empty response"

            if not expected_video_id:
                return True, None

            if info.get("id") == expected_video_id:
                return True, None

            return False, f"Probe ID mismatch: expected {expected_video_id}, got {info.get('id')}"
        except Exception as exc:
            return False, str(exc)


class BrowserCookieSource:
    """Primary auth source using cookies from installed browsers."""

    source_name = "browser"

    def __init__(
        self,
        coordinator: YouTubeCookieSourceCoordinator,
        preferred_browser: str | None = None,
        force_reprobe: bool = False,
    ) -> None:
        self.coordinator = coordinator
        self.preferred_browser = preferred_browser
        self.force_reprobe = force_reprobe

    def resolve(self) -> list[YouTubeAuthConfig]:
        if not (candidates := self.coordinator.get_browser_candidates()):
            logger.info("[YOUTUBE_COOKIE_COORDINATOR] No browser candidates available")
            return []

        if preferred_candidate := self._resolve_preferred_candidate(candidates):
            return [
                YouTubeAuthConfig(
                    label=f"browser-cookies-{preferred_candidate.name}",
                    source=self.source_name,
                    browser=preferred_candidate.name,
                    ytdlp_options={"cookiesfrombrowser": preferred_candidate.to_option_tuple()},
                )
            ]
        return [
            YouTubeAuthConfig(
                label=f"browser-cookies-{candidate.name}",
                source=self.source_name,
                browser=candidate.name,
                ytdlp_options={"cookiesfrombrowser": candidate.to_option_tuple()},
            )
            for candidate in candidates
        ]

    def _resolve_preferred_candidate(
        self,
        candidates: list[BrowserProbeCandidate],
    ) -> BrowserProbeCandidate | None:
        if self.preferred_browser and (
            selected := next((c for c in candidates if c.name == self.preferred_browser), None)
        ):
            return selected

        if (
            not self.force_reprobe
            and self.coordinator.state.is_cache_valid()
            and (cached_name := self.coordinator.state.preferred_browser)
            and (selected := next((c for c in candidates if c.name == cached_name), None))
        ):
            return selected

        if selected := self.coordinator.probe_browsers(candidates):
            return selected

        if not (cached_name := self.coordinator.state.preferred_browser):
            return None

        return next((c for c in candidates if c.name == cached_name), None)


class ManualCookieFileSource:
    """Manual cookie file source for explicit user overrides."""

    source_name = "manual"

    def __init__(self, cookie_path: str | None) -> None:
        self.cookie_path = cookie_path

    def resolve(self) -> list[YouTubeAuthConfig]:
        if not self.cookie_path:
            return []

        cookie_file = Path(self.cookie_path)
        if not cookie_file.exists() or cookie_file.stat().st_size == 0:
            return []

        return [
            YouTubeAuthConfig(
                label="manual-cookie-file",
                source=self.source_name,
                ytdlp_options={"cookiefile": str(cookie_file)},
            )
        ]


class GeneratedGuestCookieSource:
    """Fallback source backed by existing auto cookie manager generation."""

    source_name = "generated"

    def __init__(self, auto_cookie_manager: IAutoCookieManager | None) -> None:
        self.auto_cookie_manager = auto_cookie_manager

    def resolve(self) -> list[YouTubeAuthConfig]:
        if not self.auto_cookie_manager:
            return []

        try:
            cookie_path = self.auto_cookie_manager.get_cookies()
        except Exception as exc:
            logger.warning(
                f"[YOUTUBE_COOKIE_COORDINATOR] Failed to resolve generated cookies: {exc}"
            )
            return []

        if not cookie_path:
            return []

        cookie_file = Path(cookie_path)
        if not cookie_file.exists() or cookie_file.stat().st_size == 0:
            return []

        return [
            YouTubeAuthConfig(
                label="generated-cookie-file",
                source=self.source_name,
                ytdlp_options={"cookiefile": str(cookie_file)},
            )
        ]


class NoCookieSource:
    """Last-resort source with no cookie auth."""

    source_name = "none"

    def resolve(self) -> list[YouTubeAuthConfig]:
        return [
            YouTubeAuthConfig(
                label="no-cookies",
                source=self.source_name,
                ytdlp_options={},
            )
        ]


class YouTubeCookieSourceCoordinator:
    """Factory + strategy coordinator for YouTube cookie auth sources."""

    def __init__(
        self,
        auto_cookie_manager: IAutoCookieManager | None = None,
        cookie_handler: ICookieHandler | None = None,
        storage_dir: Path | None = None,
        config: AppConfig = get_config(),
    ) -> None:
        self.config = config
        self.auto_cookie_manager = auto_cookie_manager
        self.cookie_handler = cookie_handler
        self.storage_dir = storage_dir or self.config.cookies.storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.probe_state_file = self.storage_dir / "youtube_cookie_probe_state.json"

        self._probe_runner = _YouTubeProbeRunner(config=self.config)
        self.state = self._load_state()

    def build_auth_strategies(
        self,
        cookie_path_hint: str | None = None,
        preferred_browser: str | None = None,
        force_reprobe: bool = False,
    ) -> list[YouTubeAuthConfig]:
        manual_cookie_path = self._resolve_manual_cookie_hint(cookie_path_hint)

        browser_source = BrowserCookieSource(
            coordinator=self,
            preferred_browser=preferred_browser,
            force_reprobe=force_reprobe,
        )
        manual_source = ManualCookieFileSource(cookie_path=manual_cookie_path)
        generated_source = GeneratedGuestCookieSource(auto_cookie_manager=self.auto_cookie_manager)
        no_cookie_source = NoCookieSource()

        explicit_manual = self._is_manual_override(manual_cookie_path)

        ordered_sources: list[YouTubeCookieSourceStrategy]
        if explicit_manual:
            ordered_sources = [manual_source, browser_source, generated_source, no_cookie_source]
        else:
            ordered_sources = [browser_source, manual_source, generated_source, no_cookie_source]

        strategies: list[YouTubeAuthConfig] = []
        seen_signatures: set[tuple[Any, ...]] = set()

        for source in ordered_sources:
            for strategy in source.resolve():
                if (signature := _freeze_json_like(strategy.ytdlp_options)) in seen_signatures:
                    continue
                seen_signatures.add(signature)
                strategies.append(strategy)

        return strategies

    def probe_browsers(
        self, candidates: list[BrowserProbeCandidate]
    ) -> BrowserProbeCandidate | None:
        probe_urls = list(YOUTUBE_STRICT_PROBE_URLS)
        probe_results: dict[str, dict[str, Any]] = {}

        for candidate in candidates:
            result = self._probe_runner.probe_browser(candidate, probe_urls)
            probe_results[candidate.name] = asdict(result)
            if result.success:
                now_iso = _utc_now_iso()
                self.state.preferred_source = "browser"
                self.state.preferred_browser = candidate.name
                self.state.last_success_at = now_iso
                self.state.ttl_expires_at = (
                    datetime.now(timezone.utc) + timedelta(hours=_BROWSER_PROBE_TTL_HOURS)
                ).isoformat()
                self.state.per_browser_result = probe_results
                self.state.last_probe_urls = probe_urls
                self.state.last_failure_reason = None
                self._save_state()
                logger.info(f"[YOUTUBE_COOKIE_COORDINATOR] Browser probe winner: {candidate.name}")
                return candidate

        self.state.per_browser_result = probe_results
        self.state.last_probe_urls = probe_urls
        self.state.last_failure_reason = "No browser probe succeeded"
        self._save_state()
        logger.warning("[YOUTUBE_COOKIE_COORDINATOR] Browser probing failed for all candidates")
        return None

    def get_browser_candidates(self) -> list[BrowserProbeCandidate]:
        candidates: list[BrowserProbeCandidate] = []

        # Explicit priority requested by product behavior:
        # chrome -> firefox -> zen -> remaining browsers.
        if self._is_browser_available("chrome"):
            candidates.append(BrowserProbeCandidate(name="chrome", ytdlp_browser="chrome"))
        if self._is_browser_available("firefox"):
            candidates.append(BrowserProbeCandidate(name="firefox", ytdlp_browser="firefox"))

        if zen_profile := self._find_firefox_compatible_profile("zen"):
            candidates.append(
                BrowserProbeCandidate(
                    name="zen",
                    ytdlp_browser="firefox",
                    profile_path=zen_profile,
                )
            )

        remaining_browsers = ["chromium", "brave", "edge", "vivaldi", "opera"]
        for browser in remaining_browsers:
            if not self._is_browser_available(browser):
                continue
            candidates.append(BrowserProbeCandidate(name=browser, ytdlp_browser=browser))

        if librewolf_profile := self._find_firefox_compatible_profile("librewolf"):
            candidates.append(
                BrowserProbeCandidate(
                    name="librewolf",
                    ytdlp_browser="firefox",
                    profile_path=librewolf_profile,
                )
            )

        return candidates

    def reset_probe_state(self) -> None:
        self.state = YouTubeCookieProbeState()
        self._save_state()

    def force_reprobe(self) -> list[YouTubeAuthConfig]:
        return self.build_auth_strategies(force_reprobe=True)

    def _resolve_manual_cookie_hint(self, cookie_path_hint: str | None) -> str | None:
        manual_hint: str | None = None
        if cookie_path_hint and self._is_valid_cookie_file(cookie_path_hint):
            manual_hint = cookie_path_hint
            # If UI passes back the same path already managed by auto cookie manager,
            # keep it in generated-cookie source instead of manual-cookie source.
            if self.auto_cookie_manager:
                try:
                    managed_path = self.auto_cookie_manager.get_cookies()
                except Exception:
                    managed_path = None

                if managed_path:
                    try:
                        if Path(cookie_path_hint).resolve() == Path(managed_path).resolve():
                            manual_hint = None
                    except Exception:
                        pass
        if manual_hint:
            return manual_hint

        if not self.cookie_handler:
            return None

        try:
            cookie_info = self.cookie_handler.get_cookie_info_for_ytdlp()
        except Exception as exc:
            logger.warning(f"[YOUTUBE_COOKIE_COORDINATOR] Manual cookie lookup failed: {exc}")
            return None

        if not cookie_info:
            return None

        cookie_file = cookie_info.get("cookiefile")
        if isinstance(cookie_file, str) and self._is_valid_cookie_file(cookie_file):
            return cookie_file

        return None

    def _is_manual_override(self, cookie_path: str | None) -> bool:
        if not cookie_path:
            return False

        if _cookie_file_has_auth_signals(cookie_path):
            return True

        if not self.auto_cookie_manager:
            return False

        try:
            managed_path = self.auto_cookie_manager.get_cookies()
        except Exception:
            return False

        if not managed_path:
            return True

        return Path(cookie_path).resolve() != Path(managed_path).resolve()

    def _is_valid_cookie_file(self, cookie_path: str) -> bool:
        cookie_file = Path(cookie_path)
        if not cookie_file.exists():
            return False
        return cookie_file.stat().st_size > 0

    def _load_state(self) -> YouTubeCookieProbeState:
        if not self.probe_state_file.exists():
            return YouTubeCookieProbeState()

        try:
            with open(self.probe_state_file, encoding="utf-8") as handle:
                data = json.load(handle)
            return YouTubeCookieProbeState.from_dict(data)
        except Exception as exc:
            logger.warning(
                f"[YOUTUBE_COOKIE_COORDINATOR] Failed to load probe state: {exc}",
                exc_info=True,
            )
            return YouTubeCookieProbeState()

    def _save_state(self) -> None:
        try:
            with open(self.probe_state_file, "w", encoding="utf-8") as handle:
                json.dump(self.state.to_dict(), handle, indent=2)
        except Exception as exc:
            logger.warning(
                f"[YOUTUBE_COOKIE_COORDINATOR] Failed to save probe state: {exc}",
                exc_info=True,
            )

    def _is_browser_available(self, browser: str) -> bool:
        browser_checks: dict[str, dict[str, list[str | None]]] = {
            "chrome": {
                "paths": [
                    "~/Library/Application Support/Google/Chrome",
                    "~/.config/google-chrome",
                    "~/.var/app/com.google.Chrome/config/google-chrome",
                    _join_env("LOCALAPPDATA", "Google", "Chrome", "User Data"),
                ],
                "commands": ["google-chrome", "chrome"],
            },
            "chromium": {
                "paths": [
                    "~/Library/Application Support/Chromium",
                    "~/.config/chromium",
                    "~/.var/app/org.chromium.Chromium/config/chromium",
                    _join_env("LOCALAPPDATA", "Chromium", "User Data"),
                ],
                "commands": ["chromium", "chromium-browser"],
            },
            "brave": {
                "paths": [
                    "~/Library/Application Support/BraveSoftware/Brave-Browser",
                    "~/.config/BraveSoftware/Brave-Browser",
                    _join_env("LOCALAPPDATA", "BraveSoftware", "Brave-Browser", "User Data"),
                ],
                "commands": ["brave", "brave-browser"],
            },
            "edge": {
                "paths": [
                    "~/Library/Application Support/Microsoft Edge",
                    "~/.config/microsoft-edge",
                    _join_env("LOCALAPPDATA", "Microsoft", "Edge", "User Data"),
                ],
                "commands": ["microsoft-edge", "edge"],
            },
            "vivaldi": {
                "paths": [
                    "~/Library/Application Support/Vivaldi",
                    "~/.config/vivaldi",
                    _join_env("LOCALAPPDATA", "Vivaldi", "User Data"),
                ],
                "commands": ["vivaldi"],
            },
            "opera": {
                "paths": [
                    "~/Library/Application Support/com.operasoftware.Opera",
                    "~/.config/opera",
                    _join_env("APPDATA", "Opera Software", "Opera Stable"),
                ],
                "commands": ["opera"],
            },
            "firefox": {
                "paths": [
                    "~/Library/Application Support/Firefox/Profiles",
                    "~/.mozilla/firefox",
                    _join_env("APPDATA", "Mozilla", "Firefox", "Profiles"),
                ],
                "commands": ["firefox"],
            },
        }
        if not (check := browser_checks.get(browser)):
            return False

        existing_paths = [Path(path).expanduser() for path in check["paths"] if path]
        if not (existing_paths := [path for path in existing_paths if path.exists()]):
            return False

        if browser == "firefox":
            return any(_has_firefox_cookie_db(root) for root in existing_paths)

        # Chromium-family browsers.
        return any(_has_chromium_cookie_db(root) for root in existing_paths)

    def _find_firefox_compatible_profile(self, browser: str) -> str | None:
        match browser:
            case "zen":
                roots = [
                    "~/Library/Application Support/zen/Profiles",
                    "~/.zen",
                    _join_env("APPDATA", "zen", "Profiles"),
                ]
            case "librewolf":
                roots = [
                    "~/Library/Application Support/LibreWolf/Profiles",
                    "~/.librewolf",
                    _join_env("APPDATA", "LibreWolf", "Profiles"),
                ]
            case _:
                return None

        for root_str in roots:
            if not root_str:
                continue

            root = Path(root_str).expanduser()
            if not root.exists():
                continue

            if profile := _find_profile_directory(root):
                return str(profile)

        return None

    @staticmethod
    def _any_path_exists(raw_paths: list[str | None]) -> bool:
        for raw_path in raw_paths:
            if not raw_path:
                continue
            if Path(raw_path).expanduser().exists():
                return True
        return False


def probe_youtube_cookie_file(
    cookie_path: str,
    probe_urls: list[str] | None = None,
    config: AppConfig = get_config(),
) -> tuple[bool, str | None]:
    """Validate a cookie file against strict YouTube probe URLs."""

    runner = _YouTubeProbeRunner(config=config)
    return runner.probe_cookie_file(cookie_path, probe_urls or list(YOUTUBE_STRICT_PROBE_URLS))


def _cookie_file_has_auth_signals(cookie_path: str) -> bool:
    auth_cookie_names = {
        "sid",
        "hsid",
        "ssid",
        "apisid",
        "sapisid",
        "__secure-1psid",
        "__secure-3psid",
        "__secure-1papisid",
        "__secure-3papisid",
        "login_info",
    }

    try:
        with open(cookie_path, encoding="utf-8") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped or stripped.startswith("#"):
                    continue

                parts = stripped.split("\t")
                if len(parts) < 7:
                    continue

                if parts[5].strip().lower() in auth_cookie_names:
                    return True
    except Exception:
        return False

    return False


def _extract_video_id(url: str) -> str | None:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()

    if host in {"www.youtube.com", "youtube.com", "m.youtube.com", "music.youtube.com"}:
        if parsed.path == "/watch":
            query = parse_qs(parsed.query)
            return query.get("v", [None])[0]
        if parsed.path.startswith("/shorts/"):
            return parsed.path.removeprefix("/shorts/").split("/")[0]

    if host == "youtu.be":
        return parsed.path.removeprefix("/").split("/")[0]

    return None


def _freeze_json_like(value: object) -> tuple[Any, ...]:
    if isinstance(value, dict):
        return tuple(sorted((str(key), _freeze_json_like(val)) for key, val in value.items()))
    if isinstance(value, list | tuple):
        return tuple(_freeze_json_like(item) for item in value)
    return (value,)


def _has_chromium_cookie_db(root: Path) -> bool:
    direct_candidates = [
        root / "Cookies",
        root / "Network" / "Cookies",
        root / "Default" / "Cookies",
        root / "Default" / "Network" / "Cookies",
    ]
    if any(candidate.exists() for candidate in direct_candidates):
        return True

    if not root.is_dir():
        return False

    with os.scandir(root) as entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            if not (
                entry.name.startswith("Profile ") or entry.name in {"Default", "Guest Profile"}
            ):
                continue
            profile_path = Path(entry.path)
            if (profile_path / "Cookies").exists() or (
                profile_path / "Network" / "Cookies"
            ).exists():
                return True

    return False


def _has_firefox_cookie_db(root: Path) -> bool:
    if (root / "cookies.sqlite").exists():
        return True

    if not root.is_dir():
        return False

    with os.scandir(root) as entries:
        for entry in entries:
            if not entry.is_dir():
                continue
            if (Path(entry.path) / "cookies.sqlite").exists():
                return True

    return False


def _find_profile_directory(root: Path) -> Path | None:
    if (root / "cookies.sqlite").exists():
        return root

    profile_dirs = [path for path in root.iterdir() if path.is_dir()] if root.is_dir() else []

    if profile_with_db := [path for path in profile_dirs if (path / "cookies.sqlite").exists()]:
        return max(profile_with_db, key=lambda path: path.stat().st_mtime)

    if profile_dirs:
        return max(profile_dirs, key=lambda path: path.stat().st_mtime)

    return None


def _join_env(key: str, *parts: str) -> str | None:
    if not (value := os.environ.get(key)):
        return None
    return str(Path(value, *parts))


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
