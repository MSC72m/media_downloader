"""Base handler class for link handlers with shared dependencies."""

import re
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, TYPE_CHECKING

from src.core.config import AppConfig, get_config
from src.core.interfaces import IMessageQueue, INotifier
from src.services.notifications.notifier import NotifierService

if TYPE_CHECKING:
    from .link_detector import DetectionResult
else:
    # Import at runtime to avoid circular dependency
    DetectionResult = None


class BaseHandler(ABC):
    """Base class for link handlers with shared dependencies.
    
    Provides:
    - config: AppConfig instance
    - message_queue: IMessageQueue for notifications
    - notifier: INotifier instance with service-specific templates
    - Polymorphic can_handle() using get_patterns()
    """
    
    def __init__(
        self,
        message_queue: IMessageQueue,
        config: AppConfig = get_config(),
        service_name: str = "",
    ):
        """Initialize base handler with shared dependencies.
        
        Args:
            message_queue: Message queue for notifications
            config: Application configuration
            service_name: Service name for loading templates (e.g., 'youtube', 'instagram')
        """
        self.config = config
        self.message_queue = message_queue
        self.service_name = service_name
        
        # Load service-specific templates from config
        templates = self._get_service_templates(service_name)
        self.notifier: INotifier = NotifierService(message_queue, custom_templates=templates)
    
    def _get_service_templates(self, service_name: str) -> Dict[str, Dict[str, Any]]:
        """Get notification templates for the service from config.
        
        Args:
            service_name: Service name (e.g., 'youtube', 'instagram')
            
        Returns:
            Dictionary of notification templates
        """
        if not service_name:
            return {}
        
        templates_attr = getattr(self.config.notifications, service_name, None)
        return templates_attr if templates_attr else {}
    
    @classmethod
    @abstractmethod
    def get_patterns(cls) -> List[str]:
        """Get URL patterns for this handler.
        
        Returns:
            List of regex patterns to match URLs
        """
        ...
    
    def can_handle(self, url: str) -> "DetectionResult":
        """Polymorphic URL detection using patterns from get_patterns().
        
        Subclasses can override _extract_metadata() to provide custom metadata.
        
        Args:
            url: URL to check
            
        Returns:
            DetectionResult with service_type, confidence, and metadata
        """
        from .link_detector import DetectionResult
        
        patterns = self.get_patterns()
        
        for pattern in patterns:
            if re.match(pattern, url):
                metadata = self._extract_metadata(url)
                return DetectionResult(
                    service_type=self.service_name,
                    confidence=1.0,
                    metadata=metadata,
                )
        
        return DetectionResult(service_type="unknown", confidence=0.0)
    
    def _extract_metadata(self, url: str) -> Dict[str, Any]:
        """Extract metadata from URL. Override in subclasses for custom extraction.
        
        Args:
            url: URL to extract metadata from
            
        Returns:
            Dictionary of metadata
        """
        return {}
    
    @abstractmethod
    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata for the URL."""
        ...
    
    @abstractmethod
    def process_download(self, url: str, options: Dict[str, Any]) -> bool:
        """Process the download with given options."""
        ...
    
    @abstractmethod
    def get_ui_callback(self) -> Callable:
        """Get the UI callback for handling this link type."""
        ...

