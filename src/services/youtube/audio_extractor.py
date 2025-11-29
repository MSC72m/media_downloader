import os
import subprocess

from src.core.config import AppConfig, get_config
from src.core.interfaces import IErrorNotifier
from src.utils.logger import get_logger

logger = get_logger(__name__)


class AudioExtractor:
    def __init__(
        self,
        config: AppConfig = get_config(),
        error_handler: IErrorNotifier | None = None,
    ):
        self.config = config
        self.error_handler = error_handler

    def _run_ffmpeg_extraction(
        self, video_path: str, output_path: str, use_copy: bool = True
    ) -> subprocess.CompletedProcess[str]:
        """Run FFmpeg extraction command.

        Args:
            video_path: Path to video file
            output_path: Output path for audio
            use_copy: Whether to use copy codec (faster) or re-encode

        Returns:
            CompletedProcess result
        """
        if use_copy:
            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                "copy",
                "-y",
                output_path,
            ]
        else:
            cmd = [
                "ffmpeg",
                "-i",
                video_path,
                "-vn",
                "-acodec",
                self.config.youtube.audio_codec,
                "-ab",
                "192k",
                "-y",
                output_path,
            ]

        return subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=300)

    def _handle_extraction_error(self, error_type: str, message: str) -> bool:
        """Handle extraction errors.

        Args:
            error_type: Type of error
            message: Error message

        Returns:
            False (always fails)
        """
        logger.error(f"[AUDIO_EXTRACTOR] {error_type}: {message}")
        if self.error_handler:
            self.error_handler.show_warning(error_type, message)
        return False

    def _extract_with_ffmpeg(self, video_path: str, output_path: str) -> bool:
        """Perform FFmpeg extraction.

        Args:
            video_path: Path to video file
            output_path: Output path for audio

        Returns:
            True if successful, False otherwise
        """
        result = self._run_ffmpeg_extraction(video_path, output_path, use_copy=True)

        if result.returncode != 0:
            logger.debug(f"[AUDIO_EXTRACTOR] Copy codec failed, trying re-encode: {result.stderr}")
            result = self._run_ffmpeg_extraction(video_path, output_path, use_copy=False)

        if result.returncode == 0:
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"[AUDIO_EXTRACTOR] Successfully extracted audio to {output_path}")
                return True
            return self._handle_extraction_error("Audio file created but is empty or missing", "")

        return self._handle_extraction_error(
            "Audio Extraction Failed", f"Failed to extract audio: {result.stderr[:200]}"
        )

    def _handle_extraction_exceptions(self, e: Exception) -> bool:
        """Handle extraction exceptions.

        Args:
            e: Exception that occurred

        Returns:
            False (always fails)
        """
        if isinstance(e, subprocess.TimeoutExpired):
            return self._handle_extraction_error(
                "Audio Extraction Timeout", "Audio extraction took too long and was cancelled."
            )
        if isinstance(e, FileNotFoundError):
            return self._handle_extraction_error(
                "FFmpeg Not Found",
                "FFmpeg is required to extract audio. Please install FFmpeg to enable audio extraction.",
            )
        logger.error(f"[AUDIO_EXTRACTOR] Error extracting audio: {e}", exc_info=True)
        if self.error_handler:
            self.error_handler.handle_exception(e, "Audio extraction", "Audio Extractor")
        return self._handle_extraction_error("Audio Extraction Error", str(e))

    def extract_audio(self, video_path: str, output_path: str | None = None) -> bool:
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
            return self._handle_extraction_error(
                "Video file does not exist", f"Video file does not exist: {video_path}"
            )

        try:
            if output_path is None:
                base_path = os.path.splitext(video_path)[0]
                output_path = base_path + self.config.youtube.file_extensions["audio"]

            logger.info(f"[AUDIO_EXTRACTOR] Extracting audio from {video_path} to {output_path}")
            return self._extract_with_ffmpeg(video_path, output_path)

        except Exception as e:
            return self._handle_extraction_exceptions(e)
