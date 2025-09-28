"""Extensible link detection system with automatic registration."""

import re
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type, Callable, Any
from dataclasses import dataclass


@dataclass
class DetectionResult:
    """Result of link detection."""
    service_type: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] = None


class LinkHandlerInterface(ABC):
    """Interface for link handlers."""

    @abstractmethod
    def can_handle(self, url: str) -> DetectionResult:
        """Check if this handler can process the given URL."""
        pass

    @abstractmethod
    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata for the URL."""
        pass

    @abstractmethod
    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process the download with given options."""
        pass

    @abstractmethod
    def get_ui_callback(self) -> Callable:
        """Get the UI callback for handling this link type."""
        pass


class LinkDetectionRegistry:
    """Registry for link handlers with automatic registration."""

    _instance = None
    _handlers: Dict[str, Type[LinkHandlerInterface]] = {}
    _compiled_patterns: Dict[str, re.Pattern] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, handler_class: Type[LinkHandlerInterface]):
        """Register a link handler class."""
        handler_name = handler_class.__name__
        cls._handlers[handler_name] = handler_class

        # Compile patterns for faster matching
        if hasattr(handler_class, 'get_patterns'):
            patterns = handler_class.get_patterns()
            cls._compiled_patterns[handler_name] = [re.compile(pattern) for pattern in patterns]

    @classmethod
    def detect_handler(cls, url: str) -> Optional[LinkHandlerInterface]:
        """Detect the appropriate handler for a URL."""
        best_handler = None
        best_confidence = 0.0

        for handler_name, handler_class in cls._handlers.items():
            try:
                handler = handler_class()
                result = handler.can_handle(url)
                if result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_handler = handler
            except Exception as e:
                print(f"Error testing handler {handler_name}: {e}")

        return best_handler if best_confidence > 0.5 else None

    @classmethod
    def quick_detect(cls, url: str) -> Optional[str]:
        """Quick detection using pre-compiled patterns."""
        for handler_name, patterns in cls._compiled_patterns.items():
            for pattern in patterns:
                if pattern.match(url):
                    return handler_name
        return None

    @classmethod
    def get_registered_handlers(cls) -> List[str]:
        """Get list of registered handler names."""
        return list(cls._handlers.keys())

    @classmethod
    def clear(cls):
        """Clear all registered handlers (mainly for testing)."""
        cls._handlers.clear()
        cls._compiled_patterns.clear()


class LinkDetector:
    """Main link detector that uses the registry."""

    def __init__(self):
        self.registry = LinkDetectionRegistry()

    def detect_and_handle(self, url: str, ui_context: Any = None) -> bool:
        """Detect URL type and trigger appropriate handling."""
        handler = self.registry.detect_handler(url)
        if handler:
            try:
                callback = handler.get_ui_callback()
                if callback and ui_context:
                    callback(url, ui_context)
                    return True
            except Exception as e:
                print(f"Error handling URL with {handler.__class__.__name__}: {e}")
        return False

    def get_url_info(self, url: str) -> Optional[DetectionResult]:
        """Get information about a URL without processing it."""
        handler = self.registry.detect_handler(url)
        if handler:
            try:
                return handler.can_handle(url)
            except Exception as e:
                print(f"Error getting URL info: {e}")
        return None


def auto_register_handler(handler_class: Type[LinkHandlerInterface]):
    """Decorator for automatic handler registration."""
    LinkDetectionRegistry.register(handler_class)
    return handler_class