from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    require_trainer_or_admin,
    require_visible_for_optional_client_id,
)
from ..db.session import get_db

router = APIRouter()


# Training Plans
@router.post(
    "/",
    response_model=schemas.TrainingPlanOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_training_plan(
    plan: schemas.TrainingPlanCreate, db: Session = Depends(get_db)
):
    """Create a new training plan"""
    return crud.create_training_plan(db=db, plan_data=plan)


@router.get(
    "/",
    response_model=List[schemas.TrainingPlanOut],
    dependencies=[Depends(require_visible_for_optional_client_id)],
)
def get_training_plans(
    trainer_id: int = Query(None, description="Filter by trainer ID"),
    client_id: int = Query(None, description="Filter by client ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get training plans with optional filtering"""
    if trainer_id:
        return crud.get_training_plans_by_trainer(
            db=db, trainer_id=trainer_id, skip=skip, limit=limit
        )
    elif client_id:
        return crud.get_training_plans_by_client(
            db=db, client_id=client_id, skip=skip, limit=limit
        )
    else:
        raise HTTPException(
            status_code=400, detail="Must specify either trainer_id or client_id"
        )


@router.get(
    "/{plan_id}",
    response_model=schemas.TrainingPlanOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get a specific training plan"""
    plan = crud.get_training_plan(db=db, plan_id=plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return plan


@router.put(
    "/{plan_id}",
    response_model=schemas.TrainingPlanOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_training_plan(
    plan_id: int, plan: schemas.TrainingPlanUpdate, db: Session = Depends(get_db)
):
    """Update a training plan"""
    updated_plan = crud.update_training_plan(db=db, plan_id=plan_id, plan_data=plan)
    if not updated_plan:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return updated_plan


@router.delete("/{plan_id}", dependencies=[Depends(require_trainer_or_admin)])
def delete_training_plan(plan_id: int, db: Session = Depends(get_db)):
    """Delete a training plan"""
    success = crud.delete_training_plan(db=db, plan_id=plan_id)
    if not success:
        raise HTTPException(status_code=404, detail="Training plan not found")
    return {"message": "Training plan deleted successfully"}


# Macrocycles
@router.post(
    "/{plan_id}/macrocycles",
    response_model=schemas.MacrocycleOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_macrocycle(
    plan_id: int, macrocycle: schemas.MacrocycleCreate, db: Session = Depends(get_db)
):
    """Create a new macrocycle for a training plan"""
    # Override the training_plan_id from the URL parameter
    macrocycle_data = macrocycle.model_dump()
    macrocycle_data["training_plan_id"] = plan_id
    return crud.create_macrocycle(
        db=db, macrocycle_data=schemas.MacrocycleCreate(**macrocycle_data)
    )


@router.get(
    "/{plan_id}/macrocycles",
    response_model=List[schemas.MacrocycleOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_macrocycles(
    plan_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all macrocycles for a training plan"""
    return crud.get_macrocycles_by_plan(
        db=db, training_plan_id=plan_id, skip=skip, limit=limit
    )


@router.get(
    "/macrocycles/{macrocycle_id}",
    response_model=schemas.MacrocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_macrocycle(macrocycle_id: int, db: Session = Depends(get_db)):
    """Get a specific macrocycle"""
    macrocycle = crud.get_macrocycle(db=db, macrocycle_id=macrocycle_id)
    if not macrocycle:
        raise HTTPException(status_code=404, detail="Macrocycle not found")
    return macrocycle


@router.put(
    "/macrocycles/{macrocycle_id}",
    response_model=schemas.MacrocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_macrocycle(
    macrocycle_id: int,
    macrocycle: schemas.MacrocycleUpdate,
    db: Session = Depends(get_db),
):
    """Update a macrocycle"""
    updated_macrocycle = crud.update_macrocycle(
        db=db, macrocycle_id=macrocycle_id, macrocycle_data=macrocycle
    )
    if not updated_macrocycle:
        raise HTTPException(status_code=404, detail="Macrocycle not found")
    return updated_macrocycle


@router.delete(
    "/macrocycles/{macrocycle_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_macrocycle(macrocycle_id: int, db: Session = Depends(get_db)):
    """Delete a macrocycle"""
    success = crud.delete_macrocycle(db=db, macrocycle_id=macrocycle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Macrocycle not found")
    return {"message": "Macrocycle deleted successfully"}


# Mesocycles
@router.post(
    "/macrocycles/{macrocycle_id}/mesocycles",
    response_model=schemas.MesocycleOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_mesocycle(
    macrocycle_id: int,
    mesocycle: schemas.MesocycleCreate,
    db: Session = Depends(get_db),
):
    """Create a new mesocycle for a macrocycle"""
    # Override the macrocycle_id from the URL parameter
    mesocycle_data = mesocycle.model_dump()
    mesocycle_data["macrocycle_id"] = macrocycle_id
    return crud.create_mesocycle(
        db=db, mesocycle_data=schemas.MesocycleCreate(**mesocycle_data)
    )


@router.get(
    "/macrocycles/{macrocycle_id}/mesocycles",
    response_model=List[schemas.MesocycleOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_mesocycles(
    macrocycle_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all mesocycles for a macrocycle"""
    return crud.get_mesocycles_by_macrocycle(
        db=db, macrocycle_id=macrocycle_id, skip=skip, limit=limit
    )


@router.get(
    "/mesocycles/{mesocycle_id}",
    response_model=schemas.MesocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_mesocycle(mesocycle_id: int, db: Session = Depends(get_db)):
    """Get a specific mesocycle"""
    mesocycle = crud.get_mesocycle(db=db, mesocycle_id=mesocycle_id)
    if not mesocycle:
        raise HTTPException(status_code=404, detail="Mesocycle not found")
    return mesocycle


@router.put(
    "/mesocycles/{mesocycle_id}",
    response_model=schemas.MesocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_mesocycle(
    mesocycle_id: int, mesocycle: schemas.MesocycleUpdate, db: Session = Depends(get_db)
):
    """Update a mesocycle"""
    updated_mesocycle = crud.update_mesocycle(
        db=db, mesocycle_id=mesocycle_id, mesocycle_data=mesocycle
    )
    if not updated_mesocycle:
        raise HTTPException(status_code=404, detail="Mesocycle not found")
    return updated_mesocycle


@router.delete(
    "/mesocycles/{mesocycle_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_mesocycle(mesocycle_id: int, db: Session = Depends(get_db)):
    """Delete a mesocycle"""
    success = crud.delete_mesocycle(db=db, mesocycle_id=mesocycle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mesocycle not found")
    return {"message": "Mesocycle deleted successfully"}


# Microcycles
@router.post(
    "/mesocycles/{mesocycle_id}/microcycles",
    response_model=schemas.MicrocycleOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_microcycle(
    mesocycle_id: int,
    microcycle: schemas.MicrocycleCreate,
    db: Session = Depends(get_db),
):
    """Create a new microcycle for a mesocycle"""
    # Override the mesocycle_id from the URL parameter
    microcycle_data = microcycle.model_dump()
    microcycle_data["mesocycle_id"] = mesocycle_id
    return crud.create_microcycle(
        db=db, microcycle_data=schemas.MicrocycleCreate(**microcycle_data)
    )


@router.get(
    "/mesocycles/{mesocycle_id}/microcycles",
    response_model=List[schemas.MicrocycleOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_microcycles(
    mesocycle_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all microcycles for a mesocycle"""
    return crud.get_microcycles_by_mesocycle(
        db=db, mesocycle_id=mesocycle_id, skip=skip, limit=limit
    )


@router.get(
    "/microcycles/{microcycle_id}",
    response_model=schemas.MicrocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_microcycle(microcycle_id: int, db: Session = Depends(get_db)):
    """Get a specific microcycle"""
    microcycle = crud.get_microcycle(db=db, microcycle_id=microcycle_id)
    if not microcycle:
        raise HTTPException(status_code=404, detail="Microcycle not found")
    return microcycle


@router.put(
    "/microcycles/{microcycle_id}",
    response_model=schemas.MicrocycleOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_microcycle(
    microcycle_id: int,
    microcycle: schemas.MicrocycleUpdate,
    db: Session = Depends(get_db),
):
    """Update a microcycle"""
    updated_microcycle = crud.update_microcycle(
        db=db, microcycle_id=microcycle_id, microcycle_data=microcycle
    )
    if not updated_microcycle:
        raise HTTPException(status_code=404, detail="Microcycle not found")
    return updated_microcycle


@router.delete(
    "/microcycles/{microcycle_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_microcycle(microcycle_id: int, db: Session = Depends(get_db)):
    """Delete a microcycle"""
    success = crud.delete_microcycle(db=db, microcycle_id=microcycle_id)
    if not success:
        raise HTTPException(status_code=404, detail="Microcycle not found")
    return {"message": "Microcycle deleted successfully"}
