import json
import logging
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

# Keys that must NEVER be recorded in audit logs
_FORBIDDEN_KEYS = {
    "password", "plain_password", "hashed_password", "password_hash",
    "secret", "secret_key", "password_pepper", "pepper",
    "token", "access_token", "refresh_token", "authorization",
    "admin_bootstrap_secret", "cookie", "session_id"
}


def _sanitize_details(details: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if not details:
        return None
    
    clean = {}
    for k, v in details.items():
        if k.lower() in _FORBIDDEN_KEYS:
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = _sanitize_details(v)
        else:
            clean[k] = v
    return clean


async def log_audit_event(
    db: AsyncSession,
    event_type: str,
    user_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[dict[str, Any]] = None
) -> AuditLog:
    """
    Appends a security audit log event to the database.
    No update or delete API endpoints exist for audit logs.
    Automatically redacts passwords, tokens, and secret fields.
    """
    clean_details = _sanitize_details(details)
    details_json = json.dumps(clean_details) if clean_details else None

    entry = AuditLog(
        event_type=event_type,
        user_id=user_id,
        ip_address=ip_address,
        details_json=details_json
    )
    db.add(entry)
    await db.commit()
    logger.info(f"SECURITY AUDIT LOG [{event_type}] User: {user_id or 'Anonymous'} IP: {ip_address or 'Unknown'}")
    return entry
