# Security Analysis — VMT

- **Subprocess Execution**: FFmpeg arguments passed as strict token lists rather than shell strings (`shell=False`) to prevent command injection.
- **Extension Integrity**: Manifest validation ensures extension IDs conform to reverse domain notation and cannot execute unauthorized filesystem operations.
