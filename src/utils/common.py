import importlib.util
import sys
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


def resource_path(relative_path: str) -> Path:
    """Return absolute path to a resource, works for dev and PyInstaller bundle."""
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base_path = Path(__file__).resolve().parent.parent.parent
    return base_path / relative_path


def set_windows_dpi_awareness() -> None:
    """Enable Windows DPI awareness so the UI renders at native resolution."""
    if sys.platform != "win32":
        return
    try:
        from ctypes import windll

        windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            from ctypes import windll

            windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def ensure_gui_available() -> bool:
    try:
        if not importlib.util.find_spec("tkinter"):
            raise ImportError("tkinter module is not available")
        if not importlib.util.find_spec("customtkinter"):
            raise ImportError("customtkinter module is not available")
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
