# System Design — VMT

| Component | Responsibility | Inputs | Outputs | Dependencies |
|---|---|---|---|---|
| `FFmpegRunner` | Execute FFmpeg process asynchronously, parse progress | Command args list | Real-time percent signal, Output file | `subprocess`, `threading` |
| `JobQueue` | Manage sequential or parallel transcode queue | `Job` instances | Execution states, signals | `QThread` / `threading` |
| `ExtensionLoader`| Inspect `.vmte` ZIP archive, validate manifest, load bytecode | `.vmte` path | Loaded extension module | `zipfile`, `importlib` |
| `VmtSDK` | Public API contract for extension authors | Plugin context, hooks | UI Page registration, FFmpeg tasks | `PySide6`, `vmt_sdk` |
