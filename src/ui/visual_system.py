"""Canonical visual system for the desktop UI.

Tk does not understand CSS rgba values and CTk's ``transparent`` color is not
real alpha compositing.  This module therefore keeps alpha in pure color math,
pre-composites glass colors against the active background, and only passes
``#RRGGBB`` values to Tk.  Real gradients are rendered by Pillow on one canvas;
all rendering and animation callbacks run on Tk's main thread via ``after``.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageTk

from src.core.enums.theme_event import ThemeEvent
from src.ui.utils.theme_manager import ThemeManager, get_theme_manager

HexColor = str


def _coerce_hex(value: Any, fallback: HexColor) -> HexColor:
    """Return a concrete ``#RRGGBB`` color safe for raw Tk options."""
    if isinstance(value, list | tuple):
        value = value[0] if value else fallback
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    if len(value) == 7 and value.startswith("#"):
        try:
            int(value[1:], 16)
        except ValueError:
            return fallback
        return value.upper()
    return fallback


def _rgb(color: HexColor) -> tuple[int, int, int]:
    color = _coerce_hex(color, "#000000")
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _hex(rgb: tuple[int, int, int]) -> HexColor:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def blend(foreground: HexColor, background: HexColor, alpha: float) -> HexColor:
    """Alpha composite ``foreground`` over ``background`` as opaque hex."""
    alpha = max(0.0, min(1.0, alpha))
    fg = _rgb(foreground)
    bg = _rgb(background)
    return _hex(tuple(round(f * alpha + b * (1.0 - alpha)) for f, b in zip(fg, bg, strict=True)))  # type: ignore[arg-type]


def lighten(color: HexColor, amount: float) -> HexColor:
    return blend("#FFFFFF", color, amount)


def darken(color: HexColor, amount: float) -> HexColor:
    return blend("#000000", color, amount)


@dataclass(frozen=True)
class Palette:
    appearance: Literal["dark", "light"]
    background_top: HexColor
    background_bottom: HexColor
    background_mid: HexColor
    surface: HexColor
    surface_raised: HexColor
    surface_hover: HexColor
    border: HexColor
    border_strong: HexColor
    text: HexColor
    text_secondary: HexColor
    text_muted: HexColor
    accent: HexColor
    accent_end: HexColor
    accent_hover: HexColor
    success: HexColor
    warning: HexColor
    error: HexColor
    progress_track: HexColor
    disabled: HexColor


def resolve_palette(theme_manager: ThemeManager) -> Palette:
    """Resolve the current CTk theme to one coherent desktop palette."""
    appearance = theme_manager.get_appearance().value.lower()
    is_dark = appearance != "light"
    theme = theme_manager.get_theme_json()
    accent = _coerce_hex(theme.get("CTkButton", {}).get("fg_color"), "#FF4F78")

    if is_dark:
        base = "#0E0F14"
        top = blend(accent, "#171820", 0.10)
        bottom = "#0B0C10"
        mid = blend(accent, base, 0.035)
        return Palette(
            appearance="dark",
            background_top=top,
            background_bottom=bottom,
            background_mid=mid,
            surface=blend("#FFFFFF", mid, 0.055),
            surface_raised=blend("#FFFFFF", mid, 0.085),
            surface_hover=blend("#FFFFFF", mid, 0.12),
            border=blend("#FFFFFF", mid, 0.10),
            border_strong=blend("#FFFFFF", mid, 0.16),
            text="#F5F6FA",
            text_secondary="#B4B7C3",
            text_muted="#747887",
            accent=accent,
            accent_end=lighten(accent, 0.25),
            accent_hover=lighten(accent, 0.12),
            success="#39D98A",
            warning="#F6B94A",
            error="#FF657A",
            progress_track=blend("#FFFFFF", mid, 0.10),
            disabled=blend("#FFFFFF", mid, 0.15),
        )

    base = "#F2F3F7"
    top = blend(accent, "#FAFAFC", 0.055)
    bottom = "#EDEEF3"
    mid = blend(accent, base, 0.018)
    return Palette(
        appearance="light",
        background_top=top,
        background_bottom=bottom,
        background_mid=mid,
        surface=blend("#FFFFFF", mid, 0.72),
        surface_raised=blend("#FFFFFF", mid, 0.90),
        surface_hover="#FFFFFF",
        border=blend("#1A1B22", mid, 0.10),
        border_strong=blend("#1A1B22", mid, 0.17),
        text="#181A22",
        text_secondary="#4D5160",
        text_muted="#858A98",
        accent=accent,
        accent_end=lighten(accent, 0.20),
        accent_hover=darken(accent, 0.07),
        success="#168F5B",
        warning="#B9760B",
        error="#D83B55",
        progress_track=blend("#1A1B22", mid, 0.10),
        disabled=blend("#1A1B22", mid, 0.14),
    )


