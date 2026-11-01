# API & SDK Reference — VMT

## Extension Manifest Specification (`manifest.json`)
```json
{
  "id": "com.example.myextension",
  "name": "My Custom Processor",
  "version": "1.0.0",
  "author": "Developer",
  "description": "Custom video filter extension",
  "entrypoint": "extension:main",
  "capabilities": ["ffmpeg.execute", "ui.page", "storage.local"],
  "min_vmt_version": "1.0.0"
}
```

## SDK Core Interfaces (`sdk/vmt_sdk.py`)
- `VmtExtension`: Base class that all plugins must inherit.
- `on_load(context)`: Called upon extension initialization.
- `register_page(title, widget_class)`: Adds a new tab in the VMT UI.
- `execute_ffmpeg_command(args, on_progress)`: Dispatches FFmpeg process via the VMT runner.
