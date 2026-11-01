from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError

from app.database import get_db
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, RefreshRequest
from app.security.hashing import hash_password, verify_password, dummy_verify_password
from app.security.jwt_utils import create_access_token, create_refresh_token, decode_token, hash_refresh_token
from app.security.rate_limiter import slowapi_limiter
from app.services.audit_service import log_audit_event
from app.config import settings

router = APIRouter()


@router.post("/register", status_code=201)
async def register(req: UserRegister, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None

    # Check if username or email exists
    stmt = select(User).where((User.username == req.username) | (User.email == req.email))
    res = await db.execute(stmt)
    existing = res.scalars().first()
    
    if existing:
        await log_audit_event(db, "account_creation_failed_duplicate", ip_address=ip, details={"username": req.username})
        # Generic error message to prevent enumeration where appropriate
        if existing.username == req.username:
            raise HTTPException(400, "Username is already registered")
        raise HTTPException(400, "Email is already registered")

    new_user = User(
        username=req.username,
        email=req.email,
        hashed_password=hash_password(req.password),
        role="developer",
        is_developer=True,
        is_admin=False,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    await log_audit_event(db, "account_creation_success", user_id=new_user.id, ip_address=ip, details={"username": new_user.username, "role": new_user.role})
    return {"detail": "Developer account created successfully", "user_id": new_user.id}


@router.post("/login", response_model=TokenResponse)
async def login(req: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None

    # Look up user by username or email
    stmt = select(User).where((User.username == req.username) | (User.email == req.username))
    res = await db.execute(stmt)
    user = res.scalars().first()

    # Timing Defense: execute dummy Argon2id verification if user does not exist
    if not user:
        dummy_verify_password()
        await log_audit_event(db, "login_failure_invalid_credentials", ip_address=ip, details={"attempted_identifier": req.username})
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Account activation check
    if not user.is_active:
        dummy_verify_password()
        await log_audit_event(db, "login_failure_account_disabled", user_id=user.id, ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Verify password with Argon2id & legacy bcrypt fallback
    is_valid, needs_rehash = verify_password(req.password, user.hashed_password)
    if not is_valid:
        await log_audit_event(db, "login_failure_invalid_credentials", user_id=user.id, ip_address=ip)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Rehash legacy bcrypt password to Argon2id if valid
    if needs_rehash:
        user.hashed_password = hash_password(req.password)

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)

    # Generate Access & Refresh Tokens
    access_token = create_access_token({"sub": user.id, "role": user.role})
    raw_refresh_token = create_refresh_token({"sub": user.id})

    # Create server session with hashed refresh token
    refresh_hash = hash_refresh_token(raw_refresh_token)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        device_info=request.headers.get("User-Agent", "Unknown"),
        is_revoked=False,
        expires_at=expires_at
    )
    db.add(session)
    await db.commit()

    await log_audit_event(db, "login_success", user_id=user.id, ip_address=ip, details={"session_id": session.id})
    return TokenResponse(access_token=access_token, refresh_token=raw_refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None

    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(401, "Invalid token type")
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(401, "Invalid refresh token")
    except JWTError:
        raise HTTPException(401, "Invalid refresh token")

    refresh_hash = hash_refresh_token(req.refresh_token)
    stmt = select(UserSession).where(UserSession.refresh_token_hash == refresh_hash)
    res = await db.execute(stmt)
    session = res.scalars().first()

    # Reuse Detection / Revoked Session Defense
    if not session or session.is_revoked or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        if session and session.is_revoked:
            # Revoke all active sessions for this user due to potential token theft
            stmt_all = select(UserSession).where(UserSession.user_id == user_id, UserSession.is_revoked == False)
            res_all = await db.execute(stmt_all)
            for s in res_all.scalars().all():
                s.is_revoked = True
                s.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            await log_audit_event(db, "token_reuse_detected_security_revocation", user_id=user_id, ip_address=ip)
        
        raise HTTPException(401, "Refresh token is invalid or has been revoked")

    # Rotate refresh token (revoke current session, create new session)
    session.is_revoked = True
    session.revoked_at = datetime.now(timezone.utc)

    stmt_u = select(User).where(User.id == user_id)
    res_u = await db.execute(stmt_u)
    user = res_u.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(401, "Account disabled")

    new_access = create_access_token({"sub": user.id, "role": user.role})
    new_raw_refresh = create_refresh_token({"sub": user.id})
    new_hash = hash_refresh_token(new_raw_refresh)

    new_session = UserSession(
        user_id=user.id,
        refresh_token_hash=new_hash,
        device_info=request.headers.get("User-Agent", "Unknown"),
        is_revoked=False,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_session)
    await db.commit()

    await log_audit_event(db, "token_refresh_success", user_id=user.id, ip_address=ip)
    return TokenResponse(access_token=new_access, refresh_token=new_raw_refresh)


@router.post("/logout")
async def logout(req: RefreshRequest, request: Request, db: AsyncSession = Depends(get_db)):
    ip = request.client.host if request.client else None
    refresh_hash = hash_refresh_token(req.refresh_token)

    stmt = select(UserSession).where(UserSession.refresh_token_hash == refresh_hash)
    res = await db.execute(stmt)
    session = res.scalars().first()

    if session:
        session.is_revoked = True
        session.revoked_at = datetime.now(timezone.utc)
        await db.commit()
        await log_audit_event(db, "logout_success", user_id=session.user_id, ip_address=ip)

    return {"detail": "Logged out successfully"}
