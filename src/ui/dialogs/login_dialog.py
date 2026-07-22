from typing import Any

import customtkinter as ctk

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.events.queue import Message
from src.ui import tokens
from src.ui.utils.theme_manager import ThemeManager
from src.ui.visual_system import GlassFrame, GradientButton, resolve_palette
from src.utils.logger import get_logger

from .base_dialog import BaseDialog

logger = get_logger(__name__)


class LoginDialog(BaseDialog):
    def __init__(
        self,
        parent: Any,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
        theme_manager: ThemeManager | None = None,
    ) -> None:
        logger.info(f"[LOGIN_DIALOG] Initializing with parent: {parent}")
        super().__init__(parent, title="Instagram Login", theme_manager=theme_manager)

        self.username: str | None = None
        self.password: str | None = None
        self.error_handler = error_handler
        self.message_queue = message_queue

        self.create_widgets()
        self.bind("<Return>", lambda _event: self.handle_login())
        self._finalize_init(
            preferred_width=400,
            preferred_height=300,
            min_width=360,
            min_height=280,
            modal=True,
        )
        self.username_entry.focus_set()
        logger.info("[LOGIN_DIALOG] Initialization complete")

    def create_widgets(self) -> None:
        palette = resolve_palette(self._theme_manager)
        self.form_frame = GlassFrame(
            self.content_parent,
            theme_manager=self._theme_manager,
            elevation="raised",
        )
        self.form_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.form_frame.grid_columnconfigure(0, weight=1)

        self.username_label = ctk.CTkLabel(
            self.form_frame,
            text="Username",
            font=tokens.font("body", weight="bold"),
            text_color=palette.text,
            anchor="w",
        )
        self.username_label.grid(row=0, column=0, sticky="ew", padx=24, pady=(20, 6))

        self.username_entry = ctk.CTkEntry(
            self.form_frame,
            height=tokens.CONTROL_H_LG,
            font=tokens.font("body"),
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )
        self.username_entry.grid(row=1, column=0, sticky="ew", padx=24)

        self.password_label = ctk.CTkLabel(
            self.form_frame,
            text="Password",
            font=tokens.font("body", weight="bold"),
            text_color=palette.text,
            anchor="w",
        )
        self.password_label.grid(row=2, column=0, sticky="ew", padx=24, pady=(14, 6))

        self.password_entry = ctk.CTkEntry(
            self.form_frame,
            height=tokens.CONTROL_H_LG,
            show="*",
            font=tokens.font("body"),
            fg_color=palette.surface,
            border_color=palette.border_strong,
            text_color=palette.text,
        )
        self.password_entry.grid(row=3, column=0, sticky="ew", padx=24)

        self.login_button = GradientButton(
            self.form_frame,
            text="Login",
            command=self.handle_login,
            theme_manager=self._theme_manager,
            height=tokens.CONTROL_H_LG,
        )
        self.login_button.grid(row=4, column=0, sticky="ew", padx=24, pady=20)

    def handle_login(self) -> None:
        logger.info("[LOGIN_DIALOG] handle_login called")
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()

        logger.info(
            "[LOGIN_DIALOG] Username: %s, Password: %s",
            self.username,
            "*" * len(self.password) if self.password else "empty",
        )

        if self.username and self.password:
            logger.info("[LOGIN_DIALOG] Credentials provided, closing dialog")
            self.destroy()
            return

        logger.warning("[LOGIN_DIALOG] Missing credentials, showing error")
        error_msg = "Please enter both username and password"
        if self.error_handler:
            self.error_handler.show_error("Login Error", error_msg)
        elif self.message_queue:
            self.message_queue.add_message(
                Message(text=error_msg, level=MessageLevel.ERROR, title="Login Error")
            )

    def _on_theme_changed(self, _appearance: str, _color: str) -> None:
        palette = resolve_palette(self._theme_manager)
        self.username_label.configure(text_color=palette.text)
        self.password_label.configure(text_color=palette.text)
        for entry in (self.username_entry, self.password_entry):
            entry.configure(
                fg_color=palette.surface,
                border_color=palette.border_strong,
                text_color=palette.text,
            )
