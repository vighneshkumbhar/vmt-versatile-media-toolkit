from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
import json
from app.database import get_db
from app.models.extension import Extension
from app.models.extension_version import ExtensionVersion, VerificationStatus
from app.schemas.extension import ExtensionSummaryResponse, ExtensionDetailResponse, VersionResponse
from app.storage import get_storage

router = APIRouter()

@router.get("/", response_model=List[ExtensionSummaryResponse])
async def list_extensions(db: AsyncSession = Depends(get_db)):
    stmt = select(Extension).where(Extension.is_disabled == False).options(selectinload(Extension.versions), selectinload(Extension.author))
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
            id=ext.id, name=ext.name, description=ext.description, author=ext.author.username, category=ext.category,
            recommended_version=recc_resp, total_download_count=ext.total_download_count, is_disabled=ext.is_disabled
        ))
    return resp

@router.get("/{ext_id}", response_model=ExtensionDetailResponse)
async def get_extension(ext_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Extension).where(Extension.id == ext_id, Extension.is_disabled == False).options(selectinload(Extension.versions), selectinload(Extension.author))
    res = await db.execute(stmt)
    ext = res.scalars().first()
    if not ext:
        raise HTTPException(404, "Extension not found")
        
    versions = []
    for v in sorted(ext.versions, key=lambda x: x.created_at, reverse=True):
        versions.append(VersionResponse(
            version=v.version, verification_status=v.verification_status, verification_reason=v.verification_reason,
            changelog=v.changelog, created_at=v.created_at, permissions=json.loads(v.permissions), min_vmt_version=v.min_vmt_version
        ))
    
    recc_resp = next((v for v in versions if v.verification_status == VerificationStatus.VERIFIED), None)
    if not recc_resp and versions:
        recc_resp = versions[0]
        
    return ExtensionDetailResponse(
        id=ext.id, name=ext.name, description=ext.description, author=ext.author.username, category=ext.category,
        recommended_version=recc_resp, total_download_count=ext.total_download_count, is_disabled=ext.is_disabled,
        versions=versions, website="", repository=""
    )

@router.get("/{ext_id}/download")
async def download_recommended(ext_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(Extension).where(Extension.id == ext_id).options(selectinload(Extension.versions))
    res = await db.execute(stmt)
    ext = res.scalars().first()
    if not ext or ext.is_disabled:
        raise HTTPException(404, "Extension not found")
        
    recc = next((v for v in sorted(ext.versions, key=lambda x: x.created_at, reverse=True) if v.verification_status == VerificationStatus.VERIFIED), None)
    if not recc and ext.versions:
        recc = sorted(ext.versions, key=lambda x: x.created_at, reverse=True)[0]
        
    if not recc:
        raise HTTPException(404, "No versions available")
        
    storage = get_storage()
    data = await storage.retrieve(recc.storage_key)
    
    ext.total_download_count += 1
    await db.commit()
    
    return Response(content=data, media_type="application/octet-stream", headers={"X-Package-Hash": recc.package_hash, "Content-Disposition": f"attachment; filename={ext_id}_{recc.version}.vmte"})

@router.get("/{ext_id}/versions/{ver}/download")
async def download_version(ext_id: str, ver: str, db: AsyncSession = Depends(get_db)):
    stmt = select(ExtensionVersion).where(ExtensionVersion.extension_id == ext_id, ExtensionVersion.version == ver)
    res = await db.execute(stmt)
    version = res.scalars().first()
    if not version:
        raise HTTPException(404, "Version not found")
        
    storage = get_storage()
    data = await storage.retrieve(version.storage_key)
    
    stmt_ext = select(Extension).where(Extension.id == ext_id)
    res_ext = await db.execute(stmt_ext)
    ext = res_ext.scalars().first()
    if ext:
        ext.total_download_count += 1
        await db.commit()
        
    return Response(content=data, media_type="application/octet-stream", headers={"X-Package-Hash": version.package_hash, "Content-Disposition": f"attachment; filename={ext_id}_{version.version}.vmte"})
