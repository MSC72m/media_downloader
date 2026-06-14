"""PyInstaller hook for CustomTkinter.

Ensures all CustomTkinter assets (themes, fonts, icons) are bundled
with the frozen application.
"""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "customtkinter",
    includes=[
        "assets/**/*.json",
        "assets/**/*.otf",
        "assets/**/*.ttf",
        "assets/**/*.ico",
        "assets/**/*.png",
        "assets/**/*.gif",
    ],
)
