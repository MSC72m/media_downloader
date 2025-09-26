import customtkinter as ctk
from src.utils.window import WindowCenterMixin

class CenteredInputDialog(ctk.CTkInputDialog, WindowCenterMixin):
    def __init__(self, title: str, text: str):
        super().__init__(text=text, title=title)
        self.center_window()