import importlib
from typing import TYPE_CHECKING, cast

from .di_container import ServiceContainer

if TYPE_CHECKING:
    from .orchestrator import ApplicationOrchestrator


def _load_symbol(module_path: str, symbol_name: str) -> type:
    module = importlib.import_module(module_path)
    symbol = getattr(module, symbol_name)
    if isinstance(symbol, type):
        return symbol
    raise TypeError(f"{module_path}.{symbol_name} is not a class")


def get_orchestrator() -> type["ApplicationOrchestrator"]:
    return cast(
        type["ApplicationOrchestrator"],
        _load_symbol("src.application.orchestrator", "ApplicationOrchestrator"),
    )


__all__ = ["ServiceContainer", "get_orchestrator"]
