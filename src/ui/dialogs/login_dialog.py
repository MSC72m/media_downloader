import customtkinter as ctk

from src.core.enums.message_level import MessageLevel
from src.core.interfaces import IErrorNotifier, IMessageQueue
from src.services.events.queue import Message
from src.utils.logger import get_logger
from src.utils.window import WindowCenterMixin

logger = get_logger(__name__)


class LoginDialog(ctk.CTkToplevel, WindowCenterMixin):
    def __init__(
        self,
        parent,
        error_handler: IErrorNotifier | None = None,
        message_queue: IMessageQueue | None = None,
    ):
        logger.info(f"[LOGIN_DIALOG] Initializing with parent: {parent}")
        super().__init__(parent)

        self.title("Instagram Login")
        self.geometry("400x250")
        self.resizable(False, False)

        # Make dialog modal
        self.transient(parent)
        logger.info("[LOGIN_DIALOG] Window properties set")

        self.username: str | None = None
        self.password: str | None = None
        self.error_handler = error_handler
        self.message_queue = message_queue

        # Create widgets FIRST
        logger.info("[LOGIN_DIALOG] Creating widgets")
        self.create_widgets()
        logger.info("[LOGIN_DIALOG] Widgets created")

        # Center the window
        logger.info("[LOGIN_DIALOG] Centering window")
        self.center_window()
        logger.info("[LOGIN_DIALOG] Window centered")

        # Update the window to ensure it's drawn
        self.update_idletasks()

        # Now make it visible and grab focus
        logger.info("[LOGIN_DIALOG] Making window visible and grabbing focus")
        self.grab_set()
        self.focus_set()
        logger.info("[LOGIN_DIALOG] Window should now be visible with focus")

        # Bind enter key
        self.bind("<Return>", lambda e: self.handle_login())
        logger.info("[LOGIN_DIALOG] Initialization complete")

    def create_widgets(self):
        # Username
        self.username_label = ctk.CTkLabel(self, text="Username:", font=("Roboto", 14))
        self.username_label.pack(pady=(20, 5))

        self.username_entry = ctk.CTkEntry(self, width=280, font=("Roboto", 14))
        self.username_entry.pack(pady=5)

        # Password
        self.password_label = ctk.CTkLabel(self, text="Password:", font=("Roboto", 14))
        self.password_label.pack(pady=(10, 5))

        self.password_entry = ctk.CTkEntry(self, width=280, show="*", font=("Roboto", 14))
        self.password_entry.pack(pady=5)

        # Login button
        self.login_button = ctk.CTkButton(
            self,
            text="Login",
            command=self.handle_login,
            width=200,
            font=("Roboto", 14),
        )
        self.login_button.pack(pady=20)

        # Set initial focus
        self.username_entry.focus()

    def handle_login(self):
        logger.info("[LOGIN_DIALOG] handle_login called")
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()

        logger.info(
            f"[LOGIN_DIALOG] Username: {self.username}, Password: {'*' * len(self.password) if self.password else 'empty'}"
        )

        if self.username and self.password:
            logger.info("[LOGIN_DIALOG] Credentials provided, closing dialog")
            self.destroy()
        else:
            logger.warning("[LOGIN_DIALOG] Missing credentials, showing error")
            error_msg = "Please enter both username and password"
            if self.error_handler:
                self.error_handler.show_error("Login Error", error_msg)
            elif self.message_queue:
                self.message_queue.add_message(
                    Message(text=error_msg, level=MessageLevel.ERROR, title="Login Error")
                )
