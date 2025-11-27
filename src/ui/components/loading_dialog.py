"""Centralized loading dialog component with animated dots for all platforms."""

import customtkinter as ctk

from ...core.config import get_config
from ...utils.window import WindowCenterMixin
from ...utils.logger import get_logger

logger = get_logger(__name__)


class LoadingDialog(ctk.CTkToplevel, WindowCenterMixin):
    """Centralized loading dialog with cycling animated dots.
    
    Used by YouTube, Instagram, and other platforms for showing loading states.
    Features:
    - Customizable message text
    - Configurable timeout
    - Cycling dot animation (deletes old dots after max)
    - Automatic cleanup in finally blocks
    """

    def __init__(
        self,
        parent,
        message: str = "Loading",
        timeout: int = 90,
        max_dots: int = 3,
        dot_animation_interval: int = 500,
        **kwargs
    ):
        """Initialize loading dialog.
        
        Args:
            parent: Parent window
            message: Loading message text (customizable)
            timeout: Timeout in seconds before auto-closing
            max_dots: Maximum number of dots before cycling (default: 3)
            dot_animation_interval: Milliseconds between dot updates (default: 500)
        """
        super().__init__(parent, **kwargs)

        self.message = message
        self.timeout = timeout
        self.max_dots = max_dots
        self.dot_animation_interval = dot_animation_interval
        self.dot_count = 0
        self.is_running = False
        self._timeout_id = None
        self._animation_id = None

        # Configure window
        self.title("Loading")
        self.geometry("300x100")
        self.resizable(False, False)
        self.overrideredirect(False)
        self.transient(parent)

        # Create content
        self._create_content()

        # Center the window
        self.center_window()

        # Update to ensure window is drawn
        self.update_idletasks()

        # Make visible and grab focus
        self.grab_set()
        self.focus_set()

        # Start animation
        self.start_animation()

        # Set timeout
        if timeout > 0:
            self._timeout_id = self.after(timeout * 1000, self._timeout)

    def _create_content(self):
        """Create the loading dialog content."""
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(expand=True, fill="both", padx=20, pady=20)

        self.message_label = ctk.CTkLabel(
            main_frame,
            text=self.message,
            font=("Roboto", 14),
            text_color=("gray10", "gray90"),
        )
        self.message_label.pack(expand=True)

    def start_animation(self):
        """Start the dot animation."""
        if self.is_running:
            return
        
        self.is_running = True
        self._animate_dots()

    def _animate_dots(self):
        """Animate dots with cycling behavior."""
        if not self.is_running:
            return

        # Cycle dots: increment until max, then reset to 1
        self.dot_count = (self.dot_count % self.max_dots) + 1

        # Create dots string
        dots = "." * self.dot_count
        self.message_label.configure(text=f"{self.message}{dots}")

        # Schedule next frame
        self._animation_id = self.after(self.dot_animation_interval, self._animate_dots)

    def stop_animation(self):
        """Stop the animation."""
        self.is_running = False
        
        # Cancel scheduled animations
        if self._animation_id:
            try:
                self.after_cancel(self._animation_id)
            except Exception:
                pass
            self._animation_id = None

    def _timeout(self):
        """Handle timeout."""
        logger.info("[LOADING_DIALOG] Timeout reached, closing dialog")
        self.close()

    def close(self):
        """Close the dialog with proper cleanup."""
        logger.debug("[LOADING_DIALOG] close() called")
        self.stop_animation()
        
        # Cancel timeout if still pending
        if self._timeout_id:
            try:
                self.after_cancel(self._timeout_id)
            except Exception:
                pass
            self._timeout_id = None
        
        # Release grab and destroy in finally block
        try:
            self._release_grab()
        finally:
            try:
                self.destroy()
            except Exception as e:
                logger.error(f"[LOADING_DIALOG] Error in destroy(): {e}", exc_info=True)

    def _release_grab(self):
        """Release window grab if active."""
        try:
            if hasattr(self, 'grab_current') and self.grab_current():
                self.grab_release()
                logger.debug("[LOADING_DIALOG] Grab released")
        except Exception as e:
            logger.debug(f"[LOADING_DIALOG] Error releasing grab: {e}")

    def destroy(self):
        """Clean up the dialog with proper resource management."""
        logger.debug("[LOADING_DIALOG] destroy() called")
        
        # Ensure cleanup happens in finally block
        try:
            self.stop_animation()
        finally:
            try:
                self._release_grab()
            finally:
                try:
                    super().destroy()
                except Exception as e:
                    logger.error(f"[LOADING_DIALOG] Error in super().destroy(): {e}", exc_info=True)

