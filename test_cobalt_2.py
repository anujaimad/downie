import requests

instances = [
    "https://cobalt-11-h57i.onrender.com",
    "https://cobalt.um1ng.me",
    "https://cobalt-production-a2db.up.railway.app",
    "https://cobalt-api.meowing.de"
]

for inst in instances:
    print(f"Testing {inst}...")
    try:
        resp = requests.post(
            f"{inst}/", # Cobalt v11 uses / 
            json={"url": "https://www.youtube.com/watch?v=hM8Su6CJ-C0"},
            headers={"Accept": "application/json"},
            timeout=5
        )
        print(f"Status: {resp.status_code}")
        print(resp.text[:200])
    except Exception as e:
        print(e)
