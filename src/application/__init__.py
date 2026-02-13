import importlib
from typing import Any

from .di_container import ServiceContainer


def _load_symbol(module_path: str, symbol_name: str) -> Any:
    module = importlib.import_module(module_path)
    return getattr(module, symbol_name)


def get_orchestrator():
    return _load_symbol("src.application.orchestrator", "ApplicationOrchestrator")


__all__ = ["ServiceContainer", "get_orchestrator"]
