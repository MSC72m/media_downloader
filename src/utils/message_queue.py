import queue
import threading
import tkinter as tk
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class MessageType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    INFO = "info"


@dataclass
class Message:
    type: MessageType
    text: str
    title: Optional[str] = None


class MessageQueue:
    def __init__(self, root: tk.Tk):
        self.queue = queue.Queue()
        self.root = root
        self.processing = False
        self._start_processing()

    def _start_processing(self):
        """Start processing messages in the queue."""
        if self.processing:
            return

        def process_messages():
            try:
                while True:
                    # Check for messages without blocking
                    try:
                        msg = self.queue.get_nowait()
                        self._show_message(msg)
                        self.queue.task_done()
                    except queue.Empty:
                        break
            finally:
                self.processing = False

            # Schedule next check if there are messages
            if not self.queue.empty():
                self.processing = True
                self.root.after(100, process_messages)

        self.processing = True
        self.root.after(100, process_messages)

    def add_message(self, message: Message):
        """Add a message to the queue."""
        self.queue.put(message)
        if not self.processing:
            self._start_processing()

    @staticmethod
    def _show_message(message: Message):
        """Show the message dialog."""
        from tkinter import messagebox

        if message.type == MessageType.ERROR:
            messagebox.showerror(message.title or "Error", message.text)
        elif message.type == MessageType.SUCCESS:
            messagebox.showinfo(message.title or "Success", message.text)
        else:
            messagebox.showinfo(message.title or "Information", message.text)