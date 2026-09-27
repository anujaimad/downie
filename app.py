# Application: DOWNIE
# Developed by: 1mad
# 100% Copyrights to 1mad. All rights reserved.

import os
import re
import sys
import time
import uuid
import json
import threading
import imageio_ffmpeg
from urllib.parse import urlparse

import yt_dlp
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

# ─────────────────────────────────────────────────────────────────────────────
#  Bootstrap
# ─────────────────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
downloads: dict = {}

# ── Restore cookies.txt from environment variable (for Render.com) ────────────
#
#  On Render: Dashboard → Environment → add key YOUTUBE_COOKIES
#  Value: paste the entire text content of your cookies.txt file.
#
#  How to get fresh cookies (do this every few weeks):
#    1. Install the "Get cookies.txt LOCALLY" Chrome/Brave extension
#    2. Go to youtube.com while logged in
#    3. Click the extension → Export → copy the text
#    4. Paste into Render YOUTUBE_COOKIES environment variable
#
_cookies_env = os.environ.get('YOUTUBE_COOKIES', '').strip()
COOKIES_FILE  = 'cookies.txt'

if _cookies_env:
    with open(COOKIES_FILE, 'w') as _fh:
        _fh.write(_cookies_env)
    print('[auth] ✅ Loaded cookies.txt from YOUTUBE_COOKIES env var', flush=True)
elif os.path.exists(COOKIES_FILE):
    print('[auth] 📄 Using existing cookies.txt file', flush=True)
else:
    print('[auth] ⚠️  No cookies — bot detection may occur on Render', flush=True)

