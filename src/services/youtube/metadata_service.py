"""YouTube metadata service implementation."""

import yt_dlp
import json
import re
import subprocess
import os
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

    def fetch_metadata(self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None) -> Optional[YouTubeMetadata]:
        """Fetch basic metadata for a YouTube URL without fetching formats."""
        try:
            logger.info(f"Fetching metadata for URL: {url}")

            if not self.validate_url(url):
                return YouTubeMetadata(error="Invalid YouTube URL")

            # Get basic video info without fetching formats to avoid storyboard noise
            info = self._get_basic_video_info(url, cookie_path, browser)
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

    def _get_basic_video_info(self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get basic video info using command line yt-dlp instead of Python API."""
        try:
            # Build command line arguments
            cmd = ['.venv/bin/yt-dlp']

            # Add cookies if available
            print(f"DEBUG: Metadata service received cookie_path: {cookie_path}")
            print(f"DEBUG: Browser parameter: {browser}")

            # Priority 1: Use browser parameter if provided
            if browser:
                cmd.extend(['--cookies-from-browser', browser])
                print(f"DEBUG: Using cookies-from-browser: {browser}")

            # Priority 2: Use manual cookie path if provided
            elif cookie_path:
                if os.path.exists(cookie_path):
                    cmd.extend(['--cookies', cookie_path])
                    print(f"DEBUG: Using cookies file: {cookie_path}")
                else:
                    print(f"DEBUG: Cookie file does not exist: {cookie_path}")

            else:
                print("DEBUG: No cookies will be used")

            # Add other options
            cmd.extend([
                '--quiet',
                '--no-warnings',
                '--skip-download',
                '--no-playlist',
                '--print', 'title',
                '--print', 'duration',
                '--print', 'view_count',
                '--print', 'upload_date',
                '--print', 'channel',
                '--print', 'description',
                '--print', 'thumbnail',
                url
            ])

            print(f"DEBUG: Running command: {' '.join(cmd)}")

            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0:
                # Parse multi-line output
                try:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) >= 7:
                        # Get REAL subtitle data
                        subtitles_data = self._get_real_subtitles(url, cookie_path, browser)

                        info = {
                            'title': lines[0] if lines[0] != 'NA' else '',
                            'duration': int(lines[1]) if lines[1] != 'NA' else 0,
                            'view_count': int(lines[2]) if lines[2] != 'NA' else 0,
                            'upload_date': lines[3] if lines[3] != 'NA' else '',
                            'channel': lines[4] if lines[4] != 'NA' else '',
                            'description': lines[5] if lines[5] != 'NA' else '',
                            'thumbnail': lines[6] if lines[6] != 'NA' else '',
                            'subtitles': subtitles_data.get('subtitles', {}),
                            'automatic_captions': subtitles_data.get('automatic_captions', {})
                        }
                        print("DEBUG: Successfully fetched video info via command line")
                        logger.info("Successfully fetched basic video info")
                        return info
                    else:
                        print(f"DEBUG: Unexpected output format: {len(lines)} lines")
                        print(f"DEBUG: Raw output: {result.stdout[:500]}...")
                except Exception as e:
                    print(f"DEBUG: Failed to parse output: {e}")
                    print(f"DEBUG: Raw output: {result.stdout[:500]}...")
            else:
                print(f"DEBUG: Command failed with return code {result.returncode}")
                print(f"DEBUG: Error output: {result.stderr}")

        except subprocess.TimeoutExpired:
            print("DEBUG: Command timed out")
            logger.warning("Command line yt-dlp timed out")
        except Exception as e:
            logger.warning(f"Command line extraction failed: {e}")
            print(f"DEBUG: Command line error: {e}")

        # Fallback without cookies if cookies failed
        if cookie_path or browser:
            print("DEBUG: Trying fallback without cookies...")
            try:
                cmd_fallback = ['.venv/bin/yt-dlp',
                    '--quiet',
                    '--no-warnings',
                    '--skip-download',
                    '--no-playlist',
                    '--print', 'title',
                    '--print', 'duration',
                    '--print', 'view_count',
                    '--print', 'upload_date',
                    '--print', 'channel',
                    '--print', 'description',
                    '--print', 'thumbnail',
                    url
                ]

                print(f"DEBUG: Running fallback command: {' '.join(cmd_fallback)}")
                result = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=60)

                if result.returncode == 0:
                    try:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) >= 7:
                            # Get REAL subtitle data for fallback too
                            subtitles_data = self._get_real_subtitles(url, None, None)

                            info = {
                                'title': lines[0] if lines[0] != 'NA' else '',
                                'duration': int(lines[1]) if lines[1] != 'NA' else 0,
                                'view_count': int(lines[2]) if lines[2] != 'NA' else 0,
                                'upload_date': lines[3] if lines[3] != 'NA' else '',
                                'channel': lines[4] if lines[4] != 'NA' else '',
                                'description': lines[5] if lines[5] != 'NA' else '',
                                'thumbnail': lines[6] if lines[6] != 'NA' else '',
                                'subtitles': subtitles_data.get('subtitles', {}),
                                'automatic_captions': subtitles_data.get('automatic_captions', {})
                            }
                            print("DEBUG: Successfully fetched video info via fallback command")
                            logger.info("Successfully fetched basic video info without cookies")
                            return info
                        else:
                            print(f"DEBUG: Unexpected fallback output format: {len(lines)} lines")
                            print(f"DEBUG: Raw fallback output: {result.stdout[:500]}...")
                    except Exception as e:
                        print(f"DEBUG: Failed to parse fallback output: {e}")
                else:
                    print(f"DEBUG: Fallback command failed with return code {result.returncode}")
                    print(f"DEBUG: Fallback error output: {result.stderr}")

            except Exception as e:
                logger.error(f"Fallback command line extraction failed: {e}")
                print(f"DEBUG: Fallback command line error: {e}")

        return None

    def _get_real_subtitles(self, url: str, cookie_path: Optional[str] = None, browser: Optional[str] = None) -> Dict[str, Any]:
        """Get REAL subtitle data from yt-dlp."""
        try:
            # Build command for subtitle info only
            cmd = ['.venv/bin/yt-dlp']

            # Add cookies if available
            if browser:
                cmd.extend(['--cookies-from-browser', browser])
            elif cookie_path and os.path.exists(cookie_path):
                cmd.extend(['--cookies', cookie_path])

            # Add subtitle-specific options
            cmd.extend([
                '--quiet',
                '--no-warnings',
                '--skip-download',
                '--no-playlist',
                '--list-subs',
                url
            ])

            print(f"DEBUG: Running subtitle command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                return self._parse_subtitle_output(result.stdout)
            else:
                print(f"DEBUG: Subtitle command failed: {result.stderr}")

        except Exception as e:
            print(f"DEBUG: Error getting subtitles: {e}")

        # Return empty data on failure
        return {'subtitles': {}, 'automatic_captions': {}}

    def _parse_subtitle_output(self, output: str) -> Dict[str, Any]:
        """Parse yt-dlp --list-subs output."""
        subtitles = {}
        automatic_captions = {}

        try:
            lines = output.strip().split('\n')

            # Parse the subtitle format
            # Example output:
            # Language Name                  Formats
            # en                             vtt, srt, ttml, srv3, srv2, srv1, json3
            # en-US                          vtt, srt, ttml, srv3, srv2, srv1, json3 (auto)

            current_section = None  # 'subtitles' or 'automatic_captions'

            for line in lines:
                line = line.strip()

                if line.startswith('Language formats available'):
                    continue
                elif line.startswith('Available automatic captions'):
                    current_section = 'automatic_captions'
                    continue
                elif line.startswith('Available subtitles'):
                    current_section = 'subtitles'
                    continue
                elif not line or line.startswith('-') or line.startswith('Formats'):
                    continue

                # Parse language line
                if '  ' in line and any(fmt in line for fmt in ['vtt', 'srt', 'ttml']):
                    parts = line.split('  ')
                    if len(parts) >= 2:
                        lang_code = parts[0].strip()
                        formats_info = ' '.join(parts[1:]).strip()

                        # Check if it's auto-generated
                        is_auto = '(auto)' in formats_info

                        # Create entry
                        entry = [{'url': ''}]  # We don't need real URLs for selection

                        if is_auto:
                            automatic_captions[lang_code] = entry
                        else:
                            subtitles[lang_code] = entry

                        print(f"DEBUG: Found subtitle: {lang_code} (auto: {is_auto})")

            print(f"DEBUG: Parsed {len(subtitles)} manual subtitles, {len(automatic_captions)} auto captions")

        except Exception as e:
            print(f"DEBUG: Error parsing subtitle output: {e}")
            print(f"DEBUG: Raw subtitle output: {output[:500]}...")

        return {
            'subtitles': subtitles,
            'automatic_captions': automatic_captions
        }

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

        # Get manual subtitles from REAL data
        manual_subs = info.get('subtitles', {})
        for lang_code, sub_list in manual_subs.items():
            if sub_list:
                subtitles.append({
                    'language_code': lang_code,
                    'language_name': self._get_language_name(lang_code),
                    'is_auto_generated': False,
                    'url': sub_list[0].get('url', '')
                })

        # Get automatic subtitles from REAL data
        auto_subs = info.get('automatic_captions', {})
        for lang_code, sub_list in auto_subs.items():
            if sub_list:
                subtitles.append({
                    'language_code': lang_code,
                    'language_name': f"{self._get_language_name(lang_code)} (Auto)",
                    'is_auto_generated': True,
                    'url': sub_list[0].get('url', '')
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