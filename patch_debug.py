import re

with open("app.py", "r") as f:
    content = f.read()

debug_endpoint = """
@app.route('/api/debug', methods=['GET'])
def get_debug():
    import sys
    try:
        import yt_dlp
        ytdl_version = yt_dlp.version.__version__
    except:
        ytdl_version = "Not installed"
    
    return jsonify({
        "python_version": sys.version,
        "yt_dlp_version": ytdl_version,
        "cookies_exist": os.path.exists('cookies.txt')
    })
"""

content += debug_endpoint

with open("app.py", "w") as f:
    f.write(content)
