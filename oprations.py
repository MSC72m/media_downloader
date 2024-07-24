import customtkinter as ctk
from threading import Thread


def random_save_path():
    import random
    save = random.randint(50, 500)
    save_path = random.randint(save, 1000)
    return save_path


def on_button_click():
    from config import entry, download_media_button
    from main import perform_operation
    link = entry.get()
    download_media_button.configure(state=ctk.DISABLED)  # Disable the button
    Thread(target=perform_operation, args=(link,), daemon=True).start()


def on_operation_done():
    """Sets button back to normal state and usable, after each error message or success
    (after the program is done either with downloading or has encountered an error)
    should be triggered to re-enable the download button."""
    from config import download_media_button
    if download_media_button:
        download_media_button.configure(state=ctk.NORMAL)
