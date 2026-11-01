"""
paths.py
Resolves VMT user data directories (AppData on Windows, XDG on Linux/Mac).
Extensions install here — NOT inside the application directory.
"""
import os
import sys
from pathlib import Path

def get_vmt_data_dir() -> Path:
    r"""Returns the VMT user data directory.
    Windows: %APPDATA%\VMT
    Linux/Mac: ~/.local/share/VMT
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            base = Path(appdata)
        else:
            base = Path.home() / "AppData" / "Roaming"
        return base / "VMT"
    else:
        # Linux/Mac
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base = Path(xdg_data)
        else:
            base = Path.home() / ".local" / "share"
        return base / "VMT"

def get_extensions_dir() -> Path:
    return get_vmt_data_dir() / "extensions"

def get_extension_dir(ext_id: str) -> Path:
    return get_extensions_dir() / ext_id

def get_extension_config_path() -> Path:
    r"""Returns %APPDATA%\VMT\config\extensions.json"""
    return get_vmt_data_dir() / "config" / "extensions.json"

def get_download_cache_dir() -> Path:
    p = get_vmt_data_dir() / "cache" / "downloads"
    p.mkdir(parents=True, exist_ok=True)
    return p
