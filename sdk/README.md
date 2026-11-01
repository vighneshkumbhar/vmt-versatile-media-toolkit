# VMT Extension SDK

## Quick Start
Welcome to the VMT Extension SDK! This SDK allows you to build extensions for the Versatile Media Toolkit (VMT).

## Extension Structure
An extension requires a directory with a `manifest.json` and a Python module (typically `extension/__init__.py`).

## Manifest Format
The manifest requires an ID in reverse-domain format (e.g., `com.example.myextension`).

## Capabilities
Capabilities grant access to various APIs:
- `ui.register`: Register UI pages.
- `media.read`: Read media files.
- `ffmpeg.execute`: Execute FFmpeg commands.

## Extension Lifecycle
Your extension class must inherit from `VMTExtension` and implement `on_load` and `on_unload`.

## API Reference
- `VMTContext`: The main context object passed to your extension.

## Packaging (.vmte format)
Use the included `build_vmte.py` script to package your extension into a `.vmte` zip archive.

## Publishing to the VMT Ecosystem
Upload your `.vmte` file to the VMT Developer Portal.

## Example: Hello Extension
A minimal extension that logs a message on load.

## Example: UI Extension
An extension that registers a custom UI page.

## Example: FFmpeg Extension
An extension that submits an FFmpeg job.

## Security Note
IMPORTANT: Extensions run inside VMT's Python process and share its privileges. The capability system is for user disclosure and API organization, not sandboxing. Only publish extensions you would trust running on your own computer.
