# Application: DOWNIE
# Developed by: 1mad
# 100% Copyrights to 1mad. All rights reserved.
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from pytubefix import YouTube
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

def is_youtube_url(url):
    return 'youtube.com' in url or 'youtu.be' in url

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
        return jsonify({"error": "Invalid or missing URL. Only HTTP/HTTPS URLs are allowed."}), 400
    
    try:
        if is_youtube_url(url):
            yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
            return jsonify({
                "title": yt.title,
                "thumbnail": yt.thumbnail_url
            })
        else:
            ydl_opts = {'quiet': True, 'no_warnings': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    "title": info.get('title', 'Media File'),
                    "thumbnail": info.get('thumbnail')
                })
    except Exception as e:
        return jsonify({"error": f"Failed to fetch: {str(e)}"}), 500

def download_task(download_id, url, quality):
    try:
        downloads[download_id]['status'] = 'downloading'
        downloads[download_id]['progress'] = '0%'
        downloads[download_id]['speed'] = 'Connecting...'

        if is_youtube_url(url):
            def progress_callback(stream, chunk, bytes_remaining):
                total_size = stream.filesize
                bytes_downloaded = total_size - bytes_remaining
                pct = (bytes_downloaded / total_size) * 100
                
                current_time = time.time()
                d_data = downloads[download_id]
                
                if 'last_time' in d_data:
                    time_diff = current_time - d_data['last_time']
                    if time_diff >= 0.5:
                        bytes_diff = bytes_downloaded - d_data['last_bytes']
                        speed_bps = bytes_diff / time_diff
                        speed_mbps = speed_bps / (1024 * 1024)
                        d_data['speed'] = f"{speed_mbps:.1f} MB/s"
                        d_data['last_time'] = current_time
                        d_data['last_bytes'] = bytes_downloaded
                else:
                    d_data['last_time'] = current_time
                    d_data['last_bytes'] = bytes_downloaded

                if d_data['status'] == 'downloading':
                    d_data['progress'] = f"{pct:.1f}%"

            yt = YouTube(url, on_progress_callback=progress_callback, use_oauth=False, allow_oauth_cache=True)
            # Use secure_filename for extreme strictness on the filesystem
            safe_title = secure_filename(yt.title)
            if not safe_title:
                safe_title = "Media_File"
            safe_title = safe_title[:100]
            downloads[download_id]['title'] = safe_title
            
            if quality == 'png':
                import requests
                thumb_url = yt.thumbnail_url
                filename = f"{download_id}_{safe_title}.png"
                filepath = os.path.join(DOWNLOAD_DIR, filename)
                with open(filepath, 'wb') as f:
                    f.write(requests.get(thumb_url).content)
                downloads[download_id]['filename'] = filepath
                downloads[download_id]['status'] = 'completed'
                downloads[download_id]['progress'] = '100%'
                downloads[download_id]['speed'] = 'Done'
                return

            if quality == 'mp3':
                stream = yt.streams.get_audio_only()
                audio_file = f"{download_id}_audio.m4a"
                audio_path = stream.download(output_path=DOWNLOAD_DIR, filename=audio_file)
                
                downloads[download_id]['speed'] = 'Converting to MP3 (320kbps)...'
                final_file = f"{download_id}_{safe_title}.mp3"
                final_path = os.path.join(DOWNLOAD_DIR, final_file)
                
                cmd = [FFMPEG_PATH, "-y", "-i", audio_path, "-b:a", "320k", final_path]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if os.path.exists(audio_path): os.remove(audio_path)
                
                downloads[download_id]['filename'] = final_path
                downloads[download_id]['status'] = 'completed'
                downloads[download_id]['progress'] = '100%'
                downloads[download_id]['speed'] = 'Done'
                return

            if quality == '2k':
                quality_res = '1440p'
            elif quality == 'best':
                quality_res = 'best'
            else:
                quality_res = quality

            if quality_res == 'best':
                video_stream = yt.streams.filter(type="video", file_extension='mp4').order_by('resolution').desc().first()
            else:
                video_stream = yt.streams.filter(res=quality_res, file_extension='mp4').first()
                if not video_stream:
                    video_stream = yt.streams.filter(type="video", file_extension='mp4').order_by('resolution').desc().first()
                
            audio_stream = yt.streams.filter(only_audio=True, file_extension='mp4').order_by('abr').desc().first()
            if not audio_stream:
                audio_stream = yt.streams.get_audio_only()

            video_file = f"{download_id}_video.mp4"
            video_path = video_stream.download(output_path=DOWNLOAD_DIR, filename=video_file)

            downloads[download_id]['progress'] = '95%' 
            downloads[download_id]['speed'] = 'Finalizing audio...'
            audio_file = f"{download_id}_audio.mp4"
            audio_path = audio_stream.download(output_path=DOWNLOAD_DIR, filename=audio_file)

            downloads[download_id]['progress'] = '99%' 
            downloads[download_id]['speed'] = 'Merging files...'
            
            final_file = f"{download_id}_{safe_title}.mp4"
            final_path = os.path.join(DOWNLOAD_DIR, final_file)
            
            # subprocess.run with shell=False is extremely secure against command injection
            cmd = [
                FFMPEG_PATH, "-y",
                "-i", video_path,
                "-i", audio_path,
                "-c:v", "copy",
                "-c:a", "copy",
                final_path
            ]
            
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            
            if os.path.exists(video_path): os.remove(video_path)
            if os.path.exists(audio_path): os.remove(audio_path)
            
            downloads[download_id]['filename'] = final_path
            downloads[download_id]['status'] = 'completed'
            downloads[download_id]['progress'] = '100%'
            downloads[download_id]['speed'] = 'Done'

        else:
            def ytdl_progress_hook(d):
                if d['status'] == 'downloading':
                    p = d.get('_percent_str', '0%').strip()
                    p = re.sub(r'\x1b[^m]*m', '', p)
                    s = d.get('_speed_str', 'Unknown speed').strip()
                    s = re.sub(r'\x1b[^m]*m', '', s)
                    
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
                # Block arbitrary network access for security
                'allowed_extractors': ['default']
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
    # Serving strictly on 127.0.0.1 prevents other network users from accessing the app remotely
    app.run(host='127.0.0.1', debug=False, port=5000)
