import requests
import yt_dlp
import sys

proxy_api = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=ipport&format=text&timeout=10000"
proxies = requests.get(proxy_api).text.strip().split('\n')

for p in proxies[:5]:
    proxy_url = f"http://{p.strip()}"
    print(f"Testing Proxy: {proxy_url}")
    
    ydl_opts = {
        'proxy': proxy_url,
        'quiet': True,
        'socket_timeout': 10,
        'extractor_args': {'youtube': {'player_client': ['web']}}
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=hM8Su6CJ-C0", download=False)
            url = info['formats'][-1]['url']
            print("Extracted URL successfully!")
            
            # Now try to download it WITHOUT proxy
            resp = requests.get(url, stream=True, timeout=10)
            if resp.status_code == 200:
                print("Direct download SUCCESS!")
                sys.exit(0)
            else:
                print(f"Direct download failed: {resp.status_code}")
    except Exception as e:
        print(f"Failed: {e}")
