import bcrypt
import logging
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from app.config import settings

logger = logging.getLogger(__name__)

# Initialize Argon2id password hasher with configured parameters
_ph = PasswordHasher(
    time_cost=settings.ARGON2_TIME_COST,
    memory_cost=settings.ARGON2_MEMORY_COST,
    parallelism=settings.ARGON2_PARALLELISM
)

# Pre-computed dummy Argon2id hash for timing-safe non-existent user verification
_DUMMY_PASSWORD = "vmt_dummy_password_timing_defense_2026"
DUMMY_HASH = _ph.hash(_DUMMY_PASSWORD + (settings.PASSWORD_PEPPER or ""))


def _get_peppered_password(plain_password: str) -> str:
    """Concatenates server-side password pepper from configuration if present."""
    pepper = settings.PASSWORD_PEPPER or ""
    return f"{plain_password}{pepper}"


def hash_password(plain_password: str) -> str:
    """
    Hashes a plain password using Argon2id with unique salt and server-side pepper.
    Password must NEVER be stored in plain text or reversible format.
    """
    peppered = _get_peppered_password(plain_password)
    return _ph.hash(peppered)


def verify_password(plain_password: str, hashed_password: str) -> tuple[bool, bool]:
    """
    Verifies a plain password against a stored hash.
    Supports legacy bcrypt hashes and signals if rehash to Argon2id is needed.
    Returns (is_valid, needs_rehash).
    """
    if not hashed_password or not plain_password:
        return False, False

    peppered = _get_peppered_password(plain_password)

    # 1. Legacy Bcrypt Hash Support
    if hashed_password.startswith("$2a$") or hashed_password.startswith("$2b$"):
        pwd_bytes = plain_password.encode("utf-8")
        if len(pwd_bytes) > 72:
            pwd_bytes = pwd_bytes[:72]
        try:
            is_valid = bcrypt.checkpw(pwd_bytes, hashed_password.encode("utf-8"))
            return is_valid, is_valid  # Needs rehash if valid legacy hash
        except Exception:
            return False, False

    # 2. Argon2id Verification
    try:
        _ph.verify(hashed_password, peppered)
        needs_rehash = _ph.check_needs_rehash(hashed_password)
        return True, needs_rehash
    except (VerifyMismatchError, InvalidHashError):
        return False, False
    except Exception as e:
        logger.error(f"Error during password verification: {e}")
        return False, False


def dummy_verify_password() -> None:
    """
    Executes a dummy Argon2id verification against a pre-computed hash.
    Used when a requested user account does not exist so authentication timing
    is indistinguishable between valid and invalid usernames/emails.
    """
    try:
        _ph.verify(DUMMY_HASH, _DUMMY_PASSWORD + (settings.PASSWORD_PEPPER or ""))
    except Exception:
        pass
