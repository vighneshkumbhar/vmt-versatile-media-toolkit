# Tech Stack — VMT

| Layer | Technology | Purpose |
|---|---|---|
| Runtime | Python 3.10+ | Core application execution |
| GUI Framework | PySide6 / PyQt | Native cross-platform desktop UI |
| Media Processing | FFmpeg & FFprobe | Video/audio decoding, filtering, encoding |
| Database | SQLite (`vmt_ecosystem.db`) | Extension registry, jobs, settings |
| Package Format | `.vmte` (Custom ZIP bundle) | Extension distribution format |
| Packaging | PyInstaller / Inno Setup | Windows installer distribution (`installer/`) |
