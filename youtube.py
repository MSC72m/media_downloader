import yt_dlp
from tkinter import messagebox

def download_youtube_video(link, save_name, quality, download_playlist, audio_only):
    ydl_opts = {
        'outtmpl': f'{save_name}.%(ext)s',
        'noplaylist': not download_playlist,
    }

    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    else:
        ydl_opts['format'] = f'bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])
        messagebox.showinfo("Success", f"YouTube {'audio' if audio_only else 'video'} downloaded successfully as {save_name}")
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube {'audio' if audio_only else 'video'}: {str(e)}")