def resolve_both_palettes(theme_manager: ThemeManager) -> tuple[Palette, Palette]:
    """Resolve both light and dark palettes for the current color theme.

    Returns (light_palette, dark_palette) tuple. Used for CTk widgets that need
    [light_color, dark_color] tuples to handle appearance mode switching.
    """
    # Build light palette
    theme = theme_manager.get_theme_json()
    accent = _coerce_hex(theme.get("CTkButton", {}).get("fg_color"), "#FF4F78")

    base_light = "#F2F3F7"
    mid_light = blend(accent, base_light, 0.018)
    light_palette = Palette(
        appearance="light",
        background_top=blend(accent, "#FAFAFC", 0.055),
        background_bottom="#EDEEF3",
        background_mid=mid_light,
        surface=blend("#FFFFFF", mid_light, 0.72),
        surface_raised=blend("#FFFFFF", mid_light, 0.90),
        surface_hover="#FFFFFF",
        border=blend("#1A1B22", mid_light, 0.10),
        border_strong=blend("#1A1B22", mid_light, 0.17),
        text="#181A22",
        text_secondary="#4D5160",
        text_muted="#858A98",
        accent=accent,
        accent_end=lighten(accent, 0.20),
        accent_hover=darken(accent, 0.07),
        success="#168F5B",
        warning="#B9760B",
        error="#D83B55",
        progress_track=blend("#1A1B22", mid_light, 0.10),
        disabled=blend("#1A1B22", mid_light, 0.14),
    )

    # Build dark palette
    base_dark = "#0E0F14"
    mid_dark = blend(accent, base_dark, 0.035)
    dark_palette = Palette(
        appearance="dark",
        background_top=blend(accent, "#171820", 0.10),
        background_bottom="#0B0C10",
        background_mid=mid_dark,
        surface=blend("#FFFFFF", mid_dark, 0.055),
        surface_raised=blend("#FFFFFF", mid_dark, 0.085),
        surface_hover=blend("#FFFFFF", mid_dark, 0.12),
        border=blend("#FFFFFF", mid_dark, 0.10),
        border_strong=blend("#FFFFFF", mid_dark, 0.16),
        text="#F5F6FA",
        text_secondary="#B4B7C3",
        text_muted="#747887",
        accent=accent,
        accent_end=lighten(accent, 0.25),
        accent_hover=lighten(accent, 0.12),
        success="#39D98A",
        warning="#F6B94A",
        error="#FF657A",
        progress_track=blend("#FFFFFF", mid_dark, 0.10),
        disabled=blend("#FFFFFF", mid_dark, 0.15),
    )

    return light_palette, dark_palette


if TYPE_CHECKING:
    _CanvasBase = tk.Canvas
else:
    _CanvasBase = getattr(tk, "Canvas", object)


