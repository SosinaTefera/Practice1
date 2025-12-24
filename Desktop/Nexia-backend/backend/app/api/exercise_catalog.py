"""
API endpoints for exercise catalog tables (Excel structure).
Includes: Movement Patterns, Muscle Groups, Equipment, Tags,
Exercise Variants, and Mappings.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import require_trainer_or_admin
from ..db.session import get_db

router = APIRouter(prefix="/exercise-catalog", tags=["exercise-catalog"])


# =============================================================================
# MOVEMENT PATTERNS
# =============================================================================


@router.post(
    "/movement-patterns/",
    response_model=schemas.MovementPatternOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_movement_pattern(
    pattern: schemas.MovementPatternCreate, db: Session = Depends(get_db)
):
    """Create a new movement pattern"""
    return crud.create_movement_pattern(db, pattern)


@router.get(
    "/movement-patterns/",
    response_model=List[schemas.MovementPatternOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_movement_patterns(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all movement patterns"""
    return crud.get_movement_patterns(db, skip=skip, limit=limit, is_active=is_active)


@router.get(
    "/movement-patterns/{pattern_id}",
    response_model=schemas.MovementPatternOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_movement_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Get a specific movement pattern"""
    pattern = crud.get_movement_pattern(db, pattern_id)
    if not pattern:
        raise HTTPException(status_code=404, detail="Movement pattern not found")
    return pattern


@router.put(
    "/movement-patterns/{pattern_id}",
    response_model=schemas.MovementPatternOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_movement_pattern(
    pattern_id: int,
    pattern: schemas.MovementPatternUpdate,
    db: Session = Depends(get_db),
):
    """Update a movement pattern"""
    updated_pattern = crud.update_movement_pattern(db, pattern_id, pattern)
    if not updated_pattern:
        raise HTTPException(status_code=404, detail="Movement pattern not found")
    return updated_pattern


@router.delete(
    "/movement-patterns/{pattern_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_movement_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) a movement pattern"""
    success = crud.delete_movement_pattern(db, pattern_id)
    if not success:
        raise HTTPException(status_code=404, detail="Movement pattern not found")
    return {"message": "Movement pattern deleted successfully"}


# =============================================================================
# MUSCLE GROUPS
# =============================================================================


@router.post(
    "/muscle-groups/",
    response_model=schemas.MuscleGroupOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_muscle_group(
    group: schemas.MuscleGroupCreate, db: Session = Depends(get_db)
):
    """Create a new muscle group"""
    return crud.create_muscle_group(db, group)


@router.get(
    "/muscle-groups/",
    response_model=List[schemas.MuscleGroupOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_muscle_groups(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all muscle groups"""
    return crud.get_muscle_groups(db, skip=skip, limit=limit, is_active=is_active)


@router.get(
    "/muscle-groups/{group_id}",
    response_model=schemas.MuscleGroupOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_muscle_group(group_id: int, db: Session = Depends(get_db)):
    """Get a specific muscle group"""
    group = crud.get_muscle_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Muscle group not found")
    return group


@router.put(
    "/muscle-groups/{group_id}",
    response_model=schemas.MuscleGroupOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_muscle_group(
    group_id: int, group: schemas.MuscleGroupUpdate, db: Session = Depends(get_db)
):
    """Update a muscle group"""
    updated_group = crud.update_muscle_group(db, group_id, group)
    if not updated_group:
        raise HTTPException(status_code=404, detail="Muscle group not found")
    return updated_group


@router.delete(
    "/muscle-groups/{group_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_muscle_group(group_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) a muscle group"""
    success = crud.delete_muscle_group(db, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Muscle group not found")
    return {"message": "Muscle group deleted successfully"}


# =============================================================================
# EQUIPMENT
# =============================================================================


@router.post(
    "/equipment/",
    response_model=schemas.EquipmentOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_equipment(equipment: schemas.EquipmentCreate, db: Session = Depends(get_db)):
    """Create a new equipment"""
    return crud.create_equipment(db, equipment)


@router.get(
    "/equipment/",
    response_model=List[schemas.EquipmentOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_equipment_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all equipment"""
    return crud.get_equipment_list(db, skip=skip, limit=limit, is_active=is_active)


@router.get(
    "/equipment/{equipment_id}",
    response_model=schemas.EquipmentOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Get a specific equipment"""
    equipment = crud.get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return equipment


@router.put(
    "/equipment/{equipment_id}",
    response_model=schemas.EquipmentOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_equipment(
    equipment_id: int,
    equipment: schemas.EquipmentUpdate,
    db: Session = Depends(get_db),
):
    """Update an equipment"""
    updated_equipment = crud.update_equipment(db, equipment_id, equipment)
    if not updated_equipment:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return updated_equipment


@router.delete(
    "/equipment/{equipment_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_equipment(equipment_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) an equipment"""
    success = crud.delete_equipment(db, equipment_id)
    if not success:
        raise HTTPException(status_code=404, detail="Equipment not found")
    return {"message": "Equipment deleted successfully"}


# =============================================================================
# TAGS
# =============================================================================


@router.post(
    "/tags/",
    response_model=schemas.TagOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_tag(tag: schemas.TagCreate, db: Session = Depends(get_db)):
    """Create a new tag"""
    return crud.create_tag(db, tag)


@router.get(
    "/tags/",
    response_model=List[schemas.TagOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_tags(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all tags"""
    return crud.get_tags(
        db, skip=skip, limit=limit, category=category, is_active=is_active
    )


@router.get(
    "/tags/{tag_id}",
    response_model=schemas.TagOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_tag(tag_id: int, db: Session = Depends(get_db)):
    """Get a specific tag"""
    tag = crud.get_tag(db, tag_id)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.put(
    "/tags/{tag_id}",
    response_model=schemas.TagOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_tag(tag_id: int, tag: schemas.TagUpdate, db: Session = Depends(get_db)):
    """Update a tag"""
    updated_tag = crud.update_tag(db, tag_id, tag)
    if not updated_tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return updated_tag


@router.delete(
    "/tags/{tag_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_tag(tag_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) a tag"""
    success = crud.delete_tag(db, tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found")
    return {"message": "Tag deleted successfully"}


# =============================================================================
# ACTIONS (Joint Movements - Independent)
# =============================================================================


@router.post(
    "/actions/",
    response_model=schemas.JointMovementOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_action(action: schemas.JointMovementCreate, db: Session = Depends(get_db)):
    """Create a new action (joint movement) - now independent entity"""
    from ..db import models

    db_action = models.JointMovement(
        name=action.name,
        name_en=action.name_en,
        name_es=action.name_es,
    )
    db.add(db_action)
    db.commit()
    db.refresh(db_action)
    return db_action


@router.get(
    "/actions/",
    response_model=List[schemas.JointMovementOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_actions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all actions (joint movements) - independent entities"""
    from ..db import models

    query = db.query(models.JointMovement)
    if is_active is not None:
        query = query.filter(models.JointMovement.is_active.is_(is_active))
    return query.offset(skip).limit(limit).all()


@router.get(
    "/actions/{action_id}",
    response_model=schemas.JointMovementOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_action(action_id: int, db: Session = Depends(get_db)):
    """Get a specific action (joint movement)"""
    from ..db import models

    action = (
        db.query(models.JointMovement)
        .filter(models.JointMovement.id == action_id)
        .first()
    )
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    return action


@router.put(
    "/actions/{action_id}",
    response_model=schemas.JointMovementOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_action(
    action_id: int,
    action: schemas.JointMovementCreate,
    db: Session = Depends(get_db),
):
    """Update an action (joint movement)"""
    from ..db import models

    db_action = (
        db.query(models.JointMovement)
        .filter(models.JointMovement.id == action_id)
        .first()
    )
    if not db_action:
        raise HTTPException(status_code=404, detail="Action not found")

    db_action.name = action.name
    db_action.name_en = action.name_en
    db_action.name_es = action.name_es

    db.commit()
    db.refresh(db_action)
    return db_action


@router.delete(
    "/actions/{action_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_action(action_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) an action"""
    from ..db import models

    db_action = (
        db.query(models.JointMovement)
        .filter(models.JointMovement.id == action_id)
        .first()
    )
    if not db_action:
        raise HTTPException(status_code=404, detail="Action not found")

    db_action.is_active = False
    db.commit()
    return {"message": "Action deleted successfully"}


# =============================================================================
# EXERCISE VARIANTS
# =============================================================================


@router.post(
    "/variants/",
    response_model=schemas.ExerciseVariantOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise_variant(
    variant: schemas.ExerciseVariantCreate, db: Session = Depends(get_db)
):
    """Create a new exercise variant"""
    return crud.create_exercise_variant(db, variant)


@router.get(
    "/variants/",
    response_model=List[schemas.ExerciseVariantOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_variants(
    base_exercise_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """Get all exercise variants"""
    return crud.get_exercise_variants(
        db,
        base_exercise_id=base_exercise_id,
        skip=skip,
        limit=limit,
        is_active=is_active,
    )


@router.get(
    "/variants/{variant_id}",
    response_model=schemas.ExerciseVariantOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_variant(variant_id: int, db: Session = Depends(get_db)):
    """Get a specific exercise variant"""
    variant = crud.get_exercise_variant(db, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Exercise variant not found")
    return variant


@router.put(
    "/variants/{variant_id}",
    response_model=schemas.ExerciseVariantOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_exercise_variant(
    variant_id: int,
    variant: schemas.ExerciseVariantUpdate,
    db: Session = Depends(get_db),
):
    """Update an exercise variant"""
    updated_variant = crud.update_exercise_variant(db, variant_id, variant)
    if not updated_variant:
        raise HTTPException(status_code=404, detail="Exercise variant not found")
    return updated_variant


@router.delete(
    "/variants/{variant_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_exercise_variant(variant_id: int, db: Session = Depends(get_db)):
    """Delete (soft delete) an exercise variant"""
    success = crud.delete_exercise_variant(db, variant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Exercise variant not found")
    return {"message": "Exercise variant deleted successfully"}


# =============================================================================
# EXERCISE MAPPINGS
# =============================================================================


@router.post(
    "/exercises/{exercise_id}/movement-patterns/",
    response_model=schemas.ExerciseMovementPatternOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise_movement_pattern(
    exercise_id: int,
    mapping: schemas.ExerciseMovementPatternCreate,
    db: Session = Depends(get_db),
):
    """Create exercise to movement pattern mapping"""
    if mapping.exercise_id != exercise_id:
        raise HTTPException(
            status_code=422, detail="exercise_id in body must match path parameter"
        )
    return crud.create_exercise_movement_pattern(db, mapping)


@router.get(
    "/exercises/{exercise_id}/movement-patterns/",
    response_model=List[schemas.ExerciseMovementPatternOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_movement_patterns(exercise_id: int, db: Session = Depends(get_db)):
    """Get movement patterns for an exercise"""
    return crud.get_exercise_movement_patterns(db, exercise_id=exercise_id)


@router.post(
    "/exercises/{exercise_id}/muscles/",
    response_model=schemas.ExerciseMuscleOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise_muscle(
    exercise_id: int,
    mapping: schemas.ExerciseMuscleCreate,
    db: Session = Depends(get_db),
):
    """Create exercise to muscle mapping"""
    if mapping.exercise_id != exercise_id:
        raise HTTPException(
            status_code=422, detail="exercise_id in body must match path parameter"
        )
    return crud.create_exercise_muscle(db, mapping)


@router.get(
    "/exercises/{exercise_id}/muscles/",
    response_model=List[schemas.ExerciseMuscleOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_muscles(exercise_id: int, db: Session = Depends(get_db)):
    """Get muscles for an exercise"""
    return crud.get_exercise_muscles(db, exercise_id=exercise_id)


@router.post(
    "/exercises/{exercise_id}/equipment/",
    response_model=schemas.ExerciseEquipmentOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise_equipment(
    exercise_id: int,
    mapping: schemas.ExerciseEquipmentCreate,
    db: Session = Depends(get_db),
):
    """Create exercise to equipment mapping"""
    if mapping.exercise_id != exercise_id:
        raise HTTPException(
            status_code=422, detail="exercise_id in body must match path parameter"
        )
    return crud.create_exercise_equipment(db, mapping)


@router.get(
    "/exercises/{exercise_id}/equipment/",
    response_model=List[schemas.ExerciseEquipmentOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_equipment_list(exercise_id: int, db: Session = Depends(get_db)):
    """Get equipment for an exercise"""
    return crud.get_exercise_equipment_list(db, exercise_id=exercise_id)


@router.post(
    "/exercises/{exercise_id}/tags/",
    response_model=schemas.ExerciseTagOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_exercise_tag(
    exercise_id: int, mapping: schemas.ExerciseTagCreate, db: Session = Depends(get_db)
):
    """Create exercise to tag mapping"""
    if mapping.exercise_id != exercise_id:
        raise HTTPException(
            status_code=422, detail="exercise_id in body must match path parameter"
        )
    return crud.create_exercise_tag(db, mapping)


@router.get(
    "/exercises/{exercise_id}/tags/",
    response_model=List[schemas.ExerciseTagOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_exercise_tags(exercise_id: int, db: Session = Depends(get_db)):
    """Get tags for an exercise"""
    return crud.get_exercise_tags(db, exercise_id=exercise_id)


# =============================================================================
# STANDALONE MAPPING ENDPOINTS (for bulk operations and testing)
# =============================================================================


@router.get(
    "/exercise-movement-patterns/",
    response_model=List[schemas.ExerciseMovementPatternOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_all_exercise_movement_patterns(
    exercise_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercise-movement pattern mappings"""
    if exercise_id:
        return crud.get_exercise_movement_patterns(db, exercise_id=exercise_id)
    # Get all mappings
    from ..db import models

    return (
        db.query(models.ExerciseMovementPattern)
        .filter(models.ExerciseMovementPattern.is_active.is_(True))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/exercise-muscles/",
    response_model=List[schemas.ExerciseMuscleOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_all_exercise_muscles(
    exercise_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercise-muscle mappings"""
    if exercise_id:
        return crud.get_exercise_muscles(db, exercise_id=exercise_id)
    # Get all mappings
    from ..db import models

    return (
        db.query(models.ExerciseMuscle)
        .filter(models.ExerciseMuscle.is_active.is_(True))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/exercise-equipment/",
    response_model=List[schemas.ExerciseEquipmentOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_all_exercise_equipment(
    exercise_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercise-equipment mappings"""
    if exercise_id:
        return crud.get_exercise_equipment_list(db, exercise_id=exercise_id)
    # Get all mappings
    from ..db import models

    return (
        db.query(models.ExerciseEquipment)
        .filter(models.ExerciseEquipment.is_active.is_(True))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get(
    "/exercise-tags/",
    response_model=List[schemas.ExerciseTagOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_all_exercise_tags(
    exercise_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all exercise-tag mappings"""
    if exercise_id:
        return crud.get_exercise_tags(db, exercise_id=exercise_id)
    # Get all mappings
    from ..db import models

    return (
        db.query(models.ExerciseTag)
        .filter(models.ExerciseTag.is_active.is_(True))
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.delete(
    "/mappings/{mapping_type}/{mapping_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_exercise_mapping(
    mapping_type: str, mapping_id: int, db: Session = Depends(get_db)
):
    """Delete an exercise mapping (movement_pattern, muscle, equipment, or tag)"""
    success = crud.delete_exercise_mapping(db, mapping_id, mapping_type)
    if not success:
        raise HTTPException(status_code=404, detail="Mapping not found")
    return {"message": "Mapping deleted successfully"}


# =============================================================================
# VARIANT MAPPING ENDPOINTS
# =============================================================================


@router.post(
    "/variant-equipment/",
    response_model=schemas.VariantEquipmentOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_variant_equipment(
    mapping: schemas.VariantEquipmentCreate, db: Session = Depends(get_db)
):
    """Create variant to equipment mapping"""
    return crud.create_variant_equipment(db, mapping)


@router.get(
    "/variant-equipment/",
    response_model=List[schemas.VariantEquipmentOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_variant_equipment(
    variant_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get variant to equipment mappings"""
    return crud.get_variant_equipment(db, variant_id=variant_id, skip=skip, limit=limit)


@router.post(
    "/variant-joint-actions/",
    response_model=schemas.VariantJointActionOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_variant_joint_action(
    mapping: schemas.VariantJointActionCreate, db: Session = Depends(get_db)
):
    """Create variant to joint action mapping"""
    return crud.create_variant_joint_action(db, mapping)


@router.get(
    "/variant-joint-actions/",
    response_model=List[schemas.VariantJointActionOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_variant_joint_actions(
    variant_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get variant to joint action mappings"""
    return crud.get_variant_joint_actions(
        db, variant_id=variant_id, skip=skip, limit=limit
    )
