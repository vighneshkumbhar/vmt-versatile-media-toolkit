from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jose import JWTError
from app.database import get_db
from app.security.jwt_utils import decode_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise credentials_exception
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def require_developer(current_user: User = Depends(get_current_user)) -> User:
    """
    Server-side authorization check for Developer access.
    A developer can ONLY: manage own profile, submit extensions, view own submissions, withdraw pending submissions.
    Developer role DOES NOT grant admin privileges or auto-verification permissions.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if current_user.role not in ("developer", "admin") and not current_user.is_developer and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Developer access required")
    return current_user


async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    Server-side authorization check for Admin access.
    Only an authorized admin can verify extensions or approve submissions.
    Never trusts client role claims; authorization is enforced server-side.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if current_user.role != "admin" and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
