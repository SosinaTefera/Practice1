from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import crud
from ..auth.deps import get_current_payload
from ..db.session import get_db

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/readiness")
def billing_readiness(
    db: Session = Depends(get_db), payload: dict = Depends(get_current_payload)
):
    """Return whether the current user is allowed to initiate billing flows.

    Policy (per product decision): must have verified email.
    Additional checks can be added later (e.g., KYC, profile completeness).
    """
    user = crud.get_user_by_id(db, payload.get("user_id"))
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    is_ready = bool(getattr(user, "is_verified", False))
    reason = None if is_ready else "Email not verified"

    return {
        "ready": is_ready,
        "reason": reason,
        "requirements": {"email_verified": getattr(user, "is_verified", False)},
    }
