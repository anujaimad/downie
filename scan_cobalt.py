import requests
import json

instances = [
    "https://cobalt.kwiatekmateusz.pl",
    "https://co.wuk.sh",
    "https://cobalt.casi.lv",
    "https://cobalt.seasi.dev",
    "https://cobalt.s.wio.nu",
    "https://api.cobalt.tools"
]

for inst in instances:
    print(f"Testing {inst}...")
    try:
        resp = requests.post(
            f"{inst}/api/json",
            json={"url": "https://www.youtube.com/watch?v=hM8Su6CJ-C0"},
            headers={"Accept": "application/json"},
            timeout=5
        )
        if resp.status_code == 200:
            print(f"SUCCESS: {inst}")
            print(resp.json())
        else:
            print(f"Failed HTTP {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")
