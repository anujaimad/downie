import re

with open("app.py", "r") as f:
    content = f.read()

# Remove the entire YouTube custom if-block
old_youtube_block = r"""        if 'youtube.com' in url or 'youtu.be' in url:
            from pytubefix import YouTube
            import time
            
            # Helper to calculate speed
            downloads\[download_id\]\['_last_time'\] = time.time\(\)
            downloads\[download_id\]\['_last_bytes'\] = 0
            
            def pytube_progress\(stream, chunk, bytes_remaining\):
                if downloads\[download_id\]\['status'\] != 'downloading':
                    return
                total_size = stream.filesize
                bytes_downloaded = total_size - bytes_remaining
                percentage = \(bytes_downloaded / total_size\) \* 100
                downloads\[download_id\]\['progress'\] = f"\{percentage:.1f\}%"
                
                # Calculate speed
                current_time = time.time\(\)
                time_diff = current_time - downloads\[download_id\].get\('_last_time', current_time\)
                if time_diff > 1.0:
                    bytes_diff = bytes_downloaded - downloads\[download_id\].get\('_last_bytes', 0\)
                    speed_mbps = \(bytes_diff / time_diff\) / \(1024 \* 1024\)
                    downloads\[download_id\]\['speed'\] = f"\{speed_mbps:.1f\} MiB/s"
                    downloads\[download_id\]\['_last_time'\] = current_time
                    downloads\[download_id\]\['_last_bytes'\] = bytes_downloaded

            yt = None
            clients = \['ANDROID', 'IOS', 'TV', 'MWEB', 'WEB', 'ANDROID_CREATOR', 'IOS_CREATOR'\]
            for client in clients:
                try:
                    temp_yt = YouTube\(url, client=client, on_progress_callback=pytube_progress\)
                    _ = temp_yt.streams # This verifies that the stream URL can be fetched without bot detection
                    yt = temp_yt
                    break
                except Exception:
                    pass
            if not yt:
                raise Exception\("YouTube bot detection blocked all requests. Please upload cookies.txt"\)
                
            # Get video and audio streams
            res = format_id if format_id and format_id != 'best' else '1080p'
            
            # Try to get requested resolution, fallback to highest available
            video_stream = yt.streams.filter\(res=res, type="video"\).first\(\)
            if not video_stream:
                video_stream = yt.streams.filter\(type="video"\).order_by\('resolution'\).desc\(\).first\(\)
                
            audio_stream = yt.streams.filter\(only_audio=True\).order_by\('abr'\).desc\(\).first\(\)
            
            if not video_stream or not audio_stream:
                raise Exception\("Could not find suitable video/audio streams"\)
                
            safe_title = yt.title.replace\("/", ""\).replace\("\\\\", ""\)
            downloads\[download_id\]\['title'\] = safe_title
            
            # Download streams
            v_file = video_stream.download\(output_path=DOWNLOAD_DIR, filename=f"v_\{download_id\}.mp4"\)
            a_file = audio_stream.download\(output_path=DOWNLOAD_DIR, filename=f"a_\{download_id\}.mp4"\)
            
            if downloads\[download_id\]\['status'\] != 'downloading':
                return
                
            # Merge using ffmpeg
            downloads\[download_id\]\['progress'\] = "Merging video and audio..."
            out_file = os.path.join\(DOWNLOAD_DIR, f"\{download_id\}_\{safe_title\}.mp4"\)
            
            import subprocess
            import imageio_ffmpeg
            ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe\(\)
            
            subprocess.run\(\[
                ffmpeg_path, '-y', 
                '-i', v_file, 
                '-i', a_file, 
                '-c:v', 'copy', 
                '-c:a', 'aac', 
                out_file
            \], check=True, capture_output=True\)
            
            # Cleanup temp files
            try:
                os.remove\(v_file\)
                os.remove\(a_file\)
            except:
                pass
                
            downloads\[download_id\]\['status'\] = 'completed'
            downloads\[download_id\]\['filename'\] = os.path.basename\(out_file\)
            downloads\[download_id\]\['progress'\] = '100%'
            return"""
            
content = re.sub(old_youtube_block, "", content)

# Add cookiefile to ydl_opts
old_opts = """            'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s_{download_id}.%(ext)s'),
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,"""
new_opts = """            'outtmpl': os.path.join(DOWNLOAD_DIR, f'%(title)s_{download_id}.%(ext)s'),
            'progress_hooks': [ytdl_progress_hook],
            'quiet': True,
            'no_warnings': True,
            'cookiefile': 'cookies.txt' if os.path.exists('cookies.txt') else None,"""
            
content = content.replace(old_opts, new_opts)

with open("app.py", "w") as f:
    f.write(content)
print("Updated app.py!")
