from pytubefix import YouTube

url = 'https://www.youtube.com/watch?v=hM8Su6CJ-C0'
clients = ['ANDROID', 'IOS', 'TV', 'MWEB', 'WEB']
yt = None
for client in clients:
    try:
        temp_yt = YouTube(url, client=client)
        title = temp_yt.title
        print(f"Success with {client}: {title}")
        yt = temp_yt
        break
    except Exception as e:
        print(f"Failed with {client}: {e}")
