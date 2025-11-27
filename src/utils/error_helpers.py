"""Error handling helper utilities for consistent error formatting and classification."""

from typing import Optional
from enum import Enum

from src.utils.logger import get_logger

logger = get_logger(__name__)


class ErrorType(Enum):
    """Error type classification."""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    SERVICE = "service"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


def extract_error_context(exception: Exception, service: str = "", operation: str = "", url: str = "") -> dict:
    """Extract error context from exception and parameters.

    Args:
        exception: The exception that occurred
        service: Service name where error occurred
        operation: Operation that was being performed
        url: URL where error occurred

    Returns:
        Dictionary with error context
    """
    return {
        "error_type": type(exception).__name__,
        "error_message": str(exception),
        "service": service,
        "operation": operation,
        "url": url,
    }


def format_user_friendly_error(error_context: dict) -> str:
    """Format error context into user-friendly message.

    Args:
        error_context: Error context dictionary from extract_error_context

    Returns:
        User-friendly error message
    """
    error_msg = error_context.get("error_message", "Unknown error")
    service = error_context.get("service", "")
    operation = error_context.get("operation", "")
    url = error_context.get("url", "")

    if service and operation:
        base_msg = f"{service} {operation} failed"
    elif service:
        base_msg = f"{service} operation failed"
    elif operation:
        base_msg = f"{operation} failed"
    else:
        base_msg = "Operation failed"

    if url:
        return f"{base_msg} for {url}: {error_msg}"

    return f"{base_msg}: {error_msg}"


def classify_error_type(error_message: str) -> ErrorType:
    """Classify error type based on error message patterns.

    Args:
        error_message: Error message to classify

    Returns:
        ErrorType enum value
    """
    error_lower = error_message.lower()

    network_patterns = ["connection", "network", "timeout", "dns", "socket", "refused", "unreachable"]
    auth_patterns = ["authentication", "unauthorized", "forbidden", "401", "403", "login", "password"]
    validation_patterns = ["invalid", "validation", "format", "malformed", "missing"]

    if any(pattern in error_lower for pattern in network_patterns):
        return ErrorType.NETWORK

    if any(pattern in error_lower for pattern in auth_patterns):
        return ErrorType.AUTHENTICATION

    if any(pattern in error_lower for pattern in validation_patterns):
        return ErrorType.VALIDATION

    return ErrorType.UNKNOWN


def get_error_suggestion(error_type: ErrorType, service: str = "") -> str:
    """Get user-friendly suggestion based on error type.

    Args:
        error_type: Classified error type
        service: Service name for context-specific suggestions

    Returns:
        Suggestion message
    """
    suggestions = {
        ErrorType.NETWORK: "Please check your internet connection and try again.",
        ErrorType.AUTHENTICATION: f"Please check your {service} credentials and try again." if service else "Please check your credentials and try again.",
        ErrorType.VALIDATION: "Please check the URL or input and try again.",
        ErrorType.UNKNOWN: "Please try again later or contact support if the problem persists.",
    }

    return suggestions.get(error_type, suggestions[ErrorType.UNKNOWN])

