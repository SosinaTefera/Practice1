from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    get_current_payload,
    require_admin,
    require_client_visible_to_self_trainer_or_admin,
    require_trainer_or_admin,
    require_verified_and_profile_complete,
)
from ..db import models
from ..db.session import get_db

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post(
    "/",
    response_model=schemas.ClientProfileOut,
    dependencies=[
        Depends(require_trainer_or_admin),
        Depends(require_verified_and_profile_complete),
    ],
)
def create_client(profile: schemas.ClientProfileCreate, db: Session = Depends(get_db)):
    return crud.create_client_profile(db, profile)


@router.get("/profile", response_model=schemas.ClientProfileOut)
def read_current_client(
    db: Session = Depends(get_db), payload: dict = Depends(get_current_payload)
):
    # Restrict to athlete self-profile for consistency with trainers
    if payload.get("role") != "athlete":
        raise HTTPException(status_code=403, detail="Athlete role required")
    user_id = payload.get("user_id")
    client = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.user_id == user_id)
        .first()
    )
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.get(
    "/",
    response_model=schemas.ClientListResponse,
    dependencies=[Depends(require_trainer_or_admin)],
)
def read_clients(
    page: int = Query(1, ge=1, description="Page number (default 1)"),
    page_size: int = Query(
        20, ge=1, le=50, description="Page size (default 20, max 50)"
    ),
    db: Session = Depends(get_db),
):
    skip = (page - 1) * page_size
    items, total = crud.get_client_profiles_paginated(db, skip=skip, limit=page_size)
    has_more = skip + len(items) < total
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    }


