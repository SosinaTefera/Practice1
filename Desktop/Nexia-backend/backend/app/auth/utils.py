import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from ..core.config import settings

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
PASSWORD_RESET_EXPIRE_MINUTES = getattr(settings, "PASSWORD_RESET_EXPIRE_MINUTES", 15)
REFRESH_TOKEN_EXPIRE_DAYS = int(getattr(settings, "REFRESH_TOKEN_EXPIRE_DAYS", 30))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        role: str = payload.get("role")

        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"email": email, "user_id": user_id, "role": role}

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_password_reset_token(user_id: int, email: str) -> str:
    """Create a short-lived JWT for password reset with explicit scope."""
    expires = timedelta(minutes=PASSWORD_RESET_EXPIRE_MINUTES)
    payload = {"sub": email, "user_id": user_id, "scope": "password_reset"}
    return create_access_token(payload, expires_delta=expires)


def verify_password_reset_token(token: str) -> dict:
    """Verify password reset token and ensure correct scope."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scope",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"email": email, "user_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user_id(token: str) -> int:
    """Extract user ID from token"""
    payload = verify_token(token)
    return payload["user_id"]


def get_current_user_role(token: str) -> str:
    """Extract user role from token"""
    payload = verify_token(token)
    return payload["role"]


def require_trainer_role(token: str):
    """Ensure user has trainer role"""
    role = get_current_user_role(token)
    if role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Trainer role required.",
        )
    return True


# Refresh token helpers
def generate_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    """Hash refresh token for storage (avoid storing plain tokens)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_refresh_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)


# Email verification constants
EMAIL_VERIFICATION_EXPIRE_HOURS = int(
    getattr(settings, "EMAIL_VERIFICATION_EXPIRE_HOURS", 24)
)


def create_email_verification_token(user_id: int, email: str) -> str:
    """Create a JWT for email verification with explicit scope."""
    expires = timedelta(hours=EMAIL_VERIFICATION_EXPIRE_HOURS)
    payload = {"sub": email, "user_id": user_id, "scope": "email_verification"}
    return create_access_token(payload, expires_delta=expires)


def verify_email_verification_token(token: str) -> dict:
    """Verify email verification token and ensure correct scope."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("scope") != "email_verification":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token scope",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return {"email": email, "user_id": user_id}
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Generic helpers
def now_utc() -> datetime:
    return datetime.now(timezone.utc)


# OTP helpers
def generate_numeric_code(length: int = 6) -> str:
    # Generates a zero-padded numeric code of given length
    # Using secrets for cryptographic randomness
    max_val = 10**length
    num = secrets.randbelow(max_val)
    return str(num).zfill(length)


def hash_otp_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()
