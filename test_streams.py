from pytubefix import YouTube

url = "https://youtu.be/816K9yc9xYE"
yt = YouTube(url)
print("1080p:", yt.streams.filter(res="1080p", progressive=True).first())
print("720p:", yt.streams.filter(res="720p", progressive=True).first())
print("Highest:", yt.streams.get_highest_resolution())
