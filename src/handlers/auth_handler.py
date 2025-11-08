"""Concrete implementation of authentication handler."""

from src.utils.logger import get_logger
from typing import Any, Callable
from src.core.models import ServiceType

logger = get_logger(__name__)


class AuthenticationHandler:
    """Authentication handler using service container."""

    def __init__(self, auth_manager=None):
        self._auth_manager = auth_manager
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the auth handler."""
        if self._initialized:
            return
        self._initialized = True

    def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self._auth_manager, 'cleanup'):
            self._auth_manager.cleanup()
        self._initialized = False

    def authenticate_instagram(
        self,
        parent_window: Any,
        callback: Callable[[bool], None]
    ) -> None:
        """Authenticate with Instagram."""
        if self._auth_manager:
            self._auth_manager.authenticate_instagram(parent_window, callback)

    def is_authenticated(self, service: ServiceType) -> bool:
        """Check if authenticated with a service using guard clauses."""
        if not self._auth_manager:
            return False
        if service != ServiceType.INSTAGRAM:
            return False
        return bool(getattr(self._auth_manager, 'is_authenticated', False))
