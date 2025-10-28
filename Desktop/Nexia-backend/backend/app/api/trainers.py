from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    require_admin,
    require_trainer_or_admin,
    require_trainer_self_or_admin,
)
from ..db import models
from ..db.session import get_db

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get(
    "/profile",
    response_model=schemas.TrainerOut,
)
def read_current_trainer(
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Return the current trainer profile resolved from the JWT."""
    user_id = payload.get("user_id")
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer


@router.patch(
    "/profile",
    response_model=schemas.TrainerOut,
)
def update_current_trainer(
    trainer: schemas.TrainerUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Update the current trainer profile resolved from the JWT."""
    user_id = payload.get("user_id")
    db_trainer = (
        db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    )
    if not db_trainer:
        raise HTTPException(status_code=404, detail="Trainer not found")
    updated = crud.update_trainer(db, db_trainer.id, trainer)
    if updated is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return updated


@router.post(
    "/", response_model=schemas.TrainerOut, dependencies=[Depends(require_admin)]
)
def create_trainer(trainer: schemas.TrainerCreate, db: Session = Depends(get_db)):
    try:
        return crud.create_trainer(db, trainer)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Trainer email must be unique")


@router.get(
    "/", response_model=List[schemas.TrainerOut], dependencies=[Depends(require_admin)]
)
def read_trainers(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_trainers(db, skip=skip, limit=limit)


@router.get(
    "/{trainer_id}",
    response_model=schemas.TrainerOut,
    dependencies=[Depends(require_trainer_self_or_admin)],
)
def read_trainer(trainer_id: int, db: Session = Depends(get_db)):
    trainer = crud.get_trainer(db, trainer_id)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return trainer


@router.put(
    "/{trainer_id}",
    response_model=schemas.TrainerOut,
    dependencies=[Depends(require_trainer_self_or_admin)],
)
def update_trainer(
    trainer_id: int, trainer: schemas.TrainerUpdate, db: Session = Depends(get_db)
):
    updated_trainer = crud.update_trainer(db, trainer_id, trainer)
    if updated_trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return updated_trainer


@router.delete("/{trainer_id}", dependencies=[Depends(require_admin)])
def delete_trainer(trainer_id: int, db: Session = Depends(get_db)):
    success = crud.delete_trainer(db, trainer_id)
    if not success:
        raise HTTPException(status_code=404, detail="Trainer not found")
    return {"message": "Trainer deleted successfully"}


@router.post(
    "/{trainer_id}/clients/{client_id}",
    response_model=schemas.TrainerClientOut,
    status_code=201,
    dependencies=[Depends(require_trainer_self_or_admin)],
)
def link_client_to_trainer(
    trainer_id: int, client_id: int, db: Session = Depends(get_db)
):
    """Link a client to a trainer. Enforces per-trainer email uniqueness."""
    try:
        payload = schemas.TrainerClientCreate(
            trainer_id=trainer_id, client_id=client_id
        )
        return crud.create_trainer_client(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except IntegrityError:
        # DB-level unique index violation fallback
        raise HTTPException(
            status_code=400,
            detail="Client email already linked to this trainer",
        )


@router.delete(
    "/{trainer_id}/clients/{client_id}",
    dependencies=[Depends(require_trainer_self_or_admin)],
)
def unlink_client_from_trainer(
    trainer_id: int, client_id: int, db: Session = Depends(get_db)
):
    success = crud.unlink_trainer_client(db, trainer_id=trainer_id, client_id=client_id)
    if not success:
        raise HTTPException(status_code=404, detail="Link not found")
    return {"message": "Client unlinked from trainer"}


@router.get(
    "/{trainer_id}/clients",
    response_model=schemas.ClientListResponse,
    dependencies=[Depends(require_trainer_self_or_admin)],
)
def list_trainer_clients(
    trainer_id: int,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    sort_by: str = "apellidos",
    sort_order: str = "asc",
    db: Session = Depends(get_db),
):
    if page < 1:
        raise HTTPException(status_code=400, detail="page must be >= 1")
    if not (1 <= page_size <= 50):
        raise HTTPException(
            status_code=400, detail="page_size must be between 1 and 50"
        )
    if sort_by not in {"apellidos", "nombre", "edad", "fecha_alta"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid sort_by. Allowed: apellidos, nombre, edad, fecha_alta",
        )
    if sort_order not in {"asc", "desc"}:
        raise HTTPException(
            status_code=400, detail="Invalid sort_order. Allowed: asc, desc"
        )

    skip = (page - 1) * page_size
    try:
        items, total = crud.get_clients_for_trainer_paginated(
            db=db,
            trainer_id=trainer_id,
            skip=skip,
            limit=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    has_more = skip + len(items) < total
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": has_more,
    }
