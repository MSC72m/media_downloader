"""Link detection and URL handling."""

from .link_detector import LinkDetector, LinkDetectionRegistry, DetectionResult, LinkHandlerInterface, auto_register_handler

__all__ = [
    'LinkDetector',
    'LinkDetectionRegistry',
    'DetectionResult',
    'LinkHandlerInterface',
    'auto_register_handler'
]
