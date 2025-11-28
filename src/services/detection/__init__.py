"""Link detection and URL handling."""

from .link_detector import (
    LinkDetector,
    LinkDetectionRegistry,
    DetectionResult,
    LinkHandlerInterface,
    auto_register_handler,
)
from .base_handler import BaseHandler

__all__ = [
    "LinkDetector",
    "LinkDetectionRegistry",
    "DetectionResult",
    "LinkHandlerInterface",
    "BaseHandler",
    "auto_register_handler",
]
