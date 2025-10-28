import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from slowapi import Limiter
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


# Professional client IP detection for rate limiting
def get_real_client_ip(request: Request) -> str:
    """
    Extract real client IP from proxy headers.
    Handles X-Forwarded-For, X-Real-IP, and direct connections.
    """
    # Check X-Forwarded-For header (most common proxy header)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For can contain multiple IPs, take the first (original client)
        return forwarded_for.split(",")[0].strip()

    # Check X-Real-IP header (alternative proxy header)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    if request.client:
        return request.client.host

    return "unknown"


# Rate limiter instance with real client IP detection
limiter = Limiter(key_func=get_real_client_ip)

# Rate limits: disable or relax in development/testing to avoid flaky tests
if settings.is_development or settings.is_testing:
    REGISTER_LIMIT = "1000/minute"  # Very high limits in dev/testing
    LOGIN_LIMIT = "1000/minute"
    FORGOT_LIMIT = "1000/minute"
    RESET_LIMIT = "1000/minute"
    VERIFY_EMAIL_LIMIT = "1000/minute"
    RESEND_VERIFICATION_LIMIT = "1000/minute"
else:
    REGISTER_LIMIT = "5/minute"  # Stricter in production
    LOGIN_LIMIT = "3/minute"  # Stricter in production
    FORGOT_LIMIT = "3/hour"  # Stricter in production
    RESET_LIMIT = "5/hour"  # Stricter in production
    VERIFY_EMAIL_LIMIT = "10/minute"  # Allow multiple verification attempts
    RESEND_VERIFICATION_LIMIT = "3/hour"  # Limited resend attempts


@router.post("/register", status_code=201)
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

    # Generate email verification token
    token = auth_utils.create_email_verification_token(
        user_id=created.id, email=created.email
    )

    # Send verification email if SMTP is configured
    if can_send_email():
        try:
            base_url = settings.FRONTEND_VERIFICATION_URL.rstrip("/")
            verification_link = f"{base_url}?token={token}"
            subject = "Welcome! Please verify your email address"
            text = (
                f"Welcome to {settings.PROJECT_NAME}!\n\n"
                "Please verify your email address to complete your registration.\n\n"
                "Use the following token in the app, or open this link:\n"
                f"{verification_link}\n\n"
                "If you didn't create this account, please ignore this email."
            )
            html = (
                f"<h2>Welcome to {settings.PROJECT_NAME}!</h2>"
                "<p>Please verify your email address to complete your "
                "registration.</p>"
                f"<p><a href='{verification_link}' "
                f"style='background-color: #4CAF50; color: white; padding: 14px 20px; "
                f"text-decoration: none; border-radius: 4px;'>"
                f"Verify Email Address</a></p>"
                f"<p>Or copy and paste this link in your browser:<br>"
                f"{verification_link}</p>"
                f"<p>If you didn't create this account, please ignore this email.</p>"
            )
            send_email(created.email, subject, text, html)
        except Exception:
            # Avoid leaking email errors to clients; log for operators instead
            logging.exception("Failed to send verification email")

    # Auto-login: issue access and refresh tokens even if not verified
    # (feature-gated elsewhere)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth_utils.create_access_token(
        data={
            "sub": created.email,
            "user_id": created.id,
            "role": crud.get_primary_role_name(db, created.id),
            "token_version": getattr(created, "token_version", 1),
        },
        expires_delta=access_token_expires,
    )

    role_name = crud.get_primary_role_name(db, created.id)
    user_out = auth_schemas.UserOut(
        id=created.id,
        email=created.email,
        nombre=created.full_name.split(" ")[0] if created.full_name else "",
        apellidos=(
            " ".join(created.full_name.split(" ")[1:]) if created.full_name else ""
        ),
        role=role_name,
        is_active=created.is_active,
        is_verified=getattr(created, "is_verified", False),
        created_at=created.created_at,
        tos_accepted_at=getattr(created, "tos_accepted_at", None),
        tos_version=getattr(created, "tos_version", None),
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
        db, created, refresh_plain, user_agent=user_agent, ip_address=ip
    )

    # Backward-compatible response:
    # keep message (+ dev verification_token) and add token fields
    response = {
        "message": (
            "Registration successful! Please check your email to verify your "
            "account."
        ),
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": user_out,
        "refresh_token": refresh_plain,
    }
    if settings.is_development:
        response["verification_token"] = token
    return response


