from tkinter import messagebox

import customtkinter as ctk

from src.utils.window import WindowCenterMixin


class LoginDialog(ctk.CTkToplevel, WindowCenterMixin):
    def __init__(self, parent):
        super().__init__(parent)

        self.title("Instagram Login")
        self.geometry("400x250")
        self.resizable(False, False)

        # Make window visible and on top
        self.transient(parent)
        self.attributes("-topmost", True)

        self.username: str | None = None
        self.password: str | None = None

        # Create widgets
        self.create_widgets()

        # Center the window
        self.center_window()

        # Force window to be visible
        self.deiconify()
        self.lift()
        self.focus_force()

        # Grab focus after window is visible
        self.after(50, self.grab_set)
        self.after(100, lambda: self.attributes("-topmost", False))

        # Bind enter key
        self.bind("<Return>", lambda e: self.handle_login())

    def create_widgets(self):
        # Username
        self.username_label = ctk.CTkLabel(self, text="Username:", font=("Roboto", 14))
        self.username_label.pack(pady=(20, 5))

        self.username_entry = ctk.CTkEntry(self, width=280, font=("Roboto", 14))
        self.username_entry.pack(pady=5)

        # Password
        self.password_label = ctk.CTkLabel(self, text="Password:", font=("Roboto", 14))
        self.password_label.pack(pady=(10, 5))

        self.password_entry = ctk.CTkEntry(
            self, width=280, show="*", font=("Roboto", 14)
        )
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
        self.username = self.username_entry.get().strip()
        self.password = self.password_entry.get().strip()

        if self.username and self.password:
            self.destroy()
        else:
            messagebox.showerror(
                "Error", "Please enter both username and password", parent=self
            )
