# Application: DOWNIE
# Developed by: 1mad
# 100% Copyrights to 1mad. All rights reserved.
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import yt_dlp
import uuid
import threading

import time
import shutil

# Advanced Hack: Prevent Disk Space exhaustion on cloud servers (Render)
def cleanup_old_files():
    while True:
        try:
            current_time = time.time()
            for filename in os.listdir(DOWNLOAD_DIR):
                filepath = os.path.join(DOWNLOAD_DIR, filename)
                # Check if file is older than 2 hours
                if os.path.isfile(filepath) and current_time - os.path.getctime(filepath) > 7200:
                    os.remove(filepath)
            
            # Cleanup memory dictionary
            expired_ids = [did for did, ddata in downloads.items() if ddata.get('status') in ['completed', 'error'] and current_time - ddata.get('_start_time', current_time) > 7200]
            for did in expired_ids:
                del downloads[did]
                
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(3600)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()
import os
import subprocess
import imageio_ffmpeg
import time
import re
from urllib.parse import urlparse

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
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
    return app.send_static_file('index.html')

@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json
    url = data.get('url')
    
    if not url or not is_valid_url(url):
        return jsonify({"error": "Invalid URL provided."}), 400

    try:
        if 'youtube.com' in url or 'youtu.be' in url:
            import requests
            oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"
            resp = requests.get(oembed_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return jsonify({
                    "title": data.get('title', 'Unknown Title'),
                    "thumbnail": data.get('thumbnail_url', '')
                })

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'android', 'web']}}
        }
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
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
        
        # Advanced Options: Bulletproof downloading configuration
        ydl_opts = {
            'outtmpl': filepath_template,
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,
            'concurrent_fragment_downloads': 5,
            'retries': 15,
            'fragment_retries': 15,
            'extractor_retries': 5,
            'socket_timeout': 30,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'sleep_requests': 1,
            'source_address': '0.0.0.0',
            'force_ipv4': False,
            # Use clients that bypass PO Token and bot detection best
            'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'android', 'web']}}
        }
        
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
        
        # Force mp4 video and m4a audio to allow direct ffmpeg muxing without transcoding!
        # Transcoding (e.g. webm to mp4) uses huge CPU/RAM and crashes cloud servers!
        if quality == 'mp3':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
        elif quality == 'best':
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '2k':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1440]+bestaudio[ext=m4a]/best[ext=mp4][height<=1440]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '1080p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '720p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '480p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=480]+bestaudio[ext=m4a]/best[ext=mp4][height<=480]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '360p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=360]+bestaudio[ext=m4a]/best[ext=mp4][height<=360]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '240p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=240]+bestaudio[ext=m4a]/best[ext=mp4][height<=240]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == '144p':
            ydl_opts['format'] = 'bestvideo[ext=mp4][height<=144]+bestaudio[ext=m4a]/best[ext=mp4][height<=144]/best'
            ydl_opts['merge_output_format'] = 'mp4'
        elif quality == 'png':
            ydl_opts['skip_download'] = True
        else:
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            
        import yt_dlp
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Media')
            from werkzeug.utils import secure_filename
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
        error_msg = str(e)
        raw_error = error_msg
        if "Sign in to confirm" in error_msg or "reloaded" in error_msg:
            error_msg = f"Bot detection triggered. Please update your cookies.txt! (Raw: {raw_error})"
        else:
            error_msg = f"Error: {raw_error}"
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = error_msg

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
        'quality': quality,
        '_start_time': time.time()
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
    matched_file = None
    for f in os.listdir(DOWNLOAD_DIR):
        if f.startswith(download_id):
            matched_file = os.path.join(DOWNLOAD_DIR, f)
            break
            
    if not matched_file:
        return """
        <html>
            <head><title>File Not Found</title><style>body{font-family:sans-serif;text-align:center;margin-top:50px;color:#333;background:#f9f9f9;} a{color:#2563EB;text-decoration:none;}</style></head>
            <body>
                <h2>File expired or not found!</h2>
                <p>The server may have restarted or the file was deleted to save space.</p>
                <a href="/">Go back and try downloading again</a>
            </body>
        </html>
        """, 404
        
    ext = os.path.splitext(matched_file)[1]
    
    title = "Media_File"
    if download_id in downloads:
        title = downloads[download_id].get('title', 'Media_File')
    else:
        basename = os.path.basename(matched_file)
        # format is id_title.ext
        title_part = basename[len(download_id)+1:-(len(ext))]
        if title_part:
            title = title_part

    download_name = f"{title}{ext}"
    return send_from_directory(os.path.dirname(matched_file), os.path.basename(matched_file), as_attachment=True, download_name=download_name)

if __name__ == '__main__':
    # Running in production mode (debug=False) prevents Remote Code Execution via Flask Debugger
    # Serving on 0.0.0.0 allows local Wi-Fi network access for mobile testing
    app.run(host='0.0.0.0', debug=False, port=8080)

@app.route('/api/debug', methods=['GET'])
def get_debug():
    import sys
    try:
        import yt_dlp
        ytdl_version = yt_dlp.version.__version__
    except:
        ytdl_version = "Not installed"
    
    return jsonify({
        "python_version": sys.version,
        "yt_dlp_version": ytdl_version,
        "cookies_exist": os.path.exists('cookies.txt')
    })
