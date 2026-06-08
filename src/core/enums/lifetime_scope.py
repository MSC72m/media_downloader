from enum import Enum, auto


class LifetimeScope(Enum):
    SINGLETON = auto()
    TRANSIENT = auto()
