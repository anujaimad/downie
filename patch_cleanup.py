import re

with open("app.py", "r") as f:
    content = f.read()

# Replace EVERYTHING in download_task before ytdl_progress_hook
old_regex = r"def download_task\(download_id, url, quality\):.*?def ytdl_progress_hook"
new_code = """def download_task(download_id, url, quality):
    try:
        downloads[download_id]['status'] = 'downloading'
        
        def ytdl_progress_hook"""

content = re.sub(old_regex, new_code, content, flags=re.DOTALL)

with open("app.py", "w") as f:
    f.write(content)
print("Cleaned up app.py!")
