from collections.abc import Callable
from typing import Any

from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassButton, GlassFrame, GradientButton


class FileManagerButtonBar(GlassFrame):
    """Glass action bar containing file-manager controls."""

    def __init__(
        self,
        master: Any,
        on_change_dir: Callable[[], None],
        on_create_folder: Callable[[], None],
        on_cancel: Callable[[], None],
        theme_manager: ThemeManager | None = None,
    ) -> None:
        super().__init__(
            master,
            theme_manager=theme_manager,
            corner_radius=tokens.RADIUS_MD,
        )
        self.grid_columnconfigure((0, 1, 2), weight=1)

        self.change_dir_button = GradientButton(
            self,
            text="Set as Download Directory",
            command=on_change_dir,
            theme_manager=self.theme_manager,
            height=tokens.CONTROL_H_LG,
        )
        self.change_dir_button.grid(row=0, column=0, padx=(10, 5), pady=10, sticky="ew")

        self.create_folder_button = GlassButton(
            self,
            text="Create Folder",
            command=on_create_folder,
            theme_manager=self.theme_manager,
            variant="secondary",
            height=tokens.CONTROL_H_LG,
        )
        self.create_folder_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")

        self.cancel_button = GlassButton(
            self,
            text="Cancel",
            command=on_cancel,
            theme_manager=self.theme_manager,
            variant="ghost",
            height=tokens.CONTROL_H_LG,
        )
        self.cancel_button.grid(row=0, column=2, padx=(5, 10), pady=10, sticky="ew")
