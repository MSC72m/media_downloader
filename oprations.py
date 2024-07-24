import customtkinter as ctk
from threading import Thread
import queue

entries = []
entry_count = 0
operation_status = False
download_queue = queue.Queue()
download_thread = None
stop_download_thread = False


def random_save_path():
    import random
    save = random.randint(50, 500)
    save_path = random.randint(save, 1000)
    return save_path


def on_button_click():
    """Starts the downloading process when the button is clicked."""
    from config import first_entry
    global download_thread

    first_link = first_entry.get().strip()
    if first_link and first_link not in entries:
        entries.append(first_link)
        download_queue.put(first_link)
        print(entries)

    disable_button()

    if not download_thread or not download_thread.is_alive():
        download_thread = Thread(target=process_downloads, daemon=True)
        download_thread.start()


def process_downloads():
    """Process each link from the queue sequentially."""
    global stop_download_thread
    while not download_queue.empty() and not stop_download_thread:
        link = download_queue.get()
        perform_operation_thread(link)
    on_all_operations_done()


def perform_operation_thread(link):
    """Thread target function for performing operation."""
    from main import perform_operation
    global operation_status
    try:
        perform_operation(link)
    except Exception as e:
        print(f"Error: {e}")


def on_operation_done():
    """Callback to update the GUI after operation is done."""
    if download_queue.empty():
        enable_button()


def on_all_operations_done():
    """Callback when all operations are done."""
    from config import app
    app.after(0, enable_button)


def enable_button():
    from config import download_media_button
    download_media_button.configure(state=ctk.NORMAL)


def disable_button():
    from config import download_media_button
    download_media_button.configure(state=ctk.DISABLED)


def add_entry(event=None):
    global entry_count
    from config import app
    if entry_count > 9:
        return None

    entry = ctk.CTkEntry(app, width=360, placeholder_text="Enter a URL", height=50, corner_radius=5)
    entry.pack(pady=(10, 0))
    entry_count += 1

    def on_entry_change(event=None):
        link = entry.get().strip()
        if link and link not in entries:
            entries.append(link)
            download_queue.put(link)  # Only enqueue the link once
            print(entries)

    entry.bind("<Return>", on_entry_change)
    entry.bind("<FocusOut>", on_entry_change)
    return entry
