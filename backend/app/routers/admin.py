import json
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.models.extension import Extension
from app.models.extension_version import ExtensionVersion, VerificationStatus
from app.models.extension_submission import ExtensionSubmission
from app.models.audit_log import AuditLog
from app.schemas.admin import ReviewRequest
from app.services.audit_service import log_audit_event

router = APIRouter()


class SubmissionReviewPayload(BaseModel):
    action: str  # "approve" | "reject"
    rejection_reason: Optional[str] = None
    notes: Optional[str] = None


@router.get("/submissions")
async def list_all_submissions(
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """Lists all developer extension submissions for admin review."""
    query = select(ExtensionSubmission).order_by(ExtensionSubmission.submitted_at.desc())
    if status:
        query = query.where(ExtensionSubmission.status == status)

    res = await db.execute(query)
    subs = res.scalars().all()

    return [
        {
            "id": s.id,
            "developer_id": s.developer_id,
            "extension_id": s.extension_id,
            "repository_url": s.repository_url,
            "release_tag": s.release_tag,
            "submitted_version": s.submitted_version,
            "status": s.status,
            "package_quarantine_path": s.package_quarantine_path,
            "static_analysis_warnings": json.loads(s.static_analysis_warnings) if s.static_analysis_warnings else [],
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
            "reviewed_by": s.reviewed_by,
            "rejection_reason": s.rejection_reason,
            "notes": s.notes
        }
        for s in subs
    ]


@router.post("/submissions/{submission_id}/review")
async def review_submission(
    submission_id: str,
    payload: SubmissionReviewPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Executes an explicit admin review decision on a developer submission.
    Actions: 'approve' or 'reject'.
    Developer accounts CANNOT call this endpoint.
    """
    ip = request.client.host if request.client else None

    stmt = select(ExtensionSubmission).where(ExtensionSubmission.id == submission_id)
    res = await db.execute(stmt)
    sub = res.scalars().first()

    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.status not in ("pending", "reviewing"):
        raise HTTPException(400, f"Cannot review submission currently in '{sub.status}' status")

    if payload.action == "approve":
        sub.status = "approved"
        sub.reviewed_by = admin.id
        sub.reviewed_at = datetime.now(timezone.utc)
        sub.notes = payload.notes

        # Create or update extension catalog entry
        stmt_ext = select(Extension).where(Extension.id == sub.extension_id)
        res_ext = await db.execute(stmt_ext)
        ext = res_ext.scalars().first()

        if not ext:
            ext = Extension(
                id=sub.extension_id,
                name=sub.extension_id.split(".")[-1].replace("_", " ").title(),
                description="Developer submitted extension",
                author_id=sub.developer_id,
                category="utility"
            )
            db.add(ext)
            await db.commit()

        # Add ExtensionVersion entry (defaults to UNVERIFIED until separate verification)
        stmt_ver = select(ExtensionVersion).where(
            ExtensionVersion.extension_id == sub.extension_id,
            ExtensionVersion.version == sub.submitted_version
        )
        res_ver = await db.execute(stmt_ver)
        ver = res_ver.scalars().first()

        if not ver:
            ver = ExtensionVersion(
                extension_id=sub.extension_id,
                version=sub.submitted_version,
                storage_key=f"quarantine/{sub.id}",
                package_hash="quarantine_hash_placeholder",
                package_size_bytes=1024,
                min_vmt_version="1.0.0",
                verification_status=VerificationStatus.UNVERIFIED,
                permissions=json.dumps([])
            )
            db.add(ver)
            await db.commit()

        await log_audit_event(db, "admin_submission_approved", user_id=admin.id, ip_address=ip, details={"submission_id": sub.id, "extension_id": sub.extension_id, "version": sub.submitted_version})
        return {"detail": "Submission approved and registered into extension catalog as UNVERIFIED", "submission_id": sub.id, "status": "approved"}

    elif payload.action == "reject":
        if not payload.rejection_reason:
            raise HTTPException(400, "Rejection reason is required when rejecting a submission")

        sub.status = "rejected"
        sub.reviewed_by = admin.id
        sub.reviewed_at = datetime.now(timezone.utc)
        sub.rejection_reason = payload.rejection_reason
        sub.notes = payload.notes
        await db.commit()

        await log_audit_event(db, "admin_submission_rejected", user_id=admin.id, ip_address=ip, details={"submission_id": sub.id, "reason": payload.rejection_reason})
        return {"detail": "Submission rejected", "submission_id": sub.id, "status": "rejected"}

    else:
        raise HTTPException(400, "Invalid review action. Must be 'approve' or 'reject'.")


@router.get("/audit-logs")
async def list_audit_logs(
    limit: int = Query(50, le=200),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin)
):
    """
    Application Append-Only Security Audit Log Viewer.
    Only authorized admins may view security audit logs.
    No update or delete endpoints exist for audit log entries.
    """
    stmt = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
    res = await db.execute(stmt)
    logs = res.scalars().all()

    return [
        {
            "id": l.id,
            "event_type": l.event_type,
            "user_id": l.user_id,
            "ip_address": l.ip_address,
            "details": json.loads(l.details_json) if l.details_json else None,
            "timestamp": l.timestamp.isoformat() if l.timestamp else None
        }
        for l in logs
    ]


@router.post("/extensions/{ext_id}/versions/{ver}/verify")
async def verify_version(ext_id: str, ver: str, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """Explicit Admin Verification operation."""
    stmt = select(ExtensionVersion).where(ExtensionVersion.extension_id == ext_id, ExtensionVersion.version == ver)
    res = await db.execute(stmt)
    version = res.scalars().first()
    if not version:
        raise HTTPException(404, "Version not found")
        
    version.verification_status = VerificationStatus.VERIFIED
    version.verified_at = datetime.now(timezone.utc)
    version.verified_by = admin.id
    version.verification_reason = None
    await db.commit()

    await log_audit_event(db, "admin_version_verified", user_id=admin.id, details={"extension_id": ext_id, "version": ver})
    return {"detail": "Version verified"}
