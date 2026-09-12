# Application: DOWNIE
# Developed by: 1mad
# 100% Copyrights to 1mad. All rights reserved.
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import yt_dlp
import uuid
import threading
import os
import subprocess
import imageio_ffmpeg
import time
import re
from urllib.parse import urlparse

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

downloads = {}

def is_valid_url(url):
    try:
        result = urlparse(url)
        # Strictly allow only http and https, and ensure a netloc (domain) exists
        return all([result.scheme in ['http', 'https'], result.netloc])
    except ValueError:
        return False

@app.route('/')
def serve_index():
    # Set secure headers
    response = app.send_static_file('index.html')
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    
    if not url or not is_valid_url(url):
        return jsonify({"error": "Invalid URL provided."}), 400

    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'extractor_args': {'youtube': {'player_client': ['android']}}
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # extract_flat might only return id and title for youtube playlists/videos,
            # but usually it gets the thumbnail too. If thumbnail is missing, fallback to generated one.
            thumbnail = info.get('thumbnail')
            if not thumbnail and info.get('id'):
                thumbnail = f"https://img.youtube.com/vi/{info['id']}/maxresdefault.jpg"
                
            return jsonify({
                "title": info.get('title', 'Unknown Title'),
                "thumbnail": thumbnail
            })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch: {str(e)}"}), 500

def download_task(download_id, url, quality):
    try:
        downloads[download_id]['status'] = 'downloading'
        downloads[download_id]['progress'] = '0%'
        downloads[download_id]['speed'] = 'Connecting...'

        def ytdl_progress_hook(d):
            if d['status'] == 'downloading':
                p = d.get('_percent_str', '0%').strip()
                p = re.sub(r' [^m]*m', '', p)
                s = d.get('_speed_str', 'Unknown speed').strip()
                s = re.sub(r' [^m]*m', '', s)
                
                if downloads[download_id]['status'] == 'downloading':
                    downloads[download_id]['progress'] = p
                    downloads[download_id]['speed'] = s
            elif d['status'] == 'finished':
                downloads[download_id]['progress'] = '100%'
                downloads[download_id]['speed'] = 'Processing...'

        filepath_template = os.path.join(DOWNLOAD_DIR, f"{download_id}_%(title).100s.%(ext)s")
        
        ydl_opts = {
            'outtmpl': filepath_template,
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,
            'allowed_extractors': ['default'],
            'concurrent_fragment_downloads': 5,
            'extractor_args': {'youtube': {'player_client': ['android']}}
        }
        
        if quality == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        elif quality == 'best':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '2k':
            ydl_opts['format'] = 'bestvideo[height<=1440]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '1080p':
            ydl_opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '720p':
            ydl_opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '480p':
            ydl_opts['format'] = 'bestvideo[height<=480]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '360p':
            ydl_opts['format'] = 'bestvideo[height<=360]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '240p':
            ydl_opts['format'] = 'bestvideo[height<=240]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '144p':
            ydl_opts['format'] = 'bestvideo[height<=144]+bestaudio/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == 'png':
            ydl_opts['skip_download'] = True
        else:
            ydl_opts['format'] = 'best'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Media')
            safe_title = secure_filename(title)
            if not safe_title:
                safe_title = "Media_File"
            safe_title = safe_title[:100]
            downloads[download_id]['title'] = safe_title
            
            if quality == 'png':
                import requests
                thumb_url = info.get('thumbnail')
                if thumb_url:
                    filename = f"{download_id}_{safe_title}.png"
                    filepath = os.path.join(DOWNLOAD_DIR, filename)
                    with open(filepath, 'wb') as f:
                        f.write(requests.get(thumb_url).content)
                    downloads[download_id]['filename'] = filepath
                else:
                    raise Exception("No thumbnail found")
            else:
                ydl.download([url])
                for f in os.listdir(DOWNLOAD_DIR):
                    if f.startswith(download_id):
                        downloads[download_id]['filename'] = os.path.join(DOWNLOAD_DIR, f)
                        break
            
            downloads[download_id]['status'] = 'completed'
            downloads[download_id]['progress'] = '100%'
            downloads[download_id]['speed'] = 'Done'

    except Exception as e:
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = str(e)

@app.route('/api/download', methods=['POST'])
def start_download():
    data = request.json
    url = data.get('url')
    quality = data.get('quality')
    
    if not url or not is_valid_url(url):
        return jsonify({"error": "Invalid URL provided."}), 400
        
    download_id = str(uuid.uuid4())
    downloads[download_id] = {
        'status': 'starting',
        'progress': '0%',
        'speed': '',
        'url': url,
        'quality': quality
    }
    
    thread = threading.Thread(target=download_task, args=(download_id, url, quality))
    thread.start()
    
    return jsonify({"download_id": download_id})

@app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    if download_id not in downloads:
        return jsonify({"error": "Download not found"}), 404
    return jsonify(downloads[download_id])

@app.route('/api/file/<download_id>', methods=['GET'])
def get_file(download_id):
    if download_id not in downloads or downloads[download_id].get('status') != 'completed':
        return jsonify({"error": "File not ready or not found"}), 404
        
    filename = downloads[download_id].get('filename')
    title = downloads[download_id].get('title', 'Media')
    
    if filename and os.path.exists(filename):
        ext = os.path.splitext(filename)[1]
        download_name = f"{title}{ext}"
        
        response = send_from_directory(os.path.dirname(filename), os.path.basename(filename), as_attachment=True, download_name=download_name)
        # Add security headers to the download to prevent execution
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    return jsonify({"error": "File not found on disk"}), 404

if __name__ == '__main__':
    # Running in production mode (debug=False) prevents Remote Code Execution via Flask Debugger
    # Serving on 0.0.0.0 allows local Wi-Fi network access for mobile testing
    app.run(host='0.0.0.0', debug=False, port=8080)
