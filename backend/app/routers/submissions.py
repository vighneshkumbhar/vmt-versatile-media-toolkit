import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.user import User
from app.models.extension_submission import ExtensionSubmission
from app.dependencies import require_developer
from app.security.url_validator import validate_github_url
from app.security.quarantine_manager import quarantine_manager
from app.security.static_analyzer import analyze_package_statically
from app.services.audit_service import log_audit_event

router = APIRouter()


@router.post("/", status_code=201)
async def submit_extension(
    request: Request,
    repository_url: str = Form(...),
    release_tag: str = Form(...),
    extension_id: str = Form(...),
    asset_filename: Optional[str] = Form(None),
    package_file: Optional[UploadFile] = File(None),
    developer: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db)
):
    """
    Submits a new extension or extension version for manual admin review.
    Developers can submit repository URLs and release packages.
    Submissions are automatically placed in PENDING state.
    Packages are QUARANTINED and statically analyzed WITHOUT executing any code.
    Developer role CANNOT approve, verify, or publish submissions automatically.
    """
    ip = request.client.host if request.client else None

    # Validate GitHub URL and extract parsed repository details
    parsed_info = validate_github_url(repository_url)
    submitted_version = parsed_info["submitted_version"]
    clean_tag = release_tag.strip() or parsed_info["release_tag"]

    # Check for duplicate pending submission by same developer for same version
    stmt_dup = select(ExtensionSubmission).where(
        ExtensionSubmission.developer_id == developer.id,
        ExtensionSubmission.extension_id == extension_id,
        ExtensionSubmission.submitted_version == submitted_version,
        ExtensionSubmission.status.in_(["pending", "reviewing"])
    )
    dup_res = await db.execute(stmt_dup)
    if dup_res.scalars().first():
        raise HTTPException(400, f"A pending submission for extension '{extension_id}' version '{submitted_version}' already exists.")

    submission = ExtensionSubmission(
        developer_id=developer.id,
        extension_id=extension_id,
        repository_url=parsed_info["repository_url"],
        release_tag=clean_tag,
        submitted_version=submitted_version,
        asset_filename=asset_filename or parsed_info.get("asset_name"),
        status="pending"
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Quarantine & Statically Analyze package if provided
    quarantine_path = None
    warnings = []
    if package_file:
        content = await package_file.read()
        filename = package_file.filename or f"{extension_id}.vmte"
        quarantine_path = quarantine_manager.store_package(submission.id, filename, content)
        submission.package_quarantine_path = quarantine_path

        # Perform static AST & ZIP analysis without code execution
        warnings = analyze_package_statically(quarantine_manager.get_package_path(submission.id, filename))
        submission.static_analysis_warnings = json.dumps(warnings)
        await db.commit()

    await log_audit_event(
        db,
        "extension_submission_created",
        user_id=developer.id,
        ip_address=ip,
        details={
            "submission_id": submission.id,
            "extension_id": extension_id,
            "version": submitted_version,
            "warnings_count": len(warnings)
        }
    )

    return {
        "detail": "Extension submission recorded successfully and placed in QUARANTINE for manual admin review.",
        "submission_id": submission.id,
        "status": submission.status,
        "submitted_version": submission.submitted_version,
        "static_analysis_warnings": warnings
    }


@router.get("/")
async def list_my_submissions(
    developer: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db)
):
    """Lists all submissions belonging exclusively to the authenticated developer."""
    stmt = select(ExtensionSubmission).where(ExtensionSubmission.developer_id == developer.id).order_by(ExtensionSubmission.submitted_at.desc())
    res = await db.execute(stmt)
    submissions = res.scalars().all()

    return [
        {
            "id": s.id,
            "extension_id": s.extension_id,
            "repository_url": s.repository_url,
            "release_tag": s.release_tag,
            "submitted_version": s.submitted_version,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
            "rejection_reason": s.rejection_reason,
            "notes": s.notes,
            "static_analysis_warnings": json.loads(s.static_analysis_warnings) if s.static_analysis_warnings else []
        }
        for s in submissions
    ]


@router.delete("/{submission_id}/withdraw")
async def withdraw_submission(
    submission_id: str,
    developer: User = Depends(require_developer),
    db: AsyncSession = Depends(get_db)
):
    """Allows a developer to withdraw their own pending submission."""
    stmt = select(ExtensionSubmission).where(
        ExtensionSubmission.id == submission_id,
        ExtensionSubmission.developer_id == developer.id
    )
    res = await db.execute(stmt)
    sub = res.scalars().first()

    if not sub:
        raise HTTPException(404, "Submission not found")
    if sub.status not in ("pending", "reviewing"):
        raise HTTPException(400, f"Cannot withdraw submission in '{sub.status}' state")

    sub.status = "withdrawn"
    await db.commit()
    await log_audit_event(db, "extension_submission_withdrawn", user_id=developer.id, details={"submission_id": sub.id})
    return {"detail": "Submission withdrawn successfully", "submission_id": sub.id}
