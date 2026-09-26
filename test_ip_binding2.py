from pytubefix import YouTube
import requests

try:
    print("Extracting via pytubefix ANDROID...")
    yt = YouTube("https://www.youtube.com/watch?v=hM8Su6CJ-C0", client="ANDROID")
    stream = yt.streams.get_highest_resolution()
    url = stream.url
    print(f"Extracted URL: {url[:50]}...")
    
    # Try downloading directly (using my sandbox IP)
    r = requests.get(url, stream=True)
    print(f"Sandbox IP Download Status: {r.status_code}")
    
    # Try downloading via proxy (to simulate a different IP)
    proxy_api = "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=http&proxy_format=ipport&format=text&timeout=10000"
    proxies = requests.get(proxy_api).text.strip().split('\n')
    
    for p in proxies[:5]:
        proxy_url = p.strip()
        print(f"Testing proxy {proxy_url}...")
        try:
            r2 = requests.get(url, proxies={"http": f"http://{proxy_url}", "https": f"http://{proxy_url}"}, stream=True, timeout=5)
            print(f"Proxy IP Download Status: {r2.status_code}")
            break
        except Exception as e:
            pass
except Exception as e:
    print(e)
