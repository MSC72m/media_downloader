import customtkinter as ctk


# Initialize the app
app = ctk.CTk()
app.title("Social Media Toolkit")
app.geometry("500x500")


def total_links():
    global click_count
    click_count += 1
    print(click_count)


# Shared button

from oprations import on_button_click, add_entry
download_media_button = ctk.CTkButton(
    app, text="Analyze URL and Download",
    command=on_button_click, width=300,
    height=60,
    corner_radius=50,
    fg_color="#1a73e8",
    hover_color="#1557b2"
)

add_download_button = ctk.CTkButton(
    app,
    text="add",
    command=add_entry,
    width=60,
    height=60,
    corner_radius=50,
    fg_color="#1e635b",
    hover_color="#057b99"
)

# Shared entry
first_entry = ctk.CTkEntry(
    app,
    width=430,
    placeholder_text="Enter a URL",
    height=45,
    corner_radius=10
)
first_entry.pack(pady=30)
spacer = ctk.CTkLabel(app, text="", height=50)  # Spacer with 50 pixels height
spacer.pack()
