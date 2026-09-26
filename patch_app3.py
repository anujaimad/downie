import re

with open("app.py", "r") as f:
    content = f.read()

old_code = """                    temp_yt = YouTube(url, client=client, on_progress_callback=pytube_progress)
                    _ = temp_yt.title
                    yt = temp_yt
                    break"""
                    
new_code = """                    temp_yt = YouTube(url, client=client, on_progress_callback=pytube_progress)
                    _ = temp_yt.streams # This verifies that the stream URL can be fetched without bot detection
                    yt = temp_yt
                    break"""

new_content = content.replace(old_code, new_code)

with open("app.py", "w") as f:
    f.write(new_content)
print("Patched app.py streams check!")
