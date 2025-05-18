# app.py
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, flash, session
import yt_dlp
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Change this for production

# Configuration
DOWNLOAD_FOLDER = './downloads'
ALLOWED_EXTENSIONS = {'mp4', 'webm', 'mkv', 'flv', 'avi', 'mov'}
app.config['DOWNLOAD_FOLDER'] = DOWNLOAD_FOLDER

# Ensure download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def list_formats(url):
    """
    Lists all available formats for the given video URL.
    Returns the video info dictionary and formats list.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiesfrombrowser': ('chrome',)  # Add browser cookies for authentication
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        formats = info.get('formats', [])
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

def download_video(url, format_code, formats):
    """
    Downloads selected video + best audio merged with progress tracking.
    """
    audio_code = find_best_audio(formats)
    final_format = f"{format_code}+{audio_code}"

    class ProgressLogger:
        def __init__(self):
            self.last_progress = 0

        def hook(self, d):
            if d['status'] == 'downloading':
                session['download_status'] = 'downloading'
                session['download_percent'] = float(d.get('_percent_str', '0%').rstrip('%'))
                session['download_speed'] = d.get('_speed_str', 'N/A')
                session['download_eta'] = d.get('_eta_str', 'N/A')
            elif d['status'] == 'finished':
                session['download_status'] = 'finished'
                session['download_percent'] = 100

    progress_logger = ProgressLogger()

    ydl_opts = {
        'format': final_format,
        'outtmpl': os.path.join(app.config['DOWNLOAD_FOLDER'], '%(title)s.%(ext)s'),
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'progress_hooks': [progress_logger.hook],
        'cookiesfrombrowser': ('chrome',)  # Add browser cookies for authentication
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        raise Exception(f"Download error: {str(e)}")

@app.route('/progress')
def progress():
    return jsonify({
        'status': session.get('download_status', 'starting'),
        'percent': session.get('download_percent', 0),
        'speed': session.get('download_speed', 'N/A'),
        'eta': session.get('download_eta', 'N/A')
    })

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form.get('url')
        if not url:
            flash('Please enter a YouTube URL', 'error')
            return redirect(url_for('index'))

        try:
            video_info, formats = list_formats(url)
            return render_template('formats.html', 
                                video_info=video_info, 
                                formats=formats,
                                url=url)
        except Exception as e:
            flash(f'Error retrieving video info: {str(e)}', 'error')
            return redirect(url_for('index'))

    return render_template('index.html')

@app.route('/download', methods=['POST'])
def download():
    url = request.form.get('url')
    format_code = request.form.get('format_code')
    
    if not url or not format_code:
        flash('Missing required parameters', 'error')
        return redirect(url_for('index'))

    try:
        video_info, formats = list_formats(url)
        filename = download_video(url, format_code, formats)
        flash('Download completed successfully!', 'success')
        return render_template('download.html', 
                            filename=os.path.basename(filename),
                            video_title=video_info.get('title', 'Unknown Title'))
    except Exception as e:
        flash(f'Download failed: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/downloads/<filename>')
def download_file(filename):
    return send_from_directory(app.config['DOWNLOAD_FOLDER'], filename, as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)