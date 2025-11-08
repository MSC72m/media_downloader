from src.utils.logger import get_logger

logger = get_logger(__name__)


# --- GUI utilities ---------------------------------------------------------

def ensure_gui_available() -> bool:
    """Ensure tkinter/customtkinter are available; exit with message if not.

    Returns True if GUI modules import successfully, otherwise exits the
    process.
    """
    try:
        import customtkinter as _ctk  # noqa: F401
        import tkinter as _tk  # noqa: F401
        return True
    except Exception as e:
        msg = (
            "Tkinter (GUI) is not available in this Python. "
            "Install Tcl/Tk and a Python build with _tkinter enabled.\n"
            "macOS (Homebrew + pyenv): brew install tcl-tk, then "
            "reinstall Python with Tk support."
        )
        logger.error(msg)
        print(msg)
        raise SystemExit(1) from e

