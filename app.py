# Application: DOWNIE
# Developed by: 1mad
# 100% Copyrights to 1mad. All rights reserved.

import os
import re
import sys
import time
import uuid
import threading
import subprocess
import shutil
import imageio_ffmpeg
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ─────────────────────────────────────────────
#  App bootstrap
# ─────────────────────────────────────────────
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()

downloads = {}   # in-memory download state

# ─────────────────────────────────────────────
#  Security headers on every response
# ─────────────────────────────────────────────
@app.after_request
def apply_security_headers(response):
    response.headers['X-Content-Type-Options']        = 'nosniff'
    response.headers['X-Frame-Options']               = 'DENY'
    response.headers['X-XSS-Protection']              = '1; mode=block'
    response.headers['Strict-Transport-Security']     = 'max-age=31536000; includeSubDomains'
    response.headers['Referrer-Policy']               = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy']            = 'geolocation=(), microphone=()'
    return response

# ─────────────────────────────────────────────
#  Background cleanup  (disk + memory)
# ─────────────────────────────────────────────
def cleanup_old_files():
    while True:
        try:
            now = time.time()
            for fname in os.listdir(DOWNLOAD_DIR):
                fpath = os.path.join(DOWNLOAD_DIR, fname)
                if os.path.isfile(fpath) and now - os.path.getctime(fpath) > 7200:
                    try:
                        os.remove(fpath)
                    except Exception:
                        pass
            # Remove stale download records
            stale = [
                did for did, d in list(downloads.items())
                if d.get('status') in ('completed', 'error')
                and now - d.get('_start_time', now) > 7200
            ]
            for did in stale:
                downloads.pop(did, None)
        except Exception as e:
            print(f"[cleanup] {e}", flush=True)
        time.sleep(3600)

threading.Thread(target=cleanup_old_files, daemon=True).start()

# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────
def is_valid_url(url: str) -> bool:
    try:
        r = urlparse(url)
        return r.scheme in ('http', 'https') and bool(r.netloc)
    except ValueError:
        return False


def build_format_string(quality: str) -> str:
    """Return a yt-dlp format string that avoids transcoding.

    We always try to get H264 video + AAC audio so ffmpeg just muxes
    (copy mode) instead of re-encoding — this saves massive CPU/RAM.
    """
    height_map = {
        'best':  None,
        '2k':    1440,
        '1080p': 1080,
        '720p':  720,
        '480p':  480,
        '360p':  360,
        '240p':  240,
        '144p':  144,
    }
    if quality in height_map:
        h = height_map[quality]
        if h is None:
            return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'
        return (
            f'bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]'
            f'/bestvideo[height<={h}]+bestaudio'
            f'/best[height<={h}]/best'
        )
    return 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best'


# ─────────────────────────────────────────────
#  YouTube bot-detection bypass strategies
#
#  YouTube checks for a Proof-Of-Origin (PO) token on the web client.
#  The clients below skip or work around that check:
#    • mweb  — mobile web, no PO token required
#    • ios   — Apple iOS app, no PO token required
#    • android — Android app, no PO token required
#    • tv_embedded — Smart-TV embedded player, often allowed
#
#  player_skip=['webpage','configs'] tells yt-dlp not to fetch the
#  main player JS, which is what triggers the PO-token handshake.
# ─────────────────────────────────────────────
BYPASS_EXTRACTOR_ARGS = {
    'youtube': {
        'player_client': ['mweb', 'ios', 'android', 'tv_embedded'],
        'player_skip': ['webpage', 'configs'],
    }
}


def make_ydl_opts(extra: dict = None) -> dict:
    """Return a safe, bot-resistant base options dict for yt-dlp."""
    opts = {
        'quiet':                       True,
        'no_warnings':                 True,
        'geo_bypass':                  True,
        'nocheckcertificate':          True,
        'socket_timeout':              60,
        'retries':                     10,
        'fragment_retries':            10,
        'extractor_retries':           5,
        'sleep_requests':              1,
        'ffmpeg_location':             FFMPEG_PATH,
        'concurrent_fragment_downloads': 4,
        'extractor_args':              BYPASS_EXTRACTOR_ARGS,
    }
    if extra:
        opts.update(extra)
    return opts


