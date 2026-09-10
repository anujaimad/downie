import yt_dlp

ydl_opts = {
    'quiet': False,
    'no_warnings': False,
    'extractor_args': {'youtube': {'client': ['web']}},
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info('https://youtu.be/816K9yc9xYE', download=False)
        print("Success:", info.get('title'))
        formats = [f['format_id'] for f in info.get('formats', [])]
        print("Formats:", formats)
except Exception as e:
    print("Error:", str(e))
