from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import crud
from ..auth.deps import get_current_payload
from ..db.session import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


class UserDeleteRequest(BaseModel):
    emails: List[str]


class UserDeleteResponse(BaseModel):
    message: str
    deleted_count: int
    deleted_emails: List[str]


class DeleteAllResponse(BaseModel):
    message: str
    deleted_count: int


def require_admin_role(payload: dict = Depends(get_current_payload)):
    """Ensure the current user has admin role."""
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return payload


@router.delete("/users", response_model=UserDeleteResponse)
def delete_users(
    request: Request,
    user_data: UserDeleteRequest,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
):
    """
    Delete users by email addresses. Admin only.
    Safely handles foreign key constraints and related data cleanup.
    """
    deleted_emails = []
    deleted_count = 0

    try:
        for email in user_data.emails:
            email = email.strip().lower()

            # Find user
            user = crud.get_user_by_email(db, email)
            if not user:
                continue

            # Delete all related records first (foreign key constraints)

            # 1. Delete refresh tokens
            db.execute(
                text("DELETE FROM refresh_tokens WHERE user_id = :user_id"),
                {"user_id": user.id},
            )

            # 2. Delete user roles
            db.execute(
                text("DELETE FROM user_roles WHERE user_id = :user_id"),
                {"user_id": user.id},
            )

            # 3. Soft delete trainer profile if exists
            db.execute(
                text("UPDATE trainers SET is_active = false WHERE user_id = :user_id"),
                {"user_id": user.id},
            )

            # 4. Soft delete client profile if exists
            db.execute(
                text(
                    "UPDATE client_profiles SET is_active = false "
                    "WHERE user_id = :user_id"
                ),
                {"user_id": user.id},
            )

            # 5. Delete progress records (uses client_id, not user_id)
            db.execute(
                text("DELETE FROM progress_tracking WHERE client_id = :client_id"),
                {"client_id": user.id},
            )

            # 6. Soft delete the user (deactivate and clear email for re-registration)
            db.execute(
                text(
                    "UPDATE users SET is_active = false, email = NULL, username = NULL "
                    "WHERE id = :user_id"
                ),
                {"user_id": user.id},
            )

            deleted_emails.append(email)
            deleted_count += 1

        db.commit()

        return UserDeleteResponse(
            message=f"Successfully deleted {deleted_count} users",
            deleted_count=deleted_count,
            deleted_emails=deleted_emails,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting users: {str(e)}")


@router.get("/users/test")
def list_test_users(
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
):
    """
    List users that appear to be test accounts (contain 'test' in email).
    Admin only.
    """
    try:
        # Find users with 'test' in email (case insensitive)
        result = db.execute(
            text(
                """
                SELECT id, email, full_name, created_at, is_active
                FROM users
                WHERE LOWER(email) LIKE '%test%'
                ORDER BY created_at DESC
            """
            )
        ).fetchall()

        test_users = []
        for row in result:
            test_users.append(
                {
                    "id": row.id,
                    "email": row.email,
                    "full_name": row.full_name,
                    "created_at": (
                        row.created_at.isoformat() if row.created_at else None
                    ),
                    "is_active": row.is_active,
                }
            )

        return {"test_users": test_users, "count": len(test_users)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error listing test users: {str(e)}"
        )


@router.delete("/users/all", response_model=DeleteAllResponse)
def delete_all_users(
    request: Request,
    db: Session = Depends(get_db),
    admin_payload: dict = Depends(require_admin_role),
):
    """
    Delete ALL users from the database. Admin only.
    ⚠️ DANGER: This will permanently delete all users and related data!
    """
    try:
        # Count users before deletion
        user_count = db.execute(text("SELECT COUNT(*) FROM users")).scalar()

        if user_count == 0:
            return DeleteAllResponse(
                message="No users found to delete", deleted_count=0
            )

        # Delete all related records first (foreign key constraints)

        # 1. Delete all refresh tokens
        db.execute(text("DELETE FROM refresh_tokens"))

        # 2. Delete all user roles
        db.execute(text("DELETE FROM user_roles"))

        # 3. Delete all trainer profiles
        db.execute(text("DELETE FROM trainers"))

        # 4. Delete all client profiles
        db.execute(text("DELETE FROM client_profiles"))

        # 5. Delete all progress records
        db.execute(text("DELETE FROM progress_tracking"))

        # 6. Finally delete all users
        db.execute(text("DELETE FROM users"))

        db.commit()

        return DeleteAllResponse(
            message=f"Successfully deleted ALL {user_count} users and related data",
            deleted_count=user_count,
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting all users: {str(e)}"
        )
