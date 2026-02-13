from dataclasses import dataclass
from typing import Any


@dataclass
class DetectionResult:
    service_type: str
    confidence: float
    metadata: dict[str, Any] | None = None
