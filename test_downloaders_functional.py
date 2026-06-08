#!/usr/bin/env python3
"""Real functional test - actually downloads from each platform."""

import os
import sys
import tempfile

sys.path.insert(0, "/Users/msc8/code/media_downloader/src")

from src.core.config import get_config
from src.services.file.service import FileService


class MockError:
    def handle_service_failure(self, *a, **kw):
        pass

    def handle_exception(self, *a, **kw):
        pass

    def show_error(self, *a, **kw):
        pass

    def show_warning(self, *a, **kw):
        pass

    def show_info(self, *a, **kw):
        pass

    def set_message_queue(self, *a):
        pass


config = get_config()
err = MockError()
fs = FileService()

# Test URLs (public, non-age-restricted content)
TESTS = [
    (
        "TikTok",
        "src.services.tiktok.downloader",
        "TikTokDownloader",
        "https://www.tiktok.com/@scout2015/video/6718335390845095173",
    ),
    (
        "RadioJavan",
        "src.services.radiojavan.downloader",
        "RadioJavanDownloader",
        "https://www.radiojavan.com/mp3/shadmehr-asteni",
    ),
    (
        "SoundCloud",
        "src.services.soundcloud.downloader",
        "SoundCloudDownloader",
        "https://soundcloud.com/artist/track",
    ),
    (
        "Spotify",
        "src.services.spotify.downloader",
        "SpotifyDownloader",
        "https://open.spotify.com/track/4cOdK2wElTn0XaukXr0pZe",
    ),
    (
        "YouTube",
        "src.services.youtube.downloader",
        "YouTubeDownloader",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ),
    (
        "Instagram",
        "src.services.instagram.downloader",
        "InstagramDownloader",
        "https://www.instagram.com/p/Czexample123/",
    ),
    (
        "Twitter",
        "src.services.twitter.downloader",
        "TwitterDownloader",
        "https://twitter.com/elonmusk/status/1234567890",
    ),
]

results = {}
with tempfile.TemporaryDirectory() as tmpdir:
    for name, module_path, class_name, url in TESTS:
        print(f"\n{'=' * 60}")
        print(f"{name}")
        print(f"{'=' * 60}")
        try:
            mod = __import__(module_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            dl = cls(error_handler=err, file_service=fs, config=config)
            save_path = os.path.join(tmpdir, f"{name}_test")
            os.makedirs(save_path, exist_ok=True)

            print(f"  Downloading: {url}")
            ok = dl.download(url, save_path)
            print(f"  download() returned: {ok}")

            # Check for files
            files = os.listdir(save_path) if os.path.exists(save_path) else []
            media_files = [f for f in files if not f.startswith(".")]
            print(f"  Files created: {len(media_files)} {media_files[:3]}")

            if ok and media_files:
                results[name] = "✅ WORKING"
            elif ok:
                results[name] = "⚠️ download()=True but no files (may need different URL)"
            else:
                results[name] = "❌ download() returned False"
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            results[name] = f"❌ {type(e).__name__}: {e}"

print(f"\n{'=' * 60}")
print("FINAL RESULTS")
print(f"{'=' * 60}")
for name, status in results.items():
    print(f"  {name:15s} {status}")
