from pytubefix import YouTube
from pytubefix.cli import on_progress

url = "https://youtu.be/816K9yc9xYE"
try:
    yt = YouTube(url, use_oauth=False, allow_oauth_cache=True)
    print("Title:", yt.title)
    print("Thumbnail:", yt.thumbnail_url)
except Exception as e:
    print("Error:", str(e))
