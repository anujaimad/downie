from pytubefix import YouTube

try:
    yt = YouTube('https://www.youtube.com/watch?v=hM8Su6CJ-C0', client='WEB', use_po_token=True)
    print(f"WEB Client Streams: {len(yt.streams)}")
except Exception as e:
    print(f"WEB failed: {e}")

try:
    yt = YouTube('https://www.youtube.com/watch?v=hM8Su6CJ-C0', client='ANDROID', use_po_token=True)
    print(f"ANDROID Client Streams: {len(yt.streams)}")
except Exception as e:
    print(f"ANDROID failed: {e}")
