from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth.deps import (
    require_authenticated,
    require_client_visible_to_self_trainer_or_admin,
    require_trainer_or_admin,
)
from ..db import models
from ..db.session import get_db

router = APIRouter()


# Fatigue Analysis Endpoints
@router.post("/fatigue-analysis/", response_model=schemas.FatigueAnalysisOut)
def create_fatigue_analysis(
    fatigue_data: schemas.FatigueAnalysisCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_trainer_or_admin),
):
    """Create a new fatigue analysis record"""
    # Verify the client belongs to the current trainer
    client = crud.get_client_profile(db, fatigue_data.client_id)
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Client not found"
        )

    # For now, allow any trainer/admin to create fatigue analysis
    # You can add more specific authorization logic here if needed

    return crud.create_fatigue_analysis(db, fatigue_data)


@router.get("/fatigue-analysis/", response_model=List[schemas.FatigueAnalysisOut])
def get_fatigue_analysis_list(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Get all fatigue analysis records for the trainer's clients"""
    # Admin can see all; trainers are scoped to their trainer.id (not user_id)
    if current_trainer.get("role") == "admin":
        # Admin can see all fatigue analysis
        return crud.get_fatigue_analysis_list(db, skip, limit)
    else:
        # Map token user_id -> trainer.id
        trainer = (
            db.query(models.Trainer)
            .filter(models.Trainer.user_id == current_trainer.get("user_id"))
            .first()
        )
        if not trainer:
            return []
        # Trainer can only see their clients' fatigue analysis
        return crud.get_fatigue_analysis_by_trainer(db, trainer.id, skip, limit)


@router.get(
    "/fatigue-analysis/{analysis_id}", response_model=schemas.FatigueAnalysisOut
)
def get_fatigue_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated),
):
    """Get a specific fatigue analysis by ID"""
    fatigue = crud.get_fatigue_analysis(db, analysis_id)
    if not fatigue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fatigue analysis not found"
        )

    return fatigue


@router.get(
    "/clients/{client_id}/fatigue-analysis/",
    response_model=List[schemas.FatigueAnalysisOut],
)
def get_client_fatigue_analysis(
    client_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_client_visible_to_self_trainer_or_admin),
):
    """Get fatigue analysis for a specific client"""
    return crud.get_fatigue_analysis_by_client(db, client_id, skip, limit)


@router.put(
    "/fatigue-analysis/{analysis_id}", response_model=schemas.FatigueAnalysisOut
)
def update_fatigue_analysis(
    analysis_id: int,
    fatigue_data: schemas.FatigueAnalysisUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated),
):
    """Update an existing fatigue analysis record"""
    updated_fatigue = crud.update_fatigue_analysis(db, analysis_id, fatigue_data)
    if not updated_fatigue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fatigue analysis not found"
        )

    return updated_fatigue


@router.delete("/fatigue-analysis/{analysis_id}")
def delete_fatigue_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_authenticated),
):
    """Delete a fatigue analysis record"""
    success = crud.delete_fatigue_analysis(db, analysis_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Fatigue analysis not found"
        )

    return {"message": "Fatigue analysis deleted successfully"}


# Fatigue Alert Endpoints
@router.post("/fatigue-alerts/", response_model=schemas.FatigueAlertOut)
def create_fatigue_alert(
    alert_data: schemas.FatigueAlertCreate,
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Create a new fatigue alert"""
    # For now, allow any trainer/admin to create alerts
    # You can add more specific authorization logic here if needed

    return crud.create_fatigue_alert(db, alert_data)


@router.get("/fatigue-alerts/", response_model=List[schemas.FatigueAlertOut])
def get_fatigue_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Get all fatigue alerts for the current trainer"""
    if current_trainer.get("role") == "admin":
        # Admin can see all alerts
        return crud.get_fatigue_alerts(db, skip, limit)
    else:
        trainer = (
            db.query(models.Trainer)
            .filter(models.Trainer.user_id == current_trainer.get("user_id"))
            .first()
        )
        if not trainer:
            return []
        # Trainer can only see their alerts
        return crud.get_fatigue_alerts_by_trainer(db, trainer.id, skip, limit)


@router.get("/fatigue-alerts/unread/", response_model=List[schemas.FatigueAlertOut])
def get_unread_fatigue_alerts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Get unread fatigue alerts for the current trainer"""
    if current_trainer.get("role") == "admin":
        # Admin can see all unread alerts
        return crud.get_unread_fatigue_alerts(db, skip, limit)
    else:
        trainer = (
            db.query(models.Trainer)
            .filter(models.Trainer.user_id == current_trainer.get("user_id"))
            .first()
        )
        if not trainer:
            return []
        # Trainer can only see their unread alerts
        return crud.get_unread_fatigue_alerts_by_trainer(db, trainer.id, skip, limit)


@router.put("/fatigue-alerts/{alert_id}/read")
def mark_alert_as_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Mark a fatigue alert as read"""
    updated_alert = crud.mark_fatigue_alert_as_read(db, alert_id)
    if not updated_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )

    return {"message": "Alert marked as read"}


