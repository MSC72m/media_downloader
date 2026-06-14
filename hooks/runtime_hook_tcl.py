"""PyInstaller runtime hook for Tcl/Tk initialization.

Sets TCL_LIBRARY and TK_LIBRARY environment variables so the Tcl
interpreter can find its initialization scripts when running from
a PyInstaller bundle.
"""

import os
import sys


def _find_tcl_dirs(base: str) -> tuple[str | None, str | None]:
    """Search for Tcl/Tk library directories under the given base."""
    tcl_dir = None
    tk_dir = None

    for entry in os.listdir(base):
        lower = entry.lower()
        full = os.path.join(base, entry)
        if not os.path.isdir(full):
            continue
        if lower.startswith("tcl") and tcl_dir is None:
            tcl_dir = full
        elif lower.startswith("tk") and tk_dir is None:
            tk_dir = full

    return tcl_dir, tk_dir


if sys.platform == "win32" and hasattr(sys, "_MEIPASS"):
    base = sys._MEIPASS

    # Strategy 1: look directly under _MEIPASS
    tcl_dir, tk_dir = _find_tcl_dirs(base)

    # Strategy 2: look under _MEIPASS/tcl/
    if tcl_dir is None:
        tcl_sub = os.path.join(base, "tcl")
        if os.path.isdir(tcl_sub):
            tcl_dir, tk_dir = _find_tcl_dirs(tcl_sub)

    # Strategy 3: look under _MEIPASS/tcl8.6 and tk8.6
    if tcl_dir is None:
        for name in ("tcl8.6", "tcl8.5"):
            candidate = os.path.join(base, name)
            if os.path.isdir(candidate):
                tcl_dir = candidate
                break
    if tk_dir is None:
        for name in ("tk8.6", "tk8.5"):
            candidate = os.path.join(base, name)
            if os.path.isdir(candidate):
                tk_dir = candidate
                break

    if tcl_dir is not None:
        os.environ["TCL_LIBRARY"] = tcl_dir
    if tk_dir is not None:
        os.environ["TK_LIBRARY"] = tk_dir
