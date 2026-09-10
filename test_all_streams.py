from pytubefix import YouTube

url = "https://youtu.be/816K9yc9xYE"
yt = YouTube(url)
for s in yt.streams:
    print(s)
