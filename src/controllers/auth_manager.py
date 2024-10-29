import threading
import logging
from typing import Callable, Optional
import tkinter as tk

from src.downloaders.instagram import InstagramDownloader

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages authentication states and processes."""

    def __init__(self):
        self.instagram_authenticated = False
        self.auth_lock = threading.Lock()
        self.instagram_downloader = InstagramDownloader()  # Initialize the downloader

    def authenticate_instagram(
        self,
        parent_window: tk.Tk,
        callback: Callable[[bool], None]
    ) -> None:
        """Handle Instagram authentication process."""
        try:
            from src.ui.dialogs.login_dialog import LoginDialog
            dialog = LoginDialog(parent_window)
            parent_window.wait_window(dialog)

            if dialog.username and dialog.password:
                def auth_worker():
                    try:
                        success = self.instagram_downloader.authenticate(
                            username=dialog.username,
                            password=dialog.password
                        )
                        with self.auth_lock:
                            self.instagram_authenticated = success
                        parent_window.after(0, lambda: callback(success))
                    except Exception as e:
                        logger.error(f"Authentication error: {str(e)}")
                        parent_window.after(0, lambda: callback(False))

                threading.Thread(
                    target=auth_worker,
                    daemon=True
                ).start()
            else:
                callback(False)
        except Exception as e:
            logger.error(f"Dialog error: {str(e)}")
            callback(False)

    def get_instagram_downloader(self) -> Optional[InstagramDownloader]:
        """Get the authenticated Instagram downloader instance."""
        with self.auth_lock:
            if self.instagram_authenticated:
                return self.instagram_downloader
            return None

    def is_instagram_authenticated(self) -> bool:
        """Check if Instagram is authenticated."""
        with self.auth_lock:
            return self.instagram_authenticated

    def cleanup(self) -> None:
        """Clean up authentication states."""
        with self.auth_lock:
            self.instagram_authenticated = False
            self.instagram_downloader = InstagramDownloader()