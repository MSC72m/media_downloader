import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog
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
    """
    program will use popup windows inorder to indicate successful or failed downloads and it will block the program
    so till you press ok it will not start process of downloading next file so need to fix that aswell.
    need to tity up the code and add coments and update the README.md file aswell.
    need to do an release for this repo and include the .exe file for windows and appimage for linux, in adition to code.
    """
    def __init__(self):
        super().__init__()

        self.title("Media Downloader")
        self.geometry("900x700")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(3, weight=1)

        self.title_label = ctk.CTkLabel(self.main_frame, text="Media Downloader", font=("Helvetica", 26, "bold"))
        self.title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))

        self.url_entry = ctk.CTkEntry(self.main_frame, placeholder_text="Enter a URL")
        self.url_entry.grid(row=1, column=0, columnspan=3, padx=20, pady=(0, 10), sticky="ew")

        self.add_button = ctk.CTkButton(self.main_frame, text="Add", command=self.add_entry)
        self.add_button.grid(row=1, column=3, padx=(0, 20), pady=(0, 10))

        self.options_frame = ctk.CTkFrame(self.main_frame)
        self.options_frame.grid(row=2, column=0, columnspan=4, padx=20, pady=(0, 10), sticky="ew")

        self.playlist_var = ctk.StringVar(value="off")
        self.playlist_checkbox = ctk.CTkCheckBox(self.options_frame, text="Download YouTube Playlist",
                                                 variable=self.playlist_var, onvalue="on", offvalue="off")
        self.playlist_checkbox.pack(side=tk.LEFT, padx=(0, 20))

        self.audio_only_var = ctk.StringVar(value="off")
        self.audio_only_checkbox = ctk.CTkCheckBox(self.options_frame, text="Audio Only",
                                                   variable=self.audio_only_var, onvalue="on", offvalue="off")
        self.audio_only_checkbox.pack(side=tk.LEFT, padx=(0, 30))

        self.quality_var = ctk.StringVar(value="720p")
        self.quality_dropdown = ctk.CTkOptionMenu(self.options_frame, values=["360p", "480p", "720p", "1080p"],
                                                  variable=self.quality_var)
        self.quality_dropdown.pack(side=tk.LEFT)

        self.insta_login_button = ctk.CTkButton(self.options_frame, text="Instagram Login", command=self.instagram_login)
        self.insta_login_button.pack(side=tk.LEFT, padx=(20, 0))

        self.download_list = ctk.CTkTextbox(self.main_frame, activate_scrollbars=True, height=200)
        self.download_list.grid(row=3, column=0, columnspan=4, padx=20, pady=(0, 10), sticky="nsew")

        self.download_button = ctk.CTkButton(self.main_frame, text="Download All", command=self.on_download_click)
        self.download_button.grid(row=4, column=0, columnspan=2, padx=(20, 10), pady=(0, 10), sticky="ew")

        self.remove_button = ctk.CTkButton(self.main_frame, text="Remove Selected", command=self.remove_entry)
        self.remove_button.grid(row=4, column=2, columnspan=2, padx=(10, 20), pady=(0, 10), sticky="ew")

        self.status_label = ctk.CTkLabel(self.main_frame, text="Ready")
        self.status_label.grid(row=5, column=0, columnspan=4, pady=(0, 10))

        self.progress_bar = ctk.CTkProgressBar(self.main_frame)
        self.progress_bar.grid(row=6, column=0, columnspan=4, padx=20, pady=(0, 10), sticky="ew")
        self.progress_bar.set(0)

        self.download_queue = queue.Queue()
        self.download_items = []

        # Create Downloads folder
        self.downloads_folder = "Downloads"
        if not os.path.exists(self.downloads_folder):
            os.makedirs(self.downloads_folder)

    def instagram_login(self):
        username = simpledialog.askstring("Instagram Login", "Enter your Instagram username:")
        if username:
            password = simpledialog.askstring("Instagram Login", "Enter your Instagram password:", show='*')
            if password:
                if authenticate_instagram(username, password):
                    messagebox.showinfo("Instagram Login", "Successfully logged in to Instagram")
                    self.insta_login_button.configure(text="Instagram: Logged In", state="disabled")

    def add_entry(self):
        link = self.url_entry.get().strip()
        if not link:
            messagebox.showwarning("Empty URL", "Please enter a URL to add.")
            return

        name = simpledialog.askstring("Link Name", "Enter a name for this link:")
        if name:
            item = DownloadItem(name, link)
            self.download_items.append(item)
            self.update_download_list()
            self.url_entry.delete(0, tk.END)
        else:
            messagebox.showwarning("No Name", "A name is required to add the link.")

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
            messagebox.showwarning("No Selection", "Please select a link to remove.")

    def on_download_click(self):
        if not self.download_items:
            messagebox.showwarning("No URLs", "Please add at least one URL to download.")
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
                download_youtube_video(item.url, os.path.join(self.downloads_folder, item.name),
                                       self.quality_var.get(), self.playlist_var.get() == "on",
                                       audio_only=self.audio_only_var.get() == "on")
            elif 'twitter.com' in domain or 'x.com' in domain:
                download_twitter_media(item.url, os.path.join(self.downloads_folder, item.name))
            elif 'instagram.com' in domain:
                download_instagram_media(item.url, os.path.join(self.downloads_folder, item.name))
            elif 'pinterest.com' in domain:
                download_pinterest_image(item.url, os.path.join(self.downloads_folder, item.name))
            else:
                raise ValueError(f"Unsupported domain: {domain}")
            item.status = "Completed"
        except Exception as e:
            item.status = "Failed"
            messagebox.showerror("Error", f"Error downloading {item.name}: {str(e)}")

    def update_ui_after_downloads(self):
        self.download_button.configure(state="normal")
        self.status_label.configure(text="All downloads completed")
        self.progress_bar.set(1)
        self.update_download_list()

if __name__ == "__main__":
    app = MediaDownloader()
    app.mainloop()