class GradientBackdrop(_CanvasBase):
    """Single-canvas PIL gradient backdrop with debounced main-thread redraws."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        theme_manager: ThemeManager | None = None,
        **kwargs: Any,
    ) -> None:
        self.theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        palette = resolve_palette(self.theme_manager)
        super().__init__(
            master,
            bg=palette.background_mid,
            highlightthickness=0,
            borderwidth=0,
            **kwargs,
        )
        self._photo: ImageTk.PhotoImage | None = None
        self._image_item: int | None = None
        self._redraw_id: str | None = None
        self.bind("<Configure>", self._schedule_redraw, add=True)
        self.theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self._schedule_redraw()

    def _schedule_redraw(self, _event: tk.Event | None = None) -> None:
        if self._redraw_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._redraw_id)
        self._redraw_id = self.after(70, self._render)

    def _render(self) -> None:
        self._redraw_id = None
        if not self.winfo_exists():
            return
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        palette = resolve_palette(self.theme_manager)

        strip = Image.new("RGB", (1, height))
        pixels = strip.load()
        if pixels is None:  # pragma: no cover - Pillow always exposes RGB pixels
            return
        top = _rgb(palette.background_top)
        bottom = _rgb(palette.background_bottom)
        for y in range(height):
            t = y / max(1, height - 1)
            pixels[0, y] = tuple(round(a + (b - a) * t) for a, b in zip(top, bottom, strict=True))
        image = strip.resize((width, height), Image.Resampling.BILINEAR).convert("RGBA")

        # Two blurred light sources keep the surface alive without dominating it.
        blobs = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(blobs)
        radius = max(100, min(width, height) // 2)
        accent_rgb = _rgb(palette.accent)
        alpha = 24 if palette.appearance == "dark" else 13
        draw.ellipse(
            (width - radius, -radius // 2, width + radius // 2, radius),
            fill=(*accent_rgb, alpha),
        )
        cool = (72, 118, 255, 15 if palette.appearance == "dark" else 9)
        draw.ellipse(
            (-radius // 2, height - radius, radius, height + radius // 2),
            fill=cool,
        )
        blobs = blobs.filter(ImageFilter.GaussianBlur(max(50, radius // 3)))
        image = Image.alpha_composite(image, blobs)

        # Extremely subtle monochrome noise prevents large flat bands.
        noise = Image.effect_noise((max(2, width // 3), max(2, height // 3)), 7.0)
        noise = noise.resize((width, height), Image.Resampling.BILINEAR).convert("RGBA")
        noise.putalpha(4 if palette.appearance == "dark" else 3)
        image = Image.alpha_composite(image, noise)

        self._photo = ImageTk.PhotoImage(image)
        if self._image_item is None:
            self._image_item = self.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.itemconfigure(self._image_item, image=self._photo)
        self.tag_lower(self._image_item)
        self.configure(bg=palette.background_mid)

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._schedule_redraw()

    def destroy(self) -> None:
        if self._redraw_id is not None:
            with contextlib.suppress(tk.TclError):
                self.after_cancel(self._redraw_id)
        self.theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()


class GlassFrame(ctk.CTkFrame):
    """Opaque, correctly preblended glass fallback for CTk surfaces."""

    def __init__(
        self,
        master: Any,
        *,
        theme_manager: ThemeManager | None = None,
        elevation: Literal["base", "raised"] = "base",
        interactive: bool = False,
        **kwargs: Any,
    ) -> None:
        self.theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self.elevation = elevation
        self.interactive = interactive
        light_palette, dark_palette = resolve_both_palettes(self.theme_manager)
        kwargs.setdefault(
            "fg_color",
            [self._surface_color(light_palette), self._surface_color(dark_palette)],
        )
        kwargs.setdefault("border_color", [light_palette.border, dark_palette.border])
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 14)
        super().__init__(master, **kwargs)
        self.theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._handle_visual_theme_changed)
        if interactive:
            self.bind("<Enter>", self._on_enter, add=True)
            self.bind("<Leave>", self._on_leave, add=True)

    def _surface_color(self, palette: Palette) -> HexColor:
        return palette.surface_raised if self.elevation == "raised" else palette.surface

    def _apply_surface_palette(self, *, hover: bool = False) -> None:
        # Resolve both light and dark palettes so CTk can handle mode switching
        light_palette, dark_palette = resolve_both_palettes(self.theme_manager)

        light_surface = light_palette.surface_hover if hover else self._surface_color(light_palette)
        dark_surface = dark_palette.surface_hover if hover else self._surface_color(dark_palette)
        light_border = light_palette.border_strong if hover else light_palette.border
        dark_border = dark_palette.border_strong if hover else dark_palette.border

        # CTk requires [light_color, dark_color] tuples for proper mode switching
        self.configure(
            fg_color=[light_surface, dark_surface],
            border_color=[light_border, dark_border],
        )

    def _on_enter(self, _event: tk.Event | None = None) -> None:
        if self.interactive:
            self._apply_surface_palette(hover=True)

    def _on_leave(self, _event: tk.Event | None = None) -> None:
        self._apply_surface_palette()

    def _handle_visual_theme_changed(self, appearance: str, color: str) -> None:
        self._apply_surface_palette()

    def destroy(self) -> None:
        self.theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._handle_visual_theme_changed)
        super().destroy()


class GlassButton(ctk.CTkButton):
    """Compact theme-aware secondary/ghost button using only valid Tk colors."""

    def __init__(
        self,
        master: Any,
        *,
        theme_manager: ThemeManager | None = None,
        variant: Literal["secondary", "ghost", "danger"] = "secondary",
        **kwargs: Any,
    ) -> None:
        self.theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        self.variant = variant
        palette = resolve_palette(self.theme_manager)
        fg, hover, text = self._colors(palette)
        kwargs.setdefault("fg_color", fg)
        kwargs.setdefault("hover_color", hover)
        kwargs.setdefault("text_color", text)
        kwargs.setdefault("corner_radius", 10)
        kwargs.setdefault("border_width", 0)
        kwargs.setdefault("height", 34)
        kwargs.setdefault("font", ("Roboto", 12, "normal"))
        super().__init__(master, **kwargs)
        self.theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)

    def _colors(self, palette: Palette) -> tuple[HexColor | str, HexColor, HexColor]:
        if self.variant == "danger":
            return (
                blend(palette.error, palette.surface, 0.16),
                blend(palette.error, palette.surface, 0.25),
                palette.error,
            )
        if self.variant == "ghost":
            return "transparent", palette.surface_hover, palette.text_secondary
        return palette.surface_raised, palette.surface_hover, palette.text

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        palette = resolve_palette(self.theme_manager)
        fg, hover, text = self._colors(palette)
        self.configure(fg_color=fg, hover_color=hover, text_color=text)

    def destroy(self) -> None:
        self.theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()


class GradientButton(_CanvasBase):
    """Real PIL-gradient primary button with keyboard and pointer states."""

    def __init__(
        self,
        master: Any,
        *,
        text: str,
        command: Callable[[], None] | None = None,
        theme_manager: ThemeManager | None = None,
        width: int = 128,
        height: int = 40,
        corner_radius: int = 11,
        **kwargs: Any,
    ) -> None:
        self.theme_manager = theme_manager or get_theme_manager(master.winfo_toplevel())
        palette = resolve_palette(self.theme_manager)
        super().__init__(
            master,
            width=width,
            height=height,
            bg=palette.surface,
            highlightthickness=0,
            borderwidth=0,
            takefocus=1,
            **kwargs,
        )
        self._text = text
        self._command = command
        self._state = "normal"
        self._visual_state: Literal["normal", "hover", "pressed"] = "normal"
        self._photo: ImageTk.PhotoImage | None = None
        self._image_item: int | None = None
        self._text_item: int | None = None
        self._radius = corner_radius
        self.bind("<Configure>", lambda _e: self._render(), add=True)
        self.bind("<Enter>", self._enter, add=True)
        self.bind("<Leave>", self._leave, add=True)
        self.bind("<ButtonPress-1>", self._press, add=True)
        self.bind("<ButtonRelease-1>", self._release, add=True)
        self.bind("<Return>", self._keyboard_activate, add=True)
        self.bind("<space>", self._keyboard_activate, add=True)
        self.theme_manager.subscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        self.after_idle(self._render)

    def _render(self) -> None:
        if not self.winfo_exists():
            return
        width = max(2, self.winfo_width())
        height = max(2, self.winfo_height())
        palette = resolve_palette(self.theme_manager)
        start = palette.accent
        end = palette.accent_end
        if self._visual_state == "hover":
            start, end = lighten(start, 0.10), lighten(end, 0.08)
        elif self._visual_state == "pressed":
            start, end = darken(start, 0.10), darken(end, 0.10)
        if self._state == "disabled":
            start = end = palette.disabled

        scale = 2
        image = Image.new("RGBA", (width * scale, height * scale), (0, 0, 0, 0))
        gradient = Image.new("RGB", (width * scale, 1))
        px = gradient.load()
        if px is None:  # pragma: no cover - Pillow always exposes RGB pixels
            return
        a, b = _rgb(start), _rgb(end)
        for x in range(width * scale):
            t = x / max(1, width * scale - 1)
            px[x, 0] = tuple(round(c1 + (c2 - c1) * t) for c1, c2 in zip(a, b, strict=True))
        gradient = gradient.resize((width * scale, height * scale), Image.Resampling.BILINEAR)
        mask = Image.new("L", image.size, 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            (0, 0, image.width - 1, image.height - 1),
            radius=self._radius * scale,
            fill=255,
        )
        image.paste(gradient, (0, 0), mask)
        image = image.resize((width, height), Image.Resampling.LANCZOS)
        self._photo = ImageTk.PhotoImage(image)
        if self._image_item is None:
            self._image_item = self.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.itemconfigure(self._image_item, image=self._photo)
        text_color = "#FFFFFF" if self._state != "disabled" else palette.text_muted
        if self._text_item is None:
            self._text_item = self.create_text(
                width // 2,
                height // 2,
                text=self._text,
                fill=text_color,
                font=("Roboto", 12, "bold"),
            )
        else:
            self.coords(self._text_item, width // 2, height // 2)
            self.itemconfigure(self._text_item, text=self._text, fill=text_color)
        self.configure(bg=palette.surface)

    def _enter(self, _event: tk.Event | None = None) -> None:
        if self._state == "normal":
            self._visual_state = "hover"
            self.configure(cursor="pointinghand")
            self._render()

    def _leave(self, _event: tk.Event | None = None) -> None:
        self._visual_state = "normal"
        self.configure(cursor="")
        self._render()

    def _press(self, _event: tk.Event | None = None) -> None:
        if self._state == "normal":
            self.focus_set()
            self._visual_state = "pressed"
            self._render()

    def _release(self, event: tk.Event | None = None) -> None:
        if self._state != "normal":
            return
        inside = event is None or (
            0 <= event.x <= self.winfo_width() and 0 <= event.y <= self.winfo_height()
        )
        self._visual_state = "hover" if inside else "normal"
        self._render()
        if inside and self._command:
            self._command()

    def _keyboard_activate(self, _event: tk.Event | None = None) -> str:
        if self._state == "normal" and self._command:
            self._command()
        return "break"

    def configure(self, cnf: Any = None, **kwargs: Any) -> Any:
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "state" in kwargs:
            self._state = kwargs.pop("state")
            if hasattr(self, "_photo"):
                self._render()
        if "text" in kwargs:
            self._text = kwargs.pop("text")
            if hasattr(self, "_photo"):
                self._render()
        return super().configure(cnf, **kwargs)

    config = configure

    def cget(self, key: str) -> Any:
        if key == "state":
            return self._state
        if key == "text":
            return self._text
        return super().cget(key)

    def _on_theme_changed(self, appearance: str, color: str) -> None:
        self._render()

    def destroy(self) -> None:
        self.theme_manager.unsubscribe(ThemeEvent.THEME_CHANGED, self._on_theme_changed)
        super().destroy()
