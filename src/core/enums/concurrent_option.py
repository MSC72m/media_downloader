from .compat import StrEnum


class ConcurrentOption(StrEnum):
    ONE = "1"
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"

    @classmethod
    def all_options(cls) -> list[str]:
        return ["1", "2", "3", "4", "5"]

    @classmethod
    def max_value(cls) -> int:
        return 5
