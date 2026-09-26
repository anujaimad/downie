import re

with open("app.py", "r") as f:
    content = f.read()

old_except = """    except Exception as e:
        error_msg = str(e)
        if "Sign in to confirm" in error_msg or "reloaded" in error_msg:
            error_msg = "Bot detection triggered. Please update your cookies.txt!"
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = error_msg"""

new_except = """    except Exception as e:
        error_msg = str(e)
        raw_error = error_msg
        if "Sign in to confirm" in error_msg or "reloaded" in error_msg:
            error_msg = f"Bot detection triggered. Please update your cookies.txt! (Raw: {raw_error})"
        else:
            error_msg = f"Error: {raw_error}"
        downloads[download_id]['status'] = 'error'
        downloads[download_id]['error'] = error_msg"""
        
content = content.replace(old_except, new_except)

with open("app.py", "w") as f:
    f.write(content)
