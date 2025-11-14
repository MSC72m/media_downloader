import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, Type

from src.utils.logger import get_logger

logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = get_logger(__name__)


@dataclass
class DetectionResult:
    """Result of link detection."""

    service_type: str
    confidence: float  # 0.0 to 1.0
    metadata: Dict[str, Any] | None = None


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
        logger.info(f"[REGISTRATION] Attempting to register handler: {handler_name}")

        if handler_name in cls._handlers:
            logger.warning(
                f"[REGISTRATION] Handler {handler_name} already registered, replacing"
            )

        cls._handlers[handler_name] = handler_class
        logger.info(f"[REGISTRATION] Successfully registered handler: {handler_name}")
        logger.info(f"[REGISTRATION] Total handlers registered: {len(cls._handlers)}")
        logger.info(f"[REGISTRATION] Registered handlers: {list(cls._handlers.keys())}")

        # Compile patterns for faster matching
        if hasattr(handler_class, "get_patterns"):
            patterns = handler_class.get_patterns()
            cls._compiled_patterns[handler_name] = [
                re.compile(pattern) for pattern in patterns
            ]
            logger.info(
                f"[REGISTRATION] Compiled {len(patterns)} patterns for {handler_name}: {patterns}"
            )
        else:
            logger.warning(
                f"[REGISTRATION] Handler {handler_name} has no get_patterns method"
            )

    @classmethod
    def detect_handler(cls, url: str) -> Optional[LinkHandlerInterface]:
        """Detect the appropriate handler for a URL."""
        logger.info(f"[DETECTION] Starting URL detection for: {url}")
        logger.info(f"[DETECTION] Available handlers: {list(cls._handlers.keys())}")

        best_handler = None
        best_confidence = 0.0

        for handler_name, handler_class in cls._handlers.items():
            try:
                logger.debug(f"[DETECTION] Testing handler: {handler_name}")
                handler = handler_class()
                logger.debug(f"[DETECTION] Created handler instance: {handler}")
                result = handler.can_handle(url)
                logger.debug(
                    f"[DETECTION] Handler {handler_name} result: confidence={result.confidence}, service_type={result.service_type}"
                )

                if result.confidence > best_confidence:
                    best_confidence = result.confidence
                    best_handler = handler
                    logger.info(
                        f"[DETECTION] New best handler: {handler_name} with confidence {best_confidence}"
                    )
            except Exception as e:
                logger.error(
                    f"[DETECTION] Error testing handler {handler_name}: {e}",
                    exc_info=True,
                )

        logger.info(
            f"[DETECTION] Detection complete. Best handler: {best_handler.__class__.__name__ if best_handler else 'None'} with confidence {best_confidence}"
        )
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
        """Detect URL type and trigger appropriate handling with early returns."""
        logger.info(f"[LINK_DETECTOR] Starting detect_and_handle for URL: {url}")

        handler = self.registry.detect_handler(url)
        if not handler:
            logger.warning(f"[LINK_DETECTOR] No handler found for URL: {url}")
            return False

        logger.info(f"[LINK_DETECTOR] Detected handler: {handler.__class__.__name__}")

        try:
            callback = handler.get_ui_callback()
            if not callback:
                logger.warning(
                    f"[LINK_DETECTOR] No callback from handler: {handler.__class__.__name__}"
                )
                return False

            if not ui_context:
                logger.warning(f"[LINK_DETECTOR] Missing ui_context")
                return False

            logger.info(f"[LINK_DETECTOR] Executing callback with URL: {url}")
            callback(url, ui_context)
            logger.info("[LINK_DETECTOR] Callback executed successfully")
            return True
        except Exception as e:
            logger.error(
                f"[LINK_DETECTOR] Error handling URL with {handler.__class__.__name__}: {e}",
                exc_info=True,
            )
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
    logger.info(f"[DECORATOR] Auto-registering handler: {handler_class.__name__}")
    try:
        LinkDetectionRegistry.register(handler_class)
        logger.info(
            f"[DECORATOR] Successfully auto-registered handler: {handler_class.__name__}"
        )
    except Exception as e:
        logger.error(
            f"[DECORATOR] Failed to auto-register handler {handler_class.__name__}: {e}",
            exc_info=True,
        )
    return handler_class
