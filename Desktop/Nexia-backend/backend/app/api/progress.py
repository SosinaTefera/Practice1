from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    require_client_visible_to_self_trainer_or_admin,
    require_trainer_has_client_or_admin,
    require_trainer_or_admin,
)
from ..db.session import get_db

router = APIRouter(tags=["Progress Tracking"])


# Client Progress Tracking
@router.post(
    "/",
    response_model=schemas.ClientProgressOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_progress_record(
    progress: schemas.ClientProgressCreate, db: Session = Depends(get_db)
):
    """Create a new progress record for a client"""
    return crud.create_client_progress(db=db, progress_data=progress)


@router.get(
    "/",
    response_model=List[schemas.ClientProgressOut],
    dependencies=[Depends(require_trainer_has_client_or_admin)],
)
def get_progress_records(
    client_id: int = Query(..., description="Filter by client ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all progress records for a specific client"""
    return crud.get_client_progress_by_client_id(
        db=db, client_id=client_id, skip=skip, limit=limit
    )


@router.get(
    "/{progress_id}",
    response_model=schemas.ClientProgressOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_progress_record(progress_id: int, db: Session = Depends(get_db)):
    """Get a specific progress record"""
    progress = crud.get_client_progress_by_id(db=db, progress_id=progress_id)
    if not progress:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return progress


@router.put(
    "/{progress_id}",
    response_model=schemas.ClientProgressOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_progress_record(
    progress_id: int,
    progress: schemas.ClientProgressUpdate,
    db: Session = Depends(get_db),
):
    """Update a progress record"""
    updated_progress = crud.update_client_progress(
        db=db, progress_id=progress_id, progress_data=progress
    )
    if not updated_progress:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return updated_progress


@router.delete("/{progress_id}", dependencies=[Depends(require_trainer_or_admin)])
def delete_progress_record(progress_id: int, db: Session = Depends(get_db)):
    """Delete a progress record"""
    success = crud.delete_client_progress(db=db, progress_id=progress_id)
    if not success:
        raise HTTPException(status_code=404, detail="Progress record not found")
    return {"message": "Progress record deleted successfully"}


# Progress Analytics
@router.get(
    "/analytics/{client_id}",
    dependencies=[Depends(require_client_visible_to_self_trainer_or_admin)],
)
def get_progress_analytics(client_id: int, db: Session = Depends(get_db)):
    """Get progress analytics for a client"""

    from ..db.models import ClientProgress

    # Get all progress records for the client
    progress_records = (
        db.query(ClientProgress)
        .filter(ClientProgress.client_id == client_id)
        .order_by(ClientProgress.fecha_registro)
        .all()
    )

    if not progress_records:
        raise HTTPException(
            status_code=404, detail="No progress records found for this client"
        )

    # Calculate analytics
    total_records = len(progress_records)
    first_record = progress_records[0]
    latest_record = progress_records[-1]

    # Weight changes
    weight_change = None
    if first_record.peso and latest_record.peso:
        weight_change = latest_record.peso - first_record.peso

    # BMI changes
    bmi_change = None
    if first_record.imc and latest_record.imc:
        bmi_change = latest_record.imc - first_record.imc

    # Progress trend
    progress_trend = "stable"
    if weight_change:
        if weight_change < -1:  # Weight loss
            progress_trend = "losing_weight"
        elif weight_change > 1:  # Weight gain
            progress_trend = "gaining_weight"
        else:
            progress_trend = "maintaining_weight"

    return {
        "client_id": client_id,
        "total_records": total_records,
        "first_record_date": first_record.fecha_registro,
        "latest_record_date": latest_record.fecha_registro,
        "weight_change_kg": weight_change,
        "bmi_change": bmi_change,
        "progress_trend": progress_trend,
        "progress_records": [
            {
                "date": record.fecha_registro,
                "weight": record.peso,
                "height": record.altura,
                "bmi": record.imc,
                "notes": record.notas,
            }
            for record in progress_records
        ],
    }
