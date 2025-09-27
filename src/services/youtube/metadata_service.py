"""YouTube metadata service implementation."""

import yt_dlp
import json
import re
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse, parse_qs

from ...interfaces.youtube_metadata import (
    IYouTubeMetadataService, YouTubeMetadata, SubtitleInfo
)
from ...utils.logger import get_logger

logger = get_logger(__name__)


class YouTubeMetadataService(IYouTubeMetadataService):
    """Service for fetching YouTube video metadata."""

    def __init__(self):
        self._ytdlp_options = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'discard_in_playlist',
            'playlistend': 1,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'skip_download': True,
            # Don't fetch formats by default to avoid storyboard noise
        }

    def fetch_metadata(self, url: str, cookie_path: Optional[str] = None) -> Optional[YouTubeMetadata]:
        """Fetch basic metadata for a YouTube URL without fetching formats."""
        try:
            logger.info(f"Fetching metadata for URL: {url}")

            if not self.validate_url(url):
                return YouTubeMetadata(error="Invalid YouTube URL")

            # Get basic video info without fetching formats to avoid storyboard noise
            info = self._get_basic_video_info(url, cookie_path)
            if not info:
                return YouTubeMetadata(error="Failed to fetch video information")

            # Extract available qualities and formats (static options)
            available_qualities = self._extract_qualities(info)
            available_formats = self._extract_formats(info)
            available_subtitles = self._extract_subtitles(info)

            return YouTubeMetadata(
                title=info.get('title', ''),
                duration=self._format_duration(info.get('duration', 0)),
                view_count=self._format_view_count(info.get('view_count', 0)),
                upload_date=self._format_upload_date(info.get('upload_date', '')),
                channel=info.get('channel', ''),
                description=info.get('description', ''),
                thumbnail=info.get('thumbnail', ''),
                available_qualities=available_qualities,
                available_formats=available_formats,
                available_subtitles=available_subtitles,
                is_playlist='entries' in info,
                playlist_count=len(info.get('entries', []))
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error fetching metadata: {error_msg}")
            return YouTubeMetadata(error=f"Failed to fetch metadata: {error_msg}")

    def _get_basic_video_info(self, url: str, cookie_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get basic video info without ANY format fetching."""
        try:
            # Minimal options to get only basic video info and subtitles, NO FORMAT SELECTION
            basic_options = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': False,  # Don't write subtitle files
                'writeautomaticsub': False,  # Don't write auto subtitle files
                'noplaylist': True,
                'extract_flat': 'discard_in_playlist',  # Don't extract playlist items
                'playlistend': 0,  # Don't process playlist
            }

            # Add cookies if available and file is readable
            if cookie_path:
                try:
                    # Check if cookie file exists and is readable
                    with open(cookie_path, 'r', encoding='utf-8') as f:
                        # Try to read first few bytes to check if it's valid
                        f.read(100)
                    basic_options['cookiefile'] = cookie_path
                except Exception as e:
                    logger.warning(f"Cookie file not readable, proceeding without cookies: {e}")

            with yt_dlp.YoutubeDL(basic_options) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    logger.info("Successfully fetched basic video info")
                    return info

        except Exception as e:
            logger.warning(f"Basic extraction failed: {e}")

        # Fallback without cookies if cookies failed
        if cookie_path:
            try:
                basic_options_no_cookies = {
                    'quiet': True,
                    'no_warnings': True,
                    'skip_download': True,
                    'writesubtitles': False,  # Don't write subtitle files
                    'writeautomaticsub': False,  # Don't write auto subtitle files
                    'noplaylist': True,
                    'extract_flat': 'discard_in_playlist',
                    'playlistend': 0,
                }

                with yt_dlp.YoutubeDL(basic_options_no_cookies) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        logger.info("Successfully fetched basic video info without cookies")
                        return info

            except Exception as e:
                logger.error(f"Fallback extraction failed: {e}")

        return None

    def get_available_qualities(self, url: str) -> List[str]:
        """Get available video qualities for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_qualities if metadata else []
        except Exception as e:
            logger.error(f"Error fetching qualities: {str(e)}")
            return []

    def get_available_formats(self, url: str) -> List[str]:
        """Get available formats for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            return metadata.available_formats if metadata else []
        except Exception as e:
            logger.error(f"Error fetching formats: {str(e)}")
            return []

    def get_available_subtitles(self, url: str) -> List[SubtitleInfo]:
        """Get available subtitles for a YouTube URL."""
        try:
            metadata = self.fetch_metadata(url)
            if not metadata or not metadata.available_subtitles:
                return []

            return [
                SubtitleInfo(
                    language_code=sub['language_code'],
                    language_name=sub['language_name'],
                    is_auto_generated=sub['is_auto_generated'],
                    url=sub['url']
                )
                for sub in metadata.available_subtitles
            ]
        except Exception as e:
            logger.error(f"Error fetching subtitles: {str(e)}")
            return []

    def validate_url(self, url: str) -> bool:
        """Validate if URL is a valid YouTube URL."""
        youtube_patterns = [
            r'^https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/playlist\?list=[\w-]+',
            r'^https?://(?:www\.)?youtu\.be/[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/embed/[\w-]+',
            r'^https?://(?:www\.)?youtube\.com/v/[\w-]+',
        ]

        return any(re.match(pattern, url) for pattern in youtube_patterns)

    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract video ID from YouTube URL."""
        try:
            parsed_url = urlparse(url)

            if parsed_url.hostname in ['www.youtube.com', 'youtube.com']:
                if parsed_url.path == '/watch':
                    query = parse_qs(parsed_url.query)
                    return query.get('v', [None])[0]
                elif parsed_url.path.startswith('/embed/'):
                    return parsed_url.path.split('/')[2]
                elif parsed_url.path.startswith('/v/'):
                    return parsed_url.path.split('/')[2]
            elif parsed_url.hostname == 'youtu.be':
                return parsed_url.path[1:]  # Remove leading slash

            return None
        except Exception:
            return None

    def _format_duration(self, duration_seconds: int) -> str:
        """Format duration in seconds to human readable format."""
        if not duration_seconds:
            return "Unknown"

        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        seconds = duration_seconds % 60

        if hours > 0:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes}:{seconds:02d}"

    def _format_view_count(self, view_count: int) -> str:
        """Format view count to human readable format."""
        if not view_count:
            return "0 views"

        if view_count >= 1_000_000:
            return f"{view_count / 1_000_000:.1f}M views"
        elif view_count >= 1_000:
            return f"{view_count / 1_000:.1f}K views"
        else:
            return f"{view_count} views"

    def _format_upload_date(self, upload_date: str) -> str:
        """Format upload date from YYYYMMDD to readable format."""
        if not upload_date or len(upload_date) != 8:
            return "Unknown date"

        try:
            year = upload_date[:4]
            month = upload_date[4:6]
            day = upload_date[6:8]
            return f"{month}/{day}/{year}"
        except Exception:
            return "Unknown date"

    def _extract_qualities(self, info: Dict[str, Any]) -> List[str]:
        """Return standard video qualities from 144p to 4K."""
        # Just return the standard quality options, yt-dlp will handle fallbacks
        return ['144p', '240p', '360p', '480p', '720p', '1080p', '1440p', '4K']

    def _extract_formats(self, info: Dict[str, Any]) -> List[str]:
        """Extract available formats - always return the 4 main options."""
        # Always return the 4 format options the user can choose from:
        # video_only: video without audio
        # video_audio: video with audio combined
        # audio_only: audio only
        # separate: video and audio as separate files

        return ['video_only', 'video_audio', 'audio_only', 'separate']

    def _extract_subtitles(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract subtitle information from info dict."""
        subtitles = []

        # Add "None" option first
        subtitles.append({
            'language_code': 'none',
            'language_name': 'None',
            'is_auto_generated': False,
            'url': ''
        })

        # Get manual subtitles
        manual_subs = info.get('subtitles', {})
        for lang_code, sub_list in manual_subs.items():
            if sub_list:
                sub_info = sub_list[0]  # Take first subtitle format
                subtitles.append({
                    'language_code': lang_code,
                    'language_name': self._get_language_name(lang_code),
                    'is_auto_generated': False,
                    'url': sub_info.get('url', '')
                })

        # Get automatic subtitles
        auto_subs = info.get('automatic_captions', {})
        for lang_code, sub_list in auto_subs.items():
            if sub_list:
                sub_info = sub_list[0]  # Take first subtitle format
                subtitles.append({
                    'language_code': lang_code,
                    'language_name': f"{self._get_language_name(lang_code)} (Auto)",
                    'is_auto_generated': True,
                    'url': sub_info.get('url', '')
                })

        return subtitles

    def _get_language_name(self, lang_code: str) -> str:
        """Convert language code to readable language name."""
        language_names = {
            'en': 'English',
            'es': 'Spanish',
            'fr': 'French',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ru': 'Russian',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'hi': 'Hindi',
        }

        return language_names.get(lang_code.split('-')[0], lang_code)