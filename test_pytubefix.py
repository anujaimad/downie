from pytubefix import YouTube
from pytubefix.cli import on_progress
try:
    print("Testing WEB client with PO Token...")
    yt = YouTube("https://www.youtube.com/watch?v=hM8Su6CJ-C0", client="WEB", use_po_token=True)
    print(f"Title: {yt.title}")
    stream = yt.streams.get_highest_resolution()
    print(f"URL: {stream.url}")
    print("SUCCESS!")
except Exception as e:
    print(f"WEB Error: {e}")

try:
    print("\nTesting ANDROID client with PO Token...")
    yt = YouTube("https://www.youtube.com/watch?v=hM8Su6CJ-C0", client="ANDROID", use_po_token=True)
    print(f"Title: {yt.title}")
    stream = yt.streams.get_highest_resolution()
    print(f"URL: {stream.url}")
    print("SUCCESS!")
except Exception as e:
    print(f"ANDROID Error: {e}")
