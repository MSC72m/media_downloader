"""Headless contracts for the queue-first visual system."""

from __future__ import annotations

import ast
import inspect
import re
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from src.ui.visual_system import blend, resolve_palette


class _Appearance:
    value = "dark"


class _ThemeManager:
    def get_appearance(self) -> _Appearance:
        return _Appearance()

    def get_theme_json(self) -> dict[str, object]:
        return {"CTkButton": {"fg_color": ["#EF4444", "#DC2626"]}}


def test_alpha_blend_endpoints_and_midpoint() -> None:
    assert blend("#FFFFFF", "#000000", 0.0) == "#000000"
    assert blend("#FFFFFF", "#000000", 1.0) == "#FFFFFF"
    assert blend("#FFFFFF", "#000000", 0.5) == "#808080"


def test_resolved_palette_contains_only_concrete_hex_colors() -> None:
    palette = resolve_palette(_ThemeManager())  # type: ignore[arg-type]
    for name, value in vars(palette).items():
        if name == "appearance":
            continue
        assert re.fullmatch(r"#[0-9A-F]{6}", value), f"{name} is not Tk-safe: {value}"


def test_production_component_paths_do_not_contain_css_rgba() -> None:
    root = Path(__file__).parents[1] / "src" / "ui"
    paths = [root / "visual_system.py", *(root / "components").glob("*.py")]
    offenders = [str(path) for path in paths if "rgba(" in path.read_text(encoding="utf-8")]
    assert offenders == []


def test_queue_and_footer_preserve_orchestrator_protocols() -> None:
    from src.ui.components.download_card_list import DownloadCardList
    from src.ui.components.footer import AppFooter

    queue_methods = {"refresh_items", "update_item_progress"}
    footer_methods = {"set_enabled", "show_message", "show_error", "show_warning", "update_progress"}
    assert queue_methods <= set(dir(DownloadCardList))
    assert footer_methods <= set(dir(AppFooter))
    assert all(inspect.isfunction(getattr(DownloadCardList, method)) for method in queue_methods)
    assert all(inspect.isfunction(getattr(AppFooter, method)) for method in footer_methods)


_PROJECT_ROOT = Path(__file__).parents[1]


def _source(relative_path: str) -> str:
    return (_PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_main_layout_is_exactly_four_queue_first_regions() -> None:
    source = _source("src/main.py")
    tree = ast.parse(source)
    setup_layout = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_setup_layout"
    )
    gridded_self_widgets = {
        call.func.value.attr
        for call in ast.walk(setup_layout)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and call.func.attr == "grid"
        and isinstance(call.func.value, ast.Attribute)
        and isinstance(call.func.value.value, ast.Name)
        and call.func.value.value.id == "self"
    }
    assert gridded_self_widgets == {
        "background",
        "header_frame",
        "url_entry",
        "download_list",
        "footer",
    }
    assert "self.main_frame.grid_rowconfigure(2, weight=1)" in source
    assert 'self.download_list.grid(row=2, column=0, sticky="nsew"' in source
    assert "self.action_buttons = self.footer" in source
    assert "self.status_bar = self.footer" in source


def test_obsolete_and_oversized_visual_paths_are_absent() -> None:
    components = _PROJECT_ROOT / "src" / "ui" / "components"
    obsolete = {
        "premium",
        "empty_download_state.py",
        "main_action_buttons.py",
        "status_bar.py",
        "rich_download_card.py",
        "status_badge.py",
    }
    assert not any((components / path).exists() for path in obsolete)

    header_source = _source("src/ui/components/header.py")
    queue_source = _source("src/ui/components/download_card_list.py")
    production_copy = (header_source + queue_source).lower()
    assert "ctkimage" not in header_source.lower()
    assert "supported platforms" not in production_copy
    assert not ({"↓", "⬇", "⇩"} & set(queue_source))