# ─────────────────────────────────────────────────────────────────────────────
#  Security headers on every response
# ─────────────────────────────────────────────────────────────────────────────
@app.after_request
def apply_security_headers(response):
    h = response.headers
    h['X-Content-Type-Options']    = 'nosniff'
    h['X-Frame-Options']           = 'DENY'
    h['X-XSS-Protection']          = '1; mode=block'
    h['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    h['Referrer-Policy']           = 'strict-origin-when-cross-origin'
    h['Permissions-Policy']        = 'geolocation=(), microphone=()'
    return response

# ─────────────────────────────────────────────────────────────────────────────
#  Background disk/memory cleanup
# ─────────────────────────────────────────────────────────────────────────────
def _cleanup_loop():
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
            stale = [
                did for did, d in list(downloads.items())
                if d.get('status') in ('completed', 'error')
                and now - d.get('_start_time', now) > 7200
            ]
            for did in stale:
                downloads.pop(did, None)
        except Exception as e:
            print(f'[cleanup] {e}', flush=True)
        time.sleep(3600)

threading.Thread(target=_cleanup_loop, daemon=True).start()

# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────
def is_valid_url(url: str) -> bool:
    try:
        r = urlparse(url)
        return r.scheme in ('http', 'https') and bool(r.netloc)
    except ValueError:
        return False


def _format_string(quality: str) -> str:
    """Build a robust format selector with deep fallback chain.

    Priority: H264+AAC (mux-only) → any video+audio → best available.
    The final /best ensures SOMETHING always downloads regardless of
    which formats YouTube provides for the specific video.
    """
    h_map = {'best': None, '2k': 1440, '1080p': 1080, '720p': 720,
             '480p': 480, '360p': 360, '240p': 240, '144p': 144}
    h = h_map.get(quality)
    if h is None:
        return (
            'bestvideo[ext=mp4]+bestaudio[ext=m4a]'
            '/bestvideo[ext=mp4]+bestaudio'
            '/bestvideo+bestaudio[ext=m4a]'
            '/bestvideo+bestaudio'
            '/best'
        )
    return (
        # 1st choice: H264 video + AAC audio at desired height (mux-only, fastest)
        f'bestvideo[ext=mp4][height<={h}]+bestaudio[ext=m4a]'
        # 2nd: any mp4 video + any audio at desired height
        f'/bestvideo[ext=mp4][height<={h}]+bestaudio'
        # 3rd: any video + AAC at desired height
        f'/bestvideo[height<={h}]+bestaudio[ext=m4a]'
        # 4th: any video + any audio at desired height (e.g. webm/VP9)
        f'/bestvideo[height<={h}]+bestaudio'
        # 5th: combined format at desired height
        f'/best[height<={h}]'
        # 6th: best video+audio of ANY height (relaxed resolution constraint)
        '/bestvideo[ext=mp4]+bestaudio[ext=m4a]'
        '/bestvideo+bestaudio'
        # Final guaranteed fallback
        '/best'
    )


def _has_valid_cookies() -> bool:
    return os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 100


def _base_opts(extra: dict = None) -> dict:
    """Build yt-dlp options.

    Strategy:
    - With cookies  → use web_safari client (most compatible with cookies)
    - Without cookies → use mweb/ios/android clients (no PO-token required)
    """
    opts = {
        'quiet':                         True,
        'no_warnings':                   True,
        'geo_bypass':                    True,
        'nocheckcertificate':            True,
        'socket_timeout':                60,
        'retries':                       10,
        'fragment_retries':              10,
        'extractor_retries':             5,
        'sleep_requests':                1,
        'ffmpeg_location':               FFMPEG_PATH,
        'concurrent_fragment_downloads': 4,
    }

    if _has_valid_cookies():
        opts['cookiefile'] = COOKIES_FILE
        # web_safari works best with cookies; ios/android don't support browser cookies
        opts['extractor_args'] = {
            'youtube': {'player_client': ['web_safari', 'web', 'mweb']}
        }
    else:
        # Mobile/embedded clients skip PO-token check
        opts['extractor_args'] = {
            'youtube': {
                'player_client': ['mweb', 'ios', 'android', 'tv_embedded'],
                'player_skip':   ['webpage', 'configs'],
            }
        }

    if extra:
        opts.update(extra)
    return opts


# ─────────────────────────────────────────────────────────────────────────────
#  Routes
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/')
def serve_index():
    return app.send_static_file('index.html')


@app.route('/api/info', methods=['POST'])
def get_info():
    data = request.json or {}
    url  = (data.get('url') or '').strip()

    if not url or not is_valid_url(url):
        return jsonify({'error': 'Invalid URL provided.'}), 400

    try:
        # Fast path: YouTube oEmbed (no yt-dlp, instant)
        if 'youtube.com' in url or 'youtu.be' in url:
            import requests as req
            r = req.get(f'https://www.youtube.com/oembed?url={url}&format=json', timeout=10)
            if r.status_code == 200:
                d = r.json()
                return jsonify({'title': d.get('title', 'Unknown Title'),
                                'thumbnail': d.get('thumbnail_url', '')})

        opts = _base_opts({'extract_flat': True})
        with yt_dlp.YoutubeDL(opts) as ydl:
            info  = ydl.extract_info(url, download=False)
            thumb = info.get('thumbnail') or (
                f"https://img.youtube.com/vi/{info['id']}/maxresdefault.jpg"
                if info.get('id') else ''
            )
            return jsonify({'title': info.get('title', 'Unknown Title'), 'thumbnail': thumb})

    except Exception as e:
        return jsonify({'error': f'Failed to fetch: {str(e)}'}), 500


@app.route('/api/download', methods=['POST'])
def start_download():
    data    = request.json or {}
    url     = (data.get('url') or '').strip()
    quality = (data.get('quality') or '720p').strip()

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
    threading.Thread(target=_download_task, args=(download_id, url, quality), daemon=True).start()
    return jsonify({'download_id': download_id})


@app.route('/api/progress/<download_id>', methods=['GET'])
def get_progress(download_id):
    if download_id not in downloads:
        return jsonify({'error': 'Download not found'}), 404
    return jsonify(downloads[download_id])


@app.route('/api/file/<download_id>', methods=['GET'])
def get_file(download_id):
    matched = next(
        (os.path.join(DOWNLOAD_DIR, f)
         for f in os.listdir(DOWNLOAD_DIR) if f.startswith(download_id)),
        None,
    )
    if not matched:
        return (
            '<!doctype html><html><head><title>File Expired</title>'
            '<style>body{font-family:sans-serif;text-align:center;margin-top:60px;'
            'background:#f9f9f9;color:#333}a{color:#2563EB}</style></head>'
            '<body><h2>⚠️ File expired or not found</h2>'
            '<p>The server restarted or deleted the file to free space.</p>'
            '<a href="/">← Go back and download again</a></body></html>',
            404,
        )
    ext   = os.path.splitext(matched)[1]
    title = 'Media_File'
    if download_id in downloads:
        title = downloads[download_id].get('title', 'Media_File')
    else:
        part = os.path.basename(matched)[len(download_id) + 1: -len(ext)]
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
        'python_version':  sys.version,
        'yt_dlp_version':  ver,
        'ffmpeg_path':     FFMPEG_PATH,
        'cookies_present': _has_valid_cookies(),
    })


