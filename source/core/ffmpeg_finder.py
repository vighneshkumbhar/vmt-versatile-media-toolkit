"""
ffmpeg_finder.py
Locates ffmpeg.exe and ffprobe.exe.

Search order:
  1. User-configured custom path (via Settings → Locate FFmpeg)
  2. Bundled bin/ in PyInstaller internal bundle (_internal/bin/ or _MEIPASS/bin/)
  3. bin/ folder next to VMT.exe (dist/VMT/bin/)
  4. Folder containing the executable itself
  5. System PATH
"""
import os
import sys
import shutil
from pathlib import Path


def _get_app_dir() -> Path:
    """
    Returns the directory that contains VMT.exe (or main.py in dev).
    Works correctly both when running from source and when packaged by PyInstaller.
    """
    if getattr(sys, "frozen", False):
        # Running as PyInstaller bundle — sys.executable is VMT.exe
        return Path(sys.executable).parent
    else:
        # Running from source — go up from source/core/ to project root
        return Path(__file__).parent.parent.parent


_CUSTOM_FFMPEG_PATH:  str | None = None
_CUSTOM_FFPROBE_PATH: str | None = None


def set_custom_paths(ffmpeg: str | None, ffprobe: str | None) -> None:
    global _CUSTOM_FFMPEG_PATH, _CUSTOM_FFPROBE_PATH
    _CUSTOM_FFMPEG_PATH = ffmpeg
    _CUSTOM_FFPROBE_PATH = ffprobe


def _candidates(name: str) -> list[Path]:
    app_dir = _get_app_dir()
    candidates = []
    
    # 1. PyInstaller _MEIPASS (where --add-binary bundles it)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "bin" / name)
        candidates.append(Path(meipass) / name)
    
    # 2. _internal directory in onedir mode
    candidates.append(app_dir / "_internal" / "bin" / name)
    candidates.append(app_dir / "_internal" / name)
    
    # 3. bin/ directory next to VMT.exe or project root
    candidates.append(app_dir / "bin" / name)
    candidates.append(app_dir / name)
    
    return candidates


def find_ffmpeg() -> str | None:
    """Return absolute path to ffmpeg.exe, or None if not found."""
    if _CUSTOM_FFMPEG_PATH and Path(_CUSTOM_FFMPEG_PATH).exists():
        return _CUSTOM_FFMPEG_PATH

    for p in _candidates("ffmpeg.exe"):
        if p.exists():
            return str(p)

    return shutil.which("ffmpeg")


def find_ffprobe() -> str | None:
    """Return absolute path to ffprobe.exe, or None if not found."""
    if _CUSTOM_FFPROBE_PATH and Path(_CUSTOM_FFPROBE_PATH).exists():
        return _CUSTOM_FFPROBE_PATH

    for p in _candidates("ffprobe.exe"):
        if p.exists():
            return str(p)

    return shutil.which("ffprobe")


def detect_hardware_encoders(ffmpeg_path: str) -> dict[str, bool]:
    """
    Run 'ffmpeg -encoders' and detect available hardware encoders.
    Returns dict like {'nvenc': True, 'qsv': False, 'amf': False}
    """
    import subprocess
    result = {"nvenc": False, "qsv": False, "amf": False}
    try:
        proc = subprocess.run(
            [ffmpeg_path, "-encoders", "-v", "quiet"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000  # CREATE_NO_WINDOW
        )
        output = proc.stdout + proc.stderr
        if "h264_nvenc" in output:
            result["nvenc"] = True
        if "h264_qsv" in output:
            result["qsv"] = True
        if "h264_amf" in output:
            result["amf"] = True
    except Exception:
        pass
    return result
