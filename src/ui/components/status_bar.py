import queue
import re
import threading
import time

import customtkinter as ctk

from src.core.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class StatusBar(ctk.CTkFrame):
    """Status bar showing download progress and information - thread-safe via queue."""

    # Compiled regex patterns for efficient matching (more efficient than string 'in' checks)
    _SUCCESS_MESSAGE_PATTERN = re.compile(r"Download completed", re.IGNORECASE)
    _CONNECTION_CONFIRMED_PATTERN = re.compile(r"Connection confirmed", re.IGNORECASE)

    def __init__(self, master):
        super().__init__(master, fg_color="transparent")

        # Get root window for scheduling
        self._root_window = self._get_root_window()
        self._update_queue = queue.Queue()
        self._message_queue = queue.Queue()  # Queue for pending messages
        self._running = True
        self._current_message: str | None = None
        self._message_timeout: float | None = None
        self._is_error_message: bool = False  # Track if current message is an error
        self._config = get_config()

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Create center frame for alignment
        self.center_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.center_frame.grid(row=0, column=0, sticky="ew")
        self.center_frame.grid_columnconfigure(0, weight=1)

        # Status label - start empty, will be updated by connectivity check
        self.status_label = ctk.CTkLabel(
            self.center_frame, text="Initializing...", font=("Roboto", 12)
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
        # Start processing messages with timeout
        self._process_messages()

    def _get_root_window(self):
        """Get the root Tk window for scheduling."""
        try:
            # Try to get the actual root window
            return self.winfo_toplevel()
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
        """Show status message - thread-safe via queue with timeout."""
        self._add_message(message)

    def show_error(self, message: str):
        """Show error message - thread-safe via queue with longer timeout."""
        error_text = f"Error: {message}"
        self._add_message(error_text, is_error=True)

    def show_warning(self, message: str):
        """Show warning message - thread-safe via queue with timeout."""
        warning_text = f"Warning: {message}"
        self._add_message(warning_text)

    def _add_message(self, message: str, is_error: bool = False) -> None:
        """Add message to queue and show immediately if no current message.

        Args:
            message: Message text to display
            is_error: Whether this is an error message (uses longer timeout)
        """
        def _update():
            try:
                # Check if this is a success message that should interrupt current message
                # Use compiled regex patterns for efficient matching
                is_success_message = bool(self._SUCCESS_MESSAGE_PATTERN.search(message))
                is_connection_confirmed = bool(self._CONNECTION_CONFIRMED_PATTERN.search(message))
                
                # Track if connection confirmed was shown (to prevent immediate "Ready")
                if is_connection_confirmed:
                    self._connection_confirmed_shown = True
                
                # If no current message, show immediately
                if not self._current_message:
                    self._current_message = message
                    self._is_error_message = is_error
                    current_time = time.time()
                    # Use longer timeout for error messages
                    timeout_seconds = (
                        self._config.ui.error_message_timeout_seconds
                        if is_error
                        else self._config.ui.message_timeout_seconds
                    )
                    self._message_timeout = current_time + timeout_seconds
                    self.status_label.configure(text=message)
                    return
                
                # For success messages, interrupt current message to show success
                if is_success_message:
                    self._current_message = message
                    self._is_error_message = is_error
                    current_time = time.time()
                    timeout_seconds = self._config.ui.message_timeout_seconds
                    self._message_timeout = current_time + timeout_seconds
                    self.status_label.configure(text=message)
                    return
                
                # Add to queue for later (will show after current message times out)
                self._message_queue.put((message, is_error))
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error adding message: {e}", exc_info=True)

        self._queue_update(_update)

    def _process_messages(self):
        """Process message queue with timeout handling."""
        if not self._running:
            return

        try:
            current_time = time.time()

            # Check if current message has timed out
            if self._current_message and self._message_timeout:
                if current_time >= self._message_timeout:
                    # Timeout reached - clear current message
                    self._current_message = None
                    self._message_timeout = None
                    self._is_error_message = False

            # If no current message, get next from queue
            if not self._current_message and not self._message_queue.empty():
                try:
                    message_data = self._message_queue.get_nowait()
                    # Handle both old format (string) and new format (tuple)
                    if isinstance(message_data, tuple):
                        self._current_message, self._is_error_message = message_data
                    else:
                        # Backward compatibility with old string format
                        self._current_message = message_data
                        self._is_error_message = False
                    
                    # Use longer timeout for error messages
                    if self._is_error_message:
                        timeout_seconds = self._config.ui.error_message_timeout_seconds
                    else:
                        timeout_seconds = self._config.ui.message_timeout_seconds
                    
                    self._message_timeout = current_time + timeout_seconds
                    # Display the message
                    self.status_label.configure(text=self._current_message)
                except queue.Empty:
                    pass

            # If still no message, show "Ready" (default state)
            # After "Connection confirmed" times out, show "Ready"
            if not self._current_message:
                self.status_label.configure(text="Ready")
                # Reset connection confirmed flag when showing Ready
                if hasattr(self, '_connection_confirmed_shown'):
                    self._connection_confirmed_shown = False

        except Exception as e:
            logger.error(f"[STATUS_BAR] Error processing messages: {e}", exc_info=True)

        # Schedule next check (check every 100ms for timeout)
        if self._running and self._root_window:
            try:
                self._root_window.after(100, self._process_messages)
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error scheduling message check: {e}")

    def update_progress(self, progress: float):
        """Update progress display - thread-safe via queue."""

        def _update():
            try:
                self.progress_bar.set(progress / 100)
                if progress >= 100:
                    self.status_label.configure(text="Download Complete")
                else:
                    self.status_label.configure(text=f"Downloading... {progress:.1f}%")
            except Exception as e:
                logger.error(
                    f"[STATUS_BAR] Error updating progress: {e}", exc_info=True
                )

        self._queue_update(_update)

    def reset(self):
        """Reset status bar to initial state - thread-safe via queue."""

        def _update():
            try:
                self.progress_bar.set(0)
                self.status_label.configure(text="Ready")
            except Exception as e:
                logger.error(f"[STATUS_BAR] Error resetting: {e}", exc_info=True)

        self._queue_update(_update)

    def destroy(self):
        """Clean up resources."""
        self._running = False
        super().destroy()
