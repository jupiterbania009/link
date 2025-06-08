# Universal Video Player & Downloader

A web application that allows users to play and download videos from various platforms including YouTube, Terabox, Dailymotion, Vimeo, and more. Supports up to 4K video quality.

## Features

- Video playback from multiple platforms
- Download videos in various qualities (up to 4K)
- MP3 audio extraction
- Real-time video information
- Modern, responsive UI
- Support for multiple video platforms

## Prerequisites

- Python 3.7 or higher
- Node.js (for serving the frontend)
- Modern web browser

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Create downloads directory:
```bash
mkdir downloads
```

## Usage

1. Start the backend server:
```bash
python app.py
```

2. Serve the frontend (using Python's built-in server):
```bash
python -m http.server 8000
```

3. Open your browser and navigate to:
```
http://localhost:8000
```

4. Enter a video URL and select your desired quality to download.

## Supported Platforms

- YouTube
- Terabox
- Vimeo
- Dailymotion
- Facebook
- Instagram
- Twitter
- Direct video links

## Notes

- Downloads are saved in the `downloads` directory
- 4K downloads may take longer to process
- Some platforms may have restrictions on certain video qualities
- Please respect copyright laws and platform terms of service

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This tool is for personal use only. Please respect copyright laws and the terms of service of the platforms you're downloading from. 