from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import yt_dlp
import os
import uuid
import logging
from werkzeug.utils import secure_filename
import time

# Configure logging with more detail
logging.basicConfig(
    level=logging.DEBUG if os.environ.get('FLASK_ENV') == 'development' else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

# Configure download directory
DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Serve static files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# Clean up downloads older than 1 hour
def cleanup_old_downloads():
    try:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_DIR):
            filepath = os.path.join(DOWNLOAD_DIR, filename)
            if os.path.getmtime(filepath) < current_time - 3600:  # 1 hour
                os.remove(filepath)
    except Exception as e:
        logger.error(f"Error cleaning up downloads: {e}")

def get_best_format(formats, quality):
    """Helper function to get the best format for a given quality"""
    logger.debug(f"Finding best format for quality: {quality}")
    
    if quality == 'audio':
        audio_formats = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
        if audio_formats:
            best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
            logger.debug(f"Selected audio format: {best_audio.get('format_id')}")
            return best_audio
        return None

    # For video qualities
    quality_height = int(quality.replace('p', ''))
    logger.debug(f"Looking for video height: {quality_height}")
    
    # Get all formats with video
    video_formats = [f for f in formats 
                    if f.get('vcodec') != 'none' 
                    and f.get('acodec') != 'none'  # Ensure it has audio
                    and f.get('height', 0) == quality_height]
    
    if video_formats:
        # Sort by bitrate and get the best one
        best_format = max(video_formats, key=lambda x: x.get('tbr', 0) or 0)
        logger.debug(f"Selected video format: {best_format.get('format_id')} with height {best_format.get('height')}")
        return best_format
    
    logger.debug(f"No exact match found for {quality}")
    return None

def get_video_info(url):
    """Get video information using yt-dlp"""
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'format': 'best'
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            logger.debug(f"Raw formats available: {len(info['formats'])}")
            
            # Get available formats
            formats = []
            seen_qualities = set()
            
            # First, find the best audio-only format
            audio_formats = [f for f in info['formats'] if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
            logger.debug(f"Found {len(audio_formats)} audio-only formats")
            
            if audio_formats:
                best_audio = max(audio_formats, key=lambda x: x.get('abr', 0) or 0)
                formats.append({
                    'format_id': best_audio.get('format_id', ''),
                    'ext': best_audio.get('ext', ''),
                    'quality': 'audio',
                    'format_note': 'audio only',
                    'filesize': best_audio.get('filesize', 0),
                    'tbr': best_audio.get('tbr', 0),
                    'acodec': best_audio.get('acodec', '')
                })
                logger.debug("Added audio format")

            # Then process video formats
            video_formats = [f for f in info['formats'] 
                           if f.get('vcodec') != 'none' and f.get('acodec') != 'none']
            logger.debug(f"Found {len(video_formats)} video formats with audio")
            
            for f in video_formats:
                height = f.get('height', 0)
                logger.debug(f"Processing format: id={f.get('format_id')}, height={height}, vcodec={f.get('vcodec')}, acodec={f.get('acodec')}")
                
                # Map height to standard quality names
                if height >= 2160:
                    quality = '2160p'
                elif height >= 1440:
                    quality = '1440p'
                elif height >= 1080:
                    quality = '1080p'
                elif height >= 720:
                    quality = '720p'
                elif height >= 480:
                    quality = '480p'
                else:
                    continue  # Skip lower qualities
                
                if quality not in seen_qualities:
                    seen_qualities.add(quality)
                    formats.append({
                        'format_id': f.get('format_id', ''),
                        'ext': f.get('ext', ''),
                        'height': height,
                        'quality': quality,
                        'format_note': f.get('format_note', ''),
                        'filesize': f.get('filesize', 0),
                        'tbr': f.get('tbr', 0),
                        'vcodec': f.get('vcodec', ''),
                        'acodec': f.get('acodec', '')
                    })
                    logger.debug(f"Added quality option: {quality}")
            
            # Sort formats by quality
            quality_order = {'2160p': 0, '1440p': 1, '1080p': 2, '720p': 3, '480p': 4, 'audio': 5}
            formats.sort(key=lambda x: quality_order.get(x['quality'], 999))
            
            logger.debug(f"Final available qualities: {[f['quality'] for f in formats]}")
            
            return {
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'thumbnail': info.get('thumbnail', ''),
                'formats': formats,
                'webpage_url': info.get('webpage_url', ''),
                'extractor': info.get('extractor', '')
            }
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
    
    logger.debug(f"Processing video info request for URL: {url}")
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
    
    logger.debug(f"Download request - URL: {url}, Quality: {quality}")
    
    if not url or not quality:
        return jsonify({'error': 'URL and quality are required'}), 400
    
    try:
        # First get video info to find the right format
        info = yt_dlp.YoutubeDL({'quiet': True}).extract_info(url, download=False)
        
        # Get the best format for the requested quality
        selected_format = get_best_format(info['formats'], quality)
        
        if not selected_format:
            available_qualities = set()
            for f in info['formats']:
                height = f.get('height', 0)
                if f.get('vcodec') != 'none' and f.get('acodec') != 'none':
                    if height >= 2160: available_qualities.add('2160p')
                    elif height >= 1440: available_qualities.add('1440p')
                    elif height >= 1080: available_qualities.add('1080p')
                    elif height >= 720: available_qualities.add('720p')
                    elif height >= 480: available_qualities.add('480p')
                elif f.get('acodec') != 'none' and f.get('vcodec') == 'none':
                    available_qualities.add('audio')
            
            return jsonify({
                'error': f'Quality {quality} not available. Available qualities: {sorted(list(available_qualities))}'
            }), 400
        
        # Generate unique filename
        filename = f"{secure_filename(str(uuid.uuid4()))}"
        output_path = os.path.join(DOWNLOAD_DIR, filename)
        
        # Configure yt-dlp options
        ydl_opts = {
            'format': selected_format['format_id'],
            'outtmpl': output_path + '.%(ext)s',
            'quiet': True
        }
        
        # If it's audio only, add audio-specific options
        if quality == 'audio':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        
        # Download the video
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            logger.debug(f"Starting download with format ID: {selected_format['format_id']}")
            info = ydl.extract_info(url, download=True)
            ext = 'mp3' if quality == 'audio' else info['ext']
            downloaded_file = output_path + '.' + ext
            
            logger.debug(f"Download completed: {downloaded_file}")
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port) 
