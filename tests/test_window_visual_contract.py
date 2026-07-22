"""Contracts for consistent gradient/glass application windows."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

from src.ui.components.loading_dialog import LoadingDialog
from src.ui.components.loading_spinner import SmallLoadingSpinner
from src.ui.dialogs.base_dialog import BaseDialog
from src.ui.dialogs.file_manager_dialog import FileManagerDialog
from src.ui.dialogs.input_dialog import CenteredInputDialog
from src.ui.dialogs.login_dialog import LoginDialog
from src.ui.dialogs.message_dialog import MessageDialog
from src.ui.dialogs.network_status_dialog import NetworkStatusDialog
from src.ui.dialogs.spotify_downloader_dialog import SpotifyDownloaderDialog
from src.ui.dialogs.youtube_downloader_dialog import YouTubeDownloaderDialog
from src.ui.visual_system import GlassButton, GlassFrame, GradientBackdrop, GradientButton

_PROJECT_ROOT = Path(__file__).parents[1]
_SRC = _PROJECT_ROOT / "src"


def _source(relative_path: str) -> str:
    return (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_custom_top_levels_inherit_the_canonical_base() -> None:
    window_classes = (
        LoadingDialog,
        SmallLoadingSpinner,
        FileManagerDialog,
        CenteredInputDialog,
        LoginDialog,
        MessageDialog,
        NetworkStatusDialog,
        SpotifyDownloaderDialog,
        YouTubeDownloaderDialog,
    )
    assert all(issubclass(window_class, BaseDialog) for window_class in window_classes)


def test_no_window_bypasses_base_dialog_or_creates_a_second_root() -> None:
    direct_top_levels: list[str] = []
    root_constructions: list[str] = []
    input_dialog_uses: list[str] = []

    for path in _SRC.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        relative = str(path.relative_to(_PROJECT_ROOT))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    rendered = ast.unparse(base)
                    if rendered in {"ctk.CTkToplevel", "tk.Toplevel"}:
                        direct_top_levels.append(f"{relative}:{node.name}")
                    if rendered == "ctk.CTkInputDialog":
                        input_dialog_uses.append(f"{relative}:{node.name}")
            if isinstance(node, ast.Call):
                rendered = ast.unparse(node.func)
                if rendered in {"ctk.CTkToplevel", "tk.Toplevel", "ctk.CTk", "tk.Tk"}:
                    root_constructions.append(f"{relative}:{rendered}")

    assert direct_top_levels == ["src/ui/dialogs/base_dialog.py:BaseDialog"]
    assert input_dialog_uses == []
    assert root_constructions == []


def test_only_application_entrypoint_owns_a_main_loop() -> None:
    occurrences = []
    for path in _SRC.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if ".mainloop(" in source:
            occurrences.append(str(path.relative_to(_PROJECT_ROOT)))
    assert occurrences == ["src/main.py"]
    assert _source("src/main.py").count(".mainloop(") == 1


def test_base_dialog_owns_gradient_and_single_theme_subscription() -> None:
    source = inspect.getsource(BaseDialog)
    assert "GradientBackdrop(" in source
    assert "self.content_parent = self.background" in source
    assert source.count(".subscribe(") == 1
    assert source.count(".unsubscribe(") == 1
    assert "register_theme_refresh" in source
    assert "clear_dialog_content" in source


def test_dialog_subclasses_do_not_duplicate_theme_bus_lifecycle() -> None:
    paths = [
        "src/ui/components/loading_dialog.py",
        "src/ui/components/loading_spinner.py",
        "src/ui/dialogs/file_manager_dialog.py",
        "src/ui/dialogs/input_dialog.py",
        "src/ui/dialogs/login_dialog.py",
        "src/ui/dialogs/message_dialog.py",
        "src/ui/dialogs/network_status_dialog.py",
        "src/ui/dialogs/spotify_downloader_dialog.py",
        "src/ui/dialogs/youtube_downloader_dialog.py",
    ]
    for path in paths:
        source = _source(path)
        assert ".subscribe(ThemeEvent.THEME_CHANGED" not in source, path
        assert ".unsubscribe(ThemeEvent.THEME_CHANGED" not in source, path


def test_window_content_reuses_canonical_visual_primitives() -> None:
    for primitive in (GradientBackdrop, GlassFrame, GlassButton, GradientButton):
        assert ".unsubscribe(" in inspect.getsource(primitive.destroy)

    playwright_source = _source("src/services/cookies/playwright_bootstrap.py")
    assert "BaseDialog(root_window" in playwright_source
    assert "GlassFrame(" in playwright_source
    assert "ctk.CTkToplevel" not in playwright_source

    for path in (
        "src/ui/dialogs/file_manager_dialog.py",
        "src/ui/dialogs/input_dialog.py",
        "src/ui/dialogs/login_dialog.py",
        "src/ui/dialogs/message_dialog.py",
        "src/ui/dialogs/network_status_dialog.py",
        "src/ui/dialogs/spotify_downloader_dialog.py",
        "src/ui/dialogs/youtube_downloader_dialog.py",
    ):
        assert "GlassFrame(" in _source(path), path


def test_input_dialog_calls_supply_parent_and_preserve_prefill() -> None:
    handler_source = _source("src/handlers/youtube_handler.py")
    file_manager_source = _source("src/ui/dialogs/file_manager_dialog.py")
    assert "CenteredInputDialog(\n                            root," in handler_source
    assert "initial_value=track_name" in handler_source
    assert "CenteredInputDialog(\n            self," in file_manager_source


def test_startup_dialogs_stay_on_the_real_tk_thread() -> None:
    source = _source("src/main.py")
    assert "error_window = ctk.CTk()" not in source
    assert "app.after(150, _show_playwright_warning)" in source
    assert "app.after(250, _install_browser)" in source
    assert "threading.Thread(target=_bg_install" not in source


def test_nested_modals_restore_grab_and_workers_use_shared_ui_queue() -> None:
    base_source = _source("src/ui/dialogs/base_dialog.py")
    assert "self._previous_grab = self.grab_current()" in base_source
    assert "self._previous_grab.grab_set()" in base_source
    assert "queue.SimpleQueue" in base_source
    assert "def call_on_ui_thread" in base_source

    for path in (
        "src/ui/dialogs/youtube_downloader_dialog.py",
        "src/ui/dialogs/spotify_downloader_dialog.py",
    ):
        source = _source(path)
        assert "self.call_on_ui_thread(update_func)" in source
        assert "self.after(0, _update_ui)" not in source
        assert "on_timeout=self._handle_metadata_timeout" in source


def test_browser_terminal_paths_signal_ready_and_complete() -> None:
    bootstrap_source = _source("src/services/cookies/playwright_bootstrap.py")
    main_source = _source("src/main.py")
    assert "def mark_chromium_ready" in bootstrap_source
    assert "_chromium_ready.set()" in bootstrap_source
    assert "_chromium_check_done.set()" in bootstrap_source
    assert main_source.count("mark_chromium_ready()") == 2


def test_subtitle_replacement_cancels_pending_batch() -> None:
    source = _source("src/ui/components/subtitle_checklist.py")
    clear_start = source.index("    def _clear_existing_options")
    next_method = source.index("    def _create_option_item", clear_start)
    clear_source = source[clear_start:next_method]
    assert "self.after_cancel(self._batch_after_id)" in clear_source
    assert "self._batch_after_id = None" in clear_source
