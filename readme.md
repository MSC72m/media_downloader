# Social Media Toolkit

## Overview

The Social Media Toolkit is an easy-to-use application that helps you download media content from social media platforms like Instagram, YouTube, Twitter, and Pinterest. It uses Python libraries like `requests`, `BeautifulSoup`, `instaloader`, and `pytube`, and has a simple GUI built with `customtkinter`.

## Features

- **Download Videos** from YouTube and Instagram
- **Download Images** from Pinterest
- **Download Media** from Twitter
- **User-Friendly Interface** with CustomTkinter

## Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/MSC72m/social-media-toolkit.git
   cd social-media-toolkit
   ```
Create a virtual environment (optional but recommended):

```sh
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```
**Install Required Libraries:**
```
   pip install requests beautifulsoup4 customtkinter pytube instaloader threading
```
## Usage
Run the application:
```
python main.py
```
Enter a URL in the input field of the GUI and click the "Analyze URL and Download" button.


## Disclaimer
 Instagram has 12 anonymous download limit, if you encounter 401 errors it's because of that.
### Usage

1. navigate to the project directory.
2. Open the script file.
3. Replace the entire `download_instagram_video` function in your script with the following code:

    ```python
    def download_instagram_video(link, username='your_username', password='your_password'):
        loader = instaloader.Instaloader()
      """ replacing the function with this and replacing the username and password you won't have 401 error and 12 item rate limit will be lifted to 1000 """
        # Login to Instagram
        try:
            loader.login(username, password)
        except instaloader.exceptions.BadCredentialsException:
            messagebox.showerror("Error", "Invalid username or password.")
            on_operation_done() 
            return
        except instaloader.exceptions.ConnectionException:
            messagebox.showerror("Error", "Connection error, please check your internet connection.")
            on_operation_done()  # Callback to re-enable the button
            return
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")
            on_operation_done()  
            return

        try:
            post = instaloader.Post.from_shortcode(loader.context, link.split('/')[-2])
            video_url = post.video_url
            download_video(video_url, "downloaded_instagram_video.mp4")
            messagebox.showinfo("Success", "Video downloaded successfully.")
            on_operation_done() 
        except Exception as e:
            messagebox.showerror("Error", f"Error downloading Instagram video: {e}")
            on_operation_done() 
    ```

4. Replace `'your_username'` and `'your_password'` with your Instagram login credentials in the `download_instagram_video` function.
5. Run the script:
    ```bash
    python your_script.py
    ```

By following these instructions, users will be able to download more than the anonymous limit of 12 files by logging in with their Instagram credentials (it will have a 1000-item limit).

## Requirements

- Python 3.x
- Required libraries:
  - `requests`
  - `beautifulsoup4`
  - `re`
  - `customtkinter`
  - `tkinter`
  - `pytube`
  - `instaloader`
  - `threading`

## Troubleshooting

### Network Issues:
If you encounter network-related errors, ensure you have a stable internet connection and try again.

### Unsupported URL:
If you see an "Unsupported URL" warning, make sure the URL is from one of the supported domains (Instagram, YouTube, Pinterest, Twitter).

### Error Messages:
Error messages will be displayed in a message box if any issues occur during the download process. Review these messages to understand what went wrong.

## Contributing
Contributions are welcome! Please create an issue or submit a pull request for any improvements or new features.
