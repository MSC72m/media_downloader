"""Application orchestration and dependency injection."""

from .di_container import ServiceContainer


def get_orchestrator():
    """Get application orchestrator - lazy import to avoid circular dependencies."""
    from .orchestrator import ApplicationOrchestrator

    return ApplicationOrchestrator


__all__ = ["ServiceContainer", "get_orchestrator"]
