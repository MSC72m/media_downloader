"""Base handler class for link handlers with shared dependencies."""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, TYPE_CHECKING

from src.core.config import AppConfig, get_config
from src.core.interfaces import IMessageQueue, INotifier
from src.services.notifications.notifier import NotifierService

if TYPE_CHECKING:
    from .link_detector import DetectionResult


class BaseHandler(ABC):
    """Base class for link handlers with shared dependencies.
    
    Provides:
    - config: AppConfig instance
    - message_queue: IMessageQueue for notifications
    - notifier: INotifier instance with service-specific templates
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
    
    @abstractmethod
    def can_handle(self, url: str) -> "DetectionResult":
        """Check if this handler can process the given URL."""
        ...
    
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

