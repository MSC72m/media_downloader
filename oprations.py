import customtkinter as ctk
from threading import Thread
import time


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


entry_count = 0
entries = []


def add_entry():
    global entry_count
    if entry_count > 9:
        return None
    from config import app
    entry = ctk.CTkEntry(app, width=360, placeholder_text="Enter a URL", height=50, corner_radius=5)
    entry.pack(pady=(10, 0))
    entry_count += 1
    processed = False
    previous_link = ""

    def on_entry_change(event=None):
        nonlocal processed
        """
        Callback function triggered when the user presses the Enter key or the entry widget loses focus.
        Retrieves the text from the entry widget and appends it to the 'entries' list if it is not empty.
        """
        link = entry.get()
        time.sleep(0.1)
        if link != previous_link:
            if link and not processed:  # Only append if the link is not empty and is not already added
                entries.append(link)
                print(entries)
                processed = True
            previus_link = link

    # Bind the on_entry_change function to the <FocusOut> event.
    # This event is triggered when the entry widget loses focus (e.g., the user clicks outside it),
    # ensuring that the entered URL is retrieved and processed if the user moves focus away.
    entry.bind("<Return>", on_entry_change)
    # Bind the on_entry_change function to the <Return> event.
    # This event is triggered when the user presses the Enter key in the entry widget,
    # ensuring that the entered URL is retrieved and processed.
    entry.bind("<FocusOut>", on_entry_change)
    time.sleep(0.2)
    return entry
