import yt_dlp
from tkinter import messagebox
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(filename):
    invalid_chars = '<>:"/\\|?*'
    return ''.join(c for c in filename if c not in invalid_chars).strip()

def download_youtube_video(link, save_path, quality, download_playlist, audio_only):
    def get_output_template(save_name):
        return f'{save_name}_%(title)s.%(ext)s'

    ydl_opts = {
        'outtmpl': {
            'default': get_output_template(save_path)
        },
        'noplaylist': not download_playlist,
    }

    if audio_only:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '256',
            }],
        })
    else:
        try:
            quality_value = int(quality.rstrip('pP'))
            ydl_opts['format'] = f'bestvideo[height<={quality_value}]+bestaudio/best[height<={quality_value}]'
        except ValueError:
            logger.warning(f"Invalid quality format: {quality}. Using best available quality.")
            ydl_opts['format'] = 'bestvideo+bestaudio/best'

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)

            if info is None:
                raise ValueError("Failed to extract video information")

            if 'entries' in info:
                for i, entry in enumerate(info['entries']):
                    if entry:
                        video_title = sanitize_filename(entry.get('title', f'Untitled_{i + 1}'))
                        ydl_opts['outtmpl']['default'] = get_output_template(save_path)
                        ydl.download([entry.get('webpage_url', link)])
                        logger.info(f"Downloaded video: {video_title}")
                    else:
                        logger.warning(f"Skipping empty entry at index {i}")
            else:  # It's a single video
                video_title = sanitize_filename(info.get('title', 'Untitled'))
                ydl_opts['outtmpl']['default'] = get_output_template(save_path)
                ydl.download([link])
                logger.info(f"Downloaded video: {video_title}")

        messagebox.showinfo("Success", f"YouTube {'audio' if audio_only else 'video'} downloaded successfully")
        return True
    except Exception as e:
        error_message = f"Error downloading YouTube video: {str(e)}"
        logger.error(error_message)
        logger.error("Traceback:", exc_info=True)
        messagebox.showerror("Error", error_message)
        return False