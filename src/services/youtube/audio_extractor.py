"""Audio extraction utility for YouTube downloads."""

import os
import subprocess
from typing import Optional

from src.core.config import AppConfig, get_config
from src.interfaces.service_interfaces import IErrorHandler
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AudioExtractor:
    """Utility class for extracting audio from video files using FFmpeg."""

    def __init__(self, config: AppConfig = get_config(), error_handler: Optional[IErrorHandler] = None):
        """Initialize audio extractor.

        Args:
            config: Application configuration
            error_handler: Optional error handler for user notifications
        """
        self.config = config
        self.error_handler = error_handler

    def extract_audio(self, video_path: str, output_path: Optional[str] = None) -> bool:
        """Extract audio from video file to a separate audio file.
        
        This keeps the original video file intact and creates a separate audio file.
        
        Args:
            video_path: Path to the video file
            output_path: Optional output path for audio file. If not provided,
                       uses same base name as video with audio extension.
        
        Returns:
            True if audio extraction succeeded, False otherwise
        """
        if not os.path.exists(video_path):
            logger.error(f"[AUDIO_EXTRACTOR] Video file does not exist: {video_path}")
            return False
        
        try:
            # Generate audio output path if not provided
            if output_path is None:
                base_path = os.path.splitext(video_path)[0]
                output_path = base_path + self.config.youtube.file_extensions["audio"]
            
            logger.info(f"[AUDIO_EXTRACTOR] Extracting audio from {video_path} to {output_path}")
            
            # Use FFmpeg to extract audio - try copy codec first (faster, no quality loss)
            cmd = [
                "ffmpeg",
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "copy",  # Copy audio codec (no re-encoding)
                "-y",  # Overwrite output file
                output_path
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            # If copy fails (codec not supported), try re-encoding
            if result.returncode != 0:
                logger.debug(f"[AUDIO_EXTRACTOR] Copy codec failed, trying re-encode: {result.stderr}")
                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vn",  # No video
                    "-acodec", self.config.youtube.audio_codec,
                    "-ab", "192k",  # Audio bitrate
                    "-y",  # Overwrite output file
                    output_path
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
            
            if result.returncode == 0:
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    logger.info(f"[AUDIO_EXTRACTOR] Successfully extracted audio to {output_path}")
                    return True
                else:
                    logger.error(f"[AUDIO_EXTRACTOR] Audio file created but is empty or missing")
                    return False
            else:
                logger.error(f"[AUDIO_EXTRACTOR] FFmpeg failed: {result.stderr}")
                if self.error_handler:
                    self.error_handler.show_warning(
                        "Audio Extraction Failed",
                        f"Failed to extract audio: {result.stderr[:200]}"
                    )
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("[AUDIO_EXTRACTOR] Audio extraction timed out")
            if self.error_handler:
                self.error_handler.show_warning(
                    "Audio Extraction Timeout",
                    "Audio extraction took too long and was cancelled."
                )
            return False
        except FileNotFoundError:
            logger.error("[AUDIO_EXTRACTOR] FFmpeg not found. Please install FFmpeg to extract audio.")
            if self.error_handler:
                self.error_handler.show_warning(
                    "FFmpeg Not Found",
                    "FFmpeg is required to extract audio. Please install FFmpeg to enable audio extraction."
                )
            return False
        except Exception as e:
            logger.error(f"[AUDIO_EXTRACTOR] Error extracting audio: {e}", exc_info=True)
            if self.error_handler:
                self.error_handler.handle_exception(e, "Audio extraction", "Audio Extractor")
            return False

