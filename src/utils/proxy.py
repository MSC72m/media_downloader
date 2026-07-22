"""Shared proxy resolution helpers.

Single source of truth for the optional network proxy configured on
``NetworkConfig.proxy``. Both the yt-dlp code paths and the ``requests``
based downloaders resolve the proxy through these helpers so behaviour stays
consistent (DRY) and validation lives in one place.
"""

from src.core.config import AppConfig, get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Schemes understood by both ``requests`` and yt-dlp. ``socks5h://`` resolves
# DNS through the proxy; ``socks5://`` resolves locally.
SUPPORTED_PROXY_SCHEMES: tuple[str, ...] = (
    "socks5://",
    "socks5h://",
    "http://",
    "https://",
)


def get_proxy(config: AppConfig | None = None) -> str | None:
    """Return the configured proxy URL, or ``None`` when unset/invalid.

    Args:
        config: Optional configuration instance. Falls back to the singleton
            :func:`get_config` when not provided.

    Returns:
        A validated proxy URL string, or ``None`` when no proxy is configured
        or the configured value uses an unsupported scheme.
    """
    cfg = config or get_config()
    proxy = cfg.network.proxy
    if not proxy:
        return None

    proxy = proxy.strip()
    if not proxy:
        return None

    if not proxy.startswith(SUPPORTED_PROXY_SCHEMES):
        logger.warning(
            "[PROXY] Ignoring proxy with unsupported scheme: %r "
            "(supported: socks5://, socks5h://, http://, https://)",
            proxy,
        )
        return None

    return proxy


def get_request_proxies(config: AppConfig | None = None) -> dict[str, str] | None:
    """Return a ``requests``-compatible proxies mapping, or ``None``.

    Args:
        config: Optional configuration instance forwarded to :func:`get_proxy`.

    Returns:
        ``{"http": proxy, "https": proxy}`` when a proxy is configured,
        otherwise ``None`` (which ``requests`` treats as "no proxy").
    """
    proxy = get_proxy(config)
    if proxy is None:
        return None
    return {"http": proxy, "https": proxy}
