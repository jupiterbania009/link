from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
import logging
import time
from werkzeug.utils import secure_filename
from functools import lru_cache

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,  # Changed to INFO for production
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

# Configure download directory
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Cache for video info (expires after 30 minutes)
VIDEO_INFO_CACHE = {}
CACHE_DURATION = 1800  # 30 minutes in seconds

def get_cached_info(url):
    if url in VIDEO_INFO_CACHE:
        info, timestamp = VIDEO_INFO_CACHE[url]
        if time.time() - timestamp < CACHE_DURATION:
            return info
        else:
            del VIDEO_INFO_CACHE[url]
    return None

def set_cached_info(url, info):
    VIDEO_INFO_CACHE[url] = (info, time.time())

# Optimized YT-DLP options
YDL_OPTS_BASE = {
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
}

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

def get_best_format(formats, quality):
    """Helper function to get the best format for a given quality"""
    if quality == 'audio':
        audio_formats = [f for f in formats 
                        if f.get('acodec') != 'none' 
                        and f.get('vcodec') == 'none']
        if audio_formats:
            return max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
        return None

    quality_height = int(quality.replace('p', ''))
    video_formats = [f for f in formats 
                    if f.get('vcodec') != 'none' 
                    and f.get('acodec') != 'none'
                    and f.get('height', 0) == quality_height]
    
    if video_formats:
        return max(video_formats, key=lambda x: x.get('tbr', 0) or 0)
    return None

def get_video_info(url):
    """Get video information using yt-dlp with caching"""
    # Check cache first
    cached_info = get_cached_info(url)
    if cached_info:
        return cached_info

    with yt_dlp.YoutubeDL(YDL_OPTS_BASE) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            
            # Process formats
            formats = []
            seen_qualities = set()
            
            # Add audio format
            audio_formats = [f for f in info['formats'] 
                           if f.get('acodec') != 'none' 
                           and f.get('vcodec') == 'none']
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                formats.append({
                    'format_id': best_audio['format_id'],
                    'ext': best_audio.get('ext', ''),
                    'quality': 'audio',
                    'format_note': 'audio only'
                })

            # Process video formats efficiently
            for f in info['formats']:
                if f.get('vcodec') == 'none':
                    continue
                    
                height = f.get('height', 0)
                if height >= 2160: quality = '2160p'
                elif height >= 1440: quality = '1440p'
                elif height >= 1080: quality = '1080p'
                elif height >= 720: quality = '720p'
                elif height >= 480: quality = '480p'
                else: continue

                if quality not in seen_qualities:
                    seen_qualities.add(quality)
                    formats.append({
                        'format_id': f['format_id'],
                        'ext': f.get('ext', ''),
                        'quality': quality
                    })

            # Sort formats
            quality_order = {'2160p': 0, '1440p': 1, '1080p': 2, '720p': 3, '480p': 4, 'audio': 5}
            formats.sort(key=lambda x: quality_order.get(x['quality'], 999))

            result = {
                'title': info.get('title', ''),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats
            }
            
            # Cache the result
            set_cached_info(url, result)
            return result

        except Exception as e:
            logger.error(f"Error in get_video_info: {str(e)}")
            return {'error': str(e)}

@app.route('/api/video-info', methods=['POST'])
def video_info():
    """Get video information endpoint"""
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
        
    info = get_video_info(url)
    if 'error' in info:
        return jsonify(info), 400
        
    return jsonify(info)

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download video endpoint"""
    data = request.get_json()
    url = data.get('url')
    quality = data.get('quality')
    
    if not url or not quality:
        return jsonify({'error': 'URL and quality are required'}), 400
    
    try:
        # Use cached info if available
        info = get_cached_info(url)
        if not info or 'error' in info:
            with yt_dlp.YoutubeDL(YDL_OPTS_BASE) as ydl:
                info = ydl.extract_info(url, download=False)

        # Generate unique filename
        filename = f"{secure_filename(str(uuid.uuid4()))}"
        output_path = os.path.join(DOWNLOAD_DIR, filename)

        # Configure download options
        ydl_opts = {
            **YDL_OPTS_BASE,
            'outtmpl': output_path + '.%(ext)s'
        }

        if quality == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }]
            })
        else:
            # Get best format for quality
            selected_format = get_best_format(info['formats'], quality)
            if not selected_format:
                return jsonify({'error': f'Quality {quality} not available'}), 400
            ydl_opts['format'] = selected_format['format_id']

        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            ext = 'mp3' if quality == 'audio' else info['ext']
            downloaded_file = output_path + '.' + ext
            
            return jsonify({
                'success': True,
                'download_path': f'/api/download/{os.path.basename(downloaded_file)}'
            })

    except Exception as e:
        logger.error(f"Error in download_video: {str(e)}")
        return jsonify({'error': str(e)}), 400

@app.route('/api/download/<filename>')
def serve_file(filename):
    """Serve downloaded file"""
    try:
        return send_file(
            os.path.join(DOWNLOAD_DIR, filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error in serve_file: {str(e)}")
        return jsonify({'error': str(e)}), 404

# Cleanup task
def cleanup_old_downloads():
    try:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.getmtime(filepath) < current_time - 3600:  # 1 hour
                os.remove(filepath)
    except Exception as e:
        logger.error(f"Error cleaning up downloads: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 
