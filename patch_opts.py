import re

with open("app.py", "r") as f:
    content = f.read()

old_code = """        # Highly effective fix for YouTube bot detection: Use cookies if available
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'"""

new_code = """        # Highly effective fix for YouTube bot detection: Use cookies if available
        if os.path.exists('cookies.txt'):
            ydl_opts['cookiefile'] = 'cookies.txt'
            # When using cookies, we must remove mobile clients from extractor_args because they don't support cookies
            # yt-dlp master will automatically use the optimal web/default client with cookies
            if 'extractor_args' in ydl_opts:
                del ydl_opts['extractor_args']"""
                
content = content.replace(old_code, new_code)

with open("app.py", "w") as f:
    f.write(content)
print("Updated app.py extractor args for cookies!")