@router.get(
    "/search",
    response_model=schemas.ClientListResponse,
    dependencies=[Depends(require_trainer_or_admin)],
)
def search_clients(
    page: int = Query(1, ge=1, description="Page number (default 1)"),
    page_size: int = Query(
        20, ge=1, le=50, description="Page size (default 20, max 50)"
    ),
    search: Optional[str] = Query(
        None, description="Search term for name, surname, or email"
    ),
    age_min: Optional[int] = Query(
        None, ge=0, le=120, description="Minimum age filter"
    ),
    age_max: Optional[int] = Query(
        None, ge=0, le=120, description="Maximum age filter"
    ),
    gender: Optional[str] = Query(None, description="Gender filter"),
    training_goal: Optional[str] = Query(None, description="Training goal filter"),
    experience: Optional[str] = Query(None, description="Experience level filter"),
    sort_by: str = Query(
        "apellidos", description="Sort field: apellidos, nombre, edad, fecha_alta"
    ),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    db: Session = Depends(get_db),
):
    """
    Advanced client search and filtering with multiple criteria.
    Perfect for coaches managing many clients.
    """
    # Validate filters for clear error messages
    if gender is not None:
        allowed_genders = {g.value for g in models.GenderEnum}
        if gender not in allowed_genders:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid gender. Allowed: {sorted(allowed_genders)}",
            )
    if training_goal is not None:
        allowed_goals = {g.value for g in models.TrainingGoalEnum}
        if training_goal not in allowed_goals:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid training_goal. Allowed: {sorted(allowed_goals)}",
            )
    if experience is not None:
        allowed_exp = {e.value for e in models.ExperienceEnum}
        if experience not in allowed_exp:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid experience. Allowed: {sorted(allowed_exp)}",
            )

    allowed_sort_fields = {"apellidos", "nombre", "edad", "fecha_alta"}
    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_by. Allowed: apellidos, nombre, edad, fecha_alta",
        )
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_order. Allowed: asc, desc",
        )

    try:
        skip = (page - 1) * page_size
        items, total = crud.search_and_filter_clients_paginated(
            db=db,
            skip=skip,
            limit=page_size,
            search=search,
            age_min=age_min,
            age_max=age_max,
            gender=gender,
            training_goal=training_goal,
            experience=experience,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        has_more = skip + len(items) < total
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": has_more,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/stats")
def get_client_stats(
    db: Session = Depends(get_db), payload: dict = Depends(get_current_payload)
):
    """
    Get client statistics by role:
    - Trainer: Returns stats for their clients only
    - Admin: Returns global stats for all clients and trainers
    - Athlete: 403 Forbidden
    """
    from sqlalchemy import func

    from ..db.models import ClientProfile, Trainer, TrainerClient

    role = payload.get("role")
    user_id = payload.get("user_id")

    if role == "athlete":
        raise HTTPException(
            status_code=403, detail="Athletes cannot access this endpoint"
        )

    # Common stats for all roles
    total_clients = db.query(func.count(ClientProfile.id)).scalar() or 0
    active_clients = (
        db.query(func.count(ClientProfile.id))
        .filter(ClientProfile.is_active.is_(True))
        .scalar()
        or 0
    )
    inactive_clients = total_clients - active_clients
    active_percentage = round(
        (active_clients / total_clients * 100) if total_clients > 0 else 0, 1
    )

    # Average age and BMI
    avg_age = (
        db.query(func.avg(ClientProfile.edad)).scalar() or 0
        if total_clients > 0
        else None
    )
    avg_bmi = (
        db.query(func.avg(ClientProfile.imc)).scalar() or 0
        if total_clients > 0
        else None
    )

    # By goal
    by_goal = (
        db.query(
            ClientProfile.objetivo_entrenamiento,
            func.count(ClientProfile.id).label("count"),
        )
        .filter(ClientProfile.objetivo_entrenamiento.isnot(None))
        .group_by(ClientProfile.objetivo_entrenamiento)
        .all()
    )
    by_goal_dict = {
        str(goal[0].value) if hasattr(goal[0], "value") else str(goal[0]): goal[1]
        for goal in by_goal
    }

    # By experience
    by_experience = (
        db.query(ClientProfile.experiencia, func.count(ClientProfile.id).label("count"))
        .filter(ClientProfile.experiencia.isnot(None))
        .group_by(ClientProfile.experiencia)
        .all()
    )
    by_experience_dict = {
        str(exp[0].value) if hasattr(exp[0], "value") else str(exp[0]): exp[1]
        for exp in by_experience
    }

    response = {
        "total_clients": total_clients,
        "active_clients": active_clients,
        "inactive_clients": inactive_clients,
        "active_percentage": active_percentage,
        "avg_age": round(avg_age, 1) if avg_age else None,
        "avg_bmi": round(avg_bmi, 1) if avg_bmi else None,
        "by_goal": by_goal_dict,
        "by_experience": by_experience_dict,
    }

    # If admin, add additional metrics
    if role == "admin":
        total_trainers = db.query(func.count(Trainer.id)).scalar() or 0
        avg_clients_per_trainer = round(
            (total_clients / total_trainers) if total_trainers > 0 else 0, 1
        )

        response.update(
            {
                "total_trainers": total_trainers,
                "avg_clients_per_trainer": avg_clients_per_trainer,
            }
        )

    # If trainer, filter to only their clients
    elif role == "trainer":
        # Get trainer's clients
        trainer = db.query(Trainer).filter(Trainer.user_id == user_id).first()
        if trainer:
            # Update counts for trainer's clients only
            trainer_total = (
                db.query(func.count(ClientProfile.id))
                .join(TrainerClient)
                .filter(TrainerClient.trainer_id == trainer.id)
                .scalar()
                or 0
            )
            trainer_active = (
                db.query(func.count(ClientProfile.id))
                .join(TrainerClient)
                .filter(TrainerClient.trainer_id == trainer.id)
                .filter(ClientProfile.is_active.is_(True))
                .scalar()
                or 0
            )
            trainer_inactive = trainer_total - trainer_active
            trainer_percentage = round(
                (trainer_active / trainer_total * 100) if trainer_total > 0 else 0, 1
            )

            response.update(
                {
                    "total_clients": trainer_total,
                    "active_clients": trainer_active,
                    "inactive_clients": trainer_inactive,
                    "active_percentage": trainer_percentage,
                }
            )

    return response


@router.get(
    "/{client_id}",
    response_model=schemas.ClientProfileOut,
    dependencies=[Depends(require_client_visible_to_self_trainer_or_admin)],
)
def read_client(client_id: int, db: Session = Depends(get_db)):
    client = crud.get_client_profile(db, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put(
    "/{client_id}",
    response_model=schemas.ClientProfileOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_client(
    client_id: int, profile: schemas.ClientProfileUpdate, db: Session = Depends(get_db)
):
    updated_client = crud.update_client_profile(db, client_id, profile)
    if updated_client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    return updated_client


@router.delete("/{client_id}", dependencies=[Depends(require_admin)])
def delete_client(client_id: int, db: Session = Depends(get_db)):
    success = crud.delete_client_profile(db, client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted successfully"}
