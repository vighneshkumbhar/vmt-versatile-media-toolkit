"""
downloader.py
Background threads wrapping yt-dlp for non-blocking YouTube metadata extraction and video downloading.
"""
import os
import sys
import time
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtCore import QThread, Signal

# Ensure isolated dependencies folder is on sys.path
_CONTAINER_DIR = Path(__file__).resolve().parent.parent
_DEPS_DIR = _CONTAINER_DIR / "dependencies"
if _DEPS_DIR.exists() and str(_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_DEPS_DIR))

# Also support running inside installed VMT extension folder
_EXT_DEPS_DIR = Path(__file__).resolve().parent / "dependencies"
if _EXT_DEPS_DIR.exists() and str(_EXT_DEPS_DIR) not in sys.path:
    sys.path.insert(0, str(_EXT_DEPS_DIR))

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

logger = logging.getLogger(__name__)


def is_ytdlp_available() -> bool:
    return yt_dlp is not None


class FetchMetadataThread(QThread):
    info_ready = Signal(dict)
    failed = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url

    def run(self):
        if not yt_dlp:
            self.failed.emit("yt-dlp is not available.")
            return

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extract_flat': False,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)
                if not info:
                    self.failed.emit("Could not fetch video details.")
                    return

                title = info.get('title', 'Unknown Title')
                duration = info.get('duration', 0)
                thumbnail = info.get('thumbnail', '')
                formats = info.get('formats', [])

                # Format duration string
                if duration:
                    m, s = divmod(int(duration), 60)
                    h, m = divmod(m, 60)
                    dur_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
                else:
                    dur_str = "Live / Unknown"

                result = {
                    'title': title,
                    'duration_sec': duration,
                    'duration_str': dur_str,
                    'thumbnail': thumbnail,
                    'id': info.get('id', ''),
                    'webpage_url': info.get('webpage_url', self.url),
                }
                self.info_ready.emit(result)
        except Exception as e:
            self.failed.emit(str(e))


class DownloadVideoThread(QThread):
    progress = Signal(float, str, str, str)  # pct, status, speed, eta
    completed = Signal(str)                  # output_filepath
    failed = Signal(str)

    def __init__(self, url: str, output_folder: str, mode: str, quality: str, fmt: str, ffmpeg_path: Optional[str] = None):
        super().__init__()
        self.url = url
        self.output_folder = output_folder
        self.mode = mode.lower()        # "video" or "audio"
        self.quality = quality.lower()  # "best", "1080p", "720p", "480p", "360p"
        self.fmt = fmt.lower()          # "mp4", "mkv", "mp3", "m4a", "wav"
        self.ffmpeg_path = ffmpeg_path
        self._cancelled = False
        self._output_path = ""

    def cancel(self):
        self._cancelled = True

    def run(self):
        if not yt_dlp:
            self.failed.emit("yt-dlp is not available.")
            return

        os.makedirs(self.output_folder, exist_ok=True)
        out_tmpl = os.path.join(self.output_folder, '%(title)s.%(ext)s')

        # Build yt-dlp format selector
        if self.mode == "audio":
            format_spec = "bestaudio/best"
        else:
            if "1080" in self.quality:
                format_spec = "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
            elif "720" in self.quality:
                format_spec = "bestvideo[height<=720]+bestaudio/best[height<=720]/best"
            elif "480" in self.quality:
                format_spec = "bestvideo[height<=480]+bestaudio/best[height<=480]/best"
            elif "360" in self.quality:
                format_spec = "bestvideo[height<=360]+bestaudio/best[height<=360]/best"
            else:
                format_spec = "bestvideo+bestaudio/best"

        ydl_opts: Dict[str, Any] = {
            'format': format_spec,
            'outtmpl': out_tmpl,
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [self._progress_hook],
        }

        # If FFmpeg path provided, pass ffmpeg_location
        if self.ffmpeg_path and os.path.exists(self.ffmpeg_path):
            ffmpeg_dir = os.path.dirname(self.ffmpeg_path)
            ydl_opts['ffmpeg_location'] = ffmpeg_dir

        # Add postprocessors for format conversions
        postprocessors = []
        if self.mode == "audio":
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.fmt if self.fmt in ("mp3", "m4a", "wav") else "mp3",
                'preferredquality': '192',
            })
        elif self.fmt in ("mp4", "mkv"):
            ydl_opts['merge_output_format'] = self.fmt

        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=True)
                if self._cancelled:
                    self.failed.emit("Download cancelled by user.")
                    return

                if info:
                    filename = ydl.prepare_filename(info)
                    # Check for extension change if audio extracted or container merged
                    if self.mode == "audio":
                        ext = self.fmt if self.fmt in ("mp3", "m4a", "wav") else "mp3"
                        base, _ = os.path.splitext(filename)
                        filename = f"{base}.{ext}"
                    elif self.fmt in ("mp4", "mkv"):
                        base, _ = os.path.splitext(filename)
                        filename = f"{base}.{self.fmt}"

                    self._output_path = filename
                    self.progress.emit(100.0, "Complete!", "0 KB/s", "00:00")
                    self.completed.emit(self._output_path)
                else:
                    self.failed.emit("Failed to download video.")
        except Exception as e:
            if self._cancelled:
                self.failed.emit("Download cancelled by user.")
            else:
                self.failed.emit(str(e))

    def _progress_hook(self, d: dict):
        if self._cancelled:
            raise Exception("Download cancelled by user.")

        status = d.get('status')
        if status == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
            downloaded = d.get('downloaded_bytes', 0)
            pct = (downloaded / total * 100.0) if total > 0 else 0.0

            speed = d.get('speed') or 0
            speed_str = f"{speed / 1024 / 1024:.1f} MB/s" if speed >= 1024 * 1024 else f"{speed / 1024:.0f} KB/s"

            eta = d.get('eta') or 0
            eta_str = f"{int(eta)}s" if eta else "--"

            self.progress.emit(pct, f"Downloading... {pct:.1f}%", speed_str, eta_str)
        elif status == 'finished':
            self.progress.emit(99.0, "Processing media with FFmpeg...", "--", "0s")
