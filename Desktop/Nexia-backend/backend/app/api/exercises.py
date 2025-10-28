from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import require_trainer_or_admin
from ..db.session import get_db

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.post(
    "/",
    response_model=schemas.ExerciseOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise(exercise: schemas.ExerciseCreate, db: Session = Depends(get_db)):
    """Create a new exercise"""
    # Check if exercise_id already exists
    existing_exercise = crud.get_exercise_by_exercise_id(db, exercise.exercise_id)
    if existing_exercise:
        raise HTTPException(
            status_code=400,
            detail=f"Exercise with ID '{exercise.exercise_id}' already exists",
        )

    return crud.create_exercise(db, exercise)


@router.get(
    "/",
    response_model=schemas.ExerciseListResponse,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercises(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    tipo: Optional[str] = Query(None, description="Filter by exercise type"),
    categoria: Optional[str] = Query(None, description="Filter by exercise category"),
    nivel: Optional[str] = Query(None, description="Filter by difficulty level"),
    equipo: Optional[str] = Query(None, description="Filter by equipment"),
    patron_movimiento: Optional[str] = Query(
        None, description="Filter by movement pattern"
    ),
    tipo_carga: Optional[str] = Query(None, description="Filter by load type"),
    search: Optional[str] = Query(
        None, description="Search in exercise names and muscle groups"
    ),
    db: Session = Depends(get_db),
):
    """Get all exercises with optional filtering and search"""
    exercises = crud.get_exercises(
        db=db,
        skip=skip,
        limit=limit,
        tipo=tipo,
        categoria=categoria,
        nivel=nivel,
        equipo=equipo,
        patron_movimiento=patron_movimiento,
        tipo_carga=tipo_carga,
        search=search,
    )

    total = crud.get_exercise_count(
        db=db,
        tipo=tipo,
        categoria=categoria,
        nivel=nivel,
        equipo=equipo,
        patron_movimiento=patron_movimiento,
        tipo_carga=tipo_carga,
        search=search,
    )

    has_more = (skip + limit) < total

    return schemas.ExerciseListResponse(
        exercises=exercises, total=total, skip=skip, limit=limit, has_more=has_more
    )


@router.get(
    "/{exercise_id}",
    response_model=schemas.ExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Get a specific exercise by ID"""
    exercise = crud.get_exercise(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404, detail=f"Exercise with ID {exercise_id} not found"
        )
    return exercise


@router.get(
    "/by-exercise-id/{exercise_id}",
    response_model=schemas.ExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_by_exercise_id(exercise_id: str, db: Session = Depends(get_db)):
    """Get a specific exercise by exercise_id (string identifier)"""
    exercise = crud.get_exercise_by_exercise_id(db, exercise_id)
    if not exercise:
        raise HTTPException(
            status_code=404,
            detail=f"Exercise with exercise_id '{exercise_id}' not found",
        )
    return exercise


@router.put(
    "/{exercise_id}",
    response_model=schemas.ExerciseOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_exercise(
    exercise_id: int, exercise: schemas.ExerciseUpdate, db: Session = Depends(get_db)
):
    """Update an existing exercise"""
    updated_exercise = crud.update_exercise(db, exercise_id, exercise)
    if not updated_exercise:
        raise HTTPException(
            status_code=404, detail=f"Exercise with ID {exercise_id} not found"
        )
    return updated_exercise


@router.delete(
    "/{exercise_id}", status_code=204, dependencies=[Depends(require_trainer_or_admin)]
)
def delete_exercise(exercise_id: int, db: Session = Depends(get_db)):
    """Delete an exercise"""
    success = crud.delete_exercise(db, exercise_id)
    if not success:
        raise HTTPException(
            status_code=404, detail=f"Exercise with ID {exercise_id} not found"
        )
    return None


# Specialized endpoints
@router.get(
    "/by-muscle-group/{muscle_group}",
    response_model=List[schemas.ExerciseOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercises_by_muscle_group(
    muscle_group: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get exercises that target a specific muscle group"""
    exercises = crud.get_exercises_by_muscle_group(db, muscle_group, skip, limit)
    return exercises


@router.get(
    "/by-equipment/{equipment}",
    response_model=List[schemas.ExerciseOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercises_by_equipment(
    equipment: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get exercises that use specific equipment"""
    exercises = crud.get_exercises_by_equipment(db, equipment, skip, limit)
    return exercises


@router.get(
    "/by-level/{level}",
    response_model=List[schemas.ExerciseOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercises_by_level(
    level: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get exercises by difficulty level"""
    exercises = crud.get_exercises_by_level(db, level, skip, limit)
    return exercises


# Statistics endpoint
@router.get("/stats/summary", dependencies=[Depends(require_trainer_or_admin)])
def get_exercise_stats(db: Session = Depends(get_db)):
    """Get exercise statistics"""
    from sqlalchemy import func

    from ..db.models import Exercise

    total_exercises = db.query(func.count(Exercise.id)).scalar()

    # Count by type
    type_counts = (
        db.query(Exercise.tipo, func.count(Exercise.id)).group_by(Exercise.tipo).all()
    )

    # Count by category
    category_counts = (
        db.query(Exercise.categoria, func.count(Exercise.id))
        .group_by(Exercise.categoria)
        .all()
    )

    # Count by level
    level_counts = (
        db.query(Exercise.nivel, func.count(Exercise.id)).group_by(Exercise.nivel).all()
    )

    # Count by equipment
    equipment_counts = (
        db.query(Exercise.equipo, func.count(Exercise.id))
        .group_by(Exercise.equipo)
        .all()
    )

    return {
        "total_exercises": total_exercises,
        "by_type": dict(type_counts),
        "by_category": dict(category_counts),
        "by_level": dict(level_counts),
        "by_equipment": dict(equipment_counts),
    }