def test_header_and_settings_use_canonical_surfaces() -> None:
    from src.ui.components.header import AppHeader
    from src.ui.components.modern_surface import RaisedSurface
    from src.ui.components.settings_panel import SettingsPanel
    from src.ui.visual_system import GlassFrame

    assert issubclass(AppHeader, GlassFrame)
    assert issubclass(SettingsPanel, RaisedSurface)


def test_gradients_are_pillow_rendered_and_main_thread_scheduled() -> None:
    from src.ui.visual_system import GradientBackdrop, GradientButton

    backdrop_render = inspect.getsource(GradientBackdrop._render)
    backdrop_schedule = inspect.getsource(GradientBackdrop._schedule_redraw)
    button_render = inspect.getsource(GradientButton._render)
    button_init = inspect.getsource(GradientButton.__init__)

    assert "ImageTk.PhotoImage" in backdrop_render
    assert "Image.effect_noise" in backdrop_render
    assert "self.after(" in backdrop_schedule
    assert "ImageTk.PhotoImage" in button_render
    assert "ImageDraw.Draw(mask).rounded_rectangle" in button_render
    assert "self.after_idle(self._render)" in button_init
    assert "threading" not in _source("src/ui/visual_system.py")


def test_theme_subscribers_unsubscribe_and_settings_recolor_content() -> None:
    from src.ui.components.settings_panel import SettingsPanel
    from src.ui.visual_system import GlassFrame, GradientBackdrop, GradientButton

    for widget_class in (GlassFrame, GradientBackdrop, GradientButton, SettingsPanel):
        destroy_source = inspect.getsource(widget_class.destroy)
        assert ".unsubscribe(" in destroy_source

    settings_source = inspect.getsource(SettingsPanel)
    assert "self._themed_labels" in settings_source
    assert "label.configure(text_color=colors[role])" in settings_source
    assert "ThemeEvent.THEME_CHANGED, self._on_theme_changed" in settings_source


class _ThemeBus:
    def __init__(self) -> None:
        self.listeners: dict[Any, list[Any]] = {}

    def subscribe(self, event: Any, callback: Any) -> None:
        self.listeners.setdefault(event, []).append(callback)

    def unsubscribe(self, event: Any, callback: Any) -> None:
        callbacks = self.listeners.get(event, [])
        if callback in callbacks:
            callbacks.remove(callback)

    def publish(self, event: Any, **payload: str) -> None:
        for callback in tuple(self.listeners.get(event, [])):
            callback(**payload)


class _RecordedLabel:
    def __init__(self) -> None:
        self.configurations: list[dict[str, str]] = []

    def configure(self, **kwargs: str) -> None:
        self.configurations.append(kwargs)


def test_settings_theme_dispatch_updates_all_labels_and_destroy_unsubscribes(
    monkeypatch: Any,
) -> None:
    import src.ui.components.settings_panel as settings_module
    from src.core.enums.theme_event import ThemeEvent
    from src.ui.components.settings_panel import SettingsPanel
    from src.ui.visual_system import GlassFrame

    palette = SimpleNamespace(
        text="#111111",
        text_secondary="#222222",
        text_muted="#333333",
    )
    monkeypatch.setattr(settings_module, "resolve_palette", lambda _manager: palette)
    monkeypatch.setattr(GlassFrame.__mro__[1], "destroy", lambda _self: None, raising=False)

    panel = object.__new__(SettingsPanel)
    manager = _ThemeBus()
    labels = [_RecordedLabel() for _ in range(5)]
    panel._theme_manager = manager
    panel.theme_manager = manager
    panel._themed_labels = [
        (labels[0], "text"),
        (labels[1], "secondary"),
        (labels[2], "secondary"),
        (labels[3], "secondary"),
        (labels[4], "muted"),
    ]
    manager.subscribe(ThemeEvent.THEME_CHANGED, panel._on_theme_changed)

    manager.publish(ThemeEvent.THEME_CHANGED, appearance="light", color="rose")
    assert [label.configurations[-1]["text_color"] for label in labels] == [
        "#111111",
        "#222222",
        "#222222",
        "#222222",
        "#333333",
    ]

    manager.subscribe(ThemeEvent.THEME_CHANGED, panel._handle_visual_theme_changed)
    panel.destroy()
    assert manager.listeners[ThemeEvent.THEME_CHANGED] == []