@router.post("/verify-email")
@limiter.limit(VERIFY_EMAIL_LIMIT)
def verify_email(
    request: Request,
    payload: auth_schemas.EmailVerificationConfirm,
    db: Session = Depends(get_db),
):
    """Verify user's email address using the verification token."""
    data = auth_utils.verify_email_verification_token(payload.token)
    user = crud.get_user_by_id(db, data["user_id"])
    if not user or user.email != data["email"]:
        raise HTTPException(status_code=400, detail="Invalid token or user")

    if user.is_verified:
        return {"message": "Email is already verified"}

    # Mark user as verified
    crud.verify_user_email(db, user)

    return {"message": "Email verified successfully! You can now log in."}


@router.post("/resend-verification")
@limiter.limit(RESEND_VERIFICATION_LIMIT)
def resend_verification_email(
    request: Request,
    payload: auth_schemas.EmailVerificationRequest,
    db: Session = Depends(get_db),
):
    """Resend email verification for unverified users."""
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        # Return 200 to avoid user enumeration
        return {
            "message": (
                "If the email exists and is unverified, a verification link has been "
                "sent."
            )
        }

    if user.is_verified:
        return {"message": "Email is already verified"}

    # Generate new verification token
    token = auth_utils.create_email_verification_token(
        user_id=user.id, email=user.email
    )

    # Send verification email if SMTP is configured
    if can_send_email():
        try:
            base_url = settings.FRONTEND_VERIFICATION_URL.rstrip("/")
            verification_link = f"{base_url}?token={token}"
            subject = "Email verification reminder"
            text = (
                f"This is a reminder to verify your email address for "
                f"{settings.PROJECT_NAME}.\n\n"
                "Please verify your email address to complete your registration.\n\n"
                "Use the following token in the app, or open this link:\n"
                f"{verification_link}\n\n"
                "If you didn't create this account, please ignore this email."
            )
            html = (
                f"<h2>Email Verification Reminder</h2>"
                f"<p>This is a reminder to verify your email address for "
                f"{settings.PROJECT_NAME}.</p>"
                f"<p><a href='{verification_link}' "
                f"style='background-color: #4CAF50; color: white; padding: 14px 20px; "
                f"text-decoration: none; border-radius: 4px;'>"
                f"Verify Email Address</a></p>"
                f"<p>Or copy and paste this link in your browser:<br>"
                f"{verification_link}</p>"
                f"<p>If you didn't create this account, please ignore this email.</p>"
            )
            send_email(user.email, subject, text, html)
        except Exception:
            logging.exception("Failed to send verification email")

    # In development, also return token for testing
    if settings.is_development:
        return {
            "message": (
                "If the email exists and is unverified, a verification link has been "
                "sent."
            ),
            "verification_token": token,
        }

    return {
        "message": (
            "If the email exists and is unverified, a verification link has been "
            "sent."
        )
    }


