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


@router.post(
    "/",
    response_model=schemas.StandaloneSessionOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_standalone_session(
    session: schemas.StandaloneSessionCreate, db: Session = Depends(get_db)
):
    """Create a new standalone training session"""
    return crud.create_standalone_session(db=db, session_data=session)


@router.get(
    "/",
    response_model=List[schemas.StandaloneSessionOut],
    dependencies=[Depends(require_visible_for_optional_client_id)],
)
def get_standalone_sessions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    client_id: int = Query(None),
    trainer_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """Get standalone sessions with optional filtering"""
    if client_id:
        return crud.get_standalone_sessions_by_client(
            db=db, client_id=client_id, skip=skip, limit=limit
        )
    elif trainer_id:
        return crud.get_standalone_sessions_by_trainer(
            db=db, trainer_id=trainer_id, skip=skip, limit=limit
        )
    else:
        # Return all sessions (you might want to add a general get function)
        raise HTTPException(
            status_code=400, detail="Must specify either client_id or trainer_id"
        )


@router.get(
    "/{session_id}",
    response_model=schemas.StandaloneSessionOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_standalone_session(session_id: int, db: Session = Depends(get_db)):
    """Get a specific standalone session by ID"""
    session = crud.get_standalone_session(db=db, session_id=session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Standalone session not found")
    return session


@router.put(
    "/{session_id}",
    response_model=schemas.StandaloneSessionOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_standalone_session(
    session_id: int,
    session: schemas.StandaloneSessionUpdate,
    db: Session = Depends(get_db),
):
    """Update a standalone session"""
    updated_session = crud.update_standalone_session(
        db=db, session_id=session_id, session_data=session
    )
    if not updated_session:
        raise HTTPException(status_code=404, detail="Standalone session not found")
    return updated_session


@router.delete("/{session_id}", dependencies=[Depends(require_trainer_or_admin)])
def delete_standalone_session(session_id: int, db: Session = Depends(get_db)):
    """Delete a standalone session"""
    success = crud.delete_standalone_session(db=db, session_id=session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Standalone session not found")
    return {"message": "Standalone session deleted successfully"}


# Standalone Session Exercises
@router.post(
    "/{session_id}/exercises",
    response_model=schemas.StandaloneSessionExerciseOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def add_exercise_to_standalone_session(
    session_id: int,
    exercise: schemas.StandaloneSessionExerciseCreate,
    db: Session = Depends(get_db),
):
    """Add an exercise to a standalone session"""
    return crud.create_standalone_session_exercise(
        db=db, exercise_data=exercise, session_id=session_id
    )


@router.get(
    "/{session_id}/exercises",
    response_model=List[schemas.StandaloneSessionExerciseOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_standalone_session_exercises(
    session_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercises for a standalone session"""
    return crud.get_standalone_session_exercises_by_session(
        db=db, session_id=session_id, skip=skip, limit=limit
    )


@router.get(
    "/exercises/{exercise_id}",
    response_model=schemas.StandaloneSessionExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_standalone_session_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Get a specific standalone session exercise by ID"""
    exercise = crud.get_standalone_session_exercise(db=db, exercise_id=exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404, detail="Standalone session exercise not found"
        )
    return exercise


@router.put(
    "/exercises/{exercise_id}",
    response_model=schemas.StandaloneSessionExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_standalone_session_exercise(
    exercise_id: int,
    exercise: schemas.StandaloneSessionExerciseUpdate,
    db: Session = Depends(get_db),
):
    """Update a standalone session exercise"""
    updated_exercise = crud.update_standalone_session_exercise(
        db=db, exercise_id=exercise_id, exercise_data=exercise
    )
    if not updated_exercise:
        raise HTTPException(
            status_code=404, detail="Standalone session exercise not found"
        )
    return updated_exercise


@router.delete(
    "/exercises/{exercise_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_standalone_session_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Delete a standalone session exercise"""
    success = crud.delete_standalone_session_exercise(db=db, exercise_id=exercise_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Standalone session exercise not found"
        )
    return {"message": "Standalone session exercise deleted successfully"}


# Standalone Session Feedback
@router.post(
    "/{session_id}/feedback",
    response_model=schemas.StandaloneSessionFeedbackOut,
    status_code=201,
)
def add_feedback_to_standalone_session(
    session_id: int,
    feedback: schemas.StandaloneSessionFeedbackCreate,
    db: Session = Depends(get_db),
    payload: dict = Depends(get_current_payload),
):
    """Add feedback to a standalone session"""
    # Enforce that only the athlete themselves (or linked trainer/admin) can submit
    require_client_visible_to_self_trainer_or_admin(
        client_id=feedback.client_id, db=db, payload=payload
    )
    feedback.standalone_session_id = session_id
    return crud.create_standalone_session_feedback(db=db, feedback_data=feedback)


@router.get(
    "/{session_id}/feedback",
    response_model=schemas.StandaloneSessionFeedbackOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_standalone_session_feedback(session_id: int, db: Session = Depends(get_db)):
    """Get feedback for a standalone session"""
    feedback = crud.get_standalone_session_feedback_by_session(
        db=db, session_id=session_id
    )
    if not feedback:
        raise HTTPException(
            status_code=404, detail="Standalone session feedback not found"
        )
    return feedback


@router.put(
    "/feedback/{feedback_id}",
    response_model=schemas.StandaloneSessionFeedbackOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_standalone_session_feedback(
    feedback_id: int,
    feedback: schemas.StandaloneSessionFeedbackUpdate,
    db: Session = Depends(get_db),
):
    """Update standalone session feedback"""
    updated_feedback = crud.update_standalone_session_feedback(
        db=db, feedback_id=feedback_id, feedback_data=feedback
    )
    if not updated_feedback:
        raise HTTPException(
            status_code=404, detail="Standalone session feedback not found"
        )
    return updated_feedback


@router.delete(
    "/feedback/{feedback_id}", dependencies=[Depends(require_trainer_or_admin)]
)
def delete_standalone_session_feedback(feedback_id: int, db: Session = Depends(get_db)):
    """Delete standalone session feedback"""
    success = crud.delete_standalone_session_feedback(db=db, feedback_id=feedback_id)
    if not success:
        raise HTTPException(
            status_code=404, detail="Standalone session feedback not found"
        )
    return {"message": "Standalone session feedback deleted successfully"}
