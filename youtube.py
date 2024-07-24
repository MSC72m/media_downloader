from tkinter import messagebox
from pytube import YouTube
import pytube
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def download_youtube_video(link):
    from main import save_path
    from oprations import on_operation_done
    try:
        yt = YouTube(link)
        stream = yt.streams.get_highest_resolution()
        stream.download(filename=f'Youtube_video{save_path}.mp4')
        messagebox.showinfo(
            "Success", "YouTube video downloaded successfully.")
        on_operation_done()
    except pytube.exceptions.PytubeError as e:
        messagebox.showerror("Error", f"An error occurred: {e}")
        on_operation_done()
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube video: {e}")
        on_operation_done()

