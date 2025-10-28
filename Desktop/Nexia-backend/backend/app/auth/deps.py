from typing import Sequence

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

try:
    # Absolute imports when app is a package (runtime)
    from app.auth import models as auth_models  # type: ignore
    from app.auth import utils as auth_utils  # type: ignore
    from app.db import models  # type: ignore
    from app.db.session import get_db  # type: ignore
except Exception:  # pragma: no cover - fallback for local tooling
    # Keep absolute paths for lints/tooling as well
    from app.auth import models as auth_models  # type: ignore  # noqa: F401
    from app.auth import utils as auth_utils  # type: ignore  # noqa: F401
    from app.db import models  # type: ignore  # noqa: F401
    from app.db.session import get_db  # type: ignore  # noqa: F401

# Central OAuth2 scheme for dependencies across the app
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_payload(token: str = Depends(oauth2_scheme)) -> dict:
    """Decode JWT, enforce token_version against DB, return payload."""
    payload = auth_utils.verify_token(token)
    # Enforce token_version-based invalidation if present in payload
    token_version = payload.get("token_version")
    if token_version is not None:
        # Acquire a DB session for this check
        db = next(get_db())
        try:
            user = (
                db.query(auth_models.User)
                .filter(auth_models.User.id == payload.get("user_id"))
                .first()
            )
            if not user or getattr(user, "token_version", 1) != token_version:
                raise HTTPException(status_code=401, detail="Token invalidated")
        finally:
            try:
                db.close()
            except Exception:
                pass
    return payload


def require_authenticated(payload: dict = Depends(get_current_payload)) -> dict:
    """Require any authenticated user."""
    return payload


def require_roles(allowed_roles: Sequence[str]):
    """Factory to require one of the allowed roles."""

    def _dependency(payload: dict = Depends(get_current_payload)) -> dict:
        role = payload.get("role")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return payload

    return _dependency


def require_admin(payload: dict = Depends(get_current_payload)) -> dict:
    if payload.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required"
        )
    return payload


def require_trainer_or_admin(payload: dict = Depends(get_current_payload)) -> dict:
    role = payload.get("role")
    if role not in ("trainer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Trainer or admin role required",
        )
    return payload


def require_verified_user(
    db: Session = Depends(get_db), payload: dict = Depends(get_current_payload)
) -> dict:
    """Require that the authenticated user's email is verified.

    Use this dependency to gate features that need verified emails
    (e.g., billing, outbound client emails).
    """
    user_id = payload.get("user_id")
    user = db.query(auth_models.User).filter(auth_models.User.id == user_id).first()
    if not user or not getattr(user, "is_verified", False):
        raise HTTPException(status_code=403, detail="Email verification required")
    return payload


def require_verified_and_profile_complete(
    db: Session = Depends(get_db), payload: dict = Depends(get_current_payload)
) -> dict:
    """Require verified email and a complete trainer profile.

    Complete profile policy (initial): nombre, apellidos, telefono,
    occupation, training_modality, location_country, location_city.
    """
    user = (
        db.query(auth_models.User)
        .filter(auth_models.User.id == payload.get("user_id"))
        .first()
    )
    if not user or not getattr(user, "is_verified", False):
        raise HTTPException(status_code=403, detail="Email verification required")

    trainer = (
        db.query(models.Trainer)
        .filter(models.Trainer.user_id == payload.get("user_id"))
        .first()
    )
    if not trainer:
        raise HTTPException(status_code=403, detail="Trainer profile not linked")

    required = [
        trainer.nombre,
        trainer.apellidos,
        trainer.telefono,
        trainer.occupation,
        trainer.training_modality,
        trainer.location_country,
        trainer.location_city,
    ]
    if any(v is None or (isinstance(v, str) and not v.strip()) for v in required):
        raise HTTPException(status_code=403, detail="Complete profile required")
    return payload


def require_trainer_self_or_admin(
    trainer_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
) -> dict:
    """Allow admins, or the trainer accessing their own scope via trainer_id."""
    role = payload.get("role")
    if role == "admin":
        return payload
    if role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Trainer role required.",
        )

    user_id = payload.get("user_id")
    trainer = db.query(models.Trainer).filter(models.Trainer.id == trainer_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    if trainer.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this trainer scope",
        )
    return payload


def require_trainer_has_client_or_admin(
    client_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
) -> dict:
    """Allow admins, or a trainer only if the client is in their roster."""
    role = payload.get("role")
    if role == "admin":
        return payload
    if role != "trainer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Trainer role required.",
        )

    user_id = payload.get("user_id")
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    if not trainer:
        raise HTTPException(status_code=403, detail="Trainer profile not linked")

    link = (
        db.query(models.TrainerClient)
        .filter(
            models.TrainerClient.trainer_id == trainer.id,
            models.TrainerClient.client_id == client_id,
        )
        .first()
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this client",
        )
    return payload


def require_client_visible_to_self_trainer_or_admin(
    client_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
) -> dict:
    """Allow admin, trainer with linked client, or the athlete (client) themselves."""
    role = payload.get("role")
    if role == "admin":
        return payload
    if role == "trainer":
        # Find trainer by token user_id, then verify link exists
        trainer = (
            db.query(models.Trainer)
            .filter(models.Trainer.user_id == payload.get("user_id"))
            .first()
        )
        if not trainer:
            raise HTTPException(status_code=403, detail="Trainer profile not linked")
        link = (
            db.query(models.TrainerClient)
            .filter(
                models.TrainerClient.client_id == client_id,
                models.TrainerClient.trainer_id == trainer.id,
            )
            .first()
        )
        if not link:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this client",
            )
        return payload
    if role == "athlete":
        client = (
            db.query(models.ClientProfile)
            .filter(models.ClientProfile.id == client_id)
            .first()
        )
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        if client.user_id != payload.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this client",
            )
        return payload
    raise HTTPException(status_code=403, detail="Insufficient permissions")


def require_visible_for_optional_client_id(
    client_id: int | None = None,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
) -> dict:
    """
    For endpoints with optional client_id:
    - allow trainers/admin always
    - allow athletes only if client_id matches self
    - deny athletes when client_id is missing
    """
    role = payload.get("role")
    if role in ("admin", "trainer"):
        return payload
    if role == "athlete":
        if client_id is None:
            raise HTTPException(status_code=403, detail="Client ID required")
        # reuse visibility check
        return require_client_visible_to_self_trainer_or_admin(client_id, db, payload)
    raise HTTPException(status_code=403, detail="Insufficient permissions")
