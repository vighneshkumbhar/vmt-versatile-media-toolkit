from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import json
import hashlib
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.extension import Extension
from app.models.extension_version import ExtensionVersion, VerificationStatus
from app.schemas.extension import ExtensionSummaryResponse, ExtensionDetailResponse, VersionResponse
from app.security.package_validator import validate_vmte_package
from app.storage import get_storage
from app.config import settings

router = APIRouter()

@router.get("/", response_model=List[ExtensionSummaryResponse])
async def list_developer_extensions(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    stmt = select(Extension).where(Extension.author_id == user.id).options(selectinload(Extension.versions))
    result = await db.execute(stmt)
    exts = result.scalars().all()
    
    resp = []
    for ext in exts:
        recc = next((v for v in sorted(ext.versions, key=lambda x: x.created_at, reverse=True) if v.verification_status == VerificationStatus.VERIFIED), None)
        if not recc and ext.versions:
            recc = sorted(ext.versions, key=lambda x: x.created_at, reverse=True)[0]
        
        recc_resp = None
        if recc:
            recc_resp = VersionResponse(
                version=recc.version, verification_status=recc.verification_status, verification_reason=recc.verification_reason,
                changelog=recc.changelog, created_at=recc.created_at, permissions=json.loads(recc.permissions), min_vmt_version=recc.min_vmt_version
            )
            
        resp.append(ExtensionSummaryResponse(
            id=ext.id, name=ext.name, description=ext.description, author=user.username, category=ext.category,
            recommended_version=recc_resp, total_download_count=ext.total_download_count, is_disabled=ext.is_disabled
        ))
    return resp

@router.post("/", status_code=201)
async def create_extension(
    package: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    data = await package.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(413, "File too large")
        
    manifest = validate_vmte_package(data)
    ext_id = manifest["id"]
    version = manifest["version"]
    
    # Check if exists
    stmt = select(Extension).where(Extension.id == ext_id)
    res = await db.execute(stmt)
    if res.scalars().first():
        raise HTTPException(400, "Extension ID already exists")
        
    storage = get_storage()
    storage_key = await storage.store(ext_id, version, data)
    
    ext = Extension(
        id=ext_id, name=manifest.get("name", ext_id), description=manifest.get("description", ""),
        category=manifest.get("category", "utility"), author_id=user.id
    )
    db.add(ext)
    
    ver = ExtensionVersion(
        extension_id=ext_id, version=version, storage_key=storage_key, package_hash=hashlib.sha256(data).hexdigest(),
        package_size_bytes=len(data), min_vmt_version=manifest.get("min_vmt_version", "1.0.0"),
        permissions=json.dumps(manifest.get("permissions", [])), verification_status=VerificationStatus.UNVERIFIED
    )
    db.add(ver)
    await db.commit()
    return {"detail": "Extension created successfully"}

@router.post("/{ext_id}/versions", status_code=201)
async def upload_version(
    ext_id: str,
    package: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    stmt = select(Extension).where(Extension.id == ext_id)
    res = await db.execute(stmt)
    ext = res.scalars().first()
    if not ext:
        raise HTTPException(404, "Extension not found")
    if ext.author_id != user.id:
        raise HTTPException(403, "Not authorized to upload versions for this extension")
        
    data = await package.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(413, "File too large")
        
    manifest = validate_vmte_package(data)
    if manifest["id"] != ext_id:
        raise HTTPException(400, "Manifest ID does not match extension ID")
        
    version = manifest["version"]
    # Check if version exists
    stmt_v = select(ExtensionVersion).where(ExtensionVersion.extension_id == ext_id, ExtensionVersion.version == version)
    res_v = await db.execute(stmt_v)
    if res_v.scalars().first():
        raise HTTPException(400, "Version already exists")
        
    storage = get_storage()
    storage_key = await storage.store(ext_id, version, data)
    
    ver = ExtensionVersion(
        extension_id=ext_id, version=version, storage_key=storage_key, package_hash=hashlib.sha256(data).hexdigest(),
        package_size_bytes=len(data), min_vmt_version=manifest.get("min_vmt_version", "1.0.0"),
        permissions=json.dumps(manifest.get("permissions", [])), verification_status=VerificationStatus.UNVERIFIED
    )
    db.add(ver)
    await db.commit()
    return {"detail": "Version uploaded successfully"}
