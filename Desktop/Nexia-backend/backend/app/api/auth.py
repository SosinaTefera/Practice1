from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from .. import crud
from ..auth import schemas as auth_schemas
from ..auth import utils as auth_utils
from ..auth.deps import get_current_payload
from ..core.config import settings
from ..db.session import get_db
from ..services.emailer import can_send_email, send_email

router = APIRouter(prefix="/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

# Rate limiter instance
limiter = Limiter(key_func=get_remote_address)

# Rate limits: disable or relax in development/testing to avoid flaky tests
if settings.is_development or settings.is_testing:
    REGISTER_LIMIT = "1000/minute"  # Very high limits in dev/testing
    LOGIN_LIMIT = "1000/minute"
    FORGOT_LIMIT = "1000/minute"
    RESET_LIMIT = "1000/minute"
else:
    REGISTER_LIMIT = "5/minute"  # Stricter in production
    LOGIN_LIMIT = "3/minute"  # Stricter in production
    FORGOT_LIMIT = "20/minute"  # Temporarily increased for testing
    RESET_LIMIT = "5/hour"  # Stricter in production


@router.post("/register", response_model=auth_schemas.UserOut, status_code=201)
@limiter.limit(REGISTER_LIMIT)
def register_user(
    request: Request, user: auth_schemas.UserCreate, db: Session = Depends(get_db)
):
    # Prevent duplicate emails
    existing = crud.get_user_by_email(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Allow only supported roles
    allowed_roles = {"admin", "trainer", "athlete"}
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=400, detail=f"Invalid role. Allowed: {sorted(allowed_roles)}"
        )

    created = crud.create_user(db, user)
    role_name = crud.get_primary_role_name(db, created.id)
    return auth_schemas.UserOut(
        id=created.id,
        email=created.email,
        nombre=(created.full_name.split(" ")[0] if created.full_name else ""),
        apellidos=(
            " ".join(created.full_name.split(" ")[1:]) if created.full_name else ""
        ),
        role=role_name,
        is_active=created.is_active,
        created_at=created.created_at,
    )


@router.post("/login", response_model=auth_schemas.Token)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = auth_utils.create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": crud.get_primary_role_name(db, user.id),
            "token_version": getattr(user, "token_version", 1),
        },
        expires_delta=access_token_expires,
    )

    role_name = crud.get_primary_role_name(db, user.id)
    user_out = auth_schemas.UserOut(
        id=user.id,
        email=user.email,
        nombre=user.full_name.split(" ")[0] if user.full_name else "",
        apellidos=" ".join(user.full_name.split(" ")[1:]) if user.full_name else "",
        role=role_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )

    # Create refresh token (opaque)
    refresh_plain = auth_utils.generate_refresh_token()
    try:
        user_agent = request.headers.get("user-agent")
        ip = request.client.host if getattr(request, "client", None) else None
    except Exception:
        user_agent = None
        ip = None
    crud.create_refresh_token(
        db, user, refresh_plain, user_agent=user_agent, ip_address=ip
    )

    return auth_schemas.Token(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_out,
        refresh_token=refresh_plain,
    )


