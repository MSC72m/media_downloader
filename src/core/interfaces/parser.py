"""Interface for parsing and validating media content."""

from typing import Dict, Any, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class IParser(Protocol):
    def validate(self, url: str, context: Optional[Dict[str, Any]] = None) -> bool:
        ...
    
    def parse(self, data: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        ...
