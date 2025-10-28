from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    get_current_payload,
    require_client_visible_to_self_trainer_or_admin,
    require_trainer_or_admin,
    require_visible_for_optional_client_id,
)
from ..db.session import get_db

router = APIRouter()


# Training Sessions
@router.post(
    "/",
    response_model=schemas.TrainingSessionOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_training_session(
    session: schemas.TrainingSessionCreate, db: Session = Depends(get_db)
):
    """Create a new training session"""
    return crud.create_training_session(db=db, session_data=session)


@router.get(
    "/",
    response_model=List[schemas.TrainingSessionOut],
    dependencies=[Depends(require_visible_for_optional_client_id)],
)
def get_training_sessions(
    microcycle_id: int = Query(None, description="Filter by microcycle ID"),
    client_id: int = Query(None, description="Filter by client ID"),
    trainer_id: int = Query(None, description="Filter by trainer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get training sessions with optional filtering"""
    if microcycle_id:
        return crud.get_training_sessions_by_microcycle(
            db=db, microcycle_id=microcycle_id, skip=skip, limit=limit
        )
    elif client_id:
        return crud.get_training_sessions_by_client(
            db=db, client_id=client_id, skip=skip, limit=limit
        )
    elif trainer_id:
        return crud.get_training_sessions_by_trainer(
            db=db, trainer_id=trainer_id, skip=skip, limit=limit
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="Must specify microcycle_id, client_id, or trainer_id",
        )


@router.get(
    "/{session_id}",
    response_model=schemas.TrainingSessionOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific training session"""
    session = crud.get_training_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Training session not found")
    return session


@router.put(
    "/{session_id}",
    response_model=schemas.TrainingSessionOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_training_session(
    session_id: int,
    session: schemas.TrainingSessionUpdate,
    db: Session = Depends(get_db),
):
    """Update a training session"""
    updated_session = crud.update_training_session(
        db=db, session_id=session_id, session_data=session
    )
    if not updated_session:
        raise HTTPException(status_code=404, detail="Training session not found")
    return updated_session


@router.delete("/{session_id}", dependencies=[Depends(require_trainer_or_admin)])
def delete_training_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a training session"""
    success = crud.delete_training_session(db=db, session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Training session not found")
    return {"message": "Training session deleted successfully"}


# Session Exercises
@router.post(
    "/{session_id}/exercises",
    response_model=schemas.SessionExerciseOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_session_exercise(
    session_id: int,
    exercise: schemas.SessionExerciseCreate,
    db: Session = Depends(get_db),
):
    """Add an exercise to a training session"""
    exercise.training_session_id = session_id
    return crud.create_session_exercise(db=db, exercise_data=exercise)


@router.get(
    "/{session_id}/exercises",
    response_model=List[schemas.SessionExerciseOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_session_exercises(
    session_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercises for a training session"""
    return crud.get_session_exercises_by_session(
        db=db, session_id=session_id, skip=skip, limit=limit
    )


@router.get(
    "/exercises/{exercise_id}",
    response_model=schemas.SessionExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_session_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Get a specific session exercise"""
    exercise = crud.get_session_exercise(db=db, exercise_id=exercise_id)
    if not exercise:
        raise HTTPException(status_code=404, detail="Session exercise not found")
    return exercise


@router.put(
    "/exercises/{exercise_id}",
    response_model=schemas.SessionExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_session_exercise(
    exercise_id: int,
    exercise: schemas.SessionExerciseUpdate,
    db: Session = Depends(get_db),
):
    """Update a session exercise"""
    updated_exercise = crud.update_session_exercise(
        db=db, exercise_id=exercise_id, exercise_data=exercise
    )
    if not updated_exercise:
        raise HTTPException(status_code=404, detail="Session exercise not found")
    return updated_exercise


@router.delete(
    "/exercises/{exercise_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_session_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Delete a session exercise"""
    success = crud.delete_session_exercise(db=db, exercise_id=exercise_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session exercise not found")
    return {"message": "Session exercise deleted successfully"}


# Client Feedback
@router.post(
    "/{session_id}/feedback", response_model=schemas.ClientFeedbackOut, status_code=201
)
def create_client_feedback(
    session_id: int,
    feedback: schemas.ClientFeedbackCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    """Create client feedback for a training session"""
    feedback.training_session_id = session_id
    # Enforce that only the athlete themselves (or linked trainer/admin) can submit
    require_client_visible_to_self_trainer_or_admin(
        client_id=feedback.client_id, db=db, payload=payload
    )
    return crud.create_client_feedback(db=db, feedback_data=feedback)


@router.get(
    "/{session_id}/feedback",
    response_model=schemas.ClientFeedbackOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_session_feedback(session_id: int, db: Session = Depends(get_db)):
    """Get client feedback for a training session"""
    feedback = crud.get_client_feedback_by_session(db=db, session_id=session_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Client feedback not found")
    return feedback


@router.get(
    "/feedback/client/{client_id}",
    response_model=List[schemas.ClientFeedbackOut],
    dependencies=[Depends(require_client_visible_to_self_trainer_or_admin)],
)
def get_client_feedback_history(
    client_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get feedback history for a client"""
    return crud.get_client_feedback_by_client(
        db=db, client_id=client_id, skip=skip, limit=limit
    )


@router.get(
    "/feedback/{feedback_id}",
    response_model=schemas.ClientFeedbackOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_client_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Get a specific client feedback"""
    feedback = crud.get_client_feedback(db=db, feedback_id=feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Client feedback not found")
    return feedback


@router.put(
    "/feedback/{feedback_id}",
    response_model=schemas.ClientFeedbackOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_client_feedback(
    feedback_id: int,
    feedback: schemas.ClientFeedbackUpdate,
    db: Session = Depends(get_db),
):
    """Update client feedback"""
    updated_feedback = crud.update_client_feedback(
        db=db, feedback_id=feedback_id, feedback_data=feedback
    )
    if not updated_feedback:
        raise HTTPException(status_code=404, detail="Client feedback not found")
    return updated_feedback


@router.delete(
    "/feedback/{feedback_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_client_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Delete client feedback"""
    success = crud.delete_client_feedback(db=db, feedback_id=feedback_id)
    if not success:
        raise HTTPException(status_code=404, detail="Client feedback not found")
    return {"message": "Client feedback deleted successfully"}


# Progress Tracking
@router.post("/progress", response_model=schemas.ProgressTrackingOut, status_code=201)
def create_progress_tracking(
    progress: schemas.ProgressTrackingCreate, db: Session = Depends(get_db)
):
    """Create a new progress tracking record"""
    return crud.create_progress_tracking(db=db, tracking_data=progress)


@router.get(
    "/progress/client/{client_id}",
    response_model=List[schemas.ProgressTrackingOut],
    dependencies=[Depends(require_client_visible_to_self_trainer_or_admin)],
)
def get_client_progress(
    client_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get progress tracking for a client"""
    return crud.get_progress_tracking_by_client(
        db=db, client_id=client_id, skip=skip, limit=limit
    )


@router.get(
    "/progress/client/{client_id}/exercise/{exercise_id}",
    response_model=List[schemas.ProgressTrackingOut],
    dependencies=[Depends(require_client_visible_to_self_trainer_or_admin)],
)
def get_exercise_progress(
    client_id: int,
    exercise_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get progress tracking for a specific exercise and client"""
    return crud.get_progress_tracking_by_client_and_exercise(
        db=db, client_id=client_id, exercise_id=exercise_id, skip=skip, limit=limit
    )


@router.get(
    "/progress/{progress_id}",
    response_model=schemas.ProgressTrackingOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_progress_tracking(progress_id: int, db: Session = Depends(get_db)):
    """Get a specific progress tracking record"""
    progress = crud.get_progress_tracking_by_id(db=db, tracking_id=progress_id)
    if not progress:
        raise HTTPException(
            status_code=404, detail="Progress tracking record not found"
        )
    return progress


@router.put(
    "/progress/{progress_id}",
    response_model=schemas.ProgressTrackingOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_progress_tracking(
    progress_id: int,
    progress: schemas.ProgressTrackingUpdate,
    db: Session = Depends(get_db),
):
    """Update a progress tracking record"""
    updated_progress = crud.update_progress_tracking(
        db=db, tracking_id=progress_id, tracking_data=progress
    )
    if not updated_progress:
        raise HTTPException(
            status_code=404, detail="Progress tracking record not found"
        )
    return updated_progress


@router.delete(
    "/progress/{progress_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_progress_tracking(progress_id: int, db: Session = Depends(get_db)):
    """Delete a progress tracking record"""
    success = crud.delete_progress_tracking(db=db, tracking_id=progress_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Progress tracking record not found"
        )
    return {"message": "Progress tracking record deleted successfully"}
