from dataclasses import dataclass

from src.core.type_defs import JSONDict


@dataclass
class DetectionResult:
    service_type: str
    confidence: float
    metadata: JSONDict | None = None
