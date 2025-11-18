import queue
import threading

import customtkinter as ctk

from src.utils.logger import get_logger

logger = get_logger(__name__)


class StatusBar(ctk.CTkFrame):
    """Status bar showing download progress and information - truly thread-safe via queue."""

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Get root window for scheduling
        self._root_window = self._get_root_window()
        self._update_queue = queue.Queue()
        self._running = True

        logger.info(f"[STATUS_BAR] Initialized with root: {self._root_window}")

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create center frame for alignment
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0, sticky="ew")
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            self.center_frame, text="Ready", font=("Roboto", 12)
        )
        self.status_label.grid(row=0, column=0, pady=(5, 5))

        # Progress bar with increased width
        self.progress_bar = ctk.CTkProgressBar(
            self.center_frame,
            height=15,
            width=400,
        )
        self.progress_bar.grid(row=1, column=0, sticky="ew", pady=(0, 10), padx=20)
        self.progress_bar.set(0)

        # Start processing updates from queue
        self._process_queue()

    def _get_root_window(self):
        """Get the root Tk window for scheduling."""
        try:
            widget = self
            while widget:
                master = getattr(widget, "master", None)
                if master is None:
                    return widget
                widget = master
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error getting root window: {e}")
        return self

    def _process_queue(self):
        """Process queued UI updates on main thread."""
        if not self._running:
            return

        try:
            # Process all pending updates
            while not self._update_queue.empty():
                try:
                    update_func = self._update_queue.get_nowait()
                    update_func()
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(
                        f"[STATUS_BAR] Error processing update: {e}", exc_info=True
                    )
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error in _process_queue: {e}", exc_info=True)

        # Schedule next queue check
        if self._running and self._root_window:
            try:
                self._root_window.after(50, self._process_queue)
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error scheduling next queue check: {e}")

    def _queue_update(self, update_func):
        """Queue an update to be processed on main thread."""
        try:
            self._update_queue.put(update_func)
        except Exception as e:
            logger.error(f"[STATUS_BAR] Error queuing update: {e}", exc_info=True)

    def show_message(self, message: str):
        """Show status message - thread-safe via queue."""
        logger.info(
            f"[STATUS_BAR] show_message: '{message}', thread={threading.current_thread().name}"
        )

        def _update():
            try:
                self.status_label.configure(text=message)
                logger.info(f"[STATUS_BAR] Message updated to: '{message}'")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error updating message: {e}", exc_info=True)

        self._queue_update(_update)

    def show_error(self, message: str):
        """Show error message - thread-safe via queue."""
        error_text = f"Error: {message}"
        logger.info(
            f"[STATUS_BAR] show_error: '{message}', thread={threading.current_thread().name}"
        )

        def _update():
            try:
                self.status_label.configure(text=error_text)
                logger.info(f"[STATUS_BAR] Error updated to: '{error_text}'")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error updating error: {e}", exc_info=True)

        self._queue_update(_update)

    def show_warning(self, message: str):
        """Show warning message - thread-safe via queue."""
        warning_text = f"Warning: {message}"
        logger.info(
            f"[STATUS_BAR] show_warning: '{message}', thread={threading.current_thread().name}"
        )

        def _update():
            try:
                self.status_label.configure(text=warning_text)
                logger.info(f"[STATUS_BAR] Warning updated to: '{warning_text}'")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error updating warning: {e}", exc_info=True)

        self._queue_update(_update)

    def update_progress(self, progress: float):
        """Update progress display - thread-safe via queue."""
        logger.info(
            f"[STATUS_BAR] update_progress: {progress}%, thread={threading.current_thread().name}"
        )

        def _update():
            try:
                self.progress_bar.set(progress / 100)
                if progress >= 100:
                    self.status_label.configure(text="Download Complete")
                else:
                    self.status_label.configure(text=f"Downloading... {progress:.1f}%")
                logger.info(f"[STATUS_BAR] Progress updated to: {progress}%")
            except Exception as e:
                logger.error(
                    f"[STATUS_BAR] Error updating progress: {e}", exc_info=True
                )

        self._queue_update(_update)

    def reset(self):
        """Reset status bar to initial state - thread-safe via queue."""
        logger.info(f"[STATUS_BAR] reset, thread={threading.current_thread().name}")

        def _update():
            try:
                self.progress_bar.set(0)
                self.status_label.configure(text="Ready")
                logger.info("[STATUS_BAR] Status bar reset to Ready")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error resetting: {e}", exc_info=True)

        self._queue_update(_update)

    def destroy(self):
        """Clean up resources."""
        self._running = False
        super().destroy()
