from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    require_trainer_or_admin,
    require_visible_for_optional_client_id,
)
from ..db import models
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
    "/with-cycles",
    response_model=schemas.PlansWithCyclesResponse,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_plans_with_cycles(
    trainer_id: int = Query(..., description="Trainer ID to fetch plans for"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Return all training plans for a trainer with their macro/meso/micro cycles."""
    plans = crud.get_training_plans_by_trainer(
        db=db, trainer_id=trainer_id, skip=skip, limit=limit
    )
    if not plans:
        return {"items": []}

    plan_ids = [p.id for p in plans]

    macrocycles = (
        db.query(models.Macrocycle)
        .filter(
            models.Macrocycle.training_plan_id.in_(plan_ids),
            models.Macrocycle.is_active.is_(True),
        )
        .all()
    )
    macro_ids = [m.id for m in macrocycles]

    mesocycles = (
        db.query(models.Mesocycle)
        .filter(
            models.Mesocycle.macrocycle_id.in_(macro_ids),
            models.Mesocycle.is_active.is_(True),
        )
        .all()
        if macro_ids
        else []
    )
    meso_ids = [m.id for m in mesocycles]

    microcycles = (
        db.query(models.Microcycle)
        .filter(
            models.Microcycle.mesocycle_id.in_(meso_ids),
            models.Microcycle.is_active.is_(True),
        )
        .all()
        if meso_ids
        else []
    )

    macros_by_plan = {pid: [] for pid in plan_ids}
    for mc in macrocycles:
        macros_by_plan.setdefault(mc.training_plan_id, []).append(mc)

    mesos_by_macro = {mid: [] for mid in macro_ids}
    for ms in mesocycles:
        mesos_by_macro.setdefault(ms.macrocycle_id, []).append(ms)

    micros_by_meso = {mid: [] for mid in meso_ids}
    for mi in microcycles:
        micros_by_meso.setdefault(mi.mesocycle_id, []).append(mi)

    items = []
    for p in plans:
        plan_macros = macros_by_plan.get(p.id, [])
        plan_meso = []
        for mc in plan_macros:
            plan_meso.extend(mesos_by_macro.get(mc.id, []))
        plan_micro = []
        for ms in plan_meso:
            plan_micro.extend(micros_by_meso.get(ms.id, []))
        items.append(
            schemas.PlanWithCycles(
                plan=p,
                macrocycles=plan_macros,
                mesocycles=plan_meso,
                microcycles=plan_micro,
            )
        )

    return {"items": items}


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


@router.get(
    "/{plan_id}/all-cycles",
    response_model=schemas.AllCyclesResponse,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_all_cycles(plan_id: int, db: Session = Depends(get_db)):
    """Return all active cycles (macro, meso, micro) for a plan in one response."""
    # Ensure plan exists and is active
    plan = (
        db.query(models.TrainingPlan)
        .filter(
            models.TrainingPlan.id == plan_id, models.TrainingPlan.is_active.is_(True)
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    macrocycles = (
        db.query(models.Macrocycle)
        .filter(
            models.Macrocycle.training_plan_id == plan_id,
            models.Macrocycle.is_active.is_(True),
        )
        .all()
    )

    macro_ids = [m.id for m in macrocycles]
    mesocycles = (
        db.query(models.Mesocycle)
        .filter(
            models.Mesocycle.macrocycle_id.in_(macro_ids),
            models.Mesocycle.is_active.is_(True),
        )
        .all()
        if macro_ids
        else []
    )

    meso_ids = [m.id for m in mesocycles]
    microcycles = (
        db.query(models.Microcycle)
        .filter(
            models.Microcycle.mesocycle_id.in_(meso_ids),
            models.Microcycle.is_active.is_(True),
        )
        .all()
        if meso_ids
        else []
    )

    return schemas.AllCyclesResponse(
        macrocycles=macrocycles, mesocycles=mesocycles, microcycles=microcycles
    )


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
    # Validate optional body parent id against path
    if mesocycle.macrocycle_id is not None and mesocycle.macrocycle_id != macrocycle_id:
        raise HTTPException(
            status_code=422,
            detail="macrocycle_id in body must match path parameter",
        )
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
    # Validate optional body parent id against path
    if microcycle.mesocycle_id is not None and microcycle.mesocycle_id != mesocycle_id:
        raise HTTPException(
            status_code=422,
            detail="mesocycle_id in body must match path parameter",
        )
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


# Milestone endpoints
@router.post(
    "/{plan_id}/milestones",
    response_model=schemas.MilestoneOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_milestone(
    plan_id: int,
    milestone: schemas.MilestoneCreate,
    db: Session = Depends(get_db),
):
    """Create a new milestone for a training plan"""
    # Validate plan exists
    plan = (
        db.query(models.TrainingPlan)
        .filter(
            models.TrainingPlan.id == plan_id, models.TrainingPlan.is_active.is_(True)
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    # Validate optional body parent id against path
    if milestone.training_plan_id is not None and milestone.training_plan_id != plan_id:
        raise HTTPException(
            status_code=422, detail="training_plan_id in body must match path parameter"
        )

    return crud.create_milestone(
        db=db, milestone_data=milestone, training_plan_id=plan_id
    )


@router.get(
    "/{plan_id}/milestones",
    response_model=List[schemas.MilestoneOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_milestones(
    plan_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get all milestones for a training plan"""
    # Validate plan exists
    plan = (
        db.query(models.TrainingPlan)
        .filter(
            models.TrainingPlan.id == plan_id, models.TrainingPlan.is_active.is_(True)
        )
        .first()
    )
    if not plan:
        raise HTTPException(status_code=404, detail="Training plan not found")

    return crud.get_milestones_by_plan(
        db=db, training_plan_id=plan_id, skip=skip, limit=limit
    )


@router.get(
    "/milestones/{milestone_id}",
    response_model=schemas.MilestoneOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_milestone(milestone_id: int, db: Session = Depends(get_db)):
    """Get a milestone by ID"""
    milestone = crud.get_milestone(db=db, milestone_id=milestone_id)
    if not milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return milestone


@router.put(
    "/milestones/{milestone_id}",
    response_model=schemas.MilestoneOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_milestone(
    milestone_id: int,
    milestone: schemas.MilestoneUpdate,
    db: Session = Depends(get_db),
):
    """Update a milestone"""
    updated_milestone = crud.update_milestone(
        db=db, milestone_id=milestone_id, milestone_data=milestone
    )
    if not updated_milestone:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return updated_milestone


@router.delete(
    "/milestones/{milestone_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_milestone(milestone_id: int, db: Session = Depends(get_db)):
    """Delete a milestone"""
    success = crud.delete_milestone(db=db, milestone_id=milestone_id)
    if not success:
        raise HTTPException(status_code=404, detail="Milestone not found")
    return {"message": "Milestone deleted successfully"}


# Training Plan Templates
@router.post(
    "/templates/",
    response_model=schemas.TrainingPlanTemplateOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_training_plan_template(
    template: schemas.TrainingPlanTemplateCreate, db: Session = Depends(get_db)
):
    """Create a new training plan template"""
    return crud.create_training_plan_template(db=db, template_data=template)


@router.get(
    "/templates/",
    response_model=List[schemas.TrainingPlanTemplateOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_plan_templates(
    trainer_id: int = Query(..., description="Filter by trainer ID"),
    category: str = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get training plan templates for a trainer"""
    return crud.get_training_plan_templates(
        db=db, trainer_id=trainer_id, category=category, skip=skip, limit=limit
    )


@router.get(
    "/templates/{template_id}",
    response_model=schemas.TrainingPlanTemplateOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_plan_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific training plan template"""
    template = crud.get_training_plan_template(db=db, template_id=template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Training plan template not found")
    return template


@router.put(
    "/templates/{template_id}",
    response_model=schemas.TrainingPlanTemplateOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_training_plan_template(
    template_id: int,
    template: schemas.TrainingPlanTemplateUpdate,
    db: Session = Depends(get_db),
):
    """Update a training plan template"""
    updated_template = crud.update_training_plan_template(
        db=db, template_id=template_id, template_data=template
    )
    if not updated_template:
        raise HTTPException(status_code=404, detail="Training plan template not found")
    return updated_template


@router.delete(
    "/templates/{template_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_training_plan_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a training plan template"""
    success = crud.delete_training_plan_template(db=db, template_id=template_id)
    if not success:
        raise HTTPException(status_code=404, detail="Training plan template not found")
    return {"message": "Training plan template deleted successfully"}


@router.post(
    "/templates/{template_id}/assign",
    response_model=schemas.TrainingPlanInstanceOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def assign_template_to_client(
    template_id: int,
    client_id: int = Query(..., description="Client ID to assign template to"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    trainer_id: int = Query(..., description="Trainer ID"),
    name: str = Query(None, description="Optional custom name for the instance"),
    db: Session = Depends(get_db),
):
    """
    Assign a template to a client (creates instance with all cycles duplicated).
    
    This endpoint:
    - Creates a new TrainingPlanInstance for the client
    - Duplicates all macrocycles, mesocycles, and microcycles from the template
    - Adjusts dates proportionally based on the new start_date/end_date
    - Increments the template's usage_count
    """
    from datetime import datetime as dt
    
    try:
        # Parse dates
        parsed_start_date = dt.strptime(start_date, "%Y-%m-%d").date()
        parsed_end_date = dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )
    
    # Validate dates
    if parsed_start_date >= parsed_end_date:
        raise HTTPException(
            status_code=422, detail="start_date must be before end_date"
        )
    
    try:
        instance = crud.assign_template_to_client(
            db=db,
            template_id=template_id,
            client_id=client_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            trainer_id=trainer_id,
            name=name,
        )
        return instance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning template: {str(e)}")


# Training Plan Instances
@router.post(
    "/instances/",
    response_model=schemas.TrainingPlanInstanceOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def create_training_plan_instance(
    instance: schemas.TrainingPlanInstanceCreate, db: Session = Depends(get_db)
):
    """Create a new training plan instance"""
    return crud.create_training_plan_instance(db=db, instance_data=instance)


@router.get(
    "/instances/",
    response_model=List[schemas.TrainingPlanInstanceOut],
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_plan_instances(
    trainer_id: int = Query(None, description="Filter by trainer ID"),
    client_id: int = Query(None, description="Filter by client ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get training plan instances with optional filtering"""
    return crud.get_training_plan_instances(
        db=db, trainer_id=trainer_id, client_id=client_id, skip=skip, limit=limit
    )


@router.get(
    "/instances/{instance_id}",
    response_model=schemas.TrainingPlanInstanceOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_training_plan_instance(instance_id: int, db: Session = Depends(get_db)):
    """Get a specific training plan instance"""
    instance = crud.get_training_plan_instance(db=db, instance_id=instance_id)
    if not instance:
        raise HTTPException(status_code=404, detail="Training plan instance not found")
    return instance


@router.put(
    "/instances/{instance_id}",
    response_model=schemas.TrainingPlanInstanceOut,
    dependencies=[Depends(require_trainer_or_admin)],
)
def update_training_plan_instance(
    instance_id: int,
    instance: schemas.TrainingPlanInstanceUpdate,
    db: Session = Depends(get_db),
):
    """Update a training plan instance"""
    updated_instance = crud.update_training_plan_instance(
        db=db, instance_id=instance_id, instance_data=instance
    )
    if not updated_instance:
        raise HTTPException(status_code=404, detail="Training plan instance not found")
    return updated_instance


@router.delete(
    "/instances/{instance_id}",
    dependencies=[Depends(require_trainer_or_admin)],
)
def delete_training_plan_instance(instance_id: int, db: Session = Depends(get_db)):
    """Delete a training plan instance"""
    success = crud.delete_training_plan_instance(db=db, instance_id=instance_id)
    if not success:
        raise HTTPException(status_code=404, detail="Training plan instance not found")
    return {"message": "Training plan instance deleted successfully"}


# Utility Endpoints
@router.post(
    "/{plan_id}/assign",
    response_model=schemas.TrainingPlanInstanceOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def assign_plan_to_another_client(
    plan_id: int,
    client_id: int = Query(..., description="Client ID to assign plan to"),
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    trainer_id: int = Query(..., description="Trainer ID"),
    name: str = Query(None, description="Optional custom name for the instance"),
    db: Session = Depends(get_db),
):
    """
    Assign a specific plan to another client (creates instance with cycles duplicated).
    """
    from datetime import datetime as dt

    try:
        parsed_start_date = dt.strptime(start_date, "%Y-%m-%d").date()
        parsed_end_date = dt.strptime(end_date, "%Y-%m-%d").date()
    except ValueError as e:
        raise HTTPException(
            status_code=422, detail=f"Invalid date format. Use YYYY-MM-DD. Error: {str(e)}"
        )

    if parsed_start_date >= parsed_end_date:
        raise HTTPException(status_code=422, detail="start_date must be before end_date")

    try:
        instance = crud.assign_plan_to_another_client(
            db=db,
            plan_id=plan_id,
            client_id=client_id,
            start_date=parsed_start_date,
            end_date=parsed_end_date,
            trainer_id=trainer_id,
            name=name,
        )
        return instance
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning plan: {str(e)}")


@router.post(
    "/{plan_id}/convert-to-template",
    response_model=schemas.TrainingPlanTemplateOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def convert_plan_to_template(
    plan_id: int,
    template_data: schemas.TrainingPlanTemplateCreate,
    db: Session = Depends(get_db),
):
    """
    Convert a specific plan to a template (reusable).
    
    This endpoint:
    - Creates a new TrainingPlanTemplate from the plan
    - Duplicates all cycles as template cycles
    - Marks the plan as converted
    """
    try:
        template = crud.convert_plan_to_template(
            db=db, plan_id=plan_id, template_data=template_data
        )
        return template
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error converting plan: {str(e)}")


@router.post(
    "/templates/{template_id}/duplicate",
    response_model=schemas.TrainingPlanTemplateOut,
    status_code=201,
    dependencies=[Depends(require_trainer_or_admin)],
)
def duplicate_template(template_id: int, db: Session = Depends(get_db)):
    """
    Duplicate a template (creates a copy with all cycles).
    """
    template = crud.get_training_plan_template(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Training plan template not found")

    # Create new template
    new_template = models.TrainingPlanTemplate(
        trainer_id=template.trainer_id,
        name=f"{template.name} (Copy)",
        description=template.description,
        goal=template.goal,
        category=template.category,
        tags=template.tags,
        estimated_duration_weeks=template.estimated_duration_weeks,
    )
    db.add(new_template)
    db.flush()

    # Duplicate cycles
    template_macrocycles = crud.get_macrocycles_by_template(db, template_id)

    for template_macro in template_macrocycles:
        new_macro = models.Macrocycle(
            template_id=new_template.id,
            name=template_macro.name,
            description=template_macro.description,
            start_date=template_macro.start_date,
            end_date=template_macro.end_date,
            focus=template_macro.focus,
            volume_intensity_ratio=template_macro.volume_intensity_ratio,
        )
        db.add(new_macro)
        db.flush()

        template_mesocycles = crud.get_mesocycles_by_macrocycle(db, template_macro.id)

        for template_meso in template_mesocycles:
            new_meso = models.Mesocycle(
                macrocycle_id=new_macro.id,
                name=template_meso.name,
                description=template_meso.description,
                start_date=template_meso.start_date,
                end_date=template_meso.end_date,
                duration_weeks=template_meso.duration_weeks,
                primary_focus=template_meso.primary_focus,
                secondary_focus=template_meso.secondary_focus,
                target_volume=template_meso.target_volume,
                target_intensity=template_meso.target_intensity,
            )
            db.add(new_meso)
            db.flush()

            template_microcycles = crud.get_microcycles_by_mesocycle(db, template_meso.id)

            for template_micro in template_microcycles:
                new_micro = models.Microcycle(
                    mesocycle_id=new_meso.id,
                    name=template_micro.name,
                    description=template_micro.description,
                    start_date=template_micro.start_date,
                    end_date=template_micro.end_date,
                    duration_days=template_micro.duration_days,
                    training_frequency=template_micro.training_frequency,
                    deload_week=template_micro.deload_week,
                    notes=template_micro.notes,
                )
                db.add(new_micro)

    db.commit()
    db.refresh(new_template)

    return new_template


# Coherence Endpoint
@router.get(
    "/{plan_id}/coherence",
    dependencies=[Depends(require_trainer_or_admin)],
)
def get_plan_coherence(
    plan_id: int,
    deviation_threshold: float = Query(20.0, ge=0, le=100, description="Deviation threshold percentage"),
    db: Session = Depends(get_db),
):
    """
    Calculate coherence for a training plan.
    
    Coherence measures how well week (Mesocycle) and day (Microcycle) values
    match the planned month (Macrocycle) values.
    
    Returns:
    - month_coherence: Baseline values (always 100%)
    - week_coherence: Comparison of weeks to months
    - day_coherence: Comparison of days to weeks
    - overall_coherence: Average coherence percentage (0-100)
    """
    try:
        coherence_result = crud.calculate_plan_coherence(
            db=db, plan_id=plan_id, deviation_threshold=deviation_threshold
        )
        return coherence_result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating coherence: {str(e)}")
