from PyQt5.QtWidgets import QMessageBox
import yt_dlp
from operations import operations

def download_youtube_video(link, save_name, progress_callback):
    video_options = {
        'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[ext=mp4]',
        'outtmpl': f'{save_name}.mp4',
        'noplaylist': True,
        'progress_hooks': [lambda d: progress_callback.emit(d['percentage'] * 100) if 'percentage' in d else None]
    }

    try:
        with yt_dlp.YoutubeDL(video_options) as ydl:
            ydl.download([link])
        QMessageBox.information(None, "Success", f"YouTube video downloaded successfully as {save_name}.mp4")
    except yt_dlp.utils.DownloadError as e:
        QMessageBox.critical(None, "Error", f"An error occurred: {str(e)}")
    except Exception as e:
        QMessageBox.critical(None, "Error", f"Error downloading YouTube video: {str(e)}")
    finally:
        operations.on_operation_done()