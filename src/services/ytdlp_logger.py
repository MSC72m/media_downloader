from __future__ import annotations

from src.utils.logger import get_logger

logger = get_logger(__name__)


class YTDLPLoggerBridge:
    """Route yt-dlp log output through app logger instead of raw stderr."""

    def __init__(self, scope: str):
        self.scope = scope

    def debug(self, msg: str) -> None:
        if message := str(msg).strip():
            logger.debug("[%s] %s", self.scope, message)

    def warning(self, msg: str) -> None:
        if message := str(msg).strip():
            logger.debug("[%s] %s", self.scope, message)

    def error(self, msg: str) -> None:
        if message := str(msg).strip():
            logger.debug("[%s] %s", self.scope, message)
