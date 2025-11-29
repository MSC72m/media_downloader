from src.utils.logger import get_logger

logger = get_logger(__name__)


def ensure_gui_available() -> bool:
    try:
        import tkinter as tk  # noqa: F401

        import customtkinter as _ctk  # noqa: F401

        return True
    except Exception as e:
        msg = (
            "Tkinter (GUI) is not available in this Python. "
            "Install Tcl/Tk and a Python build with _tkinter enabled.\n"
            "macOS (Homebrew + pyenv): brew install tcl-tk, then "
            "reinstall Python with Tk support."
        )
        logger.error(msg)
        raise SystemExit(1) from e
