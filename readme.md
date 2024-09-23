# Social Media Toolkit

A powerful, user-friendly application for downloading media content from popular social platforms.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Supported Platforms](#supported-platforms)
- [Installation](#installation)
  - [Linux Installation](#linux-installation)
  - [Windows Installation](#windows-installation)
- [Usage Guide](#usage-guide)
- [Advanced Features](#advanced-features)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Disclaimer](#disclaimer)

## Overview

The Social Media Toolkit is a sophisticated, cross-platform application designed to streamline the process of downloading media content from various social media platforms. Built with Python and featuring a modern, intuitive GUI, this toolkit empowers users to easily archive and manage their favorite online content.

## Key Features

- **Multi-Platform Support**: Seamlessly download content from major social media sites.
- **Customizable Downloads**: Choose video quality, audio-only options, and more.
- **Bulk Processing**: Queue multiple downloads for efficient batch processing.
- **User Authentication**: Securely log in to platforms like Instagram for expanded access.
- **Flexible Save Options**: Customize where and how your media is saved.
- **Progress Tracking**: Real-time updates on download status and progress.
- **Error Handling**: Robust error management with clear user feedback.

## Supported Platforms

- [![YouTube](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://img.shields.io/badge/YouTube-FF0000?style=for-the-badge&logo=youtube&logoColor=white)
- [![Instagram](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)](https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white)
- [![Twitter](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://img.shields.io/badge/Twitter-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)
- [![Pinterest](https://img.shields.io/badge/Pinterest-%23E60023.svg?&style=for-the-badge&logo=Pinterest&logoColor=white)](https://img.shields.io/badge/Pinterest-%23E60023.svg?&style=for-the-badge&logo=Pinterest&logoColor=white)

## Installation

### Linux Installation

1. Verify Python installation:
   ```bash
   python3 --version
   ```

2. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/social-media-toolkit.git
   cd social-media-toolkit
   ```

3. Set up a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Launch the application:
   ```bash
   python main.py
   ```

### Windows Installation

1. Download `SocialMediaToolkit_Setup.exe` from our releases page.
2. Run the installer and follow the wizard's instructions.
3. Launch via the desktop shortcut or start menu.

## Usage Guide

### Adding Content:

- Paste the media URL into the input field.
- Click "Add" and provide a custom name if desired.

### Configuring Options:

- YouTube: Select quality, enable playlist download, or choose audio-only.
- Instagram: Use the "Instagram Login" for authenticated access.

### Managing Queue:

- Remove items with "Remove Selected" or clear all with "Clear All".
- Initiate downloads with "Download All".

### Customizing Save Location:

- Access the file browser via "Manage Files".
- Navigate and set your preferred download directory.

### Monitoring Downloads:

- Track overall progress via the status label and progress bar.
- Check individual download statuses in the download list.

## Advanced Features

### YouTube Enhancements

- Quality selection (360p to 1080p)
- Playlist support
- Audio extraction capability

### Instagram Capabilities

- Support for posts, reels, and carousels
- Caption preservation

### Twitter Integration

- Download images and videos from tweets

### Pinterest Functionality

- High-quality image retrieval from pins and boards
- Automated file naming based on pin content

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Network Errors | Check internet connection and retry |
| Unsupported URL | Verify the URL is from a supported platform |
| Authentication Failures | Ensure correct login credentials for Instagram |
| Download Errors | Consult application logs for detailed error messages |

## Contributing

We welcome contributions! To contribute:

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/NewFeature`
3. Commit changes: `git commit -m 'Add NewFeature'`
4. Push to the branch: `git push origin feature/NewFeature`
5. Submit a pull request.

## License

This project is licensed under the MIT License. See LICENSE for details.

## Disclaimer

The Social Media Toolkit is intended for personal use only. Users are responsible for adhering to the terms of service of the respective platforms and all applicable copyright laws. The developers assume no liability for misuse of this software.