@router.post("/login", response_model=auth_schemas.Token)
@limiter.limit(LOGIN_LIMIT)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        maybe_user = crud.get_user_by_email(db, form_data.username)
        if maybe_user and getattr(maybe_user, "lockout_until", None):
            now = auth_utils.now_utc()
            if maybe_user.lockout_until and maybe_user.lockout_until > now:
                raise HTTPException(
                    status_code=429,
                    detail="Account temporarily locked. Please try again later.",
                )
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    # Allow login for non-verified users; feature gates will restrict actions elsewhere

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
    # Build response payload (Token schema) and return
    role_name = crud.get_primary_role_name(db, user.id)
    user_out = auth_schemas.UserOut(
        id=user.id,
        email=user.email,
        nombre=user.full_name.split(" ")[0] if user.full_name else "",
        apellidos=" ".join(user.full_name.split(" ")[1:]) if user.full_name else "",
        role=role_name,
        is_active=user.is_active,
        is_verified=getattr(user, "is_verified", False),
        created_at=user.created_at,
        tos_accepted_at=getattr(user, "tos_accepted_at", None),
        tos_version=getattr(user, "tos_version", None),
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


@router.post("/otp/issue")
def issue_email_otp(
    payload: auth_schemas.OTPIssueRequest, db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    code = auth_utils.generate_numeric_code(6)
    user.email_otp_hash = auth_utils.hash_otp_code(code)
    user.email_otp_expires_at = auth_utils.now_utc() + timedelta(minutes=10)
    db.add(user)
    db.commit()
    if can_send_email():
        try:
            send_email(user.email, "Your verification code", f"Your code is: {code}")
        except Exception:
            logging.exception("Failed to send OTP email")
    response = {"message": "OTP issued"}
    if settings.is_development:
        response["code"] = code
    return response


@router.post("/otp/verify")
def verify_email_otp(
    payload: auth_schemas.OTPVerifyRequest, db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, payload.email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.email_otp_hash or not user.email_otp_expires_at:
        raise HTTPException(status_code=400, detail="No OTP pending")
    if user.email_otp_expires_at <= auth_utils.now_utc():
        raise HTTPException(status_code=400, detail="OTP expired")
    if auth_utils.hash_otp_code(payload.code) != user.email_otp_hash:
        raise HTTPException(status_code=400, detail="Invalid OTP code")
    crud.verify_user_email(db, user)
    user.email_otp_hash = None
    user.email_otp_expires_at = None
    db.add(user)
    db.commit()
    return {"message": "Email verified via OTP"}


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
        is_verified=getattr(user, "is_verified", False),
        created_at=user.created_at,
        tos_accepted_at=getattr(user, "tos_accepted_at", None),
        tos_version=getattr(user, "tos_version", None),
    )


@router.post("/accept-tos")
def accept_tos(
    request: Request,
    payload: auth_schemas.TOSAcceptRequest,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
):
    data = auth_utils.verify_token(token)
    user = crud.get_user_by_id(db, data.get("user_id"))
    if not user:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    user.tos_accepted_at = auth_utils.now_utc()
    user.tos_version = payload.version
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "Terms accepted", "tos_version": user.tos_version}


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
        try:
            base_url = settings.FRONTEND_RESET_URL.rstrip("/")
            # Compose link using configurable frontend URL
            reset_link = f"{base_url}?token={token}"
            subject = "Password reset instructions"
            text = (
                "You requested to reset your password.\n\n"
                "Use the following token in the app, or open this link:\n"
                f"{reset_link}\n\n"
                "If you didn't request this, please ignore this email."
            )
            html = (
                f"<p>You requested to reset your password.</p>"
                f"<p>Use this <a href='{reset_link}'>reset link</a> "
                f"or paste the token in the app.</p>"
                f"<p>If you didn't request this, please ignore this email.</p>"
            )
            send_email(user.email, subject, text, html)
        except Exception:
            # Avoid leaking email errors to clients; log for operators instead
            logging.exception("Failed to send password reset email")

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
        is_verified=getattr(updated, "is_verified", False),
        created_at=updated.created_at,
    )


@router.delete("/me")
def delete_me(
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    # Only admins and trainers can delete themselves, not athletes
    if payload.get("role") == "athlete":
        raise HTTPException(
            status_code=403,
            detail="Athletes cannot delete themselves. Contact admin for deletion.",
        )

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
        is_verified=getattr(user, "is_verified", False),
        created_at=user.created_at,
    )
    return auth_schemas.Token(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user_out,
        refresh_token=new_refresh,
    )
