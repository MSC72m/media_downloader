import os
import sys
import queue
import logging
import threading
from typing import Optional
from urllib.parse import urlparse

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.downloaders.youtube import download_youtube_video
from src.downloaders.twitter import download_twitter_media
from src.downloaders.instagram import download_instagram_media, authenticate_instagram
from src.downloaders.pinterest import download_pinterest_image

# Configure logging
logging.basicConfig(
    filename='media_downloader.log',
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class PasswordDialog(ctk.CTkToplevel):
    def __init__(self, parent: ctk.CTk, title: str = "Password Entry", message: str = "Enter your password:"):
        super().__init__(parent)

        self.password: Optional[str] = None
        self.title(title)
        self.geometry("400x150")
        self.configure(bg="#2a2d2e")
        self.resizable(False, False)

        # Wait for the window to be ready before setting grab
        self.update_idletasks()
        self.center_window(parent)

        self.label = ctk.CTkLabel(self, text=message, font=("Roboto", 14))
        self.label.pack(pady=10)

        self.password_entry = ctk.CTkEntry(self, show="*", font=("Roboto", 15), width=280)
        self.password_entry.pack(pady=5)
        self.password_entry.bind("<Return>", lambda event: self.on_ok())

        self.ok_button = ctk.CTkButton(self, text="OK", command=self.on_ok)
        self.ok_button.pack(pady=10)

        # Set focus and grab after window is ready
        self.after(100, self._set_focus_and_grab)

        # Handle window close button
        self.protocol("WM_DELETE_WINDOW", self.on_cancel)

    def _set_focus_and_grab(self):
        """Set focus and grab after ensuring window is ready."""
        self.password_entry.focus_force()
        self.grab_set()

    def center_window(self, parent: ctk.CTk):
        """Center the dialog relative to parent window."""
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        dialog_width = 400
        dialog_height = 150

        new_x = parent_x + (parent_width // 2) - (dialog_width // 2)
        new_y = parent_y + (parent_height // 2) - (dialog_height // 2)

        self.geometry(f"{dialog_width}x{dialog_height}+{new_x}+{new_y}")

    def on_ok(self):
        """Handle OK button click."""
        self.password = self.password_entry.get()
        self.grab_release()
        self.destroy()

    def on_cancel(self):
        """Handle dialog cancellation."""
        self.password = None
        self.grab_release()
        self.destroy()


class DownloadItem:
    """Represents a single download item with its properties."""

    def __init__(self, name: str, url: str, status: str = "Pending"):
        self.name = name
        self.url = url
        self.status = status

class MediaDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Media Downloader")
        self.geometry("1000x700")
        self.configure_grid()
        self.setup_ui()

        self.download_queue = queue.Queue()
        self.download_items = []
        self.instagram_authenticated = False

        # Initialize downloads folder
        self.downloads_folder = os.path.expanduser("~/Downloads")
        os.makedirs(self.downloads_folder, exist_ok=True)

    def configure_grid(self):
        """Configure the main grid layout."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

    def manage_files(self):
        """Open file manager dialog to manage downloads directory."""
        logger.info("Opening file manager")

        try:
            file_browser = ctk.CTkToplevel(self)
            file_browser.title("File Browser")
            file_browser.geometry("600x400")
            file_browser.resizable(False, False)

            # Center the window
            self.center_window(file_browser, 600, 400)

            # Ensure window gets focus
            file_browser.focus_force()
            file_browser.lift()
            file_browser.grab_set()

            # Configure grid
            file_browser.grid_columnconfigure(0, weight=1)
            file_browser.grid_rowconfigure(1, weight=1)

            # Current path entry
            current_path_var = ctk.StringVar(value=self.downloads_folder)
            path_entry = ctk.CTkEntry(
                file_browser,
                textvariable=current_path_var,
                width=400,
                height=40,
                font=("Roboto", 14)
            )
            path_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

            def update_file_list():
                """Update the file list display."""
                try:
                    file_listbox.delete(0, tk.END)
                    # Add parent directory option
                    if current_path_var.get() != os.path.expanduser("~"):
                        file_listbox.insert(tk.END, "..")

                    # List directories first
                    items = os.listdir(current_path_var.get())
                    directories = []
                    files = []

                    for item in items:
                        full_path = os.path.join(current_path_var.get(), item)
                        if os.path.isdir(full_path):
                            directories.append(item)
                        else:
                            files.append(item)

                    # Sort and insert directories
                    for directory in sorted(directories):
                        file_listbox.insert(tk.END, f"📁 {directory}")

                    # Sort and insert files
                    for file in sorted(files):
                        file_listbox.insert(tk.END, f"📄 {file}")

                except OSError as oe:
                    logger.error(f"Error accessing directory: {oe}")
                    self.show_status("Error: Unable to access the specified directory.")

            # Go button
            go_button = ctk.CTkButton(
                file_browser,
                text="Go",
                width=60,
                command=update_file_list,
                height=40,
                font=("Roboto", 14)
            )
            go_button.grid(row=0, column=1, padx=(0, 20), pady=20)

            # File listbox
            file_listbox = tk.Listbox(
                file_browser,
                bg="#2a2d2e",
                fg="white",
                selectbackground="#1f538d",
                font=("Roboto", 12)
            )
            file_listbox.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")

            def on_double_click(event):
                """Handle double-click on file/directory."""
                selection = file_listbox.curselection()
                if selection:
                    item = file_listbox.get(selection[0])

                    # Handle parent directory
                    if item == "..":
                        new_path = os.path.dirname(current_path_var.get())
                    else:
                        # Remove icon prefix if present
                        if item.startswith("📁 ") or item.startswith("📄 "):
                            item = item[2:]

                        new_path = os.path.join(current_path_var.get(), item)

                    if os.path.isdir(new_path):
                        current_path_var.set(new_path)
                        update_file_list()

            file_listbox.bind('<Double-1>', on_double_click)

            # Button frame
            button_frame = ctk.CTkFrame(file_browser, fg_color="transparent")
            button_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
            button_frame.grid_columnconfigure((0, 1, 2), weight=1)

            def change_directory():
                """Change the download directory."""
                new_path = current_path_var.get()
                if os.path.exists(new_path) and os.path.isdir(new_path):
                    self.downloads_folder = new_path
                    logger.info(f"Download directory changed to: {self.downloads_folder}")
                    self.show_status(f"Download directory changed to: {self.downloads_folder}")
                    file_browser.destroy()
                else:
                    messagebox.showerror("Error", "Please select a valid directory.")

            def create_folder():
                """Create a new folder."""
                dialog = ctk.CTkInputDialog(title="Create Folder", text="Enter folder name:")
                folder_name = dialog.get_input()

                if folder_name:
                    new_folder_path = os.path.join(current_path_var.get(), folder_name)
                    try:
                        os.mkdir(new_folder_path)
                        logger.info(f"Created new folder: {new_folder_path}")
                        update_file_list()
                    except OSError as oe:
                        logger.error(f"Error creating folder: {oe}")
                        self.show_status("Error: Unable to create the folder.")
                        messagebox.showerror("Error", f"Unable to create folder: {str(oe)}")

            # Button styles
            button_style = {"height": 40, "font": ("Roboto", 14)}

            # Action buttons
            change_dir_button = ctk.CTkButton(
                button_frame,
                text="Set as Download Directory",
                command=change_directory,
                **button_style
            )
            change_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

            create_folder_button = ctk.CTkButton(
                button_frame,
                text="Create Folder",
                command=create_folder,
                **button_style
            )
            create_folder_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

            cancel_button = ctk.CTkButton(
                button_frame,
                text="Cancel",
                command=file_browser.destroy,
                **button_style
            )
            cancel_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

            # Initial file list update
            update_file_list()

        except Exception as e:
            logger.error(f"Error opening file manager: {str(e)}")
            self.show_status("Error opening file manager")
            messagebox.showerror("Error", f"Unable to open file manager: {str(e)}")

    def center_window(self, window, width, height):
        """Center a window relative to its parent."""
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_width = self.winfo_width()
        parent_height = self.winfo_height()

        new_x = parent_x + (parent_width // 2) - (width // 2)
        new_y = parent_y + (parent_height // 2) - (height // 2)

        window.geometry(f"{width}x{height}+{new_x}+{new_y}")

    def setup_ui(self):
        """Set up the user interface components."""
        # Title
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="Media Downloader",
            font=("Roboto", 32, "bold")
        )
        self.title_label.grid(row=0, column=0, pady=(0, 20))

        # URL Entry Frame
        self.setup_url_frame()

        # Options Frame
        self.setup_options_frame()

        # Download List
        self.download_list = ctk.CTkTextbox(
            self.main_frame,
            activate_scrollbars=True,
            height=300,
            font=("Roboto", 12)
        )
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        # Buttons Frame
        self.setup_button_frame()

        # Status and Progress
        self.setup_status_and_progress()

    def setup_url_frame(self):
        """Set up the URL input frame."""
        self.url_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            self.url_frame,
            placeholder_text="Enter a URL",
            height=40,
            font=("Roboto", 14)
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.add_button = ctk.CTkButton(
            self.url_frame,
            text="Add",
            command=self.add_entry,
            width=100,
            height=40,
            font=("Roboto", 14)
        )
        self.add_button.grid(row=0, column=1)

    def setup_options_frame(self):
        """Set up the options frame with checkboxes and buttons."""
        self.options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        # YouTube Playlist Option
        self.playlist_var = ctk.StringVar(value="off")
        self.playlist_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Download YouTube Playlist",
            variable=self.playlist_var,
            onvalue="on",
            offvalue="off",
            font=("Roboto", 12)
        )
        self.playlist_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        # Audio Only Option
        self.audio_only_var = ctk.StringVar(value="off")
        self.audio_only_checkbox = ctk.CTkCheckBox(
            self.options_frame,
            text="Audio Only",
            variable=self.audio_only_var,
            onvalue="on",
            offvalue="off",
            font=("Roboto", 12)
        )
        self.audio_only_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        # Quality Selection
        self.quality_var = ctk.StringVar(value="720p")
        self.quality_dropdown = ctk.CTkOptionMenu(
            self.options_frame,
            values=["360p", "480p", "720p", "1080p"],
            variable=self.quality_var,
            font=("Roboto", 12)
        )
        self.quality_dropdown.pack(side=tk.LEFT)

        # Instagram Login Button
        self.insta_login_button = ctk.CTkButton(
            self.options_frame,
            text="Instagram Login",
            command=self.instagram_login,
            font=("Roboto", 12)
        )
        self.insta_login_button.pack(side=tk.LEFT, padx=(20, 0))

    def setup_button_frame(self):
        """Set up the main action buttons frame."""
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        button_style = {"font": ("Roboto", 14), "height": 40, "corner_radius": 10}

        # Remove Button
        self.remove_button = ctk.CTkButton(
            self.button_frame,
            text="Remove Selected",
            command=self.remove_entry,
            **button_style
        )
        self.remove_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        # Clear Button
        self.clear_button = ctk.CTkButton(
            self.button_frame,
            text="Clear All",
            command=self.clear_all,
            **button_style
        )
        self.clear_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Download Button
        self.download_button = ctk.CTkButton(
            self.button_frame,
            text="Download All",
            command=self.on_download_click,
            **button_style
        )
        self.download_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        # Manage Files Button
        self.manage_files_button = ctk.CTkButton(
            self.button_frame,
            text="Manage Files",
            command=self.manage_files,
            **button_style
        )
        self.manage_files_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

    def setup_status_and_progress(self):
        """Set up status labels and progress bar."""
        # Main status label
        self.status_label = ctk.CTkLabel(
            self.main_frame,
            text="Ready",
            font=("Roboto", 12)
        )
        self.status_label.grid(row=5, column=0, pady=(0, 5))

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, height=15)
        self.progress_bar.grid(row=6, column=0, sticky="ew", pady=(0, 5))
        self.progress_bar.set(0)

        # Speed label
        self.speed_label = ctk.CTkLabel(
            self.main_frame,
            text="Speed: 0 B/s",
            font=("Roboto", 12)
        )
        self.speed_label.grid(row=7, column=0, pady=(0, 5))

        # ETA label
        self.eta_label = ctk.CTkLabel(
            self.main_frame,
            text="ETA: --",
            font=("Roboto", 12)
        )
        self.eta_label.grid(row=8, column=0, pady=(0, 5))

    def instagram_login(self):
        """Handle Instagram login process."""
        logger.info("Attempting Instagram login")
        self.insta_login_button.configure(state="disabled")

        try:
            dialog = ctk.CTkInputDialog(text="Enter your Instagram username:", title="Instagram Login")
            username = dialog.get_input()

            if username:
                password = self.get_password()
                if password:
                    self.handle_instagram_authentication(username, password)
                else:
                    logger.info("Instagram login cancelled - no password provided")
                    self.insta_login_button.configure(state="normal")
            else:
                logger.info("Instagram login cancelled - no username provided")
                self.insta_login_button.configure(state="normal")

        except Exception as e:
            logger.error(f"Error during Instagram login dialog: {str(e)}")
            self.show_status("Error during Instagram login")
            self.insta_login_button.configure(state="normal")

    def get_password(self) -> Optional[str]:
        """Show password dialog and return entered password."""
        dialog = PasswordDialog(self)
        self.wait_window(dialog)
        return dialog.password

    def handle_instagram_authentication(self, username: str, password: str):
        """Handle the Instagram authentication process in a separate thread."""

        def authenticate_and_update():
            try:
                if authenticate_instagram(username, password):
                    self.handle_successful_login()
                else:
                    self.handle_failed_login()
            except Exception as e:
                self.handle_login_error(str(e))

        thread = threading.Thread(target=authenticate_and_update, daemon=True)
        thread.start()

    def handle_successful_login(self):
        """Handle successful Instagram login."""
        logger.info("Successfully logged in to Instagram")
        self.instagram_authenticated = True
        self.show_status("Successfully logged in to Instagram")
        self.insta_login_button.configure(
            text="Instagram: Logged In",
            state="disabled"
        )

    def handle_failed_login(self):
        """Handle failed Instagram login."""
        logger.warning("Instagram login failed. Invalid credentials.")
        self.show_status("Failed to log in to Instagram")
        messagebox.showerror(
            "Login Failed",
            "Failed to log in to Instagram. Please check your credentials."
        )
        self.insta_login_button.configure(state="normal")

    def handle_login_error(self, error_message: str):
        """Handle Instagram login error."""
        logger.error(f"Error during Instagram authentication: {error_message}")
        self.show_status("An error occurred during Instagram login")
        messagebox.showerror("Login Error", f"An error occurred: {error_message}")
        self.insta_login_button.configure(state="normal")

    def add_entry(self):
        """Add a new download entry."""
        link = self.url_entry.get().strip()
        if not link:
            self.show_status("Please enter a URL to add.")
            return

        try:
            dialog = ctk.CTkInputDialog(text="Enter a name for this link:", title="Link Name")
            name = dialog.get_input()

            if name:
                item = DownloadItem(name, link)
                self.download_items.append(item)
                self.update_download_list()
                self.url_entry.delete(0, tk.END)
                logger.info(f"Added new download item: {name} - {link}")
            else:
                self.show_status("A name is required to add the link.")
        except Exception as e:
            logger.error(f"Error adding entry: {str(e)}")
            self.show_status("Error adding entry")

    @staticmethod
    def format_speed(speed: float) -> str:
        """Format speed into human-readable format."""
        if speed < 1024:
            return f"{speed:.1f} B/s"
        elif speed < 1024 ** 2:
            return f"{speed / 1024:.1f} KB/s"
        elif speed < 1024 ** 3:
            return f"{speed / 1024 ** 2:.1f} MB/s"
        return f"{speed / 1024 ** 3:.1f} GB/s"

    @staticmethod
    def format_eta(seconds: float) -> str:
        """Format ETA into human-readable format."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.0f}m"
        else:
            return f"{seconds / 3600:.1f}h"

    def update_download_progress(self, downloaded: int, total: int, speed: float):
        """Update progress display."""
        try:
            if total > 0:
                progress = downloaded / total
                self.progress_bar.set(progress)

                # Update speed display
                speed_text = self.format_speed(speed)
                self.speed_label.configure(text=f"Speed: {speed_text}")

                # Update ETA
                if speed > 0:
                    remaining_bytes = total - downloaded
                    eta_seconds = remaining_bytes / speed
                    eta_text = self.format_eta(eta_seconds)
                else:
                    eta_text = "∞"
                self.eta_label.configure(text=f"ETA: {eta_text}")

                # Update status
                percentage = progress * 100
                self.status_label.configure(text=f"Downloading... {percentage:.1f}%")

                # Update list to show progress
                self.update_download_list()
        except Exception as e:
            logger.error(f"Error updating progress: {str(e)}")

    def update_download_list(self):
        """Update the display of download items."""
        try:
            self.download_list.delete("1.0", tk.END)
            for item in self.download_items:
                status = item.status
                if status == "Downloading" and hasattr(item, 'progress'):
                    status = f"Downloading ({item.progress.percentage:.1f}%)"
                self.download_list.insert(tk.END, f"{item.name} | {item.url} | {status}\n")
        except Exception as e:
            logger.error(f"Error updating download list: {str(e)}")
            self.show_status("Error updating display")


    def remove_entry(self):
        """Remove the selected download entry."""
        try:
            sel_start = self.download_list.index(tk.SEL_FIRST)
            sel_end = self.download_list.index(tk.SEL_LAST)
            selected_text = self.download_list.get(sel_start, sel_end)

            for item in self.download_items[:]:  # Create a copy of the list to modify
                if f"{item.name} | {item.url}" in selected_text:
                    self.download_items.remove(item)
                    logger.info(f"Removed download item: {item.name} - {item.url}")

            self.update_download_list()
        except tk.TclError:
            self.show_status("Please select a link to remove.")
        except Exception as e:
            logger.error(f"Error removing entry: {str(e)}")
            self.show_status("Error removing entry")

    def clear_all(self):
        """Clear all download entries."""
        try:
            self.download_items.clear()
            self.update_download_list()
            self.show_status("All items cleared.")
            logger.info("Cleared all download items")
        except Exception as e:
            logger.error(f"Error clearing items: {str(e)}")
            self.show_status("Error clearing items")

    def on_download_click(self):
        """Handle the download button click."""
        if not self.download_items:
            self.show_status("Please add at least one URL to download.")
            return

        try:
            self.download_button.configure(state="disabled")
            self.status_label.configure(text="Downloading...")
            self.progress_bar.set(0)

            # Clear and refill queue
            while not self.download_queue.empty():
                self.download_queue.get()

            for item in self.download_items:
                if item.status != "Downloaded":  # Only queue items that haven't been downloaded
                    self.download_queue.put(item)

            threading.Thread(target=self.process_downloads, daemon=True).start()
        except Exception as e:
            logger.error(f"Error starting downloads: {str(e)}")
            self.show_status("Error starting downloads")
            self.download_button.configure(state="normal")

    def process_downloads(self):
        """Process all queued downloads."""
        try:
            total_items = self.download_queue.qsize()
            completed_items = 0

            while not self.download_queue.empty():
                item = self.download_queue.get()
                try:
                    self.perform_download(item)
                except Exception as e:
                    logger.error(f"Error downloading {item.name}: {str(e)}")
                    item.status = "Failed"

                completed_items += 1
                progress = completed_items / total_items if total_items > 0 else 0
                self.progress_bar.set(progress)
                self.update_download_list()

            self.update_ui_after_downloads()
        except Exception as e:
            logger.error(f"Error in download process: {str(e)}")
            self.show_status("Error in download process")
            self.update_ui_after_downloads()

    def perform_download(self, item: DownloadItem) -> None:
        """Perform the download for a single item."""
        parsed_url = urlparse(item.url)
        domain = parsed_url.netloc.lower()

        download_mapping = {
            'youtube.com': self._download_youtube,
            'youtu.be': self._download_youtube,
            'twitter.com': self._download_twitter,
            'x.com': self._download_twitter,
            'instagram.com': self._download_instagram,
            'pinterest.com': self._download_pinterest,
            'pin.it': self._download_pinterest
        }

        try:
            for key, download_func in download_mapping.items():
                if key in domain:
                    if key == 'instagram.com' and not self.instagram_authenticated:
                        raise ValueError("Instagram authentication required. Please log in first.")

                    success = download_func(item)
                    item.status = "Downloaded" if success else "Failed"
                    logger.info(f"Download status for {item.name}: {item.status}")
                    return

            raise ValueError(f"Unsupported domain: {domain}")

        except Exception as e:
            item.status = "Failed"
            error_message = f"Error downloading {item.name}: {str(e)}"
            logger.error(error_message)
            self.show_status(error_message)
            messagebox.showerror("Download Error", error_message)

    def _download_youtube(self, item: DownloadItem) -> bool:
        """Handle YouTube download."""
        return download_youtube_video(
            item.url,
            os.path.join(self.downloads_folder, item.name),
            self.quality_var.get(),
            self.playlist_var.get() == "on",
            audio_only=self.audio_only_var.get() == "on"
        )

    def _download_twitter(self, item: DownloadItem) -> bool:
        """Handle Twitter download."""
        return download_twitter_media(
            item.url,
            os.path.join(self.downloads_folder, item.name)
        )

    def _download_instagram(self, item: DownloadItem) -> bool:
        """Handle Instagram download."""
        return download_instagram_media(
            item.url,
            os.path.join(self.downloads_folder, item.name)
        )

    def _download_pinterest(self, item: DownloadItem) -> bool:
        """Handle Pinterest download."""
        return download_pinterest_image(
            item.url,
            os.path.join(self.downloads_folder, item.name)
        )

    def update_ui_after_downloads(self):
        """Update UI elements after downloads are complete."""
        try:
            self.download_button.configure(state="normal")
            self.status_label.configure(text="All downloads completed")
            self.progress_bar.set(1)
            self.update_download_list()
            self.show_status("All downloads have been completed.")
            logger.info("All downloads completed")
        except Exception as e:
            logger.error(f"Error updating UI after downloads: {str(e)}")

    def show_status(self, message: str):
        """Show a status message with auto-clear after 5 seconds."""
        try:
            self.status_label.configure(text=message)
            self.after(5000, lambda: self.status_label.configure(text="Ready"))
            logger.info(f"Status message: {message}")
        except Exception as e:
            logger.error(f"Error showing status: {str(e)}")

def main():
    """Main entry point of the application."""
    try:
        app = MediaDownloader()
        logger.info("Application started")
        app.mainloop()
    except Exception as e:
        logger.critical(f"Critical error in main application: {str(e)}")
        messagebox.showerror("Critical Error", f"An unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()