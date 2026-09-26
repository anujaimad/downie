import requests
import yt_dlp
import sys

ydl_opts = {
    'quiet': True,
    'extractor_args': {'youtube': {'player_client': ['web']}}
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    try:
        info = ydl.extract_info("https://www.youtube.com/watch?v=hM8Su6CJ-C0", download=False)
        url = info['formats'][-1]['url']
        print(f"Got URL! Length: {len(url)}")
        
        # Test download directly
        r1 = requests.get(url, stream=True)
        print(f"Direct status: {r1.status_code}")
        
        # Test download via proxy
        # We need a proxy to test if IP mismatch causes 403
        import urllib.request
        proxy_api = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=ipport&format=text&timeout=10000"
        proxies = requests.get(proxy_api).text.strip().split('\n')
        
        for p in proxies[:3]:
            try:
                print(f"Testing proxy {p}")
                r2 = requests.get(url, proxies={"http": f"http://{p}", "https": f"http://{p}"}, stream=True, timeout=5)
                print(f"Proxy status: {r2.status_code}")
                if r2.status_code == 403:
                    print("IP BINDING CONFIRMED!")
                elif r2.status_code == 200:
                    print("NOT IP BOUND!")
                break
            except:
                pass

    except Exception as e:
        print(e)
