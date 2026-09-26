import requests
import yt_dlp

try:
    # Get a free proxy
    resp = requests.get("https://proxylist.geonode.com/api/proxy-list?limit=1&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps", timeout=10)
    data = resp.json()
    proxy_ip = data['data'][0]['ip']
    proxy_port = data['data'][0]['port']
    proxy_url = f"http://{proxy_ip}:{proxy_port}"
    print(f"Testing Proxy: {proxy_url}")
    
    ydl_opts = {
        'proxy': proxy_url,
        'quiet': True,
        'socket_timeout': 10
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/watch?v=hM8Su6CJ-C0", download=False)
        print("SUCCESS! Proxy bypassed bot detection!")
except Exception as e:
    print(f"Failed: {e}")
