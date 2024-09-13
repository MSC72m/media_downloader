import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import urlparse
import threading
import queue
import os
from youtube import download_youtube_video
from twitter import download_twitter_media
from instagram import download_instagram_media, authenticate_instagram
from pinterest import download_pinterest_image

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class DownloadItem:
    def __init__(self, name, url, status="Pending"):
        self.name = name
        self.url = url
        self.status = status


class MediaDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.success = None
        self.title("Media Downloader")
        self.geometry("1000x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Media Downloader", font=("Roboto", 32, "bold"))
        self.title_label.grid(row=0, column=0, pady=(0, 20))

        self.url_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.url_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.url_frame.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(self.url_frame, placeholder_text="Enter a URL", height=40, font=("Roboto", 14))
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        self.add_button = ctk.CTkButton(self.url_frame, text="Add", command=self.add_entry, width=100, height=40,
                                        font=("Roboto", 14))
        self.add_button.grid(row=0, column=1)

        self.options_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        self.playlist_var = ctk.StringVar(value="off")
        self.playlist_checkbox = ctk.CTkCheckBox(self.options_frame, text="Download YouTube Playlist",
                                                 variable=self.playlist_var, onvalue="on", offvalue="off",
                                                 font=("Roboto", 12))
        self.playlist_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        self.audio_only_var = ctk.StringVar(value="off")
        self.audio_only_checkbox = ctk.CTkCheckBox(self.options_frame, text="Audio Only",
                                                   variable=self.audio_only_var, onvalue="on", offvalue="off",
                                                   font=("Roboto", 12))
        self.audio_only_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        self.quality_var = ctk.StringVar(value="720p")
        self.quality_dropdown = ctk.CTkOptionMenu(self.options_frame, values=["360p", "480p", "720p", "1080p"],
                                                  variable=self.quality_var, font=("Roboto", 12))
        self.quality_dropdown.pack(side=tk.LEFT)

        self.insta_login_button = ctk.CTkButton(self.options_frame, text="Instagram Login",
                                                command=self.instagram_login, font=("Roboto", 12))
        self.insta_login_button.pack(side=tk.LEFT, padx=(20, 0))

        self.download_list = ctk.CTkTextbox(self.main_frame, activate_scrollbars=True, height=300, font=("Roboto", 12))
        self.download_list.grid(row=3, column=0, sticky="nsew", pady=(0, 10))

        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))
        self.button_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        button_style = {"font": ("Roboto", 14), "height": 40, "corner_radius": 10}

        self.remove_button = ctk.CTkButton(self.button_frame, text="Remove Selected", command=self.remove_entry,
                                           **button_style)
        self.remove_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.clear_button = ctk.CTkButton(self.button_frame, text="Clear All", command=self.clear_all, **button_style)
        self.clear_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.download_button = ctk.CTkButton(self.button_frame, text="Download All", command=self.on_download_click,
                                             **button_style)
        self.download_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        self.manage_files_button = ctk.CTkButton(self.button_frame, text="Manage Files", command=self.manage_files,
                                                 **button_style)
        self.manage_files_button.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready", font=("Roboto", 12))
        self.status_label.grid(row=5, column=0, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(self.main_frame, height=15)
        self.progress_bar.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        self.progress_bar.set(0)

        self.download_queue = queue.Queue()
        self.download_items = []

        self.downloads_folder = os.path.expanduser("~/Downloads")
        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    def manage_files(self):
        file_browser = ctk.CTkToplevel(self)
        file_browser.title("File Browser")
        file_browser.geometry("600x400")
        file_browser.grid_columnconfigure(0, weight=1)
        file_browser.grid_rowconfigure(1, weight=1)

        current_path_var = ctk.StringVar(value=self.downloads_folder)
        path_entry = ctk.CTkEntry(file_browser, textvariable=current_path_var, width=400, height=40,
                                  font=("Roboto", 14))
        path_entry.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="ew")

        def update_file_list():
            file_listbox.delete(0, tk.END)
            try:
                for item in os.listdir(current_path_var.get()):
                    file_listbox.insert(tk.END, item)
            except OSError:
                self.show_status("Error: Unable to access the specified directory.")

        go_button = ctk.CTkButton(file_browser, text="Go", width=60, command=update_file_list, height=40,
                                  font=("Roboto", 14))
        go_button.grid(row=0, column=1, padx=(0, 20), pady=20)

        file_listbox = tk.Listbox(file_browser, bg="#2a2d2e", fg="white", selectbackground="#1f538d",
                                  font=("Roboto", 12))
        file_listbox.grid(row=1, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")

        def on_double_click(event):
            selection = file_listbox.curselection()
            if selection:
                item = file_listbox.get(selection[0])
                new_path = os.path.join(current_path_var.get(), item)
                if os.path.isdir(new_path):
                    current_path_var.set(new_path)
                    update_file_list()

        file_listbox.bind('<Double-1>', on_double_click)

        button_frame = ctk.CTkFrame(file_browser, fg_color="transparent")
        button_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="ew")
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        def change_directory():
            self.downloads_folder = current_path_var.get()
            self.show_status(f"Download directory changed to: {self.downloads_folder}")
            file_browser.destroy()

        change_dir_button = ctk.CTkButton(button_frame, text="Set as Download Directory", command=change_directory,
                                          height=40, font=("Roboto", 14))
        change_dir_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        def create_folder():
            dialog = ctk.CTkInputDialog(title="Create Folder", text="Enter folder name:")
            folder_name = dialog.get_input()
            if folder_name:
                new_folder_path = os.path.join(current_path_var.get(), folder_name)
                try:
                    os.mkdir(new_folder_path)
                    update_file_list()
                except OSError:
                    self.show_status("Error: Unable to create the folder.")

        create_folder_button = ctk.CTkButton(button_frame, text="Create Folder", command=create_folder, height=40,
                                             font=("Roboto", 14))
        create_folder_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        cancel_button = ctk.CTkButton(button_frame, text="Cancel", command=file_browser.destroy, height=40,
                                      font=("Roboto", 14))
        cancel_button.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

        update_file_list()

    def instagram_login(self):
        dialog = ctk.CTkInputDialog(text="Enter your Instagram username:", title="Instagram Login")
        username = dialog.get_input()
        if username:
            dialog = ctk.CTkInputDialog(text="Enter your Instagram password:", title="Instagram Login")
            password = dialog.get_input()
            if password:
                if authenticate_instagram(username, password):
                    self.show_status("Successfully logged in to Instagram")
                    self.insta_login_button.configure(text="Instagram: Logged In", state="disabled")

    def add_entry(self):
        link = self.url_entry.get().strip()
        if not link:
            self.show_status("Please enter a URL to add.")
            return

        dialog = ctk.CTkInputDialog(text="Enter a name for this link:", title="Link Name")
        name = dialog.get_input()
        if name:
            item = DownloadItem(name, link)
            self.download_items.append(item)
            self.update_download_list()
            self.url_entry.delete(0, tk.END)
        else:
            self.show_status("A name is required to add the link.")

    def update_download_list(self):
        self.download_list.delete("1.0", tk.END)
        for item in self.download_items:
            self.download_list.insert(tk.END, f"{item.name} | {item.url} | {item.status}\n")

    def remove_entry(self):
        try:
            sel_start = self.download_list.index(tk.SEL_FIRST)
            sel_end = self.download_list.index(tk.SEL_LAST)
            selected_text = self.download_list.get(sel_start, sel_end)

            for item in self.download_items[:]:
                if f"{item.name} | {item.url}" in selected_text:
                    self.download_items.remove(item)

            self.update_download_list()
        except tk.TclError:
            self.show_status("Please select a link to remove.")

    def clear_all(self):
        self.download_items.clear()
        self.update_download_list()
        self.show_status("All items cleared.")

    def on_download_click(self):
        if not self.download_items:
            self.show_status("Please add at least one URL to download.")
            return

        self.download_button.configure(state="disabled")
        self.status_label.configure(text="Downloading...")
        self.progress_bar.set(0)

        for item in self.download_items:
            self.download_queue.put(item)

        threading.Thread(target=self.process_downloads, daemon=True).start()

    def process_downloads(self):
        total_items = len(self.download_items)
        completed_items = 0

        while not self.download_queue.empty():
            item = self.download_queue.get()
            self.perform_download(item)
            completed_items += 1
            self.progress_bar.set(completed_items / total_items)
            self.update_download_list()

        self.update_ui_after_downloads()

    def perform_download(self, item):
        parsed_url = urlparse(item.url)
        domain = parsed_url.netloc
        try:
            if 'youtube.com' in domain:
                self.success = download_youtube_video(item.url, os.path.join(self.downloads_folder, item.name),
                                                      self.quality_var.get(), self.playlist_var.get() == "on",
                                                      audio_only=self.audio_only_var.get() == "on")
            elif 'twitter.com' in domain or 'x.com' in domain:
                self.success = download_twitter_media(item.url, os.path.join(self.downloads_folder, item.name))
            elif 'instagram.com' in domain:
                self.success = download_instagram_media(item.url, os.path.join(self.downloads_folder, item.name))
            elif 'pinterest.com' in domain:
                self.success = download_pinterest_image(item.url, os.path.join(self.downloads_folder, item.name))
            else:
                raise ValueError(f"Unsupported domain: {domain}")

            item.status = "Downloaded" if self.success else "Failed"

        except Exception as e:
            item.status = "Failed"
            self.show_status(f"Error downloading {item.name}: {str(e)}")

    def update_ui_after_downloads(self):
        self.download_button.configure(state="normal")
        self.status_label.configure(text="All downloads completed")
        self.progress_bar.set(1)
        self.update_download_list()
        self.show_status("All downloads have been completed.")

    def show_status(self, message):
        self.status_label.configure(text=message)
        self.after(5000, lambda: self.status_label.configure(text="Ready"))


if __name__ == "__main__":
    app = MediaDownloader()
    app.mainloop()
