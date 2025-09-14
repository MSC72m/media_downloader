"""Concrete implementation of authentication handler."""

import logging
from typing import Any, Callable
from ..abstractions import IAuthenticationHandler, IHandler
from src.models import ServiceType
from src.controllers.auth_manager import AuthenticationManager

logger = logging.getLogger(__name__)


class AuthenticationHandler(IAuthenticationHandler):
    """Lightweight handler that delegates to existing AuthenticationManager."""

    def __init__(self, auth_manager: AuthenticationManager = None):
        self._auth_manager = auth_manager or AuthenticationManager()
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
        """Delegate to existing AuthenticationManager."""
        self._auth_manager.authenticate_instagram(parent_window, callback)

    def is_authenticated(self, service: ServiceType) -> bool:
        """Check if authenticated with a service."""
        # For now, only Instagram authentication is implemented
        if service == ServiceType.INSTAGRAM:
            return hasattr(self._auth_manager, 'is_authenticated') and self._auth_manager.is_authenticated
        return False  # Other services don't require authentication yet