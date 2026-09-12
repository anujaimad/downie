from pytubefix import YouTube
import os
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
yt = YouTube('https://www.youtube.com/watch?v=5Vsn3Az9cvU', client='ANDROID')
stream = yt.streams.filter(progressive=True).order_by('resolution').desc().first()
print("Downloading:", stream.resolution)
out = stream.download(output_path=DOWNLOAD_DIR)
print("Saved to:", out)
