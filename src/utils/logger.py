import logging
import sys

_root_logger_configured = False


def get_logger(name: str) -> logging.Logger:
    global _root_logger_configured  # noqa: PLW0603

    if not _root_logger_configured:
        root_logger = logging.getLogger()
        if not root_logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            root_logger.addHandler(handler)
            root_logger.setLevel(logging.INFO)
        _root_logger_configured = True

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    return logger
