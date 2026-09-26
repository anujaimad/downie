import requests

instances = [
    "https://vid.puffyan.us",
    "https://invidious.jing.rocks",
    "https://invidious.nerdvpn.de",
    "https://yewtu.be"
]

for inst in instances:
    try:
        url = f"{inst}/api/v1/videos/hM8Su6CJ-C0"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if 'formatStreams' in data:
                print(f"Success with {inst}! Streams: {len(data['formatStreams'])}")
                break
    except Exception as e:
        print(f"Failed {inst}: {e}")
