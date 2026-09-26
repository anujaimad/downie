from curl_cffi import requests
import json

try:
    resp = requests.get('https://cobalt.directory/api/instances', impersonate="chrome")
    print(resp.status_code)
    print(resp.text[:200])
    with open("instances.json", "w") as f:
         f.write(resp.text)
except Exception as e:
    print(e)
