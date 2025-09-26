"""Concrete implementation of authentication handler."""

import logging
from typing import Any, Callable
from src.core.models import ServiceType

logger = logging.getLogger(__name__)


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
        """Check if authenticated with a service."""
        if not self._auth_manager:
            return False
        # For now, only Instagram authentication is implemented
        if service == ServiceType.INSTAGRAM:
            return hasattr(self._auth_manager, 'is_authenticated') and self._auth_manager.is_authenticated
        return False  # Other services don't require authentication yet