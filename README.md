# VMT — Versatile Media Toolkit

**A powerful, extensible desktop application for media processing, built with Python and PySide6.**

VMT (Versatile Media Toolkit) is a comprehensive media toolkit that combines video/audio processing, YouTube downloading, and a plugin architecture for custom extensions. It features a modern Qt-based UI, a FastAPI backend for package management, and a modular extension system.

## Features

### Media Processing
- **Video Conversion** — MP4, MKV, MOV, WebM, AVI with custom codecs and CRF
- **Compression** — 5 quality levels with real-time preview
- **Audio Extraction** — Pull audio from any video (MP3, WAV, FLAC, M4A, OGG, AAC, OPUS)
- **GIF Creation** — Create animated GIFs from video clips
- **Frame Extraction** — Save single frames as PNG/JPG
- **Batch Processing** — Queue multiple files with individual settings

### YouTube Downloader (`YouTubeDownloader.vmte`)
- High-quality video/audio downloads
- Format selection (up to 4K)
- Playlist and channel support
- Subtitle extraction
- Integrated as a VMT extension package

### Extension System
- **Package Format (`.vmte`)** — Self-contained extension bundles
- **Plugin Architecture** — Core, UI, and backend extensions
- **Secure Installation** — Quarantine scanning, signature verification
- **Package Manager** — Built-in store with updates

### Backend (FastAPI)
- Package storage and management
- Admin portal with bootstrap auth
- Quarantine system for security scanning
- SQLite database with async SQLAlchemy

## Tech Stack

| Layer | Technology |
|-------|------------|
| **UI** | PySide6 (Qt 6), QSS theming |
| **Backend** | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2 |
| **Media Engine** | FFmpeg (external binary) |
| **Download** | yt-dlp |
| **Database** | SQLite (aiosqlite) |
| **Packaging** | PyInstaller |
| **Testing** | pytest |

## Quick Start

### Prerequisites
- **Windows 10/11** (primary target)
- **Python 3.10+**
- **FFmpeg** — Download from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) and place `ffmpeg.exe` + `ffprobe.exe` in `bin/`

### Installation

```bash
# Clone the repository
git clone https://github.com/vighneshkumbhar/vmt-versatile-media-toolkit.git
cd vmt-versatile-media-toolkit

# Install dependencies
pip install -r backend/requirements.txt
pip install PySide6 yt-dlp

# Place FFmpeg binaries in bin/
# Download from https://www.gyan.dev/ffmpeg/builds/

# Launch the app
start.bat
# or
python -m source.main
```

### Development

```bash
# Backend development
cd backend
uvicorn main:app --reload --port 8000

# Frontend development
python -m source.main
```

### Building Executable

```bash
# Run the build script
build.bat

# Output: dist/VMT/VMT.exe
# Copy FFmpeg binaries to dist/VMT/bin/ for portable distribution
```

## Project Structure

```
VMT/
├── source/                 # Frontend (PySide6)
│   ├── main.py            # Entry point
│   ├── core/              # FFmpeg engine, job queue, settings
│   ├── ui/                # Qt widgets, styles, main window
│   └── utils/             # Helpers, formatters
├── backend/               # FastAPI backend
│   ├── app/               # API routes, models, services
│   ├── portal/            # Admin portal
│   ├── package_storage/   # Installed .vmte packages
│   └── quarantine/        # Security scanning staging
├── extensions/            # Extension definitions
├── sdk/                   # Extension SDK
├── assets/                # Icons, images, fonts
├── bin/                   # FFmpeg binaries (gitignored)
├── config/                # settings.json
├── docs/                  # Documentation
├── dist/                  # PyInstaller output (gitignored)
├── build/                 # Build artifacts (gitignored)
├── output/                # Default output folder (gitignored)
├── quarantine/            # Security staging (gitignored)
├── vmt_ecosystem.db       # SQLite database (gitignored)
├── start.bat              # Launch script
├── build.bat              # PyInstaller build
├── requirements.txt       # Python deps
├── README.md
├── LICENSE
├── SECURITY.md
└── .gitignore
```

## Extension Development

VMT uses a `.vmte` package format (ZIP-based) for extensions. See [Extension SDK](sdk/) and [docs/EXTENSIONS.md](docs/EXTENSIONS.md) for details.

### Creating an Extension

```bash
# Use the SDK to scaffold
python -m sdk.create my-extension

# Build package
python -m sdk.build my-extension
# Output: my-extension.vmte
```

## Security

- All extensions quarantined on install
- Signature verification for official packages
- Admin bootstrap secret for initial setup
- Password hashing with Argon2id (via backend pepper)
- CORS configured for local development only

See [SECURITY.md](SECURITY.md) for full details.

## License

MIT License — see [LICENSE](LICENSE) for details.

FFmpeg is licensed under LGPL/GPL. yt-dlp is licensed under Unlicense.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Roadmap

- [ ] macOS/Linux support
- [ ] Web-based remote control
- [ ] AI-powered media enhancement (upscaling, denoising)
- [ ] Cloud sync for settings/packages
- [ ] Plugin marketplace
