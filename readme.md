# Social Media Toolkit

## Overview

The Social Media Toolkit is an easy-to-use application that helps you download media content from social media platforms like Instagram, YouTube, Twitter, and Pinterest. It uses Python libraries like `requests`, `BeautifulSoup`, `instaloader`, and `pytube`, and has a simple GUI built with `customtkinter`.

## Features

- **Download Videos** from YouTube and Instagram
- **Download Images** from Pinterest
- **Download Media** from Twitter
- **Progress Bar** to track download progress
- **User-Friendly Interface** with CustomTkinter

## Installation

1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/social-media-toolkit.git
   cd social-media-toolkit
   ```
Create a virtual environment (optional but recommended):

```sh
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```
**Install Required Libraries:**
```
   pip install requests beautifulsoup4 customtkinter pytube instaloader
```
## Usage
Run the application:
```
python main.py
```
Enter a URL in the input field of the GUI and click the "Analyze URL and Download" button.

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


## Troubleshooting

### Network Issues:
If you encounter network-related errors, ensure you have a stable internet connection and try again.

### Unsupported URL:
If you see an "Unsupported URL" warning, make sure the URL is from one of the supported domains (Instagram, YouTube, Pinterest, Twitter).

### Error Messages:
Error messages will be displayed in a message box if any issues occur during the download process. Review these messages to understand what went wrong.

## Contributing
Contributions are welcome! Please create an issue or submit a pull request for any improvements or new features.