# ─────────────────────────────────────────────────────────────────────────────
#  Download worker
# ─────────────────────────────────────────────────────────────────────────────
def _download_task(download_id: str, url: str, quality: str):
    try:
        downloads[download_id]['status'] = 'downloading'
        ansi = re.compile(r'\x1b\[[0-9;]*m')

        def hook(d):
            if downloads[download_id]['status'] != 'downloading':
                return
            if d['status'] == 'downloading':
                p = ansi.sub('', d.get('_percent_str', '0%')).strip()
                s = ansi.sub('', d.get('_speed_str', '')).strip()
                downloads[download_id].update(progress=p, speed=s)
            elif d['status'] == 'finished':
                downloads[download_id].update(progress='100%', speed='Processing…')

        outtmpl = os.path.join(DOWNLOAD_DIR, f'{download_id}_%(title).100s.%(ext)s')

        if quality == 'mp3':
            fmt, mfmt, pp, skip_dl = ('bestaudio/best', None,
                [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '320'}],
                False)
        elif quality == 'png':
            fmt, mfmt, pp, skip_dl = None, None, [], True
        else:
            fmt, mfmt, pp, skip_dl = _format_string(quality), 'mp4', [], False

        quality_extra = {
            'outtmpl':             outtmpl,
            'progress_hooks':      [hook],
            'merge_output_format': mfmt,
        }
        if fmt:
            quality_extra['format'] = fmt
        if pp:
            quality_extra['postprocessors'] = pp
        if skip_dl:
            quality_extra['skip_download'] = True

        # ── Attempt 1: primary strategy (with cookies if available) ──────────
        ok, err = _attempt(download_id, url, quality, _base_opts(quality_extra))

        # ── Attempt 2: cookieless mobile clients fallback ────────────────────
        if not ok:
            print(f'[{download_id}] Attempt 1 failed ({err[:80]}) → trying cookieless mobile clients', flush=True)
            fallback_opts = dict(quality_extra)
            fallback_opts.update({
                'quiet':          True,
                'no_warnings':    True,
                'geo_bypass':     True,
                'nocheckcertificate': True,
                'socket_timeout': 60,
                'retries':        10,
                'fragment_retries': 10,
                'ffmpeg_location': FFMPEG_PATH,
                'concurrent_fragment_downloads': 4,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['mweb', 'ios', 'android'],
                        'player_skip':   ['webpage', 'configs'],
                    }
                },
            })
            ok, err = _attempt(download_id, url, quality, fallback_opts)

        # ── Attempt 3: tv_embedded only ───────────────────────────────────────
        if not ok:
            print(f'[{download_id}] Attempt 2 failed ({err[:80]}) → trying tv_embedded', flush=True)
            tv_opts = dict(quality_extra)
            tv_opts.update({
                'quiet':          True,
                'no_warnings':    True,
                'geo_bypass':     True,
                'nocheckcertificate': True,
                'socket_timeout': 60,
                'retries':        10,
                'fragment_retries': 10,
                'ffmpeg_location': FFMPEG_PATH,
                'concurrent_fragment_downloads': 4,
                'extractor_args': {'youtube': {'player_client': ['tv_embedded']}},
            })
            ok, err = _attempt(download_id, url, quality, tv_opts)

        if not ok:
            raise RuntimeError(
                'YouTube is blocking this server\'s IP address.\n\n'
                'To fix permanently:\n'
                '1. Install the "Get cookies.txt LOCALLY" extension in your browser\n'
                '2. Go to youtube.com while logged in to your Google account\n'
                '3. Click the extension → Export cookies\n'
                '4. Go to Render.com → Your Service → Environment\n'
                '5. Add: Key = YOUTUBE_COOKIES, Value = (paste the cookies text)\n'
                '6. Click Save and Render will redeploy automatically.'
            )

        if quality != 'png':
            found = next(
                (os.path.join(DOWNLOAD_DIR, f)
                 for f in os.listdir(DOWNLOAD_DIR) if f.startswith(download_id)),
                None,
            )
            if not found:
                raise RuntimeError('Download finished but output file not found on disk.')

        downloads[download_id].update(status='completed', progress='100%', speed='Done')

    except Exception as e:
        downloads[download_id].update(status='error', error=str(e))
        print(f'[{download_id}] FATAL: {e}', flush=True)


def _attempt(download_id: str, url: str, quality: str, opts: dict):
    """Single download attempt. Returns (success, error_str)."""
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info       = ydl.extract_info(url, download=False)
            title      = info.get('title', 'Media')
            safe_title = (secure_filename(title) or 'Media_File')[:100]
            downloads[download_id]['title'] = safe_title

            if quality == 'png':
                import requests as req
                thumb = info.get('thumbnail', '')
                if not thumb:
                    raise ValueError('No thumbnail URL in metadata.')
                fpath = os.path.join(DOWNLOAD_DIR, f'{download_id}_{safe_title}.png')
                with open(fpath, 'wb') as fh:
                    fh.write(req.get(thumb, timeout=30).content)
                downloads[download_id]['filename'] = fpath
            else:
                ydl.download([url])
        return True, ''
    except Exception as e:
        msg = str(e)
        bot_signals = ('sign in to confirm', 'bot', 'po token', 'not a robot')
        if any(s in msg.lower() for s in bot_signals):
            return False, msg   # retriable
        raise                   # hard error → bubble up


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=False, port=8080)
