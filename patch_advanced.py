import re

with open("app.py", "r") as f:
    content = f.read()

# Add a cleanup thread for downloaded files (runs every hour, deletes files older than 2 hours)
cleanup_code = """
import time
import shutil

# Advanced Hack: Prevent Disk Space exhaustion on cloud servers (Render)
def cleanup_old_files():
    while True:
        try:
            current_time = time.time()
            for filename in os.listdir(DOWNLOAD_DIR):
                filepath = os.path.join(DOWNLOAD_DIR, filename)
                # Check if file is older than 2 hours
                if os.path.isfile(filepath) and current_time - os.path.getctime(filepath) > 7200:
                    os.remove(filepath)
            
            # Cleanup memory dictionary
            expired_ids = [did for did, ddata in downloads.items() if ddata.get('status') in ['completed', 'error'] and current_time - ddata.get('_start_time', current_time) > 7200]
            for did in expired_ids:
                del downloads[did]
                
        except Exception as e:
            print(f"Cleanup error: {e}")
        time.sleep(3600)

cleanup_thread = threading.Thread(target=cleanup_old_files, daemon=True)
cleanup_thread.start()
"""

# Insert cleanup_code after imports
content = re.sub(r"(import threading\n)", r"\1" + cleanup_code, content)

# Enhance start_download to record _start_time
start_dl_old = """    downloads[download_id] = {
        'status': 'starting',
        'progress': '0%',
        'speed': '',
        'url': url,
        'quality': quality
    }"""
start_dl_new = """    downloads[download_id] = {
        'status': 'starting',
        'progress': '0%',
        'speed': '',
        'url': url,
        'quality': quality,
        '_start_time': time.time()
    }"""
content = content.replace(start_dl_old, start_dl_new)

# Enhance ydl_opts in download_task for maximum robustness
old_opts = """        ydl_opts = {
            'outtmpl': filepath_template,
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,
            'concurrent_fragment_downloads': 10,
            'extractor_args': {'youtube': {'player_client': ['web', 'ios', 'android']}}
        }"""
        
new_opts = """        # Advanced Options: Bulletproof downloading configuration
        ydl_opts = {
            'outtmpl': filepath_template,
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,
            'ffmpeg_location': FFMPEG_PATH,
            'concurrent_fragment_downloads': 5, # Reduced from 10 to prevent Out of Memory on Render free tier
            'retries': 15, # High retries for flaky connections
            'fragment_retries': 15,
            'extractor_retries': 5,
            'socket_timeout': 30, # Prevent hanging
            'geo_bypass': True, # Bypass geographic restrictions
            'nocheckcertificate': True, # Prevent SSL errors
            'sleep_requests': 1, # Minor delay to avoid IP rate limits
            'extractor_args': {'youtube': {'player_client': ['ios', 'android', 'web']}} # Fallback rotation
        }"""
        
content = content.replace(old_opts, new_opts)

# Better exception handling
old_except = """    except Exception as e:
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = str(e)"""

new_except = """    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "reloaded" in error_msg:
            error_msg = "Bot detection triggered. Please update your cookies.txt!"
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = error_msg"""
content = content.replace(old_except, new_except)

with open("app.py", "w") as f:
    f.write(content)

print("Applied advanced configurations!")
