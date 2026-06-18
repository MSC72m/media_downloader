import customtkinter as ctk

from src.utils.window import WindowCenterMixin


class CenteredInputDialog(ctk.CTkInputDialog, WindowCenterMixin):
    def __init__(self, title: str, text: str, initial_value: str | None = None) -> None:
        # CTkInputDialog builds its entry asynchronously via after(10, _create_widgets),
        # so the entry widget does not exist yet during __init__. Store the desired
        # initial text and apply it once the entry is actually created.
        self._initial_value = initial_value
        super().__init__(text=text, title=title)
        self.center_window()

    def _create_widgets(self) -> None:
        super()._create_widgets()
        if self._initial_value:
            self._entry.delete(0, "end")
            self._entry.insert(0, self._initial_value)
