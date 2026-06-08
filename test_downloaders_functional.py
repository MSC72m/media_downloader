#!/usr/bin/env python3
"""Functional test with real URLs for all downloaders."""

import os
import sys
import tempfile

sys.path.insert(0, "/Users/msc8/code/media_downloader/src")

from src.core.config import get_config
from src.services.file.service import FileService


class MockError:
    def handle_service_failure(self, *a, **kw): pass
    def handle_exception(self, *a, **kw): pass
    def show_error(self, *a, **kw): pass
    def show_warning(self, *a, **kw): pass
    def show_info(self, *a, **kw): pass
    def set_message_queue(self, *a): pass


config = get_config()
err = MockError()
fs = FileService()

TESTS = [
    ("SoundCloud",  "src.services.soundcloud.downloader",  "SoundCloudDownloader",  "https://soundcloud.com/forss/flickermood"),
    ("Spotify",     "src.services.spotify.downloader",     "SpotifyDownloader",     "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUc9Lp"),
    ("TikTok",      "src.services.tiktok.downloader",      "TikTokDownloader",      "https://www.tiktok.com/@scout2015/video/6718335390845095173"),
    ("RadioJavan",  "src.services.radiojavan.downloader",  "RadioJavanDownloader",  "https://www.radiojavan.com/mp3s/mp3/Arash-Boro-Boro"),
    ("Twitter",     "src.services.twitter.downloader",     "TwitterDownloader",     "https://x.com/SpaceX/status/1798743372168431848"),
    ("YouTube",     "src.services.youtube.downloader",     "YouTubeDownloader",     "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ("Instagram",   "src.services.instagram.downloader",   "InstagramDownloader",   "https://www.instagram.com/p/CuJtqA2sM4x/"),
]

results = {}
with tempfile.TemporaryDirectory() as tmpdir:
    for name, module_path, class_name, url in TESTS:
        print(f"\n{'=' * 60}")
        print(f"  {name}")
        print(f"{'=' * 60}")
        try:
            mod = __import__(module_path, fromlist=[class_name])
            cls = getattr(mod, class_name)
            dl = cls(error_handler=err, file_service=fs, config=config)

            save_path = os.path.join(tmpdir, name.replace(" ", "_"))
            print(f"  URL: {url}")
            print(f"  Save path (no ext): {save_path}")
            ok = dl.download(url, save_path)
            print(f"  download() returned: {ok}")

            # Check for files in the temp dir (downloaders may create files
            # with added extension near save_path)
            files = [f for f in os.listdir(tmpdir) if not f.startswith(".")]
            name_files = [f for f in files if f.startswith(name.replace(" ", "_"))]
            print(f"  Files created: {len(name_files)} {name_files[:3]}")

            if ok and name_files:
                sizes = [os.path.getsize(os.path.join(tmpdir, f)) for f in name_files]
                results[name] = f"PASS ({sum(sizes)//1024}KB across {len(name_files)} files)"
            elif ok:
                results[name] = "PASS (download returned True, no matching files found)"
            else:
                results[name] = "FAIL (download returned False)"
        except Exception as e:
            results[name] = f"ERROR: {type(e).__name__}: {e}"

print(f"\n{'=' * 60}")
print("  FINAL RESULTS")
print(f"{'=' * 60}")
for name, status in results.items():
    print(f"  {name:15s}  {status}")
