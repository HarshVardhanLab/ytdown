#!/usr/bin/env python3
import yt_dlp
import os

def list_formats(url):
    """
    Lists all available formats for the given video URL.
    Returns the video info dictionary and formats list.
    """
    ydl_opts = {'quiet': True, 'no_warnings': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
        print(f"\nAvailable formats for: {info.get('title', 'Unknown Title')}\n")
        print("{:<8} {:<10} {:<10} {}".format("Code", "Ext", "Res", "Note"))
        print("-" * 50)
        for f in formats:
            if f.get('vcodec') != 'none':
                print("{:<8} {:<10} {:<10} {}".format(
                    f['format_id'],
                    f['ext'],
                    f.get('resolution', 'audio'),
                    f.get('format_note', '')
                ))
        return info, formats

def find_best_audio(formats):
    """
    Find the best audio-only format with the highest bitrate.
    Safely skips formats with missing or None 'abr'.
    """
    audio_formats = [
        f for f in formats if f.get('vcodec') == 'none' and f.get('acodec') != 'none'
    ]
    audio_formats = [f for f in audio_formats if f.get('abr') is not None]

    if not audio_formats:
        raise ValueError("No valid audio formats found.")

    best_audio = max(audio_formats, key=lambda f: f['abr'])
    return best_audio['format_id']

def download_video(url, format_code, formats, output_path='./downloads'):
    """
    Downloads selected video + best audio merged.
    """
    os.makedirs(output_path, exist_ok=True)

    audio_code = find_best_audio(formats)
    final_format = f"{format_code}+{audio_code}"

    ydl_opts = {
        'format': final_format,
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print("\nDownload completed successfully!")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

def progress_hook(d):
    if d['status'] == 'downloading':
        print(f"\rDownloading: {d['_percent_str']} of {d.get('_total_bytes_str', 'Unknown')} at {d.get('_speed_str', 'Unknown')}", end='')
    elif d['status'] == 'finished':
        print("\nProcessing video...")

def main():
    url = input("Enter YouTube video URL: ").strip()
    output_path = input("Enter output directory (or press Enter for './downloads'): ").strip()
    if not output_path:
        output_path = './downloads'

    video_info, formats = list_formats(url)
    format_code = input("\nEnter video-only format code (e.g., 137): ").strip()
    download_video(url, format_code, formats, output_path)

if __name__ == '__main__':
    main()