# ─────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json or {}
    url  = data.get('url', '').strip()

    if not url or not is_valid_url(url):
        return jsonify({'error': 'Invalid URL provided.'}), 400

    try:
        # Fast path: YouTube oEmbed (no yt-dlp needed)
        if 'youtube.com' in url or 'youtu.be' in url:
            import requests as req
            r = req.get(
                f'https://www.youtube.com/oembed?url={url}&format=json',
                timeout=10
            )
            if r.status_code == 200:
                d = r.json()
                return jsonify({
                    'title':     d.get('title', 'Unknown Title'),
                    'thumbnail': d.get('thumbnail_url', ''),
                })

        # Fallback: yt-dlp extract_flat
        opts = make_ydl_opts({'extract_flat': True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumb = info.get('thumbnail') or (
                f"https://img.youtube.com/vi/{info['id']}/maxresdefault.jpg"
                if info.get('id') else ''
            )
            return jsonify({
                'title':     info.get('title', 'Unknown Title'),
                'thumbnail': thumb,
            })

    except Exception as e:
        return jsonify({'error': f'Failed to fetch media info: {str(e)}'}), 500


@app.route('/api/download', methods=['POST'])
def start_download():
    data    = request.json or {}
    url     = data.get('url', '').strip()
    quality = data.get('quality', '720p')

    if not url or not is_valid_url(url):
        return jsonify({'error': 'Invalid URL provided.'}), 400

    download_id = str(uuid.uuid4())
    downloads[download_id] = {
        'status':      'starting',
        'progress':    '0%',
        'speed':       '',
        'url':         url,
        'quality':     quality,
        '_start_time': time.time(),
    }

    thread = threading.Thread(
        target=download_task,
        args=(download_id, url, quality),
        daemon=True
    )
    thread.start()
    return jsonify({'download_id': download_id})


@app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    return jsonify(downloads[download_id])


@app.route('/api/file/<download_id>', methods=['GET'])
def get_file(download_id):
    matched = None
    for fname in os.listdir(DOWNLOAD_DIR):
        if fname.startswith(download_id):
            matched = os.path.join(DOWNLOAD_DIR, fname)
            break

    if not matched:
        return (
            """<!doctype html><html><head><title>File Expired</title>
            <style>body{font-family:sans-serif;text-align:center;margin-top:60px;
            background:#f9f9f9;color:#333;}a{color:#2563EB}</style></head>
            <body><h2>⚠️ File expired or not found</h2>
            <p>The server may have restarted, or the file was deleted to free disk space.</p>
            <a href="/">← Go back and download again</a></body></html>""",
            404,
        )

    ext   = os.path.splitext(matched)[1]
    title = 'Media_File'
    if download_id in downloads:
        title = downloads[download_id].get('title', 'Media_File')
    else:
        base  = os.path.basename(matched)
        part  = base[len(download_id) + 1: -len(ext)]
        if part:
            title = part

    return send_from_directory(
        os.path.dirname(matched),
        os.path.basename(matched),
        as_attachment=True,
        download_name=f'{title}{ext}',
    )


@app.route('/api/debug', methods=['GET'])
def get_debug():
    try:
        ver = yt_dlp.version.__version__
    except Exception:
        ver = 'unknown'
    return jsonify({
        'python_version': sys.version,
        'yt_dlp_version': ver,
        'ffmpeg_path':    FFMPEG_PATH,
    })


# ─────────────────────────────────────────────
#  Core download logic
# ─────────────────────────────────────────────
def download_task(download_id: str, url: str, quality: str):
    """Download video in a background thread.

    Strategy:
      1. Try mweb/ios/android clients (no PO token required).
      2. If that still fails with bot detection, try with tv_embedded only.
      3. If all else fails, surface a clear human-readable error.
    """
    try:
        downloads[download_id]['status'] = 'downloading'

        def progress_hook(d):
            if downloads[download_id]['status'] != 'downloading':
                return
            if d['status'] == 'downloading':
                p = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_percent_str', '0%')).strip()
                s = re.sub(r'\x1b\[[0-9;]*m', '', d.get('_speed_str',  '')).strip()
                downloads[download_id]['progress'] = p
                downloads[download_id]['speed']    = s
            elif d['status'] == 'finished':
                downloads[download_id]['progress'] = '100%'
                downloads[download_id]['speed']    = 'Processing…'

        outtmpl = os.path.join(DOWNLOAD_DIR, f'{download_id}_%(title).100s.%(ext)s')

        # Build format selector
        if quality == 'mp3':
            fmt  = 'bestaudio/best'
            pp   = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}]
            mfmt = None
        elif quality == 'png':
            fmt  = None
            pp   = []
            mfmt = None
        else:
            fmt  = build_format_string(quality)
            pp   = []
            mfmt = 'mp4'

        base_extra = {
            'outtmpl':          outtmpl,
            'progress_hooks':   [progress_hook],
            'merge_output_format': mfmt,
        }
        if fmt:
            base_extra['format'] = fmt
        if pp:
            base_extra['postprocessors'] = pp
        if quality == 'png':
            base_extra['skip_download'] = True

        # ── Attempt 1: default bypass clients ──────────────────────────
        opts = make_ydl_opts(base_extra)
        success = _try_download(download_id, url, quality, opts)

        # ── Attempt 2: tv_embedded only, no player_skip ────────────────
        if not success:
            print(f'[{download_id}] Attempt 1 failed — retrying with tv_embedded only', flush=True)
            opts2 = make_ydl_opts(base_extra)
            opts2['extractor_args'] = {
                'youtube': {'player_client': ['tv_embedded', 'mweb']}
            }
            success = _try_download(download_id, url, quality, opts2)

        if not success:
            raise RuntimeError(
                'YouTube bot detection blocked all download attempts. '
                'Please export fresh cookies from your browser and upload them to the server as cookies.txt. '
                'See: https://github.com/yt-dlp/yt-dlp/wiki/FAQ#how-do-i-pass-cookies-to-yt-dlp'
            )

        # ── Find the downloaded file ────────────────────────────────────
        found = None
        for fname in os.listdir(DOWNLOAD_DIR):
            if fname.startswith(download_id):
                found = os.path.join(DOWNLOAD_DIR, fname)
                break
        if not found and quality != 'png':
            raise RuntimeError('Download appeared to finish but file was not found on disk.')

        downloads[download_id]['status']   = 'completed'
        downloads[download_id]['progress'] = '100%'
        downloads[download_id]['speed']    = 'Done'

    except Exception as e:
        msg = str(e)
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error']  = msg
        print(f'[{download_id}] ERROR: {msg}', flush=True)


def _try_download(download_id: str, url: str, quality: str, opts: dict) -> bool:
    """Attempt a single download with the given opts. Returns True on success."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            # Extract info first to get title
            info = ydl.extract_info(url, download=False)
            title      = info.get('title', 'Media')
            safe_title = secure_filename(title)[:100] or 'Media_File'
            downloads[download_id]['title'] = safe_title

            if quality == 'png':
                import requests as req
                thumb_url = info.get('thumbnail')
                if not thumb_url:
                    raise ValueError('No thumbnail URL found in video metadata')
                fpath = os.path.join(DOWNLOAD_DIR, f'{download_id}_{safe_title}.png')
                with open(fpath, 'wb') as fh:
                    fh.write(req.get(thumb_url, timeout=30).content)
                downloads[download_id]['filename'] = fpath
            else:
                ydl.download([url])

        return True

    except Exception as e:
        err = str(e)
        # Surface bot-detection clearly but don't stop the caller from retrying
        if 'Sign in to confirm' in err or 'bot' in err.lower() or 'PO Token' in err:
            print(f'[{download_id}] Bot detection: {err[:120]}', flush=True)
            return False
        # Any other error (e.g. private video, unsupported site) — re-raise
        raise


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=8080)