@router.get("/me", response_model=auth_schemas.UserOut)
def read_me(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    payload = auth_utils.verify_token(token)
    user = crud.get_user_by_id(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    role_name = crud.get_primary_role_name(db, user.id)
    return auth_schemas.UserOut(
        id=user.id,
        email=user.email,
        nombre=user.full_name.split(" ")[0] if user.full_name else "",
        apellidos=" ".join(user.full_name.split(" ")[1:]) if user.full_name else "",
        role=role_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )


# Password recovery
@router.post("/forgot-password")
@limiter.limit(FORGOT_LIMIT)
def forgot_password(
    request: Request, payload: auth_schemas.PasswordReset, db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        # Return 200 to avoid user enumeration
        return {"message": "If the email exists, a reset link has been sent."}
    token = auth_utils.create_password_reset_token(user_id=user.id, email=user.email)
    # Send email if SMTP is configured; in development, also return token for testing
    if can_send_email():
        base_url = settings.FRONTEND_RESET_URL.rstrip("/")
        # Compose link using configurable frontend URL
        reset_link = f"{base_url}?token={token}"
        subject = "Password reset instructions"
        text = (
            f"You requested to reset your password.\n\n"
            f"Use the following token in the app, or open this link:\n{reset_link}\n\n"
            f"If you didn't request this, please ignore this email."
        )
        html = (
            f"<p>You requested to reset your password.</p>"
            f"<p>Use this <a href='{reset_link}'>reset link</a> "
            f"or paste the token in the app.</p>"
            f"<p>If you didn't request this, please ignore this email.</p>"
        )
        send_email(user.email, subject, text, html)

    # Avoid token leakage in production
    if settings.is_development:
        return {"message": "Password reset token generated.", "reset_token": token}
    return {"message": "If the email exists, a reset link has been sent."}


@router.post("/reset-password")
@limiter.limit(RESET_LIMIT)
def reset_password(
    request: Request,
    payload: auth_schemas.PasswordResetConfirm,
    db: Session = Depends(get_db),
):
    data = auth_utils.verify_password_reset_token(payload.token)
    user = crud.get_user_by_id(db, data["user_id"])
    if not user or user.email != data["email"]:
        raise HTTPException(status_code=400, detail="Invalid token or user")
    crud.set_user_password(db, user, payload.new_password)
    # Invalidate all tokens after password reset
    crud.increment_user_token_version(db, user)
    # Revoke all refresh tokens for security
    crud.revoke_all_refresh_tokens_for_user(db, user.id)
    return {"message": "Password has been reset successfully."}


@router.post("/change-password")
def change_password(
    body: auth_schemas.PasswordChange,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    user = crud.get_user_by_id(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Verify current password
    if not auth_utils.verify_password(body.current_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    crud.set_user_password(db, user, body.new_password)
    crud.increment_user_token_version(db, user)
    # Revoke all refresh tokens for this user
    crud.revoke_all_refresh_tokens_for_user(db, user.id)
    return {"message": "Password changed successfully"}


@router.put("/me", response_model=auth_schemas.UserOut)
def update_me(
    body: auth_schemas.UserUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    user = crud.get_user_by_id(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Map nombre/apellidos to full_name if provided
    full_name = user.full_name
    if body.nombre is not None or body.apellidos is not None:
        nombre = (
            body.nombre
            if body.nombre is not None
            else (user.full_name.split(" ")[0] if user.full_name else "")
        )
        apellidos = (
            body.apellidos
            if body.apellidos is not None
            else (" ".join(user.full_name.split(" ")[1:]) if user.full_name else "")
        )
        full_name = (nombre + " " + apellidos).strip()

    try:
        updated = crud.update_user_profile(
            db,
            user,
            email=body.email if body.email is not None else None,
            full_name=full_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    role_name = crud.get_primary_role_name(db, updated.id)
    return auth_schemas.UserOut(
        id=updated.id,
        email=updated.email,
        nombre=(updated.full_name.split(" ")[0] if updated.full_name else ""),
        apellidos=(
            " ".join(updated.full_name.split(" ")[1:]) if updated.full_name else ""
        ),
        role=role_name,
        is_active=updated.is_active,
        created_at=updated.created_at,
    )


@router.delete("/me")
def delete_me(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    user = crud.get_user_by_id(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    crud.deactivate_user(db, user)
    crud.increment_user_token_version(db, user)
    # Revoke all refresh tokens upon deactivation
    crud.revoke_all_refresh_tokens_for_user(db, user.id)
    return {"message": "Account deactivated"}


@router.post("/logout")
def logout(
    body: auth_schemas.RefreshRequest,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    user = crud.get_user_by_id(db, payload["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    # Revoke provided refresh token only
    crud.revoke_refresh_token(db, body.refresh_token)
    return {"message": "Logged out"}


@router.post("/refresh", response_model=auth_schemas.Token)
def refresh_token(
    body: auth_schemas.RefreshRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    rec = crud.find_valid_refresh(db, body.refresh_token)
    if not rec:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    user = crud.get_user_by_id(db, rec.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not allowed")

    # Rotate refresh token
    try:
        user_agent = request.headers.get("user-agent")
        ip = request.client.host if getattr(request, "client", None) else None
    except Exception:
        user_agent = None
        ip = None
    new_refresh = crud.rotate_refresh_token(
        db, user, body.refresh_token, user_agent=user_agent, ip_address=ip
    )

    # Issue new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token = auth_utils.create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "role": crud.get_primary_role_name(db, user.id),
            "token_version": getattr(user, "token_version", 1),
        },
        expires_delta=access_token_expires,
    )

    role_name = crud.get_primary_role_name(db, user.id)
    user_out = auth_schemas.UserOut(
        id=user.id,
        email=user.email,
        nombre=user.full_name.split(" ")[0] if user.full_name else "",
        apellidos=" ".join(user.full_name.split(" ")[1:]) if user.full_name else "",
        role=role_name,
        is_active=user.is_active,
        created_at=user.created_at,
    )
    return auth_schemas.Token(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_out,
        refresh_token=new_refresh,
    )
