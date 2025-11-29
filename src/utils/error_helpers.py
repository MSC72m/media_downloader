import re
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


def extract_error_context(
    exception: Exception, service: str = "", operation: str = "", url: str = ""
) -> dict:
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


def _truncate_url(url: str, max_length: int = 100) -> str:
    """Truncate long URLs for display.

    Args:
        url: URL to truncate
        max_length: Maximum length before truncation

    Returns:
        Truncated URL with ellipsis if needed
    """
    if len(url) <= max_length:
        return url
    return url[: max_length - 3] + "..."


def _format_checkpoint_error(error_msg: str) -> str:
    """Format Instagram checkpoint errors with user-friendly message.

    Args:
        error_msg: Original error message

    Returns:
        Formatted user-friendly message
    """
    if "checkpoint required" in error_msg.lower() or "challenge" in error_msg.lower():
        return "Instagram requires security verification. Please complete the challenge in your browser, then try again."
    return error_msg


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

    if "instagram" in service.lower() and (
        "checkpoint" in error_msg.lower() or "challenge" in error_msg.lower()
    ):
        return _format_checkpoint_error(error_msg)

    if url:
        url = _truncate_url(url, max_length=80)

    if len(error_msg) > 200:
        error_msg = _truncate_url(error_msg, max_length=200)

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

    network_pattern = re.compile(
        r"(connection|network|timeout|dns|socket|refused|unreachable)", re.IGNORECASE
    )
    auth_pattern = re.compile(
        r"(authentication|unauthorized|forbidden|401|403|login|password)", re.IGNORECASE
    )
    validation_pattern = re.compile(r"(invalid|validation|format|malformed|missing)", re.IGNORECASE)

    if network_pattern.search(error_lower):
        return ErrorType.NETWORK

    if auth_pattern.search(error_lower):
        return ErrorType.AUTHENTICATION

    if validation_pattern.search(error_lower):
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
        ErrorType.AUTHENTICATION: f"Please check your {service} credentials and try again."
        if service
        else "Please check your credentials and try again.",
        ErrorType.VALIDATION: "Please check the URL or input and try again.",
        ErrorType.UNKNOWN: "Please try again later or contact support if the problem persists.",
    }

    return suggestions.get(error_type, suggestions[ErrorType.UNKNOWN])
