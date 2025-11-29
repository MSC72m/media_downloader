from .di_container import ServiceContainer


def get_orchestrator():
    from .orchestrator import ApplicationOrchestrator

    return ApplicationOrchestrator


__all__ = ["ServiceContainer", "get_orchestrator"]
