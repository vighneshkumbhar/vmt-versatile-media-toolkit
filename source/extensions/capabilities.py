"""
capabilities.py
Capability system for VMT extensions.

IMPORTANT: This is capability management and UX disclosure, NOT a security sandbox.
Extensions run in the same Python process as VMT and have equivalent OS privileges.
Capability checks at the API layer are a developer guardrail and user disclosure
mechanism — they do not prevent a malicious extension from bypassing them.
"""
from enum import Enum

class Capability(str, Enum):
    MEDIA_READ      = "media.read"
    MEDIA_WRITE     = "media.write"
    JOBS_ADD        = "jobs.add"
    JOBS_READ       = "jobs.read"
    FFMPEG_EXECUTE  = "ffmpeg.execute"
    UI_REGISTER     = "ui.register"
    SETTINGS_READ   = "settings.read"
    SETTINGS_WRITE  = "settings.write"
    FILESYSTEM_READ = "filesystem.read"
    FILESYSTEM_WRITE = "filesystem.write"

ALLOWED_CAPABILITIES = {c.value for c in Capability}

class VMTCapabilityError(Exception):
    """Raised when an extension calls an API without declaring the required capability."""
    pass
