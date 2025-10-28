from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import require_trainer_or_admin
from ..db import models
from ..db.session import get_db

router = APIRouter(prefix="/session-programming", tags=["session-programming"])


# Training Block Types
@router.get("/training-block-types", response_model=List[schemas.TrainingBlockTypeOut])
def get_training_block_types(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get training block types (predefined + trainer's custom blocks)"""
    trainer_id = payload.get("user_id")
    return crud.get_training_block_types(
        db, skip=skip, limit=limit, trainer_id=trainer_id
    )


@router.post(
    "/training-block-types",
    response_model=schemas.TrainingBlockTypeOut,
    status_code=201,
)
def create_training_block_type(
    block_type: schemas.TrainingBlockTypeCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Create a new custom training block type"""
    user_id = payload.get("user_id")
    return crud.create_training_block_type(db, block_type, user_id)


@router.get("/block-types/{block_type_id}", response_model=schemas.TrainingBlockTypeOut)
def get_training_block_type(
    block_type_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get a specific training block type"""
    block_type = crud.get_training_block_type(db, block_type_id)
    if not block_type:
        raise HTTPException(status_code=404, detail="Training block type not found")
    return block_type


@router.put("/block-types/{block_type_id}", response_model=schemas.TrainingBlockTypeOut)
def update_training_block_type(
    block_type_id: int,
    block_type: schemas.TrainingBlockTypeUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Update a training block type"""
    updated_block_type = crud.update_training_block_type(db, block_type_id, block_type)
    if not updated_block_type:
        raise HTTPException(status_code=404, detail="Training block type not found")
    return updated_block_type


@router.delete("/block-types/{block_type_id}")
def delete_training_block_type(
    block_type_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Delete a training block type"""
    success = crud.delete_training_block_type(db, block_type_id)
    if not success:
        raise HTTPException(status_code=404, detail="Training block type not found")
    return {"message": "Training block type deleted successfully"}


# Session Templates
@router.get("/session-templates", response_model=List[schemas.SessionTemplateOut])
def get_session_templates(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get session templates (trainer's + public templates)"""
    user_id = payload.get("user_id")
    # Get trainer_id from user_id
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    if not trainer:
        raise HTTPException(status_code=404, detail="User is not a trainer")

    return crud.get_session_templates(db, trainer_id=trainer.id, skip=skip, limit=limit)


@router.post(
    "/session-templates", response_model=schemas.SessionTemplateOut, status_code=201
)
def create_session_template(
    template: schemas.SessionTemplateCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Create a new session template"""
    user_id = payload.get("user_id")
    return crud.create_session_template(db, template, user_id)


@router.get(
    "/session-templates/{template_id}", response_model=schemas.SessionTemplateOut
)
def get_session_template(
    template_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get a specific session template"""
    template = crud.get_session_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Session template not found")
    return template


@router.put(
    "/session-templates/{template_id}", response_model=schemas.SessionTemplateOut
)
def update_session_template(
    template_id: int,
    template: schemas.SessionTemplateUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Update a session template"""
    updated_template = crud.update_session_template(db, template_id, template)
    if not updated_template:
        raise HTTPException(status_code=404, detail="Session template not found")
    return updated_template


@router.delete("/session-templates/{template_id}")
def delete_session_template(
    template_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Delete a session template"""
    success = crud.delete_session_template(db, template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session template not found")
    return {"message": "Session template deleted successfully"}


@router.post("/session-templates/{template_id}/use")
def use_session_template(
    template_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Increment usage count for a session template"""
    template = crud.increment_template_usage(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Session template not found")
    return {
        "message": "Template usage incremented",
        "usage_count": template.usage_count,
    }


# Session Blocks
@router.get(
    "/sessions/{session_id}/blocks", response_model=List[schemas.SessionBlockOut]
)
def get_session_blocks(
    session_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get all blocks for a training session"""
    return crud.get_session_blocks(db, session_id)


@router.post(
    "/sessions/{session_id}/blocks",
    response_model=schemas.SessionBlockOut,
    status_code=201,
)
def create_session_block(
    session_id: int,
    block: schemas.SessionBlockCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Create a new session block"""
    return crud.create_session_block(db, block, session_id)


@router.get("/blocks/{block_id}", response_model=schemas.SessionBlockOut)
def get_session_block(
    block_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get a specific session block"""
    block = crud.get_session_block(db, block_id)
    if not block:
        raise HTTPException(status_code=404, detail="Session block not found")
    return block


@router.put("/blocks/{block_id}", response_model=schemas.SessionBlockOut)
def update_session_block(
    block_id: int,
    block: schemas.SessionBlockUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Update a session block"""
    updated_block = crud.update_session_block(db, block_id, block)
    if not updated_block:
        raise HTTPException(status_code=404, detail="Session block not found")
    return updated_block


@router.delete("/blocks/{block_id}")
def delete_session_block(
    block_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Delete a session block"""
    success = crud.delete_session_block(db, block_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session block not found")
    return {"message": "Session block deleted successfully"}


# Session Block Exercises
@router.get(
    "/blocks/{block_id}/exercises", response_model=List[schemas.SessionBlockExerciseOut]
)
def get_session_block_exercises(
    block_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get all exercises for a session block"""
    return crud.get_session_block_exercises(db, block_id)


@router.post(
    "/blocks/{block_id}/exercises",
    response_model=schemas.SessionBlockExerciseOut,
    status_code=201,
)
def create_session_block_exercise(
    block_id: int,
    exercise: schemas.SessionBlockExerciseCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Create a new session block exercise"""
    return crud.create_session_block_exercise(db, exercise, block_id)


@router.get(
    "/block-exercises/{exercise_id}", response_model=schemas.SessionBlockExerciseOut
)
def get_session_block_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get a specific session block exercise"""
    exercise = crud.get_session_block_exercise(db, exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Session block exercise not found")
    return exercise


@router.put(
    "/block-exercises/{exercise_id}", response_model=schemas.SessionBlockExerciseOut
)
def update_session_block_exercise(
    exercise_id: int,
    exercise: schemas.SessionBlockExerciseUpdate,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Update a session block exercise"""
    updated_exercise = crud.update_session_block_exercise(db, exercise_id, exercise)
    if not updated_exercise:
        raise HTTPException(status_code=404, detail="Session block exercise not found")
    return updated_exercise


@router.delete("/block-exercises/{exercise_id}")
def delete_session_block_exercise(
    exercise_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Delete a session block exercise"""
    success = crud.delete_session_block_exercise(db, exercise_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session block exercise not found")
    return {"message": "Session block exercise deleted successfully"}


# Session Summary
@router.get("/sessions/{session_id}/summary", response_model=schemas.SessionSummaryOut)
def get_session_summary(
    session_id: int,
    db: Session = Depends(get_db),
    payload: dict = Depends(require_trainer_or_admin),
):
    """Get session summary with totals and metrics"""
    summary = crud.calculate_session_summary(db, session_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Training session not found")
    return summary
