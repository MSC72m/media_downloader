import yt_dlp
from tkinter import messagebox
import os


def sanitize_filename(filename):
    # Remove invalid characters from the filename
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename.strip()


def download_youtube_video(link, save_name, quality, download_playlist, audio_only):
    def get_output_template(save_name):
        # Use the save_name as a prefix, then add the video title
        return f'{save_name}_%(title)s.%(ext)s'

    ydl_opts = {
        'outtmpl': get_output_template(save_name),
        'noplaylist': not download_playlist,
    }

    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '0',  # Use '0' for best quality
        }]
        ydl_opts['audioformat'] = 'mp3'  # Ensure we get mp3 format
        ydl_opts['audioquality'] = '0'  # '0' is the best quality
    else:
        ydl_opts['format'] = f'bestvideo[height<={quality[:-1]}]+bestaudio/best[height<={quality[:-1]}]'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            if 'entries' in info:  # It's a playlist
                for entry in info['entries']:
                    video_title = sanitize_filename(entry.get('title', 'Untitled'))
                    ydl_opts['outtmpl'] = get_output_template(os.path.join(save_name, video_title))
                    ydl.download([entry['webpage_url']])
            else:  # It's a single video
                video_title = sanitize_filename(info.get('title', 'Untitled'))
                ydl_opts['outtmpl'] = get_output_template(save_name)
                ydl.download([link])

        messagebox.showinfo("Success", f"YouTube {'audio' if audio_only else 'video'} downloaded successfully")
        return True
    except Exception as e:
        messagebox.showerror("Error", f"Error downloading YouTube {'audio' if audio_only else 'video'}: {str(e)}")
        return False