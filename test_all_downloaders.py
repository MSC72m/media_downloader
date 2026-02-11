#!/usr/bin/env python3
"""
Comprehensive downloader service test script.

Tests all downloader services (YouTube, Twitter, Pinterest, Spotify,
SoundCloud, RadioJavan, TikTok) with real URLs to verify they work.

Usage:
    uv run python test_all_downloaders.py
    uv run python test_all_downloaders.py --service youtube
    uv run python test_all_downloaders.py --service twitter --service soundcloud
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure src is importable
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_all_downloaders")

# ── Test URLs ────────────────────────────────────────────────────────

YOUTUBE_URLS = [
    # Short public-domain-ish videos
    "https://www.youtube.com/watch?v=jNQXAC9IVRw",  # Me at the zoo (first YT video)
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Astley
]

TWITTER_URLS = [
    "https://x.com/Interior/status/463440424141459456",  # Stable tweet with image media
    "https://x.com/jack/status/20",  # Historical tweet (text-only)
]

PINTEREST_URLS = [
    "https://www.pinterest.com/pin/474355773246498953/",
    "https://www.pinterest.com/pin/312296555403025498/",
]

SPOTIFY_URLS = [
    "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",  # Rick Astley
    "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3",  # Shape of You
]

SOUNDCLOUD_URLS = [
    "https://soundcloud.com/forss/flickermood",
]

RADIOJAVAN_URLS = [
    "https://www.radiojavan.com/mp3/Mohsen-Yeganeh-Behet-Ghol-Midam",
]

TIKTOK_URLS = [
    "https://www.tiktok.com/@zachking/video/6768504823220512005",
]


@dataclass
class TestResult:
    """Result of a single test."""

    service: str
    url: str
    test_type: str  # "metadata", "download", "detection", "connection"
    success: bool
    duration_seconds: float = 0.0
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "✅ PASS" if self.success else "❌ FAIL"
        msg = f"  {status} [{self.service}] {self.test_type}"
        if self.error:
            msg += f"\n         Error: {self.error[:200]}"
        if self.duration_seconds > 0:
            msg += f"  ({self.duration_seconds:.1f}s)"
        return msg


class DownloaderTestSuite:
    """Tests all downloader services."""

    def __init__(self, tmp_dir: str):
        self.tmp_dir = tmp_dir
        self.results: list[TestResult] = []

    # ── Helpers ───────────────────────────────────────────────────────

    def _run_test(
        self,
        service: str,
        test_type: str,
        url: str,
        func,
        **kwargs,
    ) -> TestResult:
        """Run a test function and capture results."""
        start = time.time()
        try:
            details = func(url, **kwargs) or {}
            elapsed = time.time() - start
            result = TestResult(
                service=service,
                url=url,
                test_type=test_type,
                success=True,
                duration_seconds=elapsed,
                details=details if isinstance(details, dict) else {},
            )
        except Exception as e:
            elapsed = time.time() - start
            result = TestResult(
                service=service,
                url=url,
                test_type=test_type,
                success=False,
                duration_seconds=elapsed,
                error=f"{type(e).__name__}: {e}",
            )
            logger.debug(traceback.format_exc())

        self.results.append(result)
        print(result)
        return result

    def _make_save_path(self, service: str, name: str) -> str:
        """Create a save path inside the temp directory."""
        svc_dir = os.path.join(self.tmp_dir, service)
        os.makedirs(svc_dir, exist_ok=True)
        return os.path.join(svc_dir, name)

    # ── YouTube ───────────────────────────────────────────────────────

    def test_youtube_metadata(self):
        """Test YouTube metadata extraction."""
        print("\n" + "=" * 60)
        print("YOUTUBE - Metadata Extraction")
        print("=" * 60)

        from src.services.youtube.info_extractor import YouTubeInfoExtractor

        extractor = YouTubeInfoExtractor()

        for url in YOUTUBE_URLS[:2]:

            def extract_meta(u):
                info = extractor.extract_info(u)
                if not info:
                    raise RuntimeError("extract_info returned None")
                return {
                    "title": info.get("title", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "uploader": info.get("uploader", ""),
                }

            self._run_test("YouTube", "metadata", url, extract_meta)

    def test_youtube_metadata_service(self):
        """Test the higher-level metadata service."""
        print("\n" + "=" * 60)
        print("YOUTUBE - Metadata Service")
        print("=" * 60)

        from src.services.youtube.metadata_service import YouTubeMetadataService

        service = YouTubeMetadataService()

        url = YOUTUBE_URLS[0]

        def fetch_meta(u):
            meta = service.fetch_metadata(u)
            if meta is None:
                raise RuntimeError("fetch_metadata returned None")
            if meta.error:
                raise RuntimeError(f"Metadata error: {meta.error}")
            return {
                "title": meta.title,
                "duration": meta.duration,
                "channel": meta.channel,
                "qualities": meta.available_qualities[:5] if meta.available_qualities else [],
            }

        self._run_test("YouTube", "metadata_service", url, fetch_meta)

    def test_youtube_download(self):
        """Test YouTube download (short video)."""
        print("\n" + "=" * 60)
        print("YOUTUBE - Download")
        print("=" * 60)

        from src.services.youtube.downloader import YouTubeDownloader

        # Download shortest possible video
        url = YOUTUBE_URLS[0]  # "Me at the zoo" - 19 seconds

        def do_download(u):
            downloader = YouTubeDownloader(
                quality="lowest",
                audio_only=False,
                download_thumbnail=False,
                embed_metadata=False,
            )
            save_path = self._make_save_path("youtube", "test_video")
            ok = downloader.download(u, save_path)
            if not ok:
                raise RuntimeError("Download returned False")

            # Check that some file was created
            svc_dir = os.path.join(self.tmp_dir, "youtube")
            files = os.listdir(svc_dir) if os.path.isdir(svc_dir) else []
            return {"files": files, "save_path": save_path}

        self._run_test("YouTube", "download", url, do_download)

    # ── Twitter ───────────────────────────────────────────────────────

    def test_twitter(self):
        """Test Twitter downloader."""
        print("\n" + "=" * 60)
        print("TWITTER - Download")
        print("=" * 60)

        from src.services.twitter.downloader import TwitterDownloader

        downloader = TwitterDownloader()

        url = TWITTER_URLS[0]

        # Test scraping
        def test_scrape(u):
            tweet_refs = TwitterDownloader._extract_tweet_references(u)
            if not tweet_refs:
                raise RuntimeError("No tweet references extracted")
            username, tweet_id = tweet_refs[0]
            data = downloader._scrape_tweet_data(tweet_id, username)
            if not data:
                raise RuntimeError("Failed to scrape tweet data")
            return {
                "tweet_refs": tweet_refs,
                "has_media": bool(data.get("media")),
                "has_text": bool(data.get("text")),
                "media_count": len(data.get("media", [])),
            }

        self._run_test("Twitter", "scrape_data", url, test_scrape)

        # Test download
        def test_download(u):
            save_path = self._make_save_path("twitter", "tweet_media")
            ok = downloader.download(u, save_path)
            if not ok:
                raise RuntimeError("Download returned False")
            svc_dir = os.path.join(self.tmp_dir, "twitter")
            files = os.listdir(svc_dir) if os.path.isdir(svc_dir) else []
            return {"files": files}

        self._run_test("Twitter", "download", url, test_download)

    # ── Pinterest ─────────────────────────────────────────────────────

    def test_pinterest(self):
        """Test Pinterest downloader."""
        print("\n" + "=" * 60)
        print("PINTEREST - Download")
        print("=" * 60)

        from src.services.pinterest.downloader import PinterestDownloader

        downloader = PinterestDownloader()

        url = PINTEREST_URLS[0]

        # Test media URL extraction
        def test_media_url(u):
            media_url = downloader._get_media_url(u)
            if not media_url:
                raise RuntimeError("Could not extract media URL")
            return {"media_url": media_url[:100]}

        self._run_test("Pinterest", "media_url_extraction", url, test_media_url)

        # Test download
        def test_download(u):
            save_path = self._make_save_path("pinterest", "pin_image")
            ok = downloader.download(u, save_path)
            if not ok:
                raise RuntimeError("Download returned False")
            svc_dir = os.path.join(self.tmp_dir, "pinterest")
            files = os.listdir(svc_dir) if os.path.isdir(svc_dir) else []
            return {"files": files}

        self._run_test("Pinterest", "download", url, test_download)

    # ── Spotify ───────────────────────────────────────────────────────

    def test_spotify(self):
        """Test Spotify metadata and YouTube search."""
        print("\n" + "=" * 60)
        print("SPOTIFY - Metadata & Search")
        print("=" * 60)

        from src.services.spotify.downloader import SpotifyDownloader

        downloader = SpotifyDownloader()

        url = SPOTIFY_URLS[0]

        # Test metadata extraction
        def test_metadata(u):
            meta = downloader._extract_spotify_metadata(u)
            if not meta or meta.get("title") == "Spotify Track":
                # OEmbed might fail, but we should still get some data
                logger.warning("OEmbed returned default title - may be rate limited")
            return {
                "title": meta.get("title", ""),
                "type": meta.get("type", ""),
                "thumbnail": bool(meta.get("thumbnail")),
            }

        self._run_test("Spotify", "metadata", url, test_metadata)

        # Test YouTube search
        def test_search(u):
            meta = downloader._extract_spotify_metadata(u)
            title = meta.get("title", "Rick Astley Never Gonna Give You Up")
            artist, track = SpotifyDownloader._parse_artist_track(title)
            if not artist:
                artist = "Rick Astley"
            if not track:
                track = "Never Gonna Give You Up"
            results = downloader._search_youtube(artist, track)
            if not results:
                raise RuntimeError("No YouTube search results found")
            return {
                "artist": artist,
                "track": track,
                "result_count": len(results),
                "first_title": results[0].get("title", "") if results else "",
            }

        self._run_test("Spotify", "youtube_search", url, test_search)

        # Test URL type detection
        def test_type_detection(u):
            url_type = downloader._detect_url_type(u)
            spotify_id = downloader._extract_spotify_id(u)
            return {"type": url_type, "id": spotify_id}

        self._run_test("Spotify", "url_detection", url, test_type_detection)

    # ── SoundCloud ────────────────────────────────────────────────────

    def test_soundcloud(self):
        """Test SoundCloud downloader."""
        print("\n" + "=" * 60)
        print("SOUNDCLOUD - Info & Download")
        print("=" * 60)

        from src.services.soundcloud.downloader import SoundCloudDownloader

        downloader = SoundCloudDownloader(
            audio_format="mp3",
            audio_quality="128",
            download_thumbnail=False,
            embed_metadata=False,
        )

        url = SOUNDCLOUD_URLS[0]

        # Test info extraction
        def test_info(u):
            info = downloader.get_info(u)
            if not info:
                raise RuntimeError("get_info returned None")
            return {
                "title": info.get("title", ""),
                "artist": info.get("artist", ""),
                "duration": info.get("duration", 0),
                "is_premium": info.get("is_available", True) is False,
            }

        self._run_test("SoundCloud", "info", url, test_info)

        # Test download
        def test_download(u):
            save_path = self._make_save_path("soundcloud", "sc_track")
            ok = downloader.download(u, save_path)
            if not ok:
                raise RuntimeError("Download returned False")
            svc_dir = os.path.join(self.tmp_dir, "soundcloud")
            files = os.listdir(svc_dir) if os.path.isdir(svc_dir) else []
            return {"files": files}

        self._run_test("SoundCloud", "download", url, test_download)

    # ── RadioJavan ────────────────────────────────────────────────────

    def test_radiojavan(self):
        """Test RadioJavan downloader."""
        print("\n" + "=" * 60)
        print("RADIOJAVAN - URL Construction & Download")
        print("=" * 60)

        from src.services.radiojavan.downloader import RadioJavanDownloader

        downloader = RadioJavanDownloader()

        url = RADIOJAVAN_URLS[0]

        # Test media name extraction
        def test_extract(u):
            media_name = downloader._extract_media_name(u)
            if not media_name:
                raise RuntimeError("Could not extract media name")
            return {"media_name": media_name}

        self._run_test("RadioJavan", "media_name_extraction", url, test_extract)

        # Test URL construction
        def test_construct(u):
            download_url = downloader._construct_download_url(u)
            if not download_url:
                raise RuntimeError(
                    "Could not construct download URL "
                    "(CDN hosts may be unreachable or media removed)"
                )
            return {"download_url": download_url[:100]}

        self._run_test("RadioJavan", "url_construction", url, test_construct)

    # ── TikTok ────────────────────────────────────────────────────────

    def test_tiktok(self):
        """Test TikTok downloader."""
        print("\n" + "=" * 60)
        print("TIKTOK - Download")
        print("=" * 60)

        from src.services.tiktok.downloader import TikTokDownloader

        downloader = TikTokDownloader()

        url = TIKTOK_URLS[0]

        def test_download(u):
            save_path = self._make_save_path("tiktok", "tiktok_video")
            ok = downloader.download(u, save_path)
            if not ok:
                raise RuntimeError("Download returned False")
            svc_dir = os.path.join(self.tmp_dir, "tiktok")
            files = os.listdir(svc_dir) if os.path.isdir(svc_dir) else []
            return {"files": files}

        self._run_test("TikTok", "download", url, test_download)

    # ── Link Detection ────────────────────────────────────────────────

    def test_link_detection(self):
        """Test that the link detector correctly identifies services."""
        print("\n" + "=" * 60)
        print("LINK DETECTION - URL Matching")
        print("=" * 60)

        from src.core.config import get_config

        config = get_config()

        test_cases = [
            ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
            ("https://youtu.be/dQw4w9WgXcQ", "youtube"),
            ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "youtube"),
            ("https://twitter.com/user/status/123456", "twitter"),
            ("https://x.com/user/status/123456", "twitter"),
            ("https://www.pinterest.com/pin/123456/", "pinterest"),
            ("https://pin.it/abc123", "pinterest"),
            ("https://open.spotify.com/track/abc123", "spotify"),
            ("https://soundcloud.com/artist/track", "soundcloud"),
            ("https://www.radiojavan.com/mp3/Artist-Song", "radiojavan"),
            ("https://www.tiktok.com/@user/video/123456", "tiktok"),
        ]

        import re

        service_patterns = {
            "youtube": config.youtube.url_patterns,
            "twitter": config.twitter.url_patterns,
            "pinterest": config.pinterest.url_patterns,
            "spotify": config.spotify.url_patterns,
            "soundcloud": config.soundcloud.url_patterns,
            "radiojavan": config.radiojavan.url_patterns,
            "tiktok": config.tiktok.url_patterns,
        }

        for url, expected_service in test_cases:

            def test_detection(u, svc=expected_service):
                patterns = service_patterns.get(svc, [])
                matched = any(re.match(p, u) for p in patterns)
                if not matched:
                    raise RuntimeError(
                        f"URL not matched by {svc} patterns. Patterns: {patterns[:3]}..."
                    )
                return {"matched_service": svc, "pattern_count": len(patterns)}

            self._run_test(
                expected_service.capitalize(),
                "link_detection",
                url,
                test_detection,
            )

    # ── Cookie System ─────────────────────────────────────────────────

    def test_cookie_system(self):
        """Test the cookie generation system."""
        print("\n" + "=" * 60)
        print("COOKIES - Cookie System")
        print("=" * 60)

        from src.services.cookies.cookie_generator import CookieGenerator

        # Test Netscape file validation
        def test_netscape_validation(url_input):
            del url_input
            generator = CookieGenerator(storage_dir=Path(self.tmp_dir) / "cookies")
            # Create a sample Netscape file
            cookie_dir = Path(self.tmp_dir) / "cookies"
            cookie_dir.mkdir(parents=True, exist_ok=True)
            sample = cookie_dir / "test_cookies.txt"
            sample.write_text(
                "# Netscape HTTP Cookie File\n"
                ".youtube.com\tTRUE\t/\tTRUE\t0\tYSC\ttest_value\n"
                ".youtube.com\tTRUE\t/\tFALSE\t0\tPREF\thl=en\n"
            )
            valid = generator.validate_netscape_file(str(sample))
            if not valid:
                raise RuntimeError("Netscape file validation failed")
            return {"valid": valid}

        self._run_test("Cookies", "netscape_validation", "N/A", test_netscape_validation)

        # Test cookie file on disk
        def test_existing_cookies(url_input):
            del url_input
            cookie_path = Path.home() / ".media_downloader" / "cookies.txt"
            if not cookie_path.exists():
                raise RuntimeError(f"No cookie file at {cookie_path}")
            size = cookie_path.stat().st_size
            lines = cookie_path.read_text().strip().split("\n")
            data_lines = [line for line in lines if line.strip() and not line.startswith("#")]
            return {
                "path": str(cookie_path),
                "size_bytes": size,
                "total_lines": len(lines),
                "cookie_lines": len(data_lines),
            }

        self._run_test("Cookies", "existing_file_check", "N/A", test_existing_cookies)

    # ── Network Connectivity ──────────────────────────────────────────

    def test_connectivity(self):
        """Test network connectivity to all services."""
        print("\n" + "=" * 60)
        print("NETWORK - Connectivity")
        print("=" * 60)

        from src.core.enums import ServiceType
        from src.services.network.checker import check_site_connection

        services = [
            ServiceType.YOUTUBE,
            ServiceType.TWITTER,
            ServiceType.PINTEREST,
            ServiceType.SOUNDCLOUD,
        ]

        for svc in services:

            def test_conn(url_input, service=svc):
                del url_input
                connected, error_msg = check_site_connection(service)
                if not connected:
                    raise RuntimeError(f"Connection failed: {error_msg}")
                return {"connected": connected}

            self._run_test(svc.name.capitalize(), "connectivity", svc.value, test_conn)

    # ── Run All ───────────────────────────────────────────────────────

    def run_all(self, services: list[str] | None = None):
        """Run all tests (or filter by service names)."""
        all_tests = {
            "connectivity": self.test_connectivity,
            "detection": self.test_link_detection,
            "cookies": self.test_cookie_system,
            "youtube": lambda: (
                self.test_youtube_metadata(),
                self.test_youtube_metadata_service(),
                self.test_youtube_download(),
            ),
            "twitter": self.test_twitter,
            "pinterest": self.test_pinterest,
            "spotify": self.test_spotify,
            "soundcloud": self.test_soundcloud,
            "radiojavan": self.test_radiojavan,
            "tiktok": self.test_tiktok,
        }

        selected = {k: v for k, v in all_tests.items() if k in services} if services else all_tests

        for name, test_fn in selected.items():
            try:
                test_fn()
            except Exception as e:
                logger.error(f"Test suite [{name}] crashed: {e}")
                traceback.print_exc()

    def print_summary(self):
        """Print a summary of all test results."""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)

        passed = sum(1 for r in self.results if r.success)
        failed = sum(1 for r in self.results if not r.success)
        total = len(self.results)

        # Group by service
        services: dict[str, list[TestResult]] = {}
        for r in self.results:
            services.setdefault(r.service, []).append(r)

        for svc, results in sorted(services.items()):
            svc_pass = sum(1 for r in results if r.success)
            svc_total = len(results)
            status = "✅" if svc_pass == svc_total else "⚠️" if svc_pass > 0 else "❌"
            print(f"\n{status} {svc}: {svc_pass}/{svc_total} passed")
            for r in results:
                icon = "  ✓" if r.success else "  ✗"
                line = f"    {icon} {r.test_type} ({r.duration_seconds:.1f}s)"
                if not r.success and r.error:
                    line += f"\n        → {r.error[:150]}"
                print(line)

        print(f"\n{'=' * 60}")
        print(f"TOTAL: {passed}/{total} passed, {failed} failed")
        if failed == 0:
            print("🎉 All tests passed!")
        else:
            print(f"⚠️  {failed} test(s) need attention")
        print("=" * 60)

        # Write JSON report
        report_path = Path(__file__).parent / "test_report.json"
        report = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "results": [
                {
                    "service": r.service,
                    "test_type": r.test_type,
                    "url": r.url,
                    "success": r.success,
                    "duration": round(r.duration_seconds, 2),
                    "error": r.error,
                    "details": r.details,
                }
                for r in self.results
            ],
        }
        report_path.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nDetailed report saved to: {report_path}")

        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Test all downloader services")
    parser.add_argument(
        "--service",
        action="append",
        dest="services",
        help="Filter to specific service(s). Can be repeated. "
        "Options: youtube, twitter, pinterest, spotify, soundcloud, radiojavan, tiktok, "
        "cookies, connectivity, detection",
    )
    parser.add_argument(
        "--keep-files",
        action="store_true",
        help="Don't delete downloaded test files",
    )
    args = parser.parse_args()

    tmp_dir = tempfile.mkdtemp(prefix="media_dl_test_")
    print(f"Test download directory: {tmp_dir}")

    try:
        suite = DownloaderTestSuite(tmp_dir)
        suite.run_all(args.services)
        all_passed = suite.print_summary()
    finally:
        if not args.keep_files:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            print(f"\nCleaned up temp directory: {tmp_dir}")
        else:
            print(f"\nTest files kept at: {tmp_dir}")

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
