"""Link detection and URL handling."""

from .base_handler import BaseHandler
from .link_detector import (
    DetectionResult,
    LinkDetectionRegistry,
    LinkDetector,
    LinkHandlerInterface,
    auto_register_handler,
)

__all__ = [
    "LinkDetector",
    "LinkDetectionRegistry",
    "DetectionResult",
    "LinkHandlerInterface",
    "BaseHandler",
    "auto_register_handler",
]
