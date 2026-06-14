import logging
import logging.handlers
import sys
from pathlib import Path

_root_logger_configured = False


def _get_log_dir() -> Path:
    """Return the log directory, creating it if needed."""
    log_dir = Path.home() / ".media_downloader" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_logger(name: str) -> logging.Logger:
    global _root_logger_configured  # noqa: PLW0603

    if not _root_logger_configured:
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

            # Console handler (stdout)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

            # Rotating file handler — 5 MB per file, keep 5 backups
            try:
                log_file = _get_log_dir() / "media_downloader.log"
                file_handler = logging.handlers.RotatingFileHandler(
                    log_file,
                    maxBytes=5 * 1024 * 1024,
                    backupCount=5,
                    encoding="utf-8",
                )
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)
            except Exception:
                pass  # Non-fatal: console logging still works

            root_logger.setLevel(logging.INFO)
        _root_logger_configured = True

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    return logger
