import re

with open("app.py", "r") as f:
    content = f.read()

# Replace the single yt = YouTube(...) with the fallback loop
old_code = r"            yt = YouTube\(url, on_progress_callback=pytube_progress\)"
new_code = """            yt = None
            clients = ['ANDROID', 'IOS', 'TV', 'MWEB', 'WEB', 'ANDROID_CREATOR', 'IOS_CREATOR']
            for client in clients:
                try:
                    temp_yt = YouTube(url, client=client, on_progress_callback=pytube_progress)
                    _ = temp_yt.title
                    yt = temp_yt
                    break
                except Exception:
                    pass
            if not yt:
                raise Exception("YouTube bot detection blocked all requests. Please upload cookies.txt")"""

new_content = re.sub(old_code, new_code, content)

with open("app.py", "w") as f:
    f.write(new_content)
print("Patched app.py with fallback loop!")
