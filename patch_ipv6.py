import re

with open("app.py", "r") as f:
    content = f.read()

old_opts = """            'sleep_requests': 1, # Minor delay to avoid IP rate limits"""
new_opts = """            'sleep_requests': 1, # Minor delay to avoid IP rate limits
            'source_address': '0.0.0.0', # Try forcing IPv4/IPv6
            'force_ipv4': False,"""

content = content.replace(old_opts, new_opts)
with open("app.py", "w") as f:
    f.write(content)