class _FakePixels:
    def __init__(self) -> None:
        self.writes: list[tuple[Any, Any]] = []

    def __setitem__(self, key: Any, value: Any) -> None:
        self.writes.append((key, value))


class _FakeImage:
    def __init__(self, size: tuple[int, int]) -> None:
        self.size = size
        self.width, self.height = size
        self.pixels = _FakePixels()

    def load(self) -> _FakePixels:
        return self.pixels

    def resize(self, size: tuple[int, int], _resampling: Any) -> _FakeImage:
        return _FakeImage(size)

    def paste(self, *_args: Any) -> None:
        return None


class _FakeDraw:
    def rounded_rectangle(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_gradient_render_executes_pillow_pipeline_and_tk_schedule_on_main_thread(
    monkeypatch: Any,
) -> None:
    import src.ui.visual_system as visual_module
    from src.ui.visual_system import GradientBackdrop, GradientButton

    created_images: list[_FakeImage] = []
    photo_threads: list[int] = []

    def new_image(_mode: str, size: tuple[int, int], _color: Any = None) -> _FakeImage:
        image = _FakeImage(size)
        created_images.append(image)
        return image

    def make_photo(image: _FakeImage) -> object:
        photo_threads.append(threading.get_ident())
        assert image.size == (120, 36)
        return object()

    monkeypatch.setattr(
        visual_module,
        "Image",
        SimpleNamespace(
            new=new_image,
            Resampling=SimpleNamespace(BILINEAR="bilinear", LANCZOS="lanczos"),
        ),
    )
    monkeypatch.setattr(
        visual_module,
        "ImageDraw",
        SimpleNamespace(Draw=lambda _image: _FakeDraw()),
    )
    monkeypatch.setattr(
        visual_module,
        "ImageTk",
        SimpleNamespace(PhotoImage=make_photo),
    )
    monkeypatch.setattr(
        visual_module,
        "resolve_palette",
        lambda _manager: SimpleNamespace(
            accent="#AA0000",
            accent_end="#0000AA",
            disabled="#777777",
            text_muted="#888888",
            surface="#101010",
        ),
    )

    canvas_calls: list[str] = []
    button = SimpleNamespace(
        theme_manager=object(),
        _visual_state="normal",
        _state="normal",
        _radius=10,
        _photo=None,
        _image_item=None,
        _text_item=None,
        _text="Add download",
        winfo_exists=lambda: True,
        winfo_width=lambda: 120,
        winfo_height=lambda: 36,
        create_image=lambda *_args, **_kwargs: canvas_calls.append("image") or 1,
        create_text=lambda *_args, **_kwargs: canvas_calls.append("text") or 2,
        itemconfigure=lambda *_args, **_kwargs: None,
        coords=lambda *_args, **_kwargs: None,
        configure=lambda **_kwargs: None,
    )
    main_thread = threading.get_ident()
    GradientButton._render(button)
    assert len(created_images) == 3
    assert canvas_calls == ["image", "text"]
    assert photo_threads == [main_thread]

    scheduled: list[tuple[int, int, Any]] = []
    render_threads: list[int] = []

    def after(delay: int, callback: Any) -> str:
        scheduled.append((threading.get_ident(), delay, callback))
        return "redraw-1"

    backdrop = SimpleNamespace(
        _redraw_id=None,
        after=after,
        _render=lambda: render_threads.append(threading.get_ident()),
    )
    GradientBackdrop._schedule_redraw(backdrop)
    assert scheduled[0][:2] == (main_thread, 70)
    scheduled[0][2]()
    assert render_threads == [main_thread]