@router.put("/fatigue-alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    db: Session = Depends(get_db),
    current_trainer: dict = Depends(require_trainer_or_admin),
):
    """Resolve a fatigue alert"""
    resolved_alert = crud.resolve_fatigue_alert(db, alert_id, resolution_notes)
    if not resolved_alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )

    return {"message": "Alert resolved successfully"}


# Workload Tracking Endpoints
@router.post("/workload-tracking/", response_model=schemas.WorkloadTrackingOut)
def create_workload_tracking(
    workload_data: schemas.WorkloadTrackingCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_trainer_or_admin),
):
    """Create a new workload tracking record"""
    # For now, allow any trainer/admin to create workload tracking
    # You can add more specific authorization logic here if needed

    return crud.create_workload_tracking(db, workload_data)


@router.get(
    "/clients/{client_id}/workload-tracking/",
    response_model=List[schemas.WorkloadTrackingOut],
)
def get_client_workload_tracking(
    client_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_client_visible_to_self_trainer_or_admin),
):
    """Get workload tracking for a specific client"""
    return crud.get_workload_tracking_by_client(db, client_id, skip, limit)


@router.get("/clients/{client_id}/fatigue-analytics/")
def get_client_fatigue_analytics(
    client_id: int,
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db),
    current_user: dict = Depends(require_client_visible_to_self_trainer_or_admin),
):
    """Get comprehensive fatigue analytics for a client"""

    # Get fatigue analysis for the specified period
    from datetime import timedelta

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    fatigue_records = (
        db.query(crud.models.FatigueAnalysis)
        .filter(
            crud.models.FatigueAnalysis.client_id == client_id,
            crud.models.FatigueAnalysis.analysis_date >= start_date,
            crud.models.FatigueAnalysis.analysis_date <= end_date,
        )
        .order_by(crud.models.FatigueAnalysis.analysis_date)
        .all()
    )

    # Calculate analytics
    analytics = {
        "total_sessions": len(fatigue_records),
        "average_pre_fatigue": 0,
        "average_post_fatigue": 0,
        "average_fatigue_delta": 0,
        "high_risk_sessions": 0,
        "medium_risk_sessions": 0,
        "low_risk_sessions": 0,
        "trends": {"fatigue_trend": [], "energy_trend": [], "risk_trend": []},
    }

    if fatigue_records:
        # Calculate averages
        pre_fatigue_values = [
            r.pre_fatigue_level
            for r in fatigue_records
            if r.pre_fatigue_level is not None
        ]
        post_fatigue_values = [
            r.post_fatigue_level
            for r in fatigue_records
            if r.post_fatigue_level is not None
        ]
        fatigue_delta_values = [
            r.fatigue_delta for r in fatigue_records if r.fatigue_delta is not None
        ]

        if pre_fatigue_values:
            analytics["average_pre_fatigue"] = sum(pre_fatigue_values) / len(
                pre_fatigue_values
            )
        if post_fatigue_values:
            analytics["average_post_fatigue"] = sum(post_fatigue_values) / len(
                post_fatigue_values
            )
        if fatigue_delta_values:
            analytics["average_fatigue_delta"] = sum(fatigue_delta_values) / len(
                fatigue_delta_values
            )

        # Count risk levels
        for record in fatigue_records:
            if record.risk_level == "high":
                analytics["high_risk_sessions"] += 1
            elif record.risk_level == "medium":
                analytics["medium_risk_sessions"] += 1
            elif record.risk_level == "low":
                analytics["low_risk_sessions"] += 1

        # Generate trends
        for record in fatigue_records:
            analytics["trends"]["fatigue_trend"].append(
                {
                    "date": record.analysis_date.isoformat(),
                    "pre_fatigue": record.pre_fatigue_level,
                    "post_fatigue": record.post_fatigue_level,
                    "fatigue_delta": record.fatigue_delta,
                }
            )

            analytics["trends"]["energy_trend"].append(
                {
                    "date": record.analysis_date.isoformat(),
                    "pre_energy": record.pre_energy_level,
                    "post_energy": record.post_energy_level,
                    "energy_delta": record.energy_delta,
                }
            )

            analytics["trends"]["risk_trend"].append(
                {
                    "date": record.analysis_date.isoformat(),
                    "risk_level": record.risk_level,
                }
            )

    return analytics
