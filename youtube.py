from tkinter import messagebox
import yt_dlp
from oprations import random_save_path
from oprations import on_operation_done

def download_youtube_video(link):


    save_path = random_save_path()

    # Options for downloading video
    video_options = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': f'Youtube_video{save_path}.mp4'
    }

    try:
        with yt_dlp.YoutubeDL(video_options) as ydl:
            ydl.download([link])
        messagebox.showinfo("Success", "YouTube video downloaded successfully.")
        on_operation_done()
    except yt_dlp.utils.DownloadError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        on_operation_done()
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube video: {e}")
        on_operation_done()
