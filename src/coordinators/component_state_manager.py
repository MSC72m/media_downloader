"""Centralized UI Component State Manager - Single source of truth for UI states."""

from enum import Enum
from typing import Any, Dict, Optional

from src.core.enums.instagram_auth_status import InstagramAuthStatus
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ComponentState(Enum):
    """Enum for component state types."""

    INSTAGRAM_AUTH = "instagram_auth"
    DOWNLOAD_IN_PROGRESS = "download_in_progress"
    BUTTONS_ENABLED = "buttons_enabled"
    NETWORK_STATUS = "network_status"


class ComponentStateManager:
    """Centralized state manager for all UI components.

    This is the SINGLE SOURCE OF TRUTH for component states.
    All state updates MUST go through this manager.
    """

    def __init__(self, container):
        """Initialize state manager with service container."""
        self.container = container
        self._states: Dict[ComponentState, Any] = {
            ComponentState.INSTAGRAM_AUTH: InstagramAuthStatus.FAILED,
            ComponentState.DOWNLOAD_IN_PROGRESS: False,
            ComponentState.BUTTONS_ENABLED: True,
            ComponentState.NETWORK_STATUS: "unknown",
        }

        # Component references (lazy loaded)
        self._options_bar = None
        self._action_buttons = None
        self._status_bar = None

        logger.info("[COMPONENT_STATE_MANAGER] Initialized")

    def refresh_components(self) -> None:
        """Refresh component references from container."""
        self._options_bar = self.container.get("options_bar")
        self._action_buttons = self.container.get("action_buttons")
        self._status_bar = self.container.get("status_bar")
        logger.info("[COMPONENT_STATE_MANAGER] Components refreshed")

    # Instagram Auth State Management
    def set_instagram_auth_state(self, status: InstagramAuthStatus) -> None:
        """Set Instagram authentication state - SINGLE SOURCE OF TRUTH.

        Args:
            status: New authentication status
        """
        logger.info(f"[COMPONENT_STATE_MANAGER] Setting Instagram auth state: {status}")

        # Update internal state
        self._states[ComponentState.INSTAGRAM_AUTH] = status

        # Update UI component if available
        if self._options_bar:
            try:
                self._options_bar.set_instagram_status(status)
                logger.debug(
                    f"[COMPONENT_STATE_MANAGER] Instagram button updated to: {status}"
                )
            except Exception as e:
                logger.error(
                    f"[COMPONENT_STATE_MANAGER] Error updating Instagram button: {e}",
                    exc_info=True,
                )
        else:
            logger.warning(
                "[COMPONENT_STATE_MANAGER] Options bar not available, state stored"
            )

    def get_instagram_auth_state(self) -> InstagramAuthStatus:
        """Get current Instagram authentication state."""
        return self._states[ComponentState.INSTAGRAM_AUTH]

    def set_instagram_logging_in(self) -> None:
        """Set Instagram to logging in state."""
        self.set_instagram_auth_state(InstagramAuthStatus.LOGGING_IN)

    def set_instagram_authenticated(self) -> None:
        """Set Instagram to authenticated state."""
        self.set_instagram_auth_state(InstagramAuthStatus.AUTHENTICATED)

    def set_instagram_failed(self) -> None:
        """Set Instagram to failed state."""
        self.set_instagram_auth_state(InstagramAuthStatus.FAILED)

    # Download Progress State Management
    def set_download_in_progress(self, in_progress: bool) -> None:
        """Set download in progress state.

        Args:
            in_progress: True if downloads are in progress
        """
        logger.info(
            f"[COMPONENT_STATE_MANAGER] Setting download in progress: {in_progress}"
        )

        self._states[ComponentState.DOWNLOAD_IN_PROGRESS] = in_progress

        # Update action buttons if available
        if self._action_buttons:
            try:
                if in_progress:
                    self._action_buttons.set_enabled(False)
                else:
                    self._action_buttons.set_enabled(True)
            except Exception as e:
                logger.error(
                    f"[COMPONENT_STATE_MANAGER] Error updating action buttons: {e}"
                )

    def is_download_in_progress(self) -> bool:
        """Check if download is in progress."""
        return self._states[ComponentState.DOWNLOAD_IN_PROGRESS]

    # Button State Management
    def set_buttons_enabled(self, enabled: bool) -> None:
        """Enable or disable action buttons.

        Args:
            enabled: True to enable, False to disable
        """
        logger.debug(f"[COMPONENT_STATE_MANAGER] Setting buttons enabled: {enabled}")

        self._states[ComponentState.BUTTONS_ENABLED] = enabled

        if self._action_buttons:
            try:
                self._action_buttons.set_enabled(enabled)
            except Exception as e:
                logger.error(
                    f"[COMPONENT_STATE_MANAGER] Error setting button states: {e}"
                )

    def are_buttons_enabled(self) -> bool:
        """Check if buttons are enabled."""
        return self._states[ComponentState.BUTTONS_ENABLED]

    # Network Status Management
    def set_network_status(self, status: str) -> None:
        """Set network connectivity status.

        Args:
            status: Network status string (e.g., 'connected', 'disconnected', 'checking')
        """
        logger.info(f"[COMPONENT_STATE_MANAGER] Setting network status: {status}")
        self._states[ComponentState.NETWORK_STATUS] = status

        # Update status bar if available
        if self._status_bar:
            try:
                is_error = status in ["disconnected", "failed", "error"]
                self._status_bar.show_message(
                    status
                ) if not is_error else self._status_bar.show_error(status)
            except Exception as e:
                logger.error(
                    f"[COMPONENT_STATE_MANAGER] Error updating status bar: {e}"
                )

    def get_network_status(self) -> str:
        """Get current network status."""
        return self._states[ComponentState.NETWORK_STATUS]

    # State Reset Methods
    def reset_instagram_state(self) -> None:
        """Reset Instagram state to initial (failed/not authenticated)."""
        logger.info("[COMPONENT_STATE_MANAGER] Resetting Instagram state")
        self.set_instagram_failed()

    def reset_all_states(self) -> None:
        """Reset all states to initial values."""
        logger.info("[COMPONENT_STATE_MANAGER] Resetting all states")
        self.set_instagram_failed()
        self.set_download_in_progress(False)
        self.set_buttons_enabled(True)
        self.set_network_status("unknown")

    # Debug Methods
    def get_all_states(self) -> Dict[str, Any]:
        """Get all current states for debugging."""
        return {
            "instagram_auth": self._states[ComponentState.INSTAGRAM_AUTH],
            "download_in_progress": self._states[ComponentState.DOWNLOAD_IN_PROGRESS],
            "buttons_enabled": self._states[ComponentState.BUTTONS_ENABLED],
            "network_status": self._states[ComponentState.NETWORK_STATUS],
        }

    def log_current_states(self) -> None:
        """Log all current states for debugging."""
        states = self.get_all_states()
        logger.info(f"[COMPONENT_STATE_MANAGER] Current states: {states}")
