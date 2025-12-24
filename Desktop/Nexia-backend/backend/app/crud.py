import calendar
import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from typing import Dict, List, Optional, Tuple, Union

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, noload

from . import schemas
from .auth import models as auth_models
from .auth import schemas as auth_schemas
from .auth import utils as auth_utils
from .core.config import settings
from .db import models
from .utils.body_composition import calculate_somatotype_heath_carter


def preview_client_calculations(profile_data: schemas.ClientProfileCreate) -> Dict:
    """
    Preview calculated values (BMI and somatotype) for a client profile
    without persisting.

    This function reuses the exact same logic as create_client_profile()
    but without database operations.

    Returns all calculated values that backend computes during creation.
    Used by the Review step in the frontend to show calculated values before creation.

    Args:
        profile_data: Client profile data (same as POST /clients)

    Returns:
        Dict with 'bmi' and 'somatotype' (endomorph, mesomorph, ectomorph)
    """
    # Calculate BMI (same logic as create_client_profile)
    bmi = None
    if profile_data.peso and profile_data.altura:
        height_m = profile_data.altura / 100  # Convert cm to meters
        bmi = round(profile_data.peso / (height_m**2), 2)

    # Calculate somatotype (same logic as create_client_profile)
    manual_endo = profile_data.somatotype_endomorph is not None
    manual_meso = profile_data.somatotype_mesomorph is not None
    manual_ecto = profile_data.somatotype_ectomorph is not None

    somatotype_result = {
        "endomorph": profile_data.somatotype_endomorph,
        "mesomorph": profile_data.somatotype_mesomorph,
        "ectomorph": profile_data.somatotype_ectomorph,
    }

    # Only calculate if at least one component is missing
    if not (manual_endo and manual_meso and manual_ecto):
        somatotype = calculate_somatotype_heath_carter(
            height_cm=profile_data.altura,
            weight_kg=profile_data.peso,
            skinfold_triceps=profile_data.skinfold_triceps,
            skinfold_subscapular=profile_data.skinfold_subscapular,
            skinfold_supraspinal=profile_data.skinfold_supraspinal,
            skinfold_calf=profile_data.skinfold_calf,
            girth_flexed_arm=profile_data.girth_flexed_contracted_arm,
            girth_calf=profile_data.girth_maximum_calf,
            diameter_humerus=profile_data.diameter_humerus_biepicondylar,
            diameter_femur=profile_data.diameter_femur_bicondylar,
        )

        # Use calculated values if manual values were NOT provided
        if not manual_endo and somatotype["somatotype_endomorph"] is not None:
            somatotype_result["endomorph"] = somatotype["somatotype_endomorph"]
        if not manual_meso and somatotype["somatotype_mesomorph"] is not None:
            somatotype_result["mesomorph"] = somatotype["somatotype_mesomorph"]
        if not manual_ecto and somatotype["somatotype_ectomorph"] is not None:
            somatotype_result["ectomorph"] = somatotype["somatotype_ectomorph"]

    return {
        "bmi": bmi,
        "somatotype": somatotype_result,
    }


def create_client_profile(
    db: Session, profile_data: schemas.ClientProfileCreate, commit: bool = True
):
    """Create client profile. If commit=False, caller handles transaction."""
    # Calculate BMI if weight and height are provided
    # Height is now in cm, so convert to meters for BMI calculation
    imc = None
    if profile_data.peso and profile_data.altura:
        height_m = profile_data.altura / 100  # Convert cm to meters
        imc = round(profile_data.peso / (height_m**2), 2)

    # Auto-calculate somatotype (Heath-Carter) if not manually provided
    profile_dict = profile_data.model_dump(exclude_unset=True)

    # Check if any manual somatotype values were provided
    manual_endo = profile_data.somatotype_endomorph is not None
    manual_meso = profile_data.somatotype_mesomorph is not None
    manual_ecto = profile_data.somatotype_ectomorph is not None

    # Only calculate if at least one component is missing
    if not (manual_endo and manual_meso and manual_ecto):
        somatotype = calculate_somatotype_heath_carter(
            height_cm=profile_data.altura,
            weight_kg=profile_data.peso,
            skinfold_triceps=profile_data.skinfold_triceps,
            skinfold_subscapular=profile_data.skinfold_subscapular,
            skinfold_supraspinal=profile_data.skinfold_supraspinal,
            skinfold_calf=profile_data.skinfold_calf,
            girth_flexed_arm=profile_data.girth_flexed_contracted_arm,
            girth_calf=profile_data.girth_maximum_calf,
            diameter_humerus=profile_data.diameter_humerus_biepicondylar,
            diameter_femur=profile_data.diameter_femur_bicondylar,
        )

        # Only set calculated values if manual values were NOT provided
        if not manual_endo and somatotype["somatotype_endomorph"] is not None:
            profile_dict["somatotype_endomorph"] = somatotype["somatotype_endomorph"]
        if not manual_meso and somatotype["somatotype_mesomorph"] is not None:
            profile_dict["somatotype_mesomorph"] = somatotype["somatotype_mesomorph"]
        if not manual_ecto and somatotype["somatotype_ectomorph"] is not None:
            profile_dict["somatotype_ectomorph"] = somatotype["somatotype_ectomorph"]

    db_profile = models.ClientProfile(**profile_dict, imc=imc)
    db.add(db_profile)
    if commit:
        db.commit()
        db.refresh(db_profile)
    return db_profile


def get_client_profiles(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ClientProfile]:
    query = db.query(models.ClientProfile)
    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", None)
    if dialect_name == "postgresql":
        primary = func.unaccent(models.ClientProfile.apellidos)
        secondary = func.unaccent(models.ClientProfile.nombre)
    else:
        primary = models.ClientProfile.apellidos
        secondary = models.ClientProfile.nombre
    query = query.order_by(primary.asc(), secondary.asc())
    return query.offset(skip).limit(limit).all()


def get_client_profiles_paginated(db: Session, skip: int = 0, limit: int = 100):
    """Return ordered client profiles with total count for pagination."""
    base_query = db.query(models.ClientProfile)

    total = base_query.count()

    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", None)
    if dialect_name == "postgresql":
        primary = func.unaccent(models.ClientProfile.apellidos)
        secondary = func.unaccent(models.ClientProfile.nombre)
    else:
        primary = models.ClientProfile.apellidos
        secondary = models.ClientProfile.nombre

    items = (
        base_query.order_by(primary.asc(), secondary.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return items, total


def search_and_filter_clients(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    age_min: int = None,
    age_max: int = None,
    gender: str = None,
    training_goal: str = None,
    experience: str = None,
    sort_by: str = "nombre",
    sort_order: str = "asc",
) -> List[models.ClientProfile]:
    """
    Advanced client search and filtering with multiple criteria
    """
    query = db.query(models.ClientProfile)

    # Determine dialect for accent-insensitive operations
    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", None)

    # Search by name or email (case- and accent-insensitive when Postgres)
    if search:
        search_filter = f"%{search}%"
        if dialect_name == "postgresql":
            query = query.filter(
                or_(
                    func.unaccent(models.ClientProfile.nombre).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.apellidos).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.mail).ilike(
                        func.unaccent(search_filter)
                    ),
                )
            )
        else:
            # SQLite and others: emulate case-insensitive search using LOWER(column)
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(models.ClientProfile.nombre).like(search_lower),
                    func.lower(models.ClientProfile.apellidos).like(search_lower),
                    func.lower(models.ClientProfile.mail).like(search_lower),
                )
            )

    # Filter by age range
    if age_min is not None:
        query = query.filter(models.ClientProfile.edad >= age_min)
    if age_max is not None:
        query = query.filter(models.ClientProfile.edad <= age_max)

    # Filter by gender
    if gender:
        query = query.filter(models.ClientProfile.sexo == gender)

    # Filter by training goal
    if training_goal:
        query = query.filter(
            models.ClientProfile.objetivo_entrenamiento == training_goal
        )

    # Filter by experience level
    if experience:
        query = query.filter(models.ClientProfile.experiencia == experience)

    # Sorting
    allowed_sort_fields = {"apellidos", "nombre", "edad", "fecha_alta"}
    if sort_by not in allowed_sort_fields:
        raise ValueError(
            "Invalid sort_by. Allowed values: apellidos, nombre, edad, fecha_alta"
        )

    if sort_by == "edad":
        column = models.ClientProfile.edad
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "fecha_alta":
        column = models.ClientProfile.fecha_alta
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "nombre":
        # Primary by nombre; tiebreaker by apellidos
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.nombre)
            secondary = func.unaccent(models.ClientProfile.apellidos)
        else:
            primary = models.ClientProfile.nombre
            secondary = models.ClientProfile.apellidos
        if sort_order == "asc":
            query = query.order_by(primary.asc(), secondary.asc())
        else:
            query = query.order_by(primary.desc(), secondary.desc())
    else:  # "apellidos"
        # Default/alphabetical: apellidos then nombre
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.apellidos)
            secondary = func.unaccent(models.ClientProfile.nombre)
        else:
            primary = models.ClientProfile.apellidos
            secondary = models.ClientProfile.nombre
        if sort_order == "asc":
            query = query.order_by(primary.asc(), secondary.asc())
        else:
            query = query.order_by(primary.desc(), secondary.desc())

    # Pagination
    return query.offset(skip).limit(limit).all()


def search_and_filter_clients_paginated(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: str = None,
    age_min: int = None,
    age_max: int = None,
    gender: str = None,
    training_goal: str = None,
    experience: str = None,
    sort_by: str = "nombre",
    sort_order: str = "asc",
):
    """Same as search_and_filter_clients but also returns total count."""
    query = db.query(models.ClientProfile)

    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", None)

    if search:
        if dialect_name == "postgresql":
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    func.unaccent(models.ClientProfile.nombre).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.apellidos).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.mail).ilike(
                        func.unaccent(search_filter)
                    ),
                )
            )
        else:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(models.ClientProfile.nombre).like(search_lower),
                    func.lower(models.ClientProfile.apellidos).like(search_lower),
                    func.lower(models.ClientProfile.mail).like(search_lower),
                )
            )

    if age_min is not None:
        query = query.filter(models.ClientProfile.edad >= age_min)
    if age_max is not None:
        query = query.filter(models.ClientProfile.edad <= age_max)

    if gender:
        query = query.filter(models.ClientProfile.sexo == gender)

    if training_goal:
        query = query.filter(
            models.ClientProfile.objetivo_entrenamiento == training_goal
        )

    if experience:
        query = query.filter(models.ClientProfile.experiencia == experience)

    # Compute total BEFORE applying ordering/pagination
    total = query.count()

    allowed_sort_fields = {"apellidos", "nombre", "edad", "fecha_alta"}
    if sort_by not in allowed_sort_fields:
        raise ValueError(
            "Invalid sort_by. Allowed values: apellidos, nombre, edad, fecha_alta"
        )

    if sort_by == "edad":
        column = models.ClientProfile.edad
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "fecha_alta":
        column = models.ClientProfile.fecha_alta
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "nombre":
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.nombre)
            secondary = func.unaccent(models.ClientProfile.apellidos)
        else:
            primary = models.ClientProfile.nombre
            secondary = models.ClientProfile.apellidos
        if sort_order == "asc":
            query = query.order_by(primary.asc(), secondary.asc())
        else:
            query = query.order_by(primary.desc(), secondary.desc())
    else:  # apellidos
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.apellidos)
            secondary = func.unaccent(models.ClientProfile.nombre)
        else:
            primary = models.ClientProfile.apellidos
            secondary = models.ClientProfile.nombre
        if sort_order == "asc":
            query = query.order_by(primary.asc(), secondary.asc())
        else:
            query = query.order_by(primary.desc(), secondary.desc())

    items = query.offset(skip).limit(limit).all()
    return items, total


def get_client_profile(db: Session, client_id: int):
    return (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.id == client_id)
        .first()
    )


def update_client_profile(
    db: Session, client_id: int, profile_data: schemas.ClientProfileUpdate
):
    db_profile = get_client_profile(db, client_id)
    if not db_profile:
        return None

    # Calculate BMI if weight or height changed
    update_data = profile_data.model_dump(exclude_unset=True)

    # Enforce email uniqueness per trainer on email change
    if "mail" in update_data and update_data["mail"]:
        new_email = update_data["mail"]
        # Find all trainers associated with this client
        trainer_links = (
            db.query(models.TrainerClient)
            .filter(models.TrainerClient.client_id == client_id)
            .all()
        )
        for link in trainer_links:
            duplicate = (
                db.query(models.TrainerClient)
                .join(
                    models.ClientProfile,
                    models.TrainerClient.client_id == models.ClientProfile.id,
                )
                .filter(models.TrainerClient.trainer_id == link.trainer_id)
                .filter(func.lower(models.ClientProfile.mail) == func.lower(new_email))
                .filter(models.ClientProfile.id != client_id)
                .first()
            )
            if duplicate:
                raise ValueError(
                    "Email must be unique per trainer. Another client with this email "
                    "is already linked to this trainer."
                )
        # If no duplicates found, update normalized email on links to keep DB invariant
        for link in trainer_links:
            link.client_email_norm = new_email.lower()
    if "peso" in update_data or "altura" in update_data:
        peso = update_data.get("peso", db_profile.peso)
        altura = update_data.get("altura", db_profile.altura)

        if peso and altura:
            # Height is now in cm, so convert to meters for BMI calculation
            height_m = altura / 100  # Convert cm to meters
            update_data["imc"] = round(peso / (height_m**2), 2)

    # Check if manual somatotype values were provided in this update
    manual_endo_provided = "somatotype_endomorph" in update_data
    manual_meso_provided = "somatotype_mesomorph" in update_data
    manual_ecto_provided = "somatotype_ectomorph" in update_data

    # Check if any anthropometric measurement was updated - recalculate somatotype
    # But only if NO manual somatotype values were provided
    somatotype_fields = [
        "altura",
        "peso",
        "skinfold_triceps",
        "skinfold_subscapular",
        "skinfold_supraspinal",
        "skinfold_calf",
        "girth_flexed_contracted_arm",
        "girth_maximum_calf",
        "diameter_humerus_biepicondylar",
        "diameter_femur_bicondylar",
    ]
    anthropometric_changed = any(field in update_data for field in somatotype_fields)

    # Only auto-calculate if anthropometric data changed AND no manual values provided
    if anthropometric_changed and not (
        manual_endo_provided and manual_meso_provided and manual_ecto_provided
    ):
        # Get current or updated values for somatotype calculation
        altura = update_data.get("altura", db_profile.altura)
        peso = update_data.get("peso", db_profile.peso)
        skinfold_triceps = update_data.get(
            "skinfold_triceps", db_profile.skinfold_triceps
        )
        skinfold_subscapular = update_data.get(
            "skinfold_subscapular", db_profile.skinfold_subscapular
        )
        skinfold_supraspinal = update_data.get(
            "skinfold_supraspinal", db_profile.skinfold_supraspinal
        )
        skinfold_calf = update_data.get("skinfold_calf", db_profile.skinfold_calf)
        girth_flexed_arm = update_data.get(
            "girth_flexed_contracted_arm", db_profile.girth_flexed_contracted_arm
        )
        girth_calf = update_data.get(
            "girth_maximum_calf", db_profile.girth_maximum_calf
        )
        diameter_humerus = update_data.get(
            "diameter_humerus_biepicondylar", db_profile.diameter_humerus_biepicondylar
        )
        diameter_femur = update_data.get(
            "diameter_femur_bicondylar", db_profile.diameter_femur_bicondylar
        )

        somatotype = calculate_somatotype_heath_carter(
            height_cm=altura,
            weight_kg=peso,
            skinfold_triceps=skinfold_triceps,
            skinfold_subscapular=skinfold_subscapular,
            skinfold_supraspinal=skinfold_supraspinal,
            skinfold_calf=skinfold_calf,
            girth_flexed_arm=girth_flexed_arm,
            girth_calf=girth_calf,
            diameter_humerus=diameter_humerus,
            diameter_femur=diameter_femur,
        )

        # Only set calculated values if manual values were NOT provided in this update
        if not manual_endo_provided and somatotype["somatotype_endomorph"] is not None:
            update_data["somatotype_endomorph"] = somatotype["somatotype_endomorph"]
        if not manual_meso_provided and somatotype["somatotype_mesomorph"] is not None:
            update_data["somatotype_mesomorph"] = somatotype["somatotype_mesomorph"]
        if not manual_ecto_provided and somatotype["somatotype_ectomorph"] is not None:
            update_data["somatotype_ectomorph"] = somatotype["somatotype_ectomorph"]

    for field, value in update_data.items():
        setattr(db_profile, field, value)

    db.commit()
    db.refresh(db_profile)
    return db_profile


def delete_client_profile(db: Session, client_id: int) -> bool:
    """Soft delete client profile and user account (preserves data for audit)."""
    db_profile = get_client_profile(db, client_id)
    if not db_profile:
        return False

    # If client has a linked user account, soft delete it too
    if db_profile.user_id:
        user = get_user_by_id(db, db_profile.user_id)
        if user:
            # Soft delete: deactivate user and clear email/username for re-registration
            user.is_active = False
            user.email = None
            user.username = None

            # Clear foreign key references to allow re-registration
            db.execute(
                text("UPDATE trainers SET user_id = NULL WHERE user_id = :user_id"),
                {"user_id": user.id},
            )
            db.execute(
                text(
                    "UPDATE client_profiles SET user_id = NULL WHERE user_id = :user_id"
                ),
                {"user_id": user.id},
            )
            db.execute(
                text("DELETE FROM refresh_tokens WHERE user_id = :user_id"),
                {"user_id": user.id},
            )
            db.execute(
                text("DELETE FROM user_roles WHERE user_id = :user_id"),
                {"user_id": user.id},
            )

            db.add(user)
    db.commit()

    # Soft delete: mark client profile as inactive
    db_profile.is_active = False
    db.add(db_profile)
    db.commit()
    return True


# Exercise CRUD operations
def create_exercise(db: Session, exercise_data: schemas.ExerciseCreate):
    db_exercise = models.Exercise(**exercise_data.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def get_exercises(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    tipo: str = None,
    categoria: str = None,
    nivel: str = None,
    equipo: str = None,
    patron_movimiento: str = None,
    tipo_carga: str = None,
    search: str = None,
) -> List[models.Exercise]:
    query = db.query(models.Exercise)

    # Apply filters
    if tipo:
        query = query.filter(models.Exercise.tipo == tipo)
    if categoria:
        query = query.filter(models.Exercise.categoria == categoria)
    if nivel:
        query = query.filter(models.Exercise.nivel == nivel)
    if equipo:
        query = query.filter(models.Exercise.equipo == equipo)
    if patron_movimiento:
        query = query.filter(models.Exercise.patron_movimiento == patron_movimiento)
    if tipo_carga:
        query = query.filter(models.Exercise.tipo_carga == tipo_carga)

    # Search functionality
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                models.Exercise.nombre.ilike(search_filter),
                models.Exercise.nombre_ingles.ilike(search_filter),
                models.Exercise.musculatura_principal.ilike(search_filter),
            )
        )

    return query.offset(skip).limit(limit).all()


def get_exercise_count(
    db: Session,
    tipo: str = None,
    categoria: str = None,
    nivel: str = None,
    equipo: str = None,
    patron_movimiento: str = None,
    tipo_carga: str = None,
    search: str = None,
) -> int:
    """Get total count of exercises with optional filtering"""
    query = db.query(models.Exercise)

    # Apply filters (same logic as get_exercises)
    if tipo:
        query = query.filter(models.Exercise.tipo == tipo)
    if categoria:
        query = query.filter(models.Exercise.categoria == categoria)
    if nivel:
        query = query.filter(models.Exercise.nivel == nivel)
    if equipo:
        query = query.filter(models.Exercise.equipo == equipo)
    if patron_movimiento:
        query = query.filter(models.Exercise.patron_movimiento == patron_movimiento)
    if tipo_carga:
        query = query.filter(models.Exercise.tipo_carga == tipo_carga)

    # Search functionality
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            or_(
                models.Exercise.nombre.ilike(search_filter),
                models.Exercise.nombre_ingles.ilike(search_filter),
                models.Exercise.musculatura_principal.ilike(search_filter),
            )
        )

    return query.count()


def get_exercise(db: Session, exercise_id: int):
    return db.query(models.Exercise).filter(models.Exercise.id == exercise_id).first()


def get_exercise_by_exercise_id(db: Session, exercise_id: str):
    return (
        db.query(models.Exercise)
        .filter(models.Exercise.exercise_id == exercise_id)
        .first()
    )


def get_exercises_by_muscle_group(
    db: Session, muscle_group: str, skip: int = 0, limit: int = 100
):
    return (
        db.query(models.Exercise)
        .filter(models.Exercise.musculatura_principal.contains(muscle_group))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_exercises_by_equipment(
    db: Session, equipment: str, skip: int = 0, limit: int = 100
):
    return (
        db.query(models.Exercise)
        .filter(models.Exercise.equipo == equipment)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_exercises_by_level(db: Session, level: str, skip: int = 0, limit: int = 100):
    return (
        db.query(models.Exercise)
        .filter(models.Exercise.nivel == level)
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_exercise(
    db: Session, exercise_id: int, exercise_data: schemas.ExerciseUpdate
):
    db_exercise = get_exercise(db, exercise_id)
    if not db_exercise:
        return None

    update_data = exercise_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exercise, field, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_exercise(db: Session, exercise_id: int) -> bool:
    db_exercise = get_exercise(db, exercise_id)
    if not db_exercise:
        return False

    db.delete(db_exercise)
    db.commit()
    return True


# Trainer CRUD operations
def create_trainer(db: Session, trainer_data: schemas.TrainerCreate):
    db_trainer = models.Trainer(**trainer_data.model_dump())
    db.add(db_trainer)
    db.commit()
    db.refresh(db_trainer)
    return db_trainer


def get_trainers(db: Session, skip: int = 0, limit: int = 100) -> List[models.Trainer]:
    return db.query(models.Trainer).offset(skip).limit(limit).all()


def get_trainer(db: Session, trainer_id: int):
    return db.query(models.Trainer).filter(models.Trainer.id == trainer_id).first()


def update_trainer(db: Session, trainer_id: int, trainer_data: schemas.TrainerUpdate):
    db_trainer = get_trainer(db, trainer_id)
    if not db_trainer:
        return None

    update_data = trainer_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trainer, field, value)

    db.commit()
    db.refresh(db_trainer)
    return db_trainer


def delete_trainer(db: Session, trainer_id: int) -> bool:
    """Soft delete trainer profile and user account (preserves data for audit)."""
    db_trainer = get_trainer(db, trainer_id)
    if not db_trainer:
        return False

    # If trainer has a linked user account, soft delete it too
    if db_trainer.user_id:
        user = get_user_by_id(db, db_trainer.user_id)
        if user:
            # Soft delete: deactivate user and clear email/username for re-registration
            user.is_active = False
            user.email = None
            user.username = None

            # Clear foreign key references to allow re-registration
            db.execute(
                text("UPDATE trainers SET user_id = NULL WHERE user_id = :user_id"),
                {"user_id": user.id},
            )
            db.execute(
                text(
                    "UPDATE client_profiles SET user_id = NULL WHERE user_id = :user_id"
                ),
                {"user_id": user.id},
            )
            db.execute(
                text("DELETE FROM refresh_tokens WHERE user_id = :user_id"),
                {"user_id": user.id},
            )
            db.execute(
                text("DELETE FROM user_roles WHERE user_id = :user_id"),
                {"user_id": user.id},
            )

            db.add(user)
            db.commit()

    # Soft delete: mark trainer profile as inactive
    db_trainer.is_active = False
    db.add(db_trainer)
    db.commit()
    return True


# Trainer Client CRUD operations
def create_trainer_client(
    db: Session, trainer_client_data: schemas.TrainerClientCreate
):
    # Enforce email uniqueness per trainer when linking
    trainer_id = trainer_client_data.trainer_id
    client_id = trainer_client_data.client_id

    client = get_client_profile(db, client_id)
    if not client:
        raise ValueError("Client not found")

    duplicate = (
        db.query(models.TrainerClient)
        .join(
            models.ClientProfile,
            models.TrainerClient.client_id == models.ClientProfile.id,
        )
        .filter(models.TrainerClient.trainer_id == trainer_id)
        .filter(func.lower(models.ClientProfile.mail) == func.lower(client.mail))
        .first()
    )
    if duplicate:
        raise ValueError(
            "Email must be unique per trainer. Another client with this email "
            "is already linked to this trainer."
        )

    db_trainer_client = models.TrainerClient(
        **trainer_client_data.model_dump(),
        client_email_norm=client.mail.lower(),
    )
    db.add(db_trainer_client)
    db.commit()
    db.refresh(db_trainer_client)
    return db_trainer_client


def get_trainer_clients(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.TrainerClient]:
    return db.query(models.TrainerClient).offset(skip).limit(limit).all()


def get_trainer_client(db: Session, trainer_client_id: int):
    return (
        db.query(models.TrainerClient)
        .filter(models.TrainerClient.id == trainer_client_id)
        .first()
    )


def update_trainer_client(
    db: Session,
    trainer_client_id: int,
    trainer_client_data: schemas.TrainerClientUpdate,
):
    db_trainer_client = get_trainer_client(db, trainer_client_id)
    if not db_trainer_client:
        return None

    update_data = trainer_client_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_trainer_client, field, value)

    # Keep normalized email in sync if client changed
    if "client_id" in update_data:
        client = get_client_profile(db, db_trainer_client.client_id)
        if client and client.mail:
            db_trainer_client.client_email_norm = client.mail.lower()

    db.commit()
    db.refresh(db_trainer_client)
    return db_trainer_client


def delete_trainer_client(db: Session, trainer_client_id: int) -> bool:
    db_trainer_client = get_trainer_client(db, trainer_client_id)
    if not db_trainer_client:
        return False

    db.delete(db_trainer_client)
    db.commit()
    return True


def get_clients_for_trainer_paginated(
    db: Session,
    trainer_id: int,
    skip: int = 0,
    limit: int = 20,
    search: str | None = None,
    sort_by: str = "apellidos",
    sort_order: str = "asc",
):
    """Return (items, total) for clients linked to a trainer.

    Supports optional search and sorting.
    """
    query = (
        db.query(models.ClientProfile)
        .join(
            models.TrainerClient,
            models.TrainerClient.client_id == models.ClientProfile.id,
        )
        .filter(models.TrainerClient.trainer_id == trainer_id)
    )

    dialect_name = getattr(getattr(db, "bind", None), "dialect", None)
    dialect_name = getattr(dialect_name, "name", None)

    if search:
        if dialect_name == "postgresql":
            search_filter = f"%{search}%"
            query = query.filter(
                or_(
                    func.unaccent(models.ClientProfile.nombre).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.apellidos).ilike(
                        func.unaccent(search_filter)
                    ),
                    func.unaccent(models.ClientProfile.mail).ilike(
                        func.unaccent(search_filter)
                    ),
                )
            )
        else:
            search_lower = f"%{search.lower()}%"
            query = query.filter(
                or_(
                    func.lower(models.ClientProfile.nombre).like(search_lower),
                    func.lower(models.ClientProfile.apellidos).like(search_lower),
                    func.lower(models.ClientProfile.mail).like(search_lower),
                )
            )

    total = query.count()

    allowed_sort_fields = {"apellidos", "nombre", "edad", "fecha_alta"}
    if sort_by not in allowed_sort_fields:
        raise ValueError(
            "Invalid sort_by. Allowed values: apellidos, nombre, edad, fecha_alta"
        )

    if sort_by == "edad":
        column = models.ClientProfile.edad
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "fecha_alta":
        column = models.ClientProfile.fecha_alta
        query = query.order_by(column.asc() if sort_order == "asc" else column.desc())
    elif sort_by == "nombre":
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.nombre)
            secondary = func.unaccent(models.ClientProfile.apellidos)
        else:
            primary = models.ClientProfile.nombre
            secondary = models.ClientProfile.apellidos
        query = query.order_by(
            primary.asc() if sort_order == "asc" else primary.desc(),
            secondary.asc() if sort_order == "asc" else secondary.desc(),
        )
    else:  # apellidos
        if dialect_name == "postgresql":
            primary = func.unaccent(models.ClientProfile.apellidos)
            secondary = func.unaccent(models.ClientProfile.nombre)
        else:
            primary = models.ClientProfile.apellidos
            secondary = models.ClientProfile.nombre
        query = query.order_by(
            primary.asc() if sort_order == "asc" else primary.desc(),
            secondary.asc() if sort_order == "asc" else secondary.desc(),
        )

    items = query.offset(skip).limit(limit).all()
    return items, total


def unlink_trainer_client(db: Session, trainer_id: int, client_id: int) -> bool:
    """Remove link between a trainer and a client."""
    link = (
        db.query(models.TrainerClient)
        .filter(models.TrainerClient.trainer_id == trainer_id)
        .filter(models.TrainerClient.client_id == client_id)
        .first()
    )
    if not link:
        return False
    db.delete(link)
    db.commit()
    return True


# Auth CRUD helpers
def get_user_by_email(db: Session, email: str):
    return db.query(auth_models.User).filter(auth_models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(auth_models.User).filter(auth_models.User.id == user_id).first()


def get_role_by_name(db: Session, name: str):
    return db.query(auth_models.Role).filter(auth_models.Role.name == name).first()


def assign_role_to_user(db: Session, user: auth_models.User, role_name: str):
    role = get_role_by_name(db, role_name)
    if not role:
        role = auth_models.Role(name=role_name, description=f"System role: {role_name}")
        db.add(role)
        db.flush()
    if role not in user.roles:
        user.roles.append(role)
    db.commit()
    db.refresh(user)
    return user


def get_primary_role_name(db: Session, user_id: int) -> str:
    user = get_user_by_id(db, user_id)
    if not user or not user.roles:
        return "trainer"
    # Return the first role name (simple primary role approach)
    return user.roles[0].name


def create_user(db: Session, user_data: auth_schemas.UserCreate):
    # Hash password
    hashed = auth_utils.get_password_hash(user_data.password)
    full_name = f"{user_data.nombre} {user_data.apellidos}".strip()
    db_user = auth_models.User(
        email=user_data.email,
        username=user_data.email,
        hashed_password=hashed,
        full_name=full_name,
        tos_accepted_at=datetime.now(timezone.utc) if user_data.tos_accepted else None,
        tos_version=user_data.tos_version if user_data.tos_accepted else None,
    )
    db.add(db_user)
    db.flush()
    assign_role_to_user(db, db_user, user_data.role)
    # Auto-create and link profiles by role
    if user_data.role == "trainer":
        trainer = (
            db.query(models.Trainer)
            .filter(func.lower(models.Trainer.mail) == func.lower(user_data.email))
            .first()
        )
        if trainer:
            # Environment-based behavior:
            # - Production: Reuse existing profile (preserve history/audit trail)
            # - Dev/Test: Only reuse if profile is active (clean onboarding tests)
            if settings.is_production or trainer.is_active:
                trainer.user_id = db_user.id
                # Reactivate if it was soft-deleted
                if not trainer.is_active:
                    trainer.is_active = True
            else:
                # In dev/test, create new profile if old one is inactive
                trainer = models.Trainer(
                    user_id=db_user.id,
                    nombre=user_data.nombre,
                    apellidos=user_data.apellidos,
                    mail=user_data.email,
                )
                db.add(trainer)
        else:
            trainer = models.Trainer(
                user_id=db_user.id,
                nombre=user_data.nombre,
                apellidos=user_data.apellidos,
                mail=user_data.email,
            )
            db.add(trainer)
    elif user_data.role == "athlete":
        client = (
            db.query(models.ClientProfile)
            .filter(
                func.lower(models.ClientProfile.mail) == func.lower(user_data.email)
            )
            .first()
        )
        if client:
            # Environment-based behavior:
            # - Production: Reuse existing profile (preserve history/audit trail)
            # - Dev/Test: Only reuse if profile is active (clean onboarding tests)
            if settings.is_production or client.is_active:
                client.user_id = db_user.id
                # Reactivate if it was soft-deleted
                if not client.is_active:
                    client.is_active = True
            else:
                # In dev/test, create new profile if old one is inactive
                client = models.ClientProfile(
                    user_id=db_user.id,
                    nombre=user_data.nombre,
                    apellidos=user_data.apellidos,
                    mail=user_data.email,
                )
                db.add(client)
        else:
            client = models.ClientProfile(
                user_id=db_user.id,
                nombre=user_data.nombre,
                apellidos=user_data.apellidos,
                mail=user_data.email,
            )
            db.add(client)
    db.commit()
    db.refresh(db_user)
    return db_user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    # Check lockout
    now = datetime.now(timezone.utc)
    if (
        getattr(user, "lockout_until", None)
        and user.lockout_until
        and user.lockout_until > now
    ):
        return None
    if not auth_utils.verify_password(password, user.hashed_password):
        # Increment failed login attempts and apply lockout if needed
        attempts = getattr(user, "failed_login_attempts", 0) + 1
        user.failed_login_attempts = attempts
        # Simple policy: lockout 15 minutes after 5 failures
        if attempts >= 5:
            user.lockout_until = now + timedelta(minutes=15)
            user.failed_login_attempts = 0
        db.add(user)
        db.commit()
        return None
    # Successful authentication: reset counters
    user.failed_login_attempts = 0
    user.lockout_until = None
    db.add(user)
    db.commit()
    return user


def set_user_password(db: Session, user: auth_models.User, new_password: str):
    """Set a new hashed password for a user and persist it."""
    user.hashed_password = auth_utils.get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_profile(
    db: Session,
    user: auth_models.User,
    *,
    email: str | None = None,
    full_name: str | None = None,
):
    """Update basic user profile fields with uniqueness check for email."""
    if email and email != user.email:
        # Ensure email unique
        existing = get_user_by_email(db, email)
        if existing and existing.id != user.id:
            raise ValueError("Email already in use")
        user.email = email

    if full_name is not None:
        user.full_name = full_name

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def verify_user_email(db: Session, user: auth_models.User):
    """Mark user's email as verified."""
    user.is_verified = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user: auth_models.User):
    """Soft-delete: mark user inactive and clear email/username for re-registration.

    Keep data for audit/RBAC links.
    """
    user.is_active = False
    # Clear email and username to allow re-registration with same email/username
    user.email = None
    user.username = None

    # Clear foreign key references to allow re-registration
    # Clear trainer profile user_id if exists
    db.execute(
        text("UPDATE trainers SET user_id = NULL WHERE user_id = :user_id"),
        {"user_id": user.id},
    )

    # Clear client profile user_id if exists
    db.execute(
        text("UPDATE client_profiles SET user_id = NULL WHERE user_id = :user_id"),
        {"user_id": user.id},
    )

    # Clear refresh tokens (these don't have unique constraints but good to clean up)
    db.execute(
        text("DELETE FROM refresh_tokens WHERE user_id = :user_id"),
        {"user_id": user.id},
    )

    # Clear user roles (these don't have unique constraints but good to clean up)
    db.execute(
        text("DELETE FROM user_roles WHERE user_id = :user_id"),
        {"user_id": user.id},
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def increment_user_token_version(db: Session, user: auth_models.User):
    """Bump user's token_version to invalidate all access tokens.

    Refresh tokens are handled separately via revocation helpers.
    """
    current = getattr(user, "token_version", 1)
    user.token_version = current + 1
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


# =========================
# Refresh token CRUD helpers
# =========================
def create_refresh_token(
    db: Session,
    user: auth_models.User,
    token_plain: str,
    *,
    user_agent: Optional[str],
    ip_address: Optional[str],
):
    token_hash = auth_utils.hash_refresh_token(token_plain)
    record = auth_models.RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=auth_utils.get_refresh_expiry(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def find_valid_refresh(
    db: Session, token_plain: str
) -> Optional[auth_models.RefreshToken]:
    token_hash = auth_utils.hash_refresh_token(token_plain)
    rec = (
        db.query(auth_models.RefreshToken)
        .filter(auth_models.RefreshToken.token_hash == token_hash)
        .first()
    )
    if not rec:
        return None
    if rec.revoked_at is not None:
        return None
    if rec.expires_at <= datetime.now(timezone.utc):
        return None
    return rec


def revoke_refresh_token(db: Session, token_plain: str) -> bool:
    token_hash = auth_utils.hash_refresh_token(token_plain)
    rec = (
        db.query(auth_models.RefreshToken)
        .filter(auth_models.RefreshToken.token_hash == token_hash)
        .first()
    )
    if not rec:
        return False
    if rec.revoked_at is None:
        rec.revoked_at = datetime.now(timezone.utc)
        db.add(rec)
        db.commit()
    return True


def revoke_all_refresh_tokens_for_user(db: Session, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    q = (
        db.query(auth_models.RefreshToken)
        .filter(auth_models.RefreshToken.user_id == user_id)
        .filter(auth_models.RefreshToken.revoked_at.is_(None))
    )
    count = 0
    for rec in q:
        rec.revoked_at = now
        db.add(rec)
        count += 1
    db.commit()
    return count


def rotate_refresh_token(
    db: Session,
    user: auth_models.User,
    old_token_plain: str,
    *,
    user_agent: Optional[str],
    ip_address: Optional[str],
):
    # Revoke old
    revoke_refresh_token(db, old_token_plain)
    # Create new
    new_token = auth_utils.generate_refresh_token()
    create_refresh_token(
        db,
        user,
        new_token,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    return new_token


# Note: increment_user_token_version defined above; avoid redefinition


# Training Routine CRUD operations
def create_training_routine(db: Session, routine_data: schemas.TrainingRoutineCreate):
    db_routine = models.TrainingRoutine(**routine_data.model_dump())
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return db_routine


def get_training_routines(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.TrainingRoutine]:
    return db.query(models.TrainingRoutine).offset(skip).limit(limit).all()


def get_training_routine(db: Session, routine_id: int):
    return (
        db.query(models.TrainingRoutine)
        .filter(models.TrainingRoutine.id == routine_id)
        .first()
    )


def update_training_routine(
    db: Session, routine_id: int, routine_data: schemas.TrainingRoutineUpdate
):
    db_routine = get_training_routine(db, routine_id)
    if not db_routine:
        return None

    update_data = routine_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_routine, field, value)

    db.commit()
    db.refresh(db_routine)
    return db_routine


def delete_training_routine(db: Session, routine_id: int) -> bool:
    db_routine = get_training_routine(db, routine_id)
    if not db_routine:
        return False

    db.delete(db_routine)
    db.commit()
    return True


# Client Routine CRUD operations
def create_client_routine(db: Session, routine_data: schemas.ClientRoutineCreate):
    db_routine = models.ClientRoutine(**routine_data.model_dump())
    db.add(db_routine)
    db.commit()
    db.refresh(db_routine)
    return db_routine


def get_client_routines(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ClientRoutine]:
    return db.query(models.ClientRoutine).offset(skip).limit(limit).all()


def get_client_routine(db: Session, routine_id: int):
    return (
        db.query(models.ClientRoutine)
        .filter(models.ClientRoutine.id == routine_id)
        .first()
    )


def update_client_routine(
    db: Session, routine_id: int, routine_data: schemas.ClientRoutineUpdate
):
    db_routine = get_client_routine(db, routine_id)
    if not db_routine:
        return None

    update_data = routine_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_routine, field, value)

    db.commit()
    db.refresh(db_routine)
    return db_routine


def delete_client_routine(db: Session, routine_id: int) -> bool:
    db_routine = get_client_routine(db, routine_id)
    if not db_routine:
        return False

    db.delete(db_routine)
    db.commit()
    return True


# Client Progress CRUD operations
def create_client_progress(db: Session, progress_data: schemas.ClientProgressCreate):
    from .utils.body_composition import calculate_body_composition

    # Get client profile for age and gender
    client = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.id == progress_data.client_id)
        .first()
    )

    progress_dict = progress_data.model_dump()

    # Calculate body composition if we have all required data
    if (
        client
        and client.edad
        and client.sexo
        and progress_dict.get("peso")
        and all(
            progress_dict.get(f"skinfold_{site}") is not None
            for site in [
                "triceps",
                "subscapular",
                "biceps",
                "iliac_crest",
                "supraspinal",
                "abdominal",
                "thigh",
            ]
        )
    ):
        composition = calculate_body_composition(
            weight_kg=progress_dict["peso"],
            age=client.edad,
            gender=(
                client.sexo.value if hasattr(client.sexo, "value") else str(client.sexo)
            ),
            skinfold_triceps=progress_dict.get("skinfold_triceps"),
            skinfold_subscapular=progress_dict.get("skinfold_subscapular"),
            skinfold_biceps=progress_dict.get("skinfold_biceps"),
            skinfold_iliac_crest=progress_dict.get("skinfold_iliac_crest"),
            skinfold_supraspinal=progress_dict.get("skinfold_supraspinal"),
            skinfold_abdominal=progress_dict.get("skinfold_abdominal"),
            skinfold_thigh=progress_dict.get("skinfold_thigh"),
        )
        progress_dict["body_fat_percentage"] = composition["body_fat_percentage"]
        progress_dict["muscle_mass_kg"] = composition["muscle_mass_kg"]
        progress_dict["fat_free_mass_kg"] = composition["fat_free_mass_kg"]

    db_progress = models.ClientProgress(**progress_dict)
    db.add(db_progress)
    db.commit()
    db.refresh(db_progress)
    return db_progress


def get_client_progress(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ClientProgress]:
    return (
        db.query(models.ClientProgress)
        .options(noload(models.ClientProgress.client))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_client_progress_by_client_id(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.ClientProgress]:
    return (
        db.query(models.ClientProgress)
        .options(noload(models.ClientProgress.client))
        .filter(models.ClientProgress.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_client_progress_by_id(db: Session, progress_id: int):
    return (
        db.query(models.ClientProgress)
        .options(noload(models.ClientProgress.client))
        .filter(models.ClientProgress.id == progress_id)
        .first()
    )


def update_client_progress(
    db: Session, progress_id: int, progress_data: schemas.ClientProgressUpdate
):
    from .utils.body_composition import calculate_body_composition

    db_progress = get_client_progress_by_id(db, progress_id)
    if not db_progress:
        return None

    update_data = progress_data.model_dump(exclude_unset=True)

    # Update fields
    for field, value in update_data.items():
        setattr(db_progress, field, value)

    # Recalculate BMI if weight or height changed
    # Height is in cm, convert to meters for BMI calculation
    if "peso" in update_data or "altura" in update_data:
        peso = update_data.get("peso", db_progress.peso)
        altura = update_data.get("altura", db_progress.altura)

        if peso is not None and altura is not None:
            # Convert cm to meters for BMI calculation
            altura_m = altura / 100
            bmi = peso / (altura_m**2)
            db_progress.imc = round(bmi, 2)
        else:
            # Clear BMI if we can't calculate it
            db_progress.imc = None

    # Recalculate body composition if anthropometric data or weight changed
    skinfold_fields = [
        "skinfold_triceps",
        "skinfold_subscapular",
        "skinfold_biceps",
        "skinfold_iliac_crest",
        "skinfold_supraspinal",
        "skinfold_abdominal",
        "skinfold_thigh",
    ]
    should_recalculate = "peso" in update_data or any(
        field in update_data for field in skinfold_fields
    )

    if should_recalculate:
        # Get client profile for age and gender
        client = (
            db.query(models.ClientProfile)
            .filter(models.ClientProfile.id == db_progress.client_id)
            .first()
        )

        if (
            client
            and client.edad
            and client.sexo
            and db_progress.peso
            and all(
                getattr(db_progress, f"skinfold_{site}", None) is not None
                for site in [
                    "triceps",
                    "subscapular",
                    "biceps",
                    "iliac_crest",
                    "supraspinal",
                    "abdominal",
                    "thigh",
                ]
            )
        ):
            composition = calculate_body_composition(
                weight_kg=db_progress.peso,
                age=client.edad,
                gender=(
                    client.sexo.value
                    if hasattr(client.sexo, "value")
                    else str(client.sexo)
                ),
                skinfold_triceps=getattr(db_progress, "skinfold_triceps", None),
                skinfold_subscapular=getattr(db_progress, "skinfold_subscapular", None),
                skinfold_biceps=getattr(db_progress, "skinfold_biceps", None),
                skinfold_iliac_crest=getattr(db_progress, "skinfold_iliac_crest", None),
                skinfold_supraspinal=getattr(db_progress, "skinfold_supraspinal", None),
                skinfold_abdominal=getattr(db_progress, "skinfold_abdominal", None),
                skinfold_thigh=getattr(db_progress, "skinfold_thigh", None),
            )
            db_progress.body_fat_percentage = composition["body_fat_percentage"]
            db_progress.muscle_mass_kg = composition["muscle_mass_kg"]
            db_progress.fat_free_mass_kg = composition["fat_free_mass_kg"]
        else:
            # Clear body composition if we can't calculate it
            db_progress.body_fat_percentage = None
            db_progress.muscle_mass_kg = None
            db_progress.fat_free_mass_kg = None

    db.commit()
    db.refresh(db_progress)
    return db_progress


def delete_client_progress(db: Session, progress_id: int) -> bool:
    db_progress = get_client_progress_by_id(db, progress_id)
    if not db_progress:
        return False

    db.delete(db_progress)
    db.commit()
    return True


# Training Plan CRUD operations
# Training Plan Template CRUD
def create_training_plan_template(
    db: Session, template_data: schemas.TrainingPlanTemplateCreate
) -> models.TrainingPlanTemplate:
    """Create a new training plan template"""
    db_template = models.TrainingPlanTemplate(**template_data.model_dump())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def get_training_plan_templates(
    db: Session,
    trainer_id: int,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.TrainingPlanTemplate]:
    """Get all templates for a trainer"""
    query = db.query(models.TrainingPlanTemplate).filter(
        models.TrainingPlanTemplate.trainer_id == trainer_id,
        models.TrainingPlanTemplate.is_active.is_(True),
    )
    if category:
        query = query.filter(models.TrainingPlanTemplate.category == category)
    return query.offset(skip).limit(limit).all()


def get_training_plan_template(
    db: Session, template_id: int
) -> Optional[models.TrainingPlanTemplate]:
    """Get a specific training plan template"""
    return (
        db.query(models.TrainingPlanTemplate)
        .filter(
            models.TrainingPlanTemplate.id == template_id,
            models.TrainingPlanTemplate.is_active.is_(True),
        )
        .first()
    )


def update_training_plan_template(
    db: Session,
    template_id: int,
    template_data: schemas.TrainingPlanTemplateUpdate,
) -> Optional[models.TrainingPlanTemplate]:
    """Update a training plan template"""
    db_template = get_training_plan_template(db, template_id)
    if not db_template:
        return None

    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_template, field, value)

    db.commit()
    db.refresh(db_template)
    return db_template


def delete_training_plan_template(db: Session, template_id: int) -> bool:
    """Delete (soft delete) a training plan template"""
    db_template = get_training_plan_template(db, template_id)
    if not db_template:
        return False

    db_template.is_active = False
    db.commit()
    return True


# Training Plan Instance CRUD
def create_training_plan_instance(
    db: Session, instance_data: schemas.TrainingPlanInstanceCreate
) -> models.TrainingPlanInstance:
    """Create a new training plan instance"""
    db_instance = models.TrainingPlanInstance(**instance_data.model_dump())
    db.add(db_instance)
    db.commit()
    db.refresh(db_instance)
    return db_instance


def get_training_plan_instances(
    db: Session,
    trainer_id: Optional[int] = None,
    client_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.TrainingPlanInstance]:
    """Get training plan instances with optional filtering"""
    query = db.query(models.TrainingPlanInstance).filter(
        models.TrainingPlanInstance.is_active.is_(True)
    )
    if trainer_id:
        query = query.filter(models.TrainingPlanInstance.trainer_id == trainer_id)
    if client_id:
        query = query.filter(models.TrainingPlanInstance.client_id == client_id)
    return query.offset(skip).limit(limit).all()


def get_training_plan_instance(
    db: Session, instance_id: int
) -> Optional[models.TrainingPlanInstance]:
    """Get a specific training plan instance"""
    return (
        db.query(models.TrainingPlanInstance)
        .filter(
            models.TrainingPlanInstance.id == instance_id,
            models.TrainingPlanInstance.is_active.is_(True),
        )
        .first()
    )


def update_training_plan_instance(
    db: Session,
    instance_id: int,
    instance_data: schemas.TrainingPlanInstanceUpdate,
) -> Optional[models.TrainingPlanInstance]:
    """Update a training plan instance"""
    db_instance = get_training_plan_instance(db, instance_id)
    if not db_instance:
        return None

    update_data = instance_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_instance, field, value)

    db.commit()
    db.refresh(db_instance)
    return db_instance


def delete_training_plan_instance(db: Session, instance_id: int) -> bool:
    """Delete (soft delete) a training plan instance"""
    db_instance = get_training_plan_instance(db, instance_id)
    if not db_instance:
        return False

    db_instance.is_active = False
    db.commit()
    return True


# Helper functions for getting cycles by template/instance
def get_macrocycles_by_template(
    db: Session, template_id: int, skip: int = 0, limit: int = 100
) -> List[models.Macrocycle]:
    """Get all macrocycles for a template"""
    return (
        db.query(models.Macrocycle)
        .filter(
            models.Macrocycle.template_id == template_id,
            models.Macrocycle.is_active.is_(True),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_macrocycles_by_instance(
    db: Session, instance_id: int, skip: int = 0, limit: int = 100
) -> List[models.Macrocycle]:
    """Get all macrocycles for an instance"""
    return (
        db.query(models.Macrocycle)
        .filter(
            models.Macrocycle.instance_id == instance_id,
            models.Macrocycle.is_active.is_(True),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def assign_template_to_client(
    db: Session,
    template_id: int,
    client_id: int,
    start_date: date,
    end_date: date,
    trainer_id: int,
    name: Optional[str] = None,
) -> models.TrainingPlanInstance:
    """
    Assign a template to a client (creates instance with all cycles duplicated).

    This function:
    1. Gets the template
    2. Creates an instance base
    3. Duplicates all macrocycles, mesocycles, and microcycles as instances
    4. Adjusts dates proportionally based on new start_date/end_date
    5. Increments template.usage_count

    Args:
        db: Database session
        template_id: ID of the template to assign
        client_id: ID of the client to assign to
        start_date: Start date for the instance
        end_date: End date for the instance
        trainer_id: ID of the trainer
        name: Optional custom name (defaults to template name)

    Returns:
        Created TrainingPlanInstance with all cycles duplicated
    """
    # 1. Get template
    template = get_training_plan_template(db, template_id)
    if not template:
        raise ValueError(f"Template {template_id} not found")

    # 2. Create instance base
    instance_name = name or template.name
    instance = models.TrainingPlanInstance(
        template_id=template_id,
        client_id=client_id,
        trainer_id=trainer_id,
        name=instance_name,
        description=template.description,
        start_date=start_date,
        end_date=end_date,
        goal=template.goal,
        status="active",
    )
    db.add(instance)
    db.flush()  # Get the ID without committing

    # 3. Get template cycles
    template_macrocycles = get_macrocycles_by_template(db, template_id)

    if template_macrocycles:
        # Calculate date adjustment ratio
        template_duration = (
            template_macrocycles[-1].end_date - template_macrocycles[0].start_date
        ).days
        instance_duration = (end_date - start_date).days
        date_ratio = (
            instance_duration / template_duration if template_duration > 0 else 1.0
        )
        template_start = template_macrocycles[0].start_date

        # 4. Duplicate cycles recursively
        macrocycle_mapping: Dict[int, int] = (
            {}
        )  # template_macro_id -> instance_macro_id
        mesocycle_mapping: Dict[int, int] = {}  # template_meso_id -> instance_meso_id

        for template_macro in template_macrocycles:
            # Calculate new dates for macrocycle
            days_from_start = (template_macro.start_date - template_start).days
            new_start = start_date + timedelta(days=int(days_from_start * date_ratio))
            new_end_days = (template_macro.end_date - template_macro.start_date).days
            new_end = new_start + timedelta(days=int(new_end_days * date_ratio))

            # Create instance macrocycle
            instance_macro = models.Macrocycle(
                instance_id=instance.id,
                name=template_macro.name,
                description=template_macro.description,
                start_date=new_start,
                end_date=new_end,
                focus=template_macro.focus,
                physical_quality=template_macro.physical_quality,
                volume=template_macro.volume,
                intensity=template_macro.intensity,
                volume_intensity_ratio=template_macro.volume_intensity_ratio,
            )
            db.add(instance_macro)
            db.flush()
            macrocycle_mapping[template_macro.id] = instance_macro.id

            # Get mesocycles for this macrocycle
            template_mesocycles = get_mesocycles_by_macrocycle(db, template_macro.id)

            for template_meso in template_mesocycles:
                # Calculate new dates for mesocycle
                days_from_macro_start = (
                    template_meso.start_date - template_macro.start_date
                ).days
                meso_start = new_start + timedelta(
                    days=int(days_from_macro_start * date_ratio)
                )
                meso_end_days = (template_meso.end_date - template_meso.start_date).days
                meso_end = meso_start + timedelta(days=int(meso_end_days * date_ratio))

                # Create instance mesocycle
                instance_meso = models.Mesocycle(
                    macrocycle_id=instance_macro.id,
                    name=template_meso.name,
                    description=template_meso.description,
                    start_date=meso_start,
                    end_date=meso_end,
                    duration_weeks=template_meso.duration_weeks,
                    primary_focus=template_meso.primary_focus,
                    secondary_focus=template_meso.secondary_focus,
                    physical_quality=template_meso.physical_quality,
                    volume=template_meso.volume,
                    intensity=template_meso.intensity,
                    target_volume=template_meso.target_volume,
                    target_intensity=template_meso.target_intensity,
                )
                db.add(instance_meso)
                db.flush()
                mesocycle_mapping[template_meso.id] = instance_meso.id

                # Get microcycles for this mesocycle
                template_microcycles = get_microcycles_by_mesocycle(
                    db, template_meso.id
                )

                for template_micro in template_microcycles:
                    # Calculate new dates for microcycle
                    days_from_meso_start = (
                        template_micro.start_date - template_meso.start_date
                    ).days
                    micro_start = meso_start + timedelta(
                        days=int(days_from_meso_start * date_ratio)
                    )
                    micro_end_days = (
                        template_micro.end_date - template_micro.start_date
                    ).days
                    micro_end = micro_start + timedelta(
                        days=int(micro_end_days * date_ratio)
                    )

                    # Create instance microcycle
                    instance_micro = models.Microcycle(
                        mesocycle_id=instance_meso.id,
                        name=template_micro.name,
                        description=template_micro.description,
                        start_date=micro_start,
                        end_date=micro_end,
                        duration_days=template_micro.duration_days,
                        training_frequency=template_micro.training_frequency,
                        deload_week=template_micro.deload_week,
                        notes=template_micro.notes,
                        physical_quality=template_micro.physical_quality,
                        volume=template_micro.volume,
                        intensity=template_micro.intensity,
                    )
                    db.add(instance_micro)

    # 5. Increment template usage_count
    template.usage_count += 1

    # Commit everything first
    db.commit()
    db.refresh(instance)

    # 6. Auto-create training sessions for generic plans (Requirement C)
    if template.is_generic:
        try:
            # Get all microcycles from the instance
            # We need to traverse: instance -> macrocycles -> mesocycles -> microcycles
            instance_macrocycles = get_macrocycles_by_instance(db, instance.id)

            for macrocycle in instance_macrocycles:
                # Get mesocycles for this macrocycle
                mesocycles = (
                    db.query(models.Mesocycle)
                    .filter(
                        models.Mesocycle.macrocycle_id == macrocycle.id,
                        models.Mesocycle.is_active.is_(True),
                    )
                    .all()
                )

                for mesocycle in mesocycles:
                    # Get microcycles for this mesocycle
                    microcycles = (
                        db.query(models.Microcycle)
                        .filter(
                            models.Microcycle.mesocycle_id == mesocycle.id,
                            models.Microcycle.is_active.is_(True),
                        )
                        .all()
                    )

                    # Generate sessions for each microcycle
                    for microcycle in microcycles:
                        generate_sessions_from_microcycle(
                            db=db,
                            microcycle_id=microcycle.id,
                            client_id=client_id,
                            trainer_id=trainer_id,
                            is_generic=True,  # Generic plan, so create generic sessions
                        )

            # Commit session creation
            db.commit()
        except Exception as e:
            # Log error but don't fail the entire assignment
            import logging

            logging.error(
                f"Failed to auto-create sessions for generic template "
                f"{template_id}: {e}",
                exc_info=True,
            )
            # Rollback session creation but keep the instance
            db.rollback()

    return instance


def convert_plan_to_template(
    db: Session,
    plan_id: int,
    template_data: schemas.TrainingPlanTemplateCreate,
) -> models.TrainingPlanTemplate:
    """
    Convert a specific plan to a template.

    This function:
    1. Gets the plan
    2. Creates a template (without client_id)
    3. Duplicates all cycles as template cycles
    4. Marks plan.was_converted_to_template = True
    5. Sets plan.template_id = new_template.id

    Args:
        db: Database session
        plan_id: ID of the plan to convert
        template_data: Template data (name, category, etc.)

    Returns:
        Created TrainingPlanTemplate
    """
    # 1. Get plan
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    # 2. Create template
    template = models.TrainingPlanTemplate(
        trainer_id=plan.trainer_id,
        name=template_data.name,
        description=template_data.description or plan.description,
        goal=template_data.goal or plan.goal,
        category=template_data.category,
        tags=template_data.tags,
        estimated_duration_weeks=template_data.estimated_duration_weeks
        or ((plan.end_date - plan.start_date).days // 7),
    )
    db.add(template)
    db.flush()

    # 3. Get plan cycles and duplicate as template cycles
    plan_macrocycles = get_macrocycles_by_plan(db, plan_id)

    for plan_macro in plan_macrocycles:
        # Create template macrocycle
        template_macro = models.Macrocycle(
            template_id=template.id,
            name=plan_macro.name,
            description=plan_macro.description,
            start_date=plan_macro.start_date,
            end_date=plan_macro.end_date,
            focus=plan_macro.focus,
            physical_quality=plan_macro.physical_quality,
            volume=plan_macro.volume,
            intensity=plan_macro.intensity,
            volume_intensity_ratio=plan_macro.volume_intensity_ratio,
        )
        db.add(template_macro)
        db.flush()

        # Get mesocycles
        plan_mesocycles = get_mesocycles_by_macrocycle(db, plan_macro.id)

        for plan_meso in plan_mesocycles:
            # Create template mesocycle
            template_meso = models.Mesocycle(
                macrocycle_id=template_macro.id,
                name=plan_meso.name,
                description=plan_meso.description,
                start_date=plan_meso.start_date,
                end_date=plan_meso.end_date,
                duration_weeks=plan_meso.duration_weeks,
                primary_focus=plan_meso.primary_focus,
                secondary_focus=plan_meso.secondary_focus,
                physical_quality=plan_meso.physical_quality,
                volume=plan_meso.volume,
                intensity=plan_meso.intensity,
                target_volume=plan_meso.target_volume,
                target_intensity=plan_meso.target_intensity,
            )
            db.add(template_meso)
            db.flush()

            # Get microcycles
            plan_microcycles = get_microcycles_by_mesocycle(db, plan_meso.id)

            for plan_micro in plan_microcycles:
                # Create template microcycle
                template_micro = models.Microcycle(
                    mesocycle_id=template_meso.id,
                    name=plan_micro.name,
                    description=plan_micro.description,
                    start_date=plan_micro.start_date,
                    end_date=plan_micro.end_date,
                    duration_days=plan_micro.duration_days,
                    training_frequency=plan_micro.training_frequency,
                    deload_week=plan_micro.deload_week,
                    notes=plan_micro.notes,
                    physical_quality=plan_micro.physical_quality,
                    volume=plan_micro.volume,
                    intensity=plan_micro.intensity,
                )
                db.add(template_micro)

    # 4. Mark plan
    plan.was_converted_to_template = True
    plan.template_id = template.id

    db.commit()
    db.refresh(template)

    return template


def assign_plan_to_another_client(
    db: Session,
    plan_id: int,
    client_id: int,
    start_date: date,
    end_date: date,
    trainer_id: int,
    name: Optional[str] = None,
) -> models.TrainingPlanInstance:
    """
    Assign a specific plan to another client (creates instance).

    Similar to assign_template_to_client but works with existing plans.

    Args:
        db: Database session
        plan_id: ID of the plan to assign
        client_id: ID of the new client
        start_date: Start date for the instance
        end_date: End date for the instance
        trainer_id: ID of the trainer
        name: Optional custom name

    Returns:
        Created TrainingPlanInstance
    """
    # Get plan
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    # Create instance
    instance_name = name or plan.name
    instance = models.TrainingPlanInstance(
        source_plan_id=plan_id,
        client_id=client_id,
        trainer_id=trainer_id,
        name=instance_name,
        description=plan.description,
        start_date=start_date,
        end_date=end_date,
        goal=plan.goal,
        status="active",
    )
    db.add(instance)
    db.flush()

    # Get plan cycles and duplicate
    plan_macrocycles = get_macrocycles_by_plan(db, plan_id)

    if plan_macrocycles:
        # Calculate date adjustment
        template_duration = (
            plan_macrocycles[-1].end_date - plan_macrocycles[0].start_date
        ).days
        instance_duration = (end_date - start_date).days
        date_ratio = (
            instance_duration / template_duration if template_duration > 0 else 1.0
        )
        plan_start = plan_macrocycles[0].start_date

        for plan_macro in plan_macrocycles:
            # Calculate new dates
            days_from_start = (plan_macro.start_date - plan_start).days
            new_start = start_date + timedelta(days=int(days_from_start * date_ratio))
            new_end_days = (plan_macro.end_date - plan_macro.start_date).days
            new_end = new_start + timedelta(days=int(new_end_days * date_ratio))

            # Create instance macrocycle
            instance_macro = models.Macrocycle(
                instance_id=instance.id,
                name=plan_macro.name,
                description=plan_macro.description,
                start_date=new_start,
                end_date=new_end,
                focus=plan_macro.focus,
                physical_quality=plan_macro.physical_quality,
                volume=plan_macro.volume,
                intensity=plan_macro.intensity,
                volume_intensity_ratio=plan_macro.volume_intensity_ratio,
            )
            db.add(instance_macro)
            db.flush()

            # Get mesocycles
            plan_mesocycles = get_mesocycles_by_macrocycle(db, plan_macro.id)

            for plan_meso in plan_mesocycles:
                # Calculate dates
                days_from_macro_start = (
                    plan_meso.start_date - plan_macro.start_date
                ).days
                meso_start = new_start + timedelta(
                    days=int(days_from_macro_start * date_ratio)
                )
                meso_end_days = (plan_meso.end_date - plan_meso.start_date).days
                meso_end = meso_start + timedelta(days=int(meso_end_days * date_ratio))

                # Create instance mesocycle
                instance_meso = models.Mesocycle(
                    macrocycle_id=instance_macro.id,
                    name=plan_meso.name,
                    description=plan_meso.description,
                    start_date=meso_start,
                    end_date=meso_end,
                    duration_weeks=plan_meso.duration_weeks,
                    primary_focus=plan_meso.primary_focus,
                    secondary_focus=plan_meso.secondary_focus,
                    physical_quality=plan_meso.physical_quality,
                    volume=plan_meso.volume,
                    intensity=plan_meso.intensity,
                    target_volume=plan_meso.target_volume,
                    target_intensity=plan_meso.target_intensity,
                )
                db.add(instance_meso)
                db.flush()

                # Get microcycles
                plan_microcycles = get_microcycles_by_mesocycle(db, plan_meso.id)

                for plan_micro in plan_microcycles:
                    # Calculate dates
                    days_from_meso_start = (
                        plan_micro.start_date - plan_meso.start_date
                    ).days
                    micro_start = meso_start + timedelta(
                        days=int(days_from_meso_start * date_ratio)
                    )
                    micro_end_days = (plan_micro.end_date - plan_micro.start_date).days
                    micro_end = micro_start + timedelta(
                        days=int(micro_end_days * date_ratio)
                    )

                    # Create instance microcycle
                    instance_micro = models.Microcycle(
                        mesocycle_id=instance_meso.id,
                        name=plan_micro.name,
                        description=plan_micro.description,
                        start_date=micro_start,
                        end_date=micro_end,
                        duration_days=plan_micro.duration_days,
                        training_frequency=plan_micro.training_frequency,
                        deload_week=plan_micro.deload_week,
                        notes=plan_micro.notes,
                        physical_quality=plan_micro.physical_quality,
                        volume=plan_micro.volume,
                        intensity=plan_micro.intensity,
                    )
                    db.add(instance_micro)

    db.commit()
    db.refresh(instance)

    return instance


# Volume Distribution Logic
def calculate_daily_volume_from_weekly(
    weekly_volume: float, training_frequency: int
) -> float:
    """
    Calculate daily volume from weekly volume based on training frequency.

    Example: If weekly volume = 10 series and training_frequency = 4 days/week,
    each day should get 10/4 = 2.5 series.

    Args:
        weekly_volume: Total weekly volume (e.g., 10 series per muscle group)
        training_frequency: Number of training days per week

    Returns:
        Recommended daily volume
    """
    if training_frequency <= 0:
        return 0.0
    return weekly_volume / training_frequency


def get_session_recommendations(
    db: Session,
    client_id: int,
    session_date: date,
    trainer_id: int,
) -> Dict:
    """
    Get session recommendations for a specific date based on:
    1. Client profile (experience, frequency, duration)
    2. Planned day values from coherence system (volume, intensity, physical_quality)
    3. Weekly volume distribution based on training_frequency

    This function:
    - Finds the active plan/instance for the client
    - Finds the microcycle (day) for the session_date
    - Gets planned volume/intensity for that day
    - Calculates recommended daily volume from weekly volume
    - Returns recommendations with coherence warnings

    Args:
        db: Database session
        client_id: ID of the client
        session_date: Date of the session
        trainer_id: ID of the trainer

    Returns:
        Dict with recommendations and coherence information
    """
    # 1. Get client profile for base recommendations
    client = get_client_profile(db, client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    # 2. Find active plan/instance for this client
    # Check instances first (new system)
    instances = get_training_plan_instances(
        db=db, client_id=client_id, trainer_id=trainer_id, skip=0, limit=10
    )
    active_instance = None
    for instance in instances:
        if (
            instance.is_active
            and instance.status == "active"
            and instance.start_date <= session_date <= instance.end_date
        ):
            active_instance = instance
            break

    # If no instance, check regular plans (backward compatibility)
    if not active_instance:
        # Get plans by client and filter by trainer
        plans = get_training_plans_by_client(
            db=db, client_id=client_id, skip=0, limit=100
        )
        active_plan = None
        for plan in plans:
            if (
                plan.trainer_id == trainer_id
                and plan.is_active
                and plan.status == "active"
                and plan.start_date <= session_date <= plan.end_date
            ):
                active_plan = plan
                break

        if not active_plan:
            return {
                "client_id": client_id,
                "session_date": session_date.isoformat(),
                "has_active_plan": False,
                "recommendations": None,
                "coherence_warnings": [],
            }

        # Get macrocycles for the plan
        macrocycles = get_macrocycles_by_plan(db, active_plan.id, skip=0, limit=100)
    else:
        # Get macrocycles for the instance
        macrocycles = get_macrocycles_by_instance(
            db, active_instance.id, skip=0, limit=100
        )

    # 3. Find the microcycle (day) for this session_date
    target_microcycle = None
    target_mesocycle = None
    target_macrocycle = None

    for macro in macrocycles:
        if macro.start_date <= session_date <= macro.end_date:
            target_macrocycle = macro
            mesocycles = get_mesocycles_by_macrocycle(db, macro.id)

            for meso in mesocycles:
                if meso.start_date <= session_date <= meso.end_date:
                    target_mesocycle = meso
                    microcycles = get_microcycles_by_mesocycle(db, meso.id)

                    for micro in microcycles:
                        if micro.start_date <= session_date <= micro.end_date:
                            target_microcycle = micro
                            break

                    if target_microcycle:
                        break

            if target_microcycle:
                break

    if not target_microcycle:
        return {
            "client_id": client_id,
            "session_date": session_date.isoformat(),
            "has_active_plan": True,
            "has_planned_day": False,
            "recommendations": None,
            "coherence_warnings": [],
        }

    # 4. Get planned values for the day (with inheritance)
    # Day values (or inherited from week)
    if target_microcycle.volume is not None and target_microcycle.intensity is not None:
        planned_day_volume = target_microcycle.volume
        planned_day_intensity = target_microcycle.intensity
        day_inherited = False
    else:
        # Inherit from week
        if (
            target_mesocycle.volume is not None
            and target_mesocycle.intensity is not None
        ):
            planned_day_volume = target_mesocycle.volume
            planned_day_intensity = target_mesocycle.intensity
            day_inherited = True
        else:
            # Inherit from month
            if (
                target_macrocycle.volume is not None
                and target_macrocycle.intensity is not None
            ):
                planned_day_volume = target_macrocycle.volume
                planned_day_intensity = target_macrocycle.intensity
                day_inherited = True
            else:
                # No planned values available
                return {
                    "client_id": client_id,
                    "session_date": session_date.isoformat(),
                    "has_active_plan": True,
                    "has_planned_day": True,
                    "has_planned_values": False,
                    "recommendations": None,
                    "coherence_warnings": [],
                }

    # 5. Get physical quality
    physical_quality = (
        target_microcycle.physical_quality
        or target_mesocycle.physical_quality
        or target_macrocycle.physical_quality
        or target_macrocycle.focus
    )

    # 6. Get training frequency from microcycle
    training_frequency = target_microcycle.training_frequency

    # 7. Calculate recommended daily volume from weekly volume
    # Convert volume scale (1-10) to actual units based on client profile
    # Use the same logic as /normalize-volume endpoint
    level_percentages = {
        1: 0.25,
        2: 0.25,
        3: 0.45,
        4: 0.45,
        5: 0.65,
        6: 0.65,
        7: 0.85,
        8: 0.85,
        9: 0.95,
        10: 0.95,
    }
    volume_level = int(round(planned_day_volume)) if planned_day_volume else 5
    volume_level = max(1, min(10, volume_level))  # Clamp to 1-10
    percentage = level_percentages.get(volume_level, 0.65)

    # Get client experience (default to intermediate if not set)
    client_experience = getattr(client, "experiencia", None) or getattr(
        client, "experience_level", None
    )
    if client_experience:
        experience_map = {
            "baja": "beginner",
            "media": "intermediate",
            "alta": "advanced",
            "low": "beginner",
            "medium": "intermediate",
            "high": "advanced",
        }
        experience = experience_map.get(str(client_experience).lower(), "intermediate")
    else:
        experience = "intermediate"

    # Determine modality from physical_quality
    modality_map = {
        "fuerza": "strength",
        "strength": "strength",
        "power": "strength",
        "aerobic": "aerobic",
        "cardio": "aerobic",
        "anaerobic": "anaerobic",
    }
    modality = modality_map.get(
        physical_quality.lower() if physical_quality else "", "strength"
    )

    # Calculate weekly volume in actual units
    if modality == "strength":
        base_ranges = {
            "beginner": (6, 10),
            "intermediate": (10, 15),
            "advanced": (15, 20),
        }
        base_min, base_max = base_ranges.get(experience, (10, 15))
        base_avg = (base_min + base_max) / 2.0
        weekly_volume_units = base_avg * percentage  # Series per muscle group per week
        unit_type = "series"
    else:
        # For aerobic/anaerobic, we'd need weekly_objective from client profile
        # For now, use scale directly
        weekly_volume_units = planned_day_volume * 10  # Placeholder conversion
        unit_type = "units"

    # Calculate daily volume from weekly volume and training frequency
    recommended_daily_volume_units = calculate_daily_volume_from_weekly(
        weekly_volume_units, training_frequency
    )

    # Keep scale values for coherence comparison
    recommended_daily_volume_scale = planned_day_volume  # Same scale for coherence
    recommended_daily_intensity_scale = (
        planned_day_intensity  # Same scale for coherence
    )

    # 8. Build recommendations
    recommendations = {
        "physical_quality": physical_quality,
        "modality": modality,
        "client_experience": experience,
        "planned_volume_scale": planned_day_volume,  # 1-10 scale
        "planned_intensity_scale": planned_day_intensity,  # 1-10 scale
        "training_frequency": training_frequency,
        "weekly_volume_units": round(
            weekly_volume_units, 2
        ),  # Actual units (e.g., series/week)
        "weekly_volume_unit_type": unit_type,
        "recommended_daily_volume_units": round(
            recommended_daily_volume_units, 2
        ),  # Actual units per day
        "recommended_daily_volume_scale": (
            recommended_daily_volume_scale
        ),  # 1-10 scale for coherence
        "recommended_daily_intensity_scale": (
            recommended_daily_intensity_scale
        ),  # 1-10 scale
        "day_inherited": day_inherited,
        "month_volume": target_macrocycle.volume,
        "month_intensity": target_macrocycle.intensity,
        "week_volume": target_mesocycle.volume,
        "week_intensity": target_mesocycle.intensity,
    }

    # 9. Coherence warnings (will be populated when session is created/updated)
    coherence_warnings = []

    return {
        "client_id": client_id,
        "session_date": session_date.isoformat(),
        "has_active_plan": True,
        "has_planned_day": True,
        "has_planned_values": True,
        "recommendations": recommendations,
        "coherence_warnings": coherence_warnings,
    }


def _count_overlap_days(
    start: date, end: date, window_start: date, window_end: date
) -> int:
    start_bound = max(start, window_start)
    end_bound = min(end, window_end)
    if end_bound < start_bound:
        return 0
    return (end_bound - start_bound).days + 1


def _quality_label(macro: models.Macrocycle) -> str:
    return (
        macro.physical_quality
        or macro.focus
        or (macro.name if getattr(macro, "name", None) else "General")
    )


def _aggregate_distribution(macros, window_start, window_end):
    quality_totals = defaultdict(float)
    total_days = 0
    for macro in macros:
        overlap = _count_overlap_days(
            macro.start_date, macro.end_date, window_start, window_end
        )
        if overlap <= 0:
            continue
        quality_totals[_quality_label(macro)] += overlap
        total_days += overlap
    if total_days == 0:
        return []
    return [
        {"name": label, "percentage": round((days / total_days) * 100, 2)}
        for label, days in sorted(
            quality_totals.items(), key=lambda item: item[1], reverse=True
        )
    ]


def _aggregate_load(macros, window_start, window_end, db: Optional[Session] = None):
    """
    Aggregate volume and intensity from macrocycles, mesocycles, and microcycles.
    Uses weighted averages based on overlap days for accurate calculations.
    """
    volume_sum = 0.0
    volume_days = 0.0
    intensity_sum = 0.0
    intensity_days = 0.0

    if not macros:
        return {
            "volume_level": 0.0,
            "intensity_level": 0.0,
        }

    macro_ids = [m.id for m in macros]

    # Batch query mesocycles and microcycles if db is available
    mesocycles_by_macro = {}
    microcycles_by_meso = {}

    if db:
        # Query all mesocycles for all macros at once
        all_mesocycles = (
            db.query(models.Mesocycle)
            .filter(
                models.Mesocycle.macrocycle_id.in_(macro_ids),
                models.Mesocycle.is_active.is_(True),
            )
            .all()
        )
        for meso in all_mesocycles:
            mesocycles_by_macro.setdefault(meso.macrocycle_id, []).append(meso)

        # Query all microcycles for all mesocycles at once
        if all_mesocycles:
            meso_ids = [m.id for m in all_mesocycles]
            all_microcycles = (
                db.query(models.Microcycle)
                .filter(
                    models.Microcycle.mesocycle_id.in_(meso_ids),
                    models.Microcycle.is_active.is_(True),
                )
                .all()
            )
            for micro in all_microcycles:
                microcycles_by_meso.setdefault(micro.mesocycle_id, []).append(micro)

    for macro in macros:
        # Check macrocycle values
        macro_overlap = _count_overlap_days(
            macro.start_date, macro.end_date, window_start, window_end
        )
        if macro_overlap > 0:
            if macro.volume is not None:
                volume_sum += macro.volume * macro_overlap
                volume_days += macro_overlap
            if macro.intensity is not None:
                intensity_sum += macro.intensity * macro_overlap
                intensity_days += macro_overlap

        # Check mesocycles within this macrocycle
        mesocycles = mesocycles_by_macro.get(macro.id, [])
        if not mesocycles and not db:
            # Try to access via relationship (may be lazy-loaded)
            mesocycles = getattr(macro, "mesocycles", [])

        for meso in mesocycles:
            if not meso.is_active:
                continue
            meso_overlap = _count_overlap_days(
                meso.start_date, meso.end_date, window_start, window_end
            )
            if meso_overlap > 0:
                if meso.volume is not None:
                    volume_sum += meso.volume * meso_overlap
                    volume_days += meso_overlap
                if meso.intensity is not None:
                    intensity_sum += meso.intensity * meso_overlap
                    intensity_days += meso_overlap

                # Check microcycles within this mesocycle
                microcycles = microcycles_by_meso.get(meso.id, [])
                if not microcycles and not db:
                    microcycles = getattr(meso, "microcycles", [])

                for micro in microcycles:
                    if not micro.is_active:
                        continue
                    micro_overlap = _count_overlap_days(
                        micro.start_date, micro.end_date, window_start, window_end
                    )
                    if micro_overlap > 0:
                        if micro.volume is not None:
                            volume_sum += micro.volume * micro_overlap
                            volume_days += micro_overlap
                        if micro.intensity is not None:
                            intensity_sum += micro.intensity * micro_overlap
                            intensity_days += micro_overlap

    return {
        "volume_level": round(volume_sum / volume_days, 2) if volume_days else 0.0,
        "intensity_level": (
            round(intensity_sum / intensity_days, 2) if intensity_days else 0.0
        ),
    }


def _avg(values: List[Optional[float]]) -> float:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 2) if clean else 0.0


def _find_active_plan_context(
    db: Session,
    client_id: int,
    trainer_id: Optional[int],
    window_start: date,
    window_end: date,
):
    """Return macrocycles/plan info for the plan overlapping the window."""
    instance_query = (
        db.query(models.TrainingPlanInstance)
        .filter(
            models.TrainingPlanInstance.client_id == client_id,
            models.TrainingPlanInstance.status == "active",
        )
        .order_by(models.TrainingPlanInstance.start_date.desc())
    )
    if trainer_id:
        instance_query = instance_query.filter(
            models.TrainingPlanInstance.trainer_id == trainer_id
        )
    for instance in instance_query.all():
        if instance.end_date >= window_start and instance.start_date <= window_end:
            macros = get_macrocycles_by_instance(
                db=db, instance_id=instance.id, limit=500
            )
            return {
                "macrocycles": macros,
                "plan_name": instance.name,
                "plan_goal": instance.goal,
                "plan_id": instance.source_plan_id,
                "instance_id": instance.id,
            }

    plan_query = (
        db.query(models.TrainingPlan)
        .filter(
            models.TrainingPlan.client_id == client_id,
            models.TrainingPlan.status == "active",
        )
        .order_by(models.TrainingPlan.start_date.desc())
    )
    if trainer_id:
        plan_query = plan_query.filter(models.TrainingPlan.trainer_id == trainer_id)
    for plan in plan_query.all():
        if plan.end_date >= window_start and plan.start_date <= window_end:
            macros = get_macrocycles_by_plan(db, plan.id, limit=500)
            return {
                "macrocycles": macros,
                "plan_name": plan.name,
                "plan_goal": plan.goal,
                "plan_id": plan.id,
                "instance_id": None,
            }
    return None


def get_client_training_plan_summary(
    db: Session,
    client_id: int,
    trainer_id: Optional[int] = None,
    year: Optional[int] = None,
) -> Dict:
    """Aggregate yearly training plan analytics for the Training Plan tab."""

    year_value = year or datetime.utcnow().year
    year_start = date(year_value, 1, 1)
    year_end = date(year_value, 12, 31)

    response = {
        "client_id": client_id,
        "year": year_value,
        "has_active_plan": False,
        "plan_name": None,
        "plan_goal": None,
        "distribution": [],
        "physical_qualities": [],
        "training_load": {"volume_level": 0.0, "intensity_level": 0.0},
        "yearly_progression": [],
        "summary": {
            "total_sessions_planned": 0,
            "sessions_completed": 0,
            "adherence_rate": 0.0,
            "narrative": "No active training plan for the selected year.",
        },
        "milestones": [],
    }

    plan_context = _find_active_plan_context(
        db=db,
        client_id=client_id,
        trainer_id=trainer_id,
        window_start=year_start,
        window_end=year_end,
    )
    if not plan_context:
        return response

    macros = plan_context["macrocycles"]
    distribution = _aggregate_distribution(macros, year_start, year_end)
    load = _aggregate_load(macros, year_start, year_end, db=db)
    progression = []
    for month in range(1, 13):
        days_in_month = calendar.monthrange(year_value, month)[1]
        month_start = date(year_value, month, 1)
        month_end = date(year_value, month, days_in_month)
        qualities = _aggregate_distribution(macros, month_start, month_end)
        load = _aggregate_load(macros, month_start, month_end, db=db)
        progression.append(
            {
                "month": month,
                "qualities": qualities,
                "volume_level": load["volume_level"],
                "intensity_level": load["intensity_level"],
            }
        )

    sessions = (
        db.query(models.TrainingSession)
        .filter(
            models.TrainingSession.client_id == client_id,
            models.TrainingSession.session_date >= year_start,
            models.TrainingSession.session_date <= year_end,
            models.TrainingSession.is_active.is_(True),
        )
        .all()
    )
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.status == "completed")
    adherence_rate = (
        round((completed_sessions / total_sessions) * 100, 2) if total_sessions else 0.0
    )

    top_quality = distribution[0]["name"] if distribution else None
    top_percentage = distribution[0]["percentage"] if distribution else 0.0

    narrative_parts = []
    if total_sessions:
        narrative_parts.append(
            (
                "The client completed "
                f"{completed_sessions} of {total_sessions} planned sessions "
                f"({adherence_rate:.0f}% adherence)."
            )
        )
    else:
        narrative_parts.append("No sessions have been scheduled for this year yet.")

    if top_quality:
        narrative_parts.append(
            f"The current emphasis is on {top_quality} ({top_percentage:.0f}%)."
        )
    if load["volume_level"] or load["intensity_level"]:
        narrative_parts.append(
            (
                f"Average volume ({load['volume_level']}/10) and intensity "
                f"({load['intensity_level']}/10) are aligned with the yearly target."
            )
        )

    milestones: List[schemas.MilestoneOut] = []
    plan_for_milestones = plan_context.get("plan_id")
    if plan_for_milestones:
        raw_milestones = get_milestones_by_plan(
            db, training_plan_id=plan_for_milestones, limit=100
        )
        milestones = [
            schemas.MilestoneOut.model_validate(milestone)
            for milestone in raw_milestones
        ]

    response.update(
        {
            "has_active_plan": True,
            "plan_name": plan_context.get("plan_name"),
            "plan_goal": plan_context.get("plan_goal"),
            "distribution": distribution,
            "physical_qualities": distribution,
            "training_load": load,
            "yearly_progression": progression,
            "summary": {
                "total_sessions_planned": total_sessions,
                "sessions_completed": completed_sessions,
                "adherence_rate": adherence_rate,
                "narrative": " ".join(narrative_parts).strip(),
            },
            "milestones": milestones,
        }
    )

    return response


def _sessions_distribution(sessions: List[models.TrainingSession]) -> Dict[str, float]:
    if not sessions:
        return {}
    counts = defaultdict(int)
    for session in sessions:
        key = (session.session_type or "General").strip().title()
        counts[key] += 1
    total = sum(counts.values())
    return {k: round((v / total) * 100, 2) for k, v in counts.items()}


def _calculate_alignment(
    planned_volume: float,
    actual_volume: float,
    planned_intensity: float,
    actual_intensity: float,
    planned_dist: List[Dict],
    actual_dist: Dict[str, float],
) -> float:
    volume_penalty = abs(planned_volume - actual_volume) / 10 * 40
    intensity_penalty = abs(planned_intensity - actual_intensity) / 10 * 40
    if planned_dist:
        diffs = []
        for item in planned_dist:
            diffs.append(abs(item["percentage"] - actual_dist.get(item["name"], 0.0)))
        quality_penalty = (sum(diffs) / len(diffs)) * 0.4
    else:
        quality_penalty = 0
    alignment = max(0.0, 100.0 - (volume_penalty + intensity_penalty + quality_penalty))
    return round(alignment, 2)


def _calculate_status(planned: float, actual: float, tolerance: float = 0.1) -> str:
    """Determine status: 'on_track' (green) or 'below_target' (red).
    For volume/intensity: tolerance is 10% of scale (1.0 out of 10).
    For percentages: tolerance is absolute difference (e.g., 5 percentage points).
    """
    if planned == 0:
        return "on_track" if actual >= 0 else "below_target"
    diff = abs(planned - actual)
    if diff <= tolerance:
        return "on_track"
    # If actual is significantly lower than planned, it's below target
    if actual < planned - tolerance:
        return "below_target"
    # If actual is higher or close, it's on track
    return "on_track"


def get_client_training_plan_monthly_summary(
    db: Session,
    client_id: int,
    trainer_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    week: Optional[int] = None,
) -> Dict:
    """Monthly breakdown used by the Training Plan - Monthly tab.
    If week (1-5) is provided, returns that specific week's
    distribution and training load.
    """

    today = datetime.utcnow().date()
    year_value = year or today.year
    month_value = month or today.month
    month_start = date(year_value, month_value, 1)
    month_end = date(
        year_value, month_value, calendar.monthrange(year_value, month_value)[1]
    )

    response = {
        "client_id": client_id,
        "year": year_value,
        "month": month_value,
        "has_active_plan": False,
        "plan_name": None,
        "plan_goal": None,
        "distribution": [],
        "physical_qualities": [],
        "training_load": {"volume_level": 0.0, "intensity_level": 0.0},
        "plan_alignment": 0.0,
        "planned_vs_actual": {
            "planned_volume": 0.0,
            "actual_volume": 0.0,
            "volume_status": "on_track",
            "planned_intensity": 0.0,
            "actual_intensity": 0.0,
            "intensity_status": "on_track",
            "qualities": [],
        },
        "weeks": [],
        "summary": {
            "total_sessions_planned": 0,
            "sessions_completed": 0,
            "adherence_rate": 0.0,
            "narrative": "No active training plan for this month.",
        },
    }

    plan_context = _find_active_plan_context(
        db,
        client_id=client_id,
        trainer_id=trainer_id,
        window_start=month_start,
        window_end=month_end,
    )
    if not plan_context:
        return response

    macros = plan_context["macrocycles"]
    distribution = _aggregate_distribution(macros, month_start, month_end)
    training_load = _aggregate_load(macros, month_start, month_end, db=db)

    # Fetch sessions for actual metrics
    sessions = (
        db.query(models.TrainingSession)
        .filter(
            models.TrainingSession.client_id == client_id,
            models.TrainingSession.session_date >= month_start,
            models.TrainingSession.session_date <= month_end,
            models.TrainingSession.is_active.is_(True),
        )
        .all()
    )
    completed_sessions = [s for s in sessions if s.status == "completed"]
    actual_distribution = _sessions_distribution(completed_sessions)

    planned_volume = training_load["volume_level"]
    planned_intensity = training_load["intensity_level"]
    actual_volume = _avg(
        [(s.actual_volume or s.planned_volume) for s in completed_sessions]
    )
    actual_intensity = _avg(
        [(s.actual_intensity or s.planned_intensity) for s in completed_sessions]
    )

    qualities_comparison = []
    actual_dist_lookup = actual_distribution
    for item in distribution:
        planned_pct = item["percentage"]
        actual_pct = actual_dist_lookup.get(item["name"], 0.0)
        status = _calculate_status(planned_pct, actual_pct, tolerance=5.0)
        qualities_comparison.append(
            {
                "name": item["name"],
                "planned_percentage": planned_pct,
                "actual_percentage": actual_pct,
                "status": status,
            }
        )

    plan_alignment = _calculate_alignment(
        planned_volume or 0.0,
        actual_volume or 0.0,
        planned_intensity or 0.0,
        actual_intensity or 0.0,
        distribution,
        actual_dist_lookup,
    )
    # Ensure plan_alignment is always a float
    plan_alignment = float(plan_alignment) if plan_alignment is not None else 0.0

    # Get annual plan values for "Planned vs Actual Average" comparison
    # (Figma shows "FROM ANNUAL PLAN" - compare against yearly plan, not monthly)
    year_start = date(year_value, 1, 1)
    year_end = date(year_value, 12, 31)
    annual_macros = _find_active_plan_context(
        db,
        client_id=client_id,
        trainer_id=trainer_id,
        window_start=year_start,
        window_end=year_end,
    )
    annual_planned_volume = planned_volume
    annual_planned_intensity = planned_intensity
    annual_planned_distribution = distribution
    if annual_macros:
        annual_macros_list = annual_macros.get("macrocycles", [])
        annual_dist = _aggregate_distribution(annual_macros_list, year_start, year_end)
        annual_load = _aggregate_load(annual_macros_list, year_start, year_end, db=db)
        annual_planned_volume = annual_load["volume_level"]
        annual_planned_intensity = annual_load["intensity_level"]
        annual_planned_distribution = annual_dist

    # Get monthly actual values (already calculated above)
    # Build annual qualities comparison for "Planned vs Actual Average"
    annual_qualities_comparison = []
    for item in annual_planned_distribution:
        planned_pct = item["percentage"]
        actual_pct = actual_dist_lookup.get(item["name"], 0.0)
        status = _calculate_status(planned_pct, actual_pct, tolerance=5.0)
        annual_qualities_comparison.append(
            {
                "name": item["name"],
                "planned_percentage": planned_pct,
                "actual_percentage": actual_pct,
                "status": status,
            }
        )

    # Weekly breakdown based on sessions (grouped by ISO week within month)
    weeks = []
    start_pointer = month_start
    week_index = 1
    while start_pointer <= month_end and week_index <= 5:
        end_pointer = min(start_pointer + timedelta(days=6), month_end)
        week_sessions = [
            s for s in sessions if start_pointer <= s.session_date <= end_pointer
        ]
        week_distribution = _sessions_distribution(week_sessions)
        week_distribution_items = [
            {"name": name, "percentage": pct} for name, pct in week_distribution.items()
        ]
        week_volume = (
            _avg([(s.planned_volume or 0.0) for s in week_sessions])
            or training_load["volume_level"]
        )
        week_intensity = (
            _avg([(s.planned_intensity or 0.0) for s in week_sessions])
            or training_load["intensity_level"]
        )
        weeks.append(
            {
                "week": week_index,
                "start_date": start_pointer,
                "end_date": end_pointer,
                "qualities": week_distribution_items
                or distribution,  # fallback to plan
                "volume_level": week_volume,
                "intensity_level": week_intensity,
            }
        )
        start_pointer = end_pointer + timedelta(days=1)
        week_index += 1

    # If a specific week is requested, use that week's data
    # for distribution and training_load
    selected_distribution = distribution
    selected_training_load = training_load
    if week is not None and 1 <= week <= len(weeks):
        selected_week = weeks[week - 1]  # week is 1-indexed
        selected_distribution = selected_week.get("qualities", distribution)
        selected_training_load = {
            "volume_level": selected_week.get(
                "volume_level", training_load["volume_level"]
            ),
            "intensity_level": selected_week.get(
                "intensity_level", training_load["intensity_level"]
            ),
        }

    # Calculate summary stats (Total Sessions Planned, Completed, Adherence Rate)
    total_sessions_planned = len(sessions)
    sessions_completed = len(completed_sessions)
    adherence_rate = (
        round((sessions_completed / total_sessions_planned * 100), 2)
        if total_sessions_planned > 0
        else 0.0
    )

    # Generate narrative
    primary_quality = (
        selected_distribution[0]["name"] if selected_distribution else "General"
    )
    primary_quality_pct = (
        selected_distribution[0]["percentage"] if selected_distribution else 0.0
    )
    narrative = (
        f"The client completed {sessions_completed} of {total_sessions_planned} "
        f"planned sessions ({int(adherence_rate)}% adherence). "
        f"The physical qualities distribution shows a balanced approach with "
        f"emphasis on {primary_quality.lower()} ({primary_quality_pct}%). "
        f"Current volume ({selected_training_load['volume_level']}/10) and "
        f"intensity ({selected_training_load['intensity_level']}/10) levels "
        f"are appropriate for the training phase."
    )

    response.update(
        {
            "has_active_plan": True,
            "plan_name": plan_context.get("plan_name"),
            "plan_goal": plan_context.get("plan_goal"),
            "distribution": selected_distribution,
            "physical_qualities": selected_distribution,
            "training_load": selected_training_load,
            "plan_alignment": plan_alignment,
            "planned_vs_actual": {
                "planned_volume": annual_planned_volume,
                "actual_volume": actual_volume,
                "volume_status": _calculate_status(
                    annual_planned_volume or 0.0, actual_volume or 0.0, tolerance=1.0
                ),
                "planned_intensity": annual_planned_intensity,
                "actual_intensity": actual_intensity,
                "intensity_status": _calculate_status(
                    annual_planned_intensity or 0.0,
                    actual_intensity or 0.0,
                    tolerance=1.0,
                ),
                "qualities": annual_qualities_comparison,
            },
            "weeks": weeks,
            "summary": {
                "total_sessions_planned": total_sessions_planned,
                "sessions_completed": sessions_completed,
                "adherence_rate": adherence_rate,
                "narrative": narrative,
            },
        }
    )
    return response


def get_client_training_plan_weekly_summary(
    db: Session,
    client_id: int,
    trainer_id: Optional[int] = None,
    week_start: Optional[date] = None,
    day: Optional[Union[str, date]] = None,
) -> Dict:
    """Weekly breakdown with session list (Training Plan - Weekly tab).
    If day (day name or date) is provided, returns that specific day's
    distribution and training load.
    """

    today = datetime.utcnow().date()
    week_start_date = week_start or (today - timedelta(days=today.weekday()))
    week_end_date = week_start_date + timedelta(days=6)

    response = {
        "client_id": client_id,
        "week_start": week_start_date,
        "week_end": week_end_date,
        "has_active_plan": False,
        "plan_name": None,
        "plan_goal": None,
        "distribution": [],
        "physical_qualities": [],
        "training_load": {"volume_level": 0.0, "intensity_level": 0.0},
        "plan_alignment": 0.0,
        "daily_progression": [],
        "planned_vs_actual": {
            "planned_volume": 0.0,
            "actual_volume": 0.0,
            "volume_status": "on_track",
            "planned_intensity": 0.0,
            "actual_intensity": 0.0,
            "intensity_status": "on_track",
            "qualities": [],
        },
        "sessions": [],
        "summary": {
            "total_sessions_planned": 0,
            "sessions_completed": 0,
            "adherence_rate": 0.0,
            "narrative": "No active training plan for this week.",
        },
    }

    plan_context = _find_active_plan_context(
        db,
        client_id=client_id,
        trainer_id=trainer_id,
        window_start=week_start_date,
        window_end=week_end_date,
    )
    if not plan_context:
        return response

    macros = plan_context["macrocycles"]
    distribution = _aggregate_distribution(macros, week_start_date, week_end_date)
    training_load = _aggregate_load(macros, week_start_date, week_end_date, db=db)

    sessions = (
        db.query(models.TrainingSession)
        .filter(
            models.TrainingSession.client_id == client_id,
            models.TrainingSession.session_date >= week_start_date,
            models.TrainingSession.session_date <= week_end_date,
            models.TrainingSession.is_active.is_(True),
        )
        .order_by(models.TrainingSession.session_date.asc())
        .all()
    )

    completed_sessions = [s for s in sessions if s.status == "completed"]
    actual_distribution = _sessions_distribution(completed_sessions)
    planned_volume = training_load["volume_level"]
    planned_intensity = training_load["intensity_level"]
    actual_volume = _avg(
        [(s.actual_volume or s.planned_volume) for s in completed_sessions]
    )
    actual_intensity = _avg(
        [(s.actual_intensity or s.planned_intensity) for s in completed_sessions]
    )

    qualities_comparison = []
    for item in distribution:
        qualities_comparison.append(
            {
                "name": item["name"],
                "planned_percentage": item["percentage"],
                "actual_percentage": actual_distribution.get(item["name"], 0.0),
            }
        )

    # Calculate plan alignment
    plan_alignment = _calculate_alignment(
        planned_volume or 0.0,
        actual_volume or 0.0,
        planned_intensity or 0.0,
        actual_intensity or 0.0,
        distribution,
        actual_distribution,
    )
    plan_alignment = float(plan_alignment) if plan_alignment is not None else 0.0

    # Get monthly plan values for "Planned vs Actual Average" comparison
    # (Figma shows "FROM MONTHLY PLAN" - compare against month, not just week)
    month_start = date(week_start_date.year, week_start_date.month, 1)
    month_end = date(
        week_start_date.year,
        week_start_date.month,
        calendar.monthrange(week_start_date.year, week_start_date.month)[1],
    )
    monthly_macros = _find_active_plan_context(
        db,
        client_id=client_id,
        trainer_id=trainer_id,
        window_start=month_start,
        window_end=month_end,
    )
    monthly_planned_volume = planned_volume
    monthly_planned_intensity = planned_intensity
    monthly_planned_distribution = distribution
    if monthly_macros:
        monthly_macros_list = monthly_macros.get("macrocycles", [])
        monthly_dist = _aggregate_distribution(
            monthly_macros_list, month_start, month_end
        )
        monthly_load = _aggregate_load(
            monthly_macros_list, month_start, month_end, db=db
        )
        monthly_planned_volume = monthly_load["volume_level"]
        monthly_planned_intensity = monthly_load["intensity_level"]
        monthly_planned_distribution = monthly_dist

    # Get monthly actual values (all completed sessions in the month)
    monthly_sessions = (
        db.query(models.TrainingSession)
        .filter(
            models.TrainingSession.client_id == client_id,
            models.TrainingSession.session_date >= month_start,
            models.TrainingSession.session_date <= month_end,
            models.TrainingSession.is_active.is_(True),
            models.TrainingSession.status == "completed",
        )
        .all()
    )
    monthly_actual_distribution = _sessions_distribution(monthly_sessions)
    monthly_actual_volume = _avg(
        [(s.actual_volume or s.planned_volume) for s in monthly_sessions]
    )
    monthly_actual_intensity = _avg(
        [(s.actual_intensity or s.planned_intensity) for s in monthly_sessions]
    )

    # Build monthly qualities comparison for "Planned vs Actual Average"
    monthly_qualities_comparison = []
    for item in monthly_planned_distribution:
        planned_pct = item["percentage"]
        actual_pct = monthly_actual_distribution.get(item["name"], 0.0)
        status = _calculate_status(planned_pct, actual_pct, tolerance=5.0)
        monthly_qualities_comparison.append(
            {
                "name": item["name"],
                "planned_percentage": planned_pct,
                "actual_percentage": actual_pct,
                "status": status,
            }
        )

    # Daily progression (Mon-Sun) for the weekly progression chart
    daily_progression = []
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    current_date = week_start_date
    for day_idx in range(7):
        day_sessions = [s for s in sessions if s.session_date == current_date]
        day_distribution = _sessions_distribution(day_sessions)
        day_distribution_items = [
            {"name": name, "percentage": pct} for name, pct in day_distribution.items()
        ]
        # If no sessions, use plan distribution for that day
        if not day_distribution_items:
            day_distribution_items = distribution

        day_volume = (
            _avg([(s.planned_volume or 0.0) for s in day_sessions])
            or training_load["volume_level"]
        )
        day_intensity = (
            _avg([(s.planned_intensity or 0.0) for s in day_sessions])
            or training_load["intensity_level"]
        )

        daily_progression.append(
            {
                "day_name": day_names[day_idx],
                "date": current_date,
                "qualities": day_distribution_items,
                "volume_level": day_volume,
                "intensity_level": day_intensity,
            }
        )
        current_date += timedelta(days=1)

    session_entries = []
    for session in sessions:
        session_entries.append(
            {
                "session_id": session.id,
                "session_date": session.session_date,
                "session_name": session.session_name,
                "session_type": session.session_type,
                "status": session.status,
                "planned_volume": session.planned_volume,
                "planned_intensity": session.planned_intensity,
                "actual_volume": session.actual_volume,
                "actual_intensity": session.actual_intensity,
            }
        )

    # If a specific day is requested, use that day's data
    # for distribution and training_load
    selected_distribution = distribution
    selected_training_load = training_load
    if day is not None:
        selected_day_data = None
        # Try to find by date first
        if isinstance(day, date):
            selected_day_data = next(
                (d for d in daily_progression if d["date"] == day), None
            )
        else:
            # Try to find by day name (case-insensitive)
            day_name_lower = str(day).lower()
            day_name_map = {
                "monday": "Mon",
                "tuesday": "Tue",
                "wednesday": "Wed",
                "thursday": "Thu",
                "friday": "Fri",
                "saturday": "Sat",
                "sunday": "Sun",
                "mon": "Mon",
                "tue": "Tue",
                "wed": "Wed",
                "thu": "Thu",
                "fri": "Fri",
                "sat": "Sat",
                "sun": "Sun",
            }
            day_name = day_name_map.get(day_name_lower)
            if day_name:
                selected_day_data = next(
                    (d for d in daily_progression if d["day_name"] == day_name), None
                )

        if selected_day_data:
            selected_distribution = selected_day_data.get("qualities", distribution)
            selected_training_load = {
                "volume_level": selected_day_data.get(
                    "volume_level", training_load["volume_level"]
                ),
                "intensity_level": selected_day_data.get(
                    "intensity_level", training_load["intensity_level"]
                ),
            }

    # Calculate summary stats (Total Sessions Planned, Completed, Adherence Rate)
    total_sessions_planned = len(sessions)
    sessions_completed = len(completed_sessions)
    adherence_rate = (
        round((sessions_completed / total_sessions_planned * 100), 2)
        if total_sessions_planned > 0
        else 0.0
    )

    # Generate narrative
    primary_quality = (
        selected_distribution[0]["name"] if selected_distribution else "General"
    )
    primary_quality_pct = (
        selected_distribution[0]["percentage"] if selected_distribution else 0.0
    )
    narrative = (
        f"The client completed {sessions_completed} of {total_sessions_planned} "
        f"planned sessions ({int(adherence_rate)}% adherence). "
        f"The physical qualities distribution shows a balanced approach with "
        f"emphasis on {primary_quality.lower()} ({primary_quality_pct}%). "
        f"Current volume ({selected_training_load['volume_level']}/10) and "
        f"intensity ({selected_training_load['intensity_level']}/10) levels "
        f"are appropriate for the training phase."
    )

    response.update(
        {
            "has_active_plan": True,
            "plan_name": plan_context.get("plan_name"),
            "plan_goal": plan_context.get("plan_goal"),
            "distribution": selected_distribution,
            "physical_qualities": selected_distribution,
            "training_load": selected_training_load,
            "plan_alignment": plan_alignment,
            "daily_progression": daily_progression,
            "planned_vs_actual": {
                "planned_volume": monthly_planned_volume,
                "actual_volume": monthly_actual_volume,
                "volume_status": _calculate_status(
                    monthly_planned_volume or 0.0,
                    monthly_actual_volume or 0.0,
                    tolerance=1.0,
                ),
                "planned_intensity": monthly_planned_intensity,
                "actual_intensity": monthly_actual_intensity,
                "intensity_status": _calculate_status(
                    monthly_planned_intensity or 0.0,
                    monthly_actual_intensity or 0.0,
                    tolerance=1.0,
                ),
                "qualities": monthly_qualities_comparison,
            },
            "sessions": session_entries,
            "summary": {
                "total_sessions_planned": total_sessions_planned,
                "sessions_completed": sessions_completed,
                "adherence_rate": adherence_rate,
                "narrative": narrative,
            },
        }
    )
    return response


def validate_session_coherence(
    db: Session,
    session_id: int,
    planned_volume: Optional[float] = None,
    planned_intensity: Optional[float] = None,
) -> Dict:
    """
    Validate session coherence against planned day values.

    This function:
    - Gets the session and its microcycle
    - Gets planned volume/intensity for that day
    - Compares session values with planned values
    - Returns coherence warnings if deviation > threshold

    Args:
        db: Database session
        session_id: ID of the training session
        planned_volume: Session planned volume (if None, gets from session)
        planned_intensity: Session planned intensity (if None, gets from session)

    Returns:
        Dict with coherence validation results
    """
    session = get_training_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")

    # Get microcycle
    microcycle = get_microcycle(db, session.microcycle_id)
    if not microcycle:
        return {
            "session_id": session_id,
            "has_planned_values": False,
            "coherence_warnings": [],
        }

    # Get planned day values (with inheritance)
    mesocycle = get_mesocycle(db, microcycle.mesocycle_id)
    macrocycle = get_macrocycle(db, mesocycle.macrocycle_id)

    # Day values or inherited
    if microcycle.volume is not None and microcycle.intensity is not None:
        planned_day_volume = microcycle.volume
        planned_day_intensity = microcycle.intensity
    elif mesocycle.volume is not None and mesocycle.intensity is not None:
        planned_day_volume = mesocycle.volume
        planned_day_intensity = mesocycle.intensity
    elif macrocycle.volume is not None and macrocycle.intensity is not None:
        planned_day_volume = macrocycle.volume
        planned_day_intensity = macrocycle.intensity
    else:
        return {
            "session_id": session_id,
            "has_planned_values": False,
            "coherence_warnings": [],
        }

    # Get session values
    session_volume = planned_volume or session.planned_volume
    session_intensity = planned_intensity or session.planned_intensity

    if session_volume is None or session_intensity is None:
        return {
            "session_id": session_id,
            "has_planned_values": True,
            "session_has_values": False,
            "coherence_warnings": [],
        }

    # Calculate deviation
    volume_deviation = (
        abs(session_volume - planned_day_volume) / planned_day_volume * 100
        if planned_day_volume > 0
        else 0
    )
    intensity_deviation = (
        abs(session_intensity - planned_day_intensity) / planned_day_intensity * 100
        if planned_day_intensity > 0
        else 0
    )

    deviation_threshold = 20.0  # 20% threshold
    warnings = []

    if volume_deviation > deviation_threshold:
        warnings.append(
            {
                "type": "volume_deviation",
                "message": (
                    f"Session volume ({session_volume:.1f}) deviates "
                    f"{volume_deviation:.1f}% from planned day volume "
                    f"({planned_day_volume:.1f})"
                ),
                "deviation_percentage": volume_deviation,
                "planned_value": planned_day_volume,
                "actual_value": session_volume,
            }
        )

    if intensity_deviation > deviation_threshold:
        warnings.append(
            {
                "type": "intensity_deviation",
                "message": (
                    f"Session intensity ({session_intensity:.1f}) deviates "
                    f"{intensity_deviation:.1f}% from planned day intensity "
                    f"({planned_day_intensity:.1f})"
                ),
                "deviation_percentage": intensity_deviation,
                "planned_value": planned_day_intensity,
                "actual_value": session_intensity,
            }
        )

    coherence_pct = max(
        0, 100 - (volume_deviation + intensity_deviation) / 2
    )  # Average deviation

    return {
        "session_id": session_id,
        "has_planned_values": True,
        "session_has_values": True,
        "planned_volume": planned_day_volume,
        "planned_intensity": planned_day_intensity,
        "session_volume": session_volume,
        "session_intensity": session_intensity,
        "volume_deviation": volume_deviation,
        "intensity_deviation": intensity_deviation,
        "coherence_percentage": coherence_pct,
        "coherence_warnings": warnings,
    }


# Coherence Calculation System
def calculate_plan_coherence(
    db: Session,
    plan_id: int,
    deviation_threshold: float = 20.0,  # Percentage threshold for warnings
) -> Dict:
    """
    Calculate coherence between month (Macrocycle) → week (Mesocycle) →
    day (Microcycle).

    Coherence is calculated by comparing volume/intensity values across levels:
    - Month (Macrocycle) is the baseline
    - Week (Mesocycle) should match month values
    - Day (Microcycle) should match week values

    Returns coherence percentage and warnings for deviations.

    Args:
        db: Database session
        plan_id: ID of the training plan
        deviation_threshold: Percentage threshold for warnings (default 20%)

    Returns:
        Dict with coherence results for each level
    """
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Plan {plan_id} not found")

    # Get all cycles for the plan
    macrocycles = get_macrocycles_by_plan(db, plan_id)

    month_coherence = []
    week_coherence = []
    day_coherence = []
    overall_coherences = []

    for macro in macrocycles:
        if macro.volume is None or macro.intensity is None:
            continue

        # Month coherence (baseline - always 100% for itself)
        month_coherence.append(
            {
                "macrocycle_id": macro.id,
                "macrocycle_name": macro.name,
                "physical_quality": macro.physical_quality or macro.focus,
                "planned_volume": macro.volume,
                "planned_intensity": macro.intensity,
                "coherence_percentage": 100.0,
                "deviation_warning": False,
            }
        )

        # Get mesocycles (weeks) for this macrocycle
        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)

        for meso in mesocycles:
            if meso.volume is None or meso.intensity is None:
                # Inheritance: if week doesn't have values, use month values
                meso_volume = macro.volume
                meso_intensity = macro.intensity
                inherited = True
            else:
                meso_volume = meso.volume
                meso_intensity = meso.intensity
                inherited = False

            # Calculate deviation from month
            volume_deviation = (
                abs(meso_volume - macro.volume) / macro.volume * 100
                if macro.volume > 0
                else 0
            )
            intensity_deviation = (
                abs(meso_intensity - macro.intensity) / macro.intensity * 100
                if macro.intensity > 0
                else 0
            )
            avg_deviation = (volume_deviation + intensity_deviation) / 2
            coherence_pct = max(0, 100 - avg_deviation)

            week_coherence.append(
                {
                    "mesocycle_id": meso.id,
                    "mesocycle_name": meso.name,
                    "macrocycle_id": macro.id,
                    "physical_quality": meso.physical_quality or meso.primary_focus,
                    "planned_volume": meso_volume,
                    "planned_intensity": meso_intensity,
                    "month_volume": macro.volume,
                    "month_intensity": macro.intensity,
                    "coherence_percentage": coherence_pct,
                    "deviation_warning": avg_deviation > deviation_threshold,
                    "inherited": inherited,
                }
            )
            overall_coherences.append(coherence_pct)

            # Get microcycles (days) for this mesocycle
            microcycles = get_microcycles_by_mesocycle(db, meso.id)

            for micro in microcycles:
                if micro.volume is None or micro.intensity is None:
                    # Inheritance: if day doesn't have values, use week values
                    micro_volume = meso_volume
                    micro_intensity = meso_intensity
                    inherited = True
                else:
                    micro_volume = micro.volume
                    micro_intensity = micro.intensity
                    inherited = False

                # Calculate deviation from week
                volume_deviation = (
                    abs(micro_volume - meso_volume) / meso_volume * 100
                    if meso_volume > 0
                    else 0
                )
                intensity_deviation = (
                    abs(micro_intensity - meso_intensity) / meso_intensity * 100
                    if meso_intensity > 0
                    else 0
                )
                avg_deviation = (volume_deviation + intensity_deviation) / 2
                coherence_pct = max(0, 100 - avg_deviation)

                day_coherence.append(
                    {
                        "microcycle_id": micro.id,
                        "microcycle_name": micro.name,
                        "mesocycle_id": meso.id,
                        "physical_quality": micro.physical_quality
                        or meso.primary_focus,
                        "planned_volume": micro_volume,
                        "planned_intensity": micro_intensity,
                        "week_volume": meso_volume,
                        "week_intensity": meso_intensity,
                        "coherence_percentage": coherence_pct,
                        "deviation_warning": avg_deviation > deviation_threshold,
                        "inherited": inherited,
                    }
                )
                overall_coherences.append(coherence_pct)

    # Calculate overall coherence
    overall_coherence = (
        sum(overall_coherences) / len(overall_coherences)
        if overall_coherences
        else 100.0
    )

    return {
        "plan_id": plan_id,
        "month_coherence": month_coherence,
        "week_coherence": week_coherence,
        "day_coherence": day_coherence,
        "overall_coherence": overall_coherence,
        "deviation_threshold": deviation_threshold,
    }


# Training Plan CRUD (existing, modified)
def create_training_plan(db: Session, plan_data: schemas.TrainingPlanCreate):
    db_plan = models.TrainingPlan(**plan_data.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan


def get_training_plans(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.TrainingPlan]:
    return db.query(models.TrainingPlan).offset(skip).limit(limit).all()


def get_training_plans_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.TrainingPlan]:
    return (
        db.query(models.TrainingPlan)
        .filter(models.TrainingPlan.trainer_id == trainer_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_training_plans_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.TrainingPlan]:
    return (
        db.query(models.TrainingPlan)
        .filter(models.TrainingPlan.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_training_plan(db: Session, plan_id: int):
    return (
        db.query(models.TrainingPlan).filter(models.TrainingPlan.id == plan_id).first()
    )


def update_training_plan(
    db: Session, plan_id: int, plan_data: schemas.TrainingPlanUpdate
):
    db_plan = get_training_plan(db, plan_id)
    if not db_plan:
        return None

    update_data = plan_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_plan, field, value)

    db.commit()
    db.refresh(db_plan)
    return db_plan


def delete_training_plan(db: Session, plan_id: int) -> bool:
    db_plan = get_training_plan(db, plan_id)
    if not db_plan:
        return False

    db.delete(db_plan)
    db.commit()
    return True


# Milestone CRUD operations
def create_milestone(
    db: Session, milestone_data: schemas.MilestoneCreate, training_plan_id: int
):
    """Create a new milestone for a training plan"""
    milestone_dict = milestone_data.model_dump(exclude_unset=True)
    milestone_dict["training_plan_id"] = training_plan_id
    db_milestone = models.Milestone(**milestone_dict)
    db.add(db_milestone)
    db.commit()
    db.refresh(db_milestone)
    return db_milestone


def get_milestones_by_plan(
    db: Session, training_plan_id: int, skip: int = 0, limit: int = 100
) -> List[models.Milestone]:
    """Get all milestones for a training plan"""
    return (
        db.query(models.Milestone)
        .filter(models.Milestone.training_plan_id == training_plan_id)
        .filter(models.Milestone.is_active.is_(True))
        .order_by(models.Milestone.milestone_date)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_milestone(db: Session, milestone_id: int):
    """Get a milestone by ID"""
    return (
        db.query(models.Milestone)
        .filter(models.Milestone.id == milestone_id)
        .filter(models.Milestone.is_active.is_(True))
        .first()
    )


def update_milestone(
    db: Session, milestone_id: int, milestone_data: schemas.MilestoneUpdate
):
    """Update a milestone"""
    db_milestone = get_milestone(db, milestone_id)
    if not db_milestone:
        return None

    update_data = milestone_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_milestone, field, value)

    db.commit()
    db.refresh(db_milestone)
    return db_milestone


def delete_milestone(db: Session, milestone_id: int) -> bool:
    """Soft delete a milestone"""
    db_milestone = get_milestone(db, milestone_id)
    if not db_milestone:
        return False

    db_milestone.is_active = False
    db.commit()
    return True


# Macrocycle CRUD operations
def create_macrocycle(db: Session, macrocycle_data: schemas.MacrocycleCreate):
    db_macrocycle = models.Macrocycle(**macrocycle_data.model_dump())
    db.add(db_macrocycle)
    db.commit()
    db.refresh(db_macrocycle)
    return db_macrocycle


def get_macrocycles(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Macrocycle]:
    return db.query(models.Macrocycle).offset(skip).limit(limit).all()


def get_macrocycles_by_plan(
    db: Session, training_plan_id: int, skip: int = 0, limit: int = 100
) -> List[models.Macrocycle]:
    return (
        db.query(models.Macrocycle)
        .filter(models.Macrocycle.training_plan_id == training_plan_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_macrocycle(db: Session, macrocycle_id: int):
    return (
        db.query(models.Macrocycle)
        .filter(models.Macrocycle.id == macrocycle_id)
        .first()
    )


def update_macrocycle(
    db: Session, macrocycle_id: int, macrocycle_data: schemas.MacrocycleUpdate
):
    db_macrocycle = get_macrocycle(db, macrocycle_id)
    if not db_macrocycle:
        return None

    update_data = macrocycle_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_macrocycle, field, value)

    db.commit()
    db.refresh(db_macrocycle)
    return db_macrocycle


def delete_macrocycle(db: Session, macrocycle_id: int) -> bool:
    db_macrocycle = get_macrocycle(db, macrocycle_id)
    if not db_macrocycle:
        return False

    db.delete(db_macrocycle)
    db.commit()
    return True


# Mesocycle CRUD operations
def create_mesocycle(db: Session, mesocycle_data: schemas.MesocycleCreate):
    db_mesocycle = models.Mesocycle(**mesocycle_data.model_dump())
    db.add(db_mesocycle)
    db.commit()
    db.refresh(db_mesocycle)
    return db_mesocycle


def get_mesocycles(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Mesocycle]:
    return db.query(models.Mesocycle).offset(skip).limit(limit).all()


def get_mesocycles_by_macrocycle(
    db: Session, macrocycle_id: int, skip: int = 0, limit: int = 100
) -> List[models.Mesocycle]:
    return (
        db.query(models.Mesocycle)
        .filter(models.Mesocycle.macrocycle_id == macrocycle_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_mesocycle(db: Session, mesocycle_id: int):
    return (
        db.query(models.Mesocycle).filter(models.Mesocycle.id == mesocycle_id).first()
    )


# ============================================================================
# Bottom-Up Propagation System (micro → meso → macro)
# ============================================================================


def _recalculate_mesocycle_from_microcycles(db: Session, mesocycle_id: int) -> Dict:
    """
    Recalculate mesocycle volume/intensity from its child microcycles.
    Uses weighted average based on microcycle duration (days).

    Returns dict with previous values, new values, and whether changes occurred.
    """
    mesocycle = get_mesocycle(db, mesocycle_id)
    if not mesocycle:
        return {"error": f"Mesocycle {mesocycle_id} not found"}

    microcycles = get_microcycles_by_mesocycle(db, mesocycle_id)
    active_micros = [m for m in microcycles if m.is_active]

    if not active_micros:
        return {
            "cycle_id": mesocycle_id,
            "cycle_type": "mesocycle",
            "cycle_name": mesocycle.name,
            "previous_volume": mesocycle.volume,
            "previous_intensity": mesocycle.intensity,
            "new_volume": mesocycle.volume,
            "new_intensity": mesocycle.intensity,
            "children_count": 0,
            "changed": False,
        }

    # Calculate weighted averages based on duration
    volume_sum = 0.0
    volume_days = 0.0
    intensity_sum = 0.0
    intensity_days = 0.0

    for micro in active_micros:
        days = micro.duration_days or 7  # Default to 7 days
        if micro.volume is not None:
            volume_sum += micro.volume * days
            volume_days += days
        if micro.intensity is not None:
            intensity_sum += micro.intensity * days
            intensity_days += days

    # Store previous values
    previous_volume = mesocycle.volume
    previous_intensity = mesocycle.intensity

    # Calculate new values (only if children have values)
    new_volume = round(volume_sum / volume_days, 2) if volume_days > 0 else None
    new_intensity = (
        round(intensity_sum / intensity_days, 2) if intensity_days > 0 else None
    )

    # Determine if values actually changed
    changed = False
    if new_volume is not None and new_volume != previous_volume:
        mesocycle.volume = new_volume
        changed = True
    if new_intensity is not None and new_intensity != previous_intensity:
        mesocycle.intensity = new_intensity
        changed = True

    if changed:
        db.commit()
        db.refresh(mesocycle)

    return {
        "cycle_id": mesocycle_id,
        "cycle_type": "mesocycle",
        "cycle_name": mesocycle.name,
        "previous_volume": previous_volume,
        "previous_intensity": previous_intensity,
        "new_volume": new_volume if new_volume is not None else previous_volume,
        "new_intensity": (
            new_intensity if new_intensity is not None else previous_intensity
        ),
        "children_count": len(active_micros),
        "changed": changed,
    }


def _recalculate_macrocycle_from_mesocycles(db: Session, macrocycle_id: int) -> Dict:
    """
    Recalculate macrocycle volume/intensity from its child mesocycles.
    Uses weighted average based on mesocycle duration (weeks).

    Returns dict with previous values, new values, and whether changes occurred.
    """
    macrocycle = get_macrocycle(db, macrocycle_id)
    if not macrocycle:
        return {"error": f"Macrocycle {macrocycle_id} not found"}

    mesocycles = get_mesocycles_by_macrocycle(db, macrocycle_id)
    active_mesos = [m for m in mesocycles if m.is_active]

    if not active_mesos:
        return {
            "cycle_id": macrocycle_id,
            "cycle_type": "macrocycle",
            "cycle_name": macrocycle.name,
            "previous_volume": macrocycle.volume,
            "previous_intensity": macrocycle.intensity,
            "new_volume": macrocycle.volume,
            "new_intensity": macrocycle.intensity,
            "children_count": 0,
            "changed": False,
        }

    # Calculate weighted averages based on duration
    volume_sum = 0.0
    volume_weeks = 0.0
    intensity_sum = 0.0
    intensity_weeks = 0.0

    for meso in active_mesos:
        weeks = meso.duration_weeks or 4  # Default to 4 weeks
        if meso.volume is not None:
            volume_sum += meso.volume * weeks
            volume_weeks += weeks
        if meso.intensity is not None:
            intensity_sum += meso.intensity * weeks
            intensity_weeks += weeks

    # Store previous values
    previous_volume = macrocycle.volume
    previous_intensity = macrocycle.intensity

    # Calculate new values (only if children have values)
    new_volume = round(volume_sum / volume_weeks, 2) if volume_weeks > 0 else None
    new_intensity = (
        round(intensity_sum / intensity_weeks, 2) if intensity_weeks > 0 else None
    )

    # Determine if values actually changed
    changed = False
    if new_volume is not None and new_volume != previous_volume:
        macrocycle.volume = new_volume
        changed = True
    if new_intensity is not None and new_intensity != previous_intensity:
        macrocycle.intensity = new_intensity
        changed = True

    if changed:
        db.commit()
        db.refresh(macrocycle)

    return {
        "cycle_id": macrocycle_id,
        "cycle_type": "macrocycle",
        "cycle_name": macrocycle.name,
        "previous_volume": previous_volume,
        "previous_intensity": previous_intensity,
        "new_volume": new_volume if new_volume is not None else previous_volume,
        "new_intensity": (
            new_intensity if new_intensity is not None else previous_intensity
        ),
        "children_count": len(active_mesos),
        "changed": changed,
    }


def update_mesocycle(
    db: Session, mesocycle_id: int, mesocycle_data: schemas.MesocycleUpdate
):
    db_mesocycle = get_mesocycle(db, mesocycle_id)
    if not db_mesocycle:
        return None

    # Extract propagate_up before applying other updates
    propagate_up = (
        mesocycle_data.propagate_up
        if hasattr(mesocycle_data, "propagate_up")
        else False
    )

    update_data = mesocycle_data.model_dump(exclude_unset=True)
    # Remove propagate_up from update_data as it's not a model field
    update_data.pop("propagate_up", None)

    for field, value in update_data.items():
        setattr(db_mesocycle, field, value)

    db.commit()
    db.refresh(db_mesocycle)

    # Bottom-up propagation: recalculate parent macrocycle if requested
    if propagate_up:
        _recalculate_macrocycle_from_mesocycles(db, db_mesocycle.macrocycle_id)

    return db_mesocycle


def delete_mesocycle(db: Session, mesocycle_id: int) -> bool:
    db_mesocycle = get_mesocycle(db, mesocycle_id)
    if not db_mesocycle:
        return False

    db.delete(db_mesocycle)
    db.commit()
    return True


# Microcycle CRUD operations
def create_microcycle(db: Session, microcycle_data: schemas.MicrocycleCreate):
    db_microcycle = models.Microcycle(**microcycle_data.model_dump())
    db.add(db_microcycle)
    db.commit()
    db.refresh(db_microcycle)
    return db_microcycle


def get_microcycles(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.Microcycle]:
    return db.query(models.Microcycle).offset(skip).limit(limit).all()


def get_microcycles_by_mesocycle(
    db: Session, mesocycle_id: int, skip: int = 0, limit: int = 100
) -> List[models.Microcycle]:
    return (
        db.query(models.Microcycle)
        .filter(models.Microcycle.mesocycle_id == mesocycle_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_microcycle(db: Session, microcycle_id: int):
    return (
        db.query(models.Microcycle)
        .filter(models.Microcycle.id == microcycle_id)
        .first()
    )


def update_microcycle(
    db: Session, microcycle_id: int, microcycle_data: schemas.MicrocycleUpdate
):
    db_microcycle = get_microcycle(db, microcycle_id)
    if not db_microcycle:
        return None

    # Extract propagate_up before applying other updates
    propagate_up = (
        microcycle_data.propagate_up
        if hasattr(microcycle_data, "propagate_up")
        else False
    )

    update_data = microcycle_data.model_dump(exclude_unset=True)
    # Remove propagate_up from update_data as it's not a model field
    update_data.pop("propagate_up", None)

    for field, value in update_data.items():
        setattr(db_microcycle, field, value)

    db.commit()
    db.refresh(db_microcycle)

    # Bottom-up propagation: recalculate parent mesocycle and macrocycle if requested
    if propagate_up:
        mesocycle_id = db_microcycle.mesocycle_id
        meso_result = _recalculate_mesocycle_from_microcycles(db, mesocycle_id)

        # Also propagate to macrocycle if mesocycle was updated
        if meso_result.get("changed", False):
            mesocycle = get_mesocycle(db, mesocycle_id)
            if mesocycle:
                _recalculate_macrocycle_from_mesocycles(db, mesocycle.macrocycle_id)

    return db_microcycle


def delete_microcycle(db: Session, microcycle_id: int) -> bool:
    db_microcycle = get_microcycle(db, microcycle_id)
    if not db_microcycle:
        return False

    db.delete(db_microcycle)
    db.commit()
    return True


# Training Session CRUD operations
def create_training_session(db: Session, session_data: schemas.TrainingSessionCreate):
    """
    Create a training session with full FK validation.
    Validates:
    - microcycle_id exists
    - microcycle belongs to the given client_id
      (via chain: microcycle → mesocycle → macrocycle → plan/instance → client_id)
    - trainer_id exists
    - client_id exists
    """
    # Validate client_id exists
    client = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.id == session_data.client_id)
        .first()
    )
    if not client:
        raise ValueError(f"Client ID {session_data.client_id} not found")

    # Validate trainer_id exists
    trainer = (
        db.query(models.Trainer)
        .filter(models.Trainer.id == session_data.trainer_id)
        .first()
    )
    if not trainer:
        raise ValueError(f"Trainer ID {session_data.trainer_id} not found")

    # Validate microcycle_id exists
    microcycle = (
        db.query(models.Microcycle)
        .filter(models.Microcycle.id == session_data.microcycle_id)
        .first()
    )
    if not microcycle:
        raise ValueError(f"Microcycle ID {session_data.microcycle_id} not found")

    # Validate microcycle belongs to client_id via the chain:
    # microcycle → mesocycle → macrocycle → (training_plan OR instance) → client_id
    mesocycle = (
        db.query(models.Mesocycle)
        .filter(models.Mesocycle.id == microcycle.mesocycle_id)
        .first()
    )
    if not mesocycle:
        raise ValueError(
            f"Mesocycle ID {microcycle.mesocycle_id} not found "
            f"for microcycle {session_data.microcycle_id}"
        )

    macrocycle = (
        db.query(models.Macrocycle)
        .filter(models.Macrocycle.id == mesocycle.macrocycle_id)
        .first()
    )
    if not macrocycle:
        raise ValueError(
            f"Macrocycle ID {mesocycle.macrocycle_id} not found "
            f"for mesocycle {mesocycle.id}"
        )

    # Check if macrocycle belongs to a training_plan or instance
    plan_client_id = None
    if macrocycle.training_plan_id:
        plan = (
            db.query(models.TrainingPlan)
            .filter(models.TrainingPlan.id == macrocycle.training_plan_id)
            .first()
        )
        if plan:
            plan_client_id = plan.client_id
    elif macrocycle.instance_id:
        instance = (
            db.query(models.TrainingPlanInstance)
            .filter(models.TrainingPlanInstance.id == macrocycle.instance_id)
            .first()
        )
        if instance:
            plan_client_id = instance.client_id

    if plan_client_id is None:
        raise ValueError(
            f"Macrocycle {macrocycle.id} is not associated "
            f"with a training plan or instance"
        )

    if plan_client_id != session_data.client_id:
        raise ValueError(
            f"Microcycle {session_data.microcycle_id} belongs to client "
            f"{plan_client_id}, but session is being created for client "
            f"{session_data.client_id}"
        )

    # Session Programming follows Training Planning structure
    # Auto-inherit volume/intensity from microcycle/mesocycle/macrocycle if not provided
    session_dict = session_data.model_dump()

    # Get planning values from hierarchy (micro → meso → macro)
    planning_volume = (
        microcycle.volume
        if microcycle.volume is not None
        else (mesocycle.volume if mesocycle.volume is not None else macrocycle.volume)
    )
    planning_intensity = (
        microcycle.intensity
        if microcycle.intensity is not None
        else (
            mesocycle.intensity
            if mesocycle.intensity is not None
            else macrocycle.intensity
        )
    )

    # Auto-fill planned_volume and planned_intensity from planning if not provided
    # Convert from 1-10 scale to percentage (0-100)
    if session_dict.get("planned_volume") is None and planning_volume is not None:
        session_dict["planned_volume"] = planning_volume * 10  # Convert 1-10 to 10-100

    if session_dict.get("planned_intensity") is None and planning_intensity is not None:
        session_dict["planned_intensity"] = (
            planning_intensity * 10
        )  # Convert 1-10 to 10-100

    # All validations passed, create the session
    db_session = models.TrainingSession(**session_dict)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def generate_sessions_from_microcycle(
    db: Session,
    microcycle_id: int,
    client_id: int,
    trainer_id: int,
    is_generic: bool = False,
) -> List[models.TrainingSession]:
    """
    Auto-generate training sessions from a microcycle based on Training Planning.
    (Session Programming follows Training Planning structure)

    For personalized plans: Creates sessions based on client's training_days and
    the microcycle's date range.

    For generic plans: Creates sessions based on training_frequency
    as Day 1, Day 2, etc.

    Args:
        db: Database session
        microcycle_id: ID of the microcycle to generate sessions from
        client_id: Client ID for the sessions
        trainer_id: Trainer ID for the sessions
        is_generic: If True, create generic sessions (Day 1, Day 2...)

    Returns:
        List of created TrainingSession objects
    """
    microcycle = get_microcycle(db, microcycle_id)
    if not microcycle:
        raise ValueError(f"Microcycle {microcycle_id} not found")

    mesocycle = get_mesocycle(db, microcycle.mesocycle_id)
    macrocycle = get_macrocycle(db, mesocycle.macrocycle_id) if mesocycle else None

    # Get planning values from hierarchy
    planning_volume = (
        microcycle.volume
        or (mesocycle.volume if mesocycle else None)
        or (macrocycle.volume if macrocycle else None)
    )
    planning_intensity = (
        microcycle.intensity
        or (mesocycle.intensity if mesocycle else None)
        or (macrocycle.intensity if macrocycle else None)
    )
    physical_quality = (
        microcycle.physical_quality
        or (mesocycle.physical_quality if mesocycle else None)
        or (macrocycle.physical_quality if macrocycle else None)
        or (mesocycle.primary_focus if mesocycle else None)
        or (macrocycle.focus if macrocycle else None)
    )

    created_sessions = []
    training_frequency = microcycle.training_frequency or 3

    if is_generic:
        # Generic plan: Create sessions as Day 1, Day 2, Day 3...
        for day_num in range(1, training_frequency + 1):
            session = models.TrainingSession(
                microcycle_id=microcycle_id,
                client_id=client_id,
                trainer_id=trainer_id,
                session_date=None,  # No real date for generic
                session_name=f"{physical_quality or 'Training'} - Day {day_num}",
                session_type=physical_quality or "General",
                training_day_number=day_num,
                is_generic_session=True,
                planned_volume=planning_volume * 10 if planning_volume else None,
                planned_intensity=(
                    planning_intensity * 10 if planning_intensity else None
                ),
                status="planned",
            )
            db.add(session)
            created_sessions.append(session)
    else:
        # Personalized plan: Create sessions based on client's training days
        client = (
            db.query(models.ClientProfile)
            .filter(models.ClientProfile.id == client_id)
            .first()
        )
        training_days = client.training_days if client else None

        # Generate dates within microcycle range
        from datetime import timedelta

        current_date = microcycle.start_date
        day_counter = 1

        while current_date <= microcycle.end_date and day_counter <= training_frequency:
            day_name = current_date.strftime("%A")

            # Check if this day should have a session
            should_create = False
            if training_days:
                should_create = (
                    day_name in training_days or day_name[:3] in training_days
                )
            else:
                # No specific days configured, distribute evenly
                should_create = True

            if should_create and day_counter <= training_frequency:
                session = models.TrainingSession(
                    microcycle_id=microcycle_id,
                    client_id=client_id,
                    trainer_id=trainer_id,
                    session_date=current_date,
                    session_name=f"{physical_quality or 'Training'} - {day_name}",
                    session_type=physical_quality or "General",
                    training_day_number=day_counter,
                    is_generic_session=False,
                    planned_volume=planning_volume * 10 if planning_volume else None,
                    planned_intensity=(
                        planning_intensity * 10 if planning_intensity else None
                    ),
                    status="planned",
                )
                db.add(session)
                created_sessions.append(session)
                day_counter += 1

            current_date += timedelta(days=1)

    db.commit()
    for session in created_sessions:
        db.refresh(session)

    return created_sessions


def get_training_sessions(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.TrainingSession]:
    return db.query(models.TrainingSession).offset(skip).limit(limit).all()


def get_training_sessions_by_microcycle(
    db: Session, microcycle_id: int, skip: int = 0, limit: int = 100
) -> List[models.TrainingSession]:
    return (
        db.query(models.TrainingSession)
        .filter(models.TrainingSession.microcycle_id == microcycle_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_training_sessions_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.TrainingSession]:
    return (
        db.query(models.TrainingSession)
        .filter(models.TrainingSession.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_training_sessions_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.TrainingSession]:
    return (
        db.query(models.TrainingSession)
        .filter(models.TrainingSession.trainer_id == trainer_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_training_session(db: Session, session_id: int):
    return (
        db.query(models.TrainingSession)
        .filter(models.TrainingSession.id == session_id)
        .first()
    )


def update_training_session(
    db: Session, session_id: int, session_data: schemas.TrainingSessionUpdate
):
    db_session = get_training_session(db, session_id)
    if not db_session:
        return None
    previous_status = db_session.status

    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)

    db.commit()
    db.refresh(db_session)

    # If the session has just been marked as completed, create a plan deviation alert
    # when actual intensity/volume differ significantly from planned values.
    try:
        if previous_status != "completed" and db_session.status == "completed":
            _maybe_create_plan_deviation_alert(db, db_session)
    except Exception:
        # Best-effort: never block the main flow if alert creation fails.
        pass

    return db_session


def delete_training_session(db: Session, session_id: int) -> bool:
    db_session = get_training_session(db, session_id)
    if not db_session:
        return False

    db.delete(db_session)
    db.commit()
    return True


# Session Exercise CRUD operations
def create_session_exercise(db: Session, exercise_data: schemas.SessionExerciseCreate):
    db_exercise = models.SessionExercise(**exercise_data.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def get_session_exercises(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.SessionExercise]:
    return db.query(models.SessionExercise).offset(skip).limit(limit).all()


def get_session_exercises_by_session(
    db: Session, session_id: int, skip: int = 0, limit: int = 100
) -> List[models.SessionExercise]:
    return (
        db.query(models.SessionExercise)
        .filter(models.SessionExercise.training_session_id == session_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_session_exercise(db: Session, exercise_id: int):
    return (
        db.query(models.SessionExercise)
        .filter(models.SessionExercise.id == exercise_id)
        .first()
    )


def update_session_exercise(
    db: Session, exercise_id: int, exercise_data: schemas.SessionExerciseUpdate
):
    db_exercise = get_session_exercise(db, exercise_id)
    if not db_exercise:
        return None

    update_data = exercise_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exercise, field, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_session_exercise(db: Session, exercise_id: int) -> bool:
    db_exercise = get_session_exercise(db, exercise_id)
    if not db_exercise:
        return False

    db.delete(db_exercise)
    db.commit()
    return True


# Client Feedback CRUD operations
def create_client_feedback(db: Session, feedback_data: schemas.ClientFeedbackCreate):
    db_feedback = models.ClientFeedback(**feedback_data.model_dump())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def get_client_feedback(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ClientFeedback]:
    return (
        db.query(models.ClientFeedback)
        .options(
            noload(models.ClientFeedback.client),
            noload(models.ClientFeedback.training_session),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_client_feedback_by_id(db: Session, feedback_id: int):
    return (
        db.query(models.ClientFeedback)
        .options(
            noload(models.ClientFeedback.client),
            noload(models.ClientFeedback.training_session),
        )
        .filter(models.ClientFeedback.id == feedback_id)
        .first()
    )


def update_client_feedback(
    db: Session, feedback_id: int, feedback_data: schemas.ClientFeedbackUpdate
):
    db_feedback = get_client_feedback_by_id(db, feedback_id)
    if not db_feedback:
        return None

    update_data = feedback_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_feedback, field, value)

    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def delete_client_feedback(db: Session, feedback_id: int) -> bool:
    db_feedback = get_client_feedback_by_id(db, feedback_id)
    if not db_feedback:
        return False

    db.delete(db_feedback)
    db.commit()
    return True


def get_client_feedback_by_session(db: Session, session_id: int):
    return (
        db.query(models.ClientFeedback)
        .options(
            noload(models.ClientFeedback.client),
            noload(models.ClientFeedback.training_session),
        )
        .filter(models.ClientFeedback.training_session_id == session_id)
        .first()
    )


def get_client_feedback_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
):
    return (
        db.query(models.ClientFeedback)
        .options(
            noload(models.ClientFeedback.client),
            noload(models.ClientFeedback.training_session),
        )
        .filter(models.ClientFeedback.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


# Progress Tracking CRUD operations
def create_progress_tracking(
    db: Session, tracking_data: schemas.ProgressTrackingCreate
):
    db_tracking = models.ProgressTracking(**tracking_data.model_dump())
    db.add(db_tracking)
    db.commit()
    db.refresh(db_tracking)
    return db_tracking


def get_progress_tracking(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.ProgressTracking]:
    return db.query(models.ProgressTracking).offset(skip).limit(limit).all()


def get_progress_tracking_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.ProgressTracking]:
    return (
        db.query(models.ProgressTracking)
        .filter(models.ProgressTracking.client_id == client_id)
        .order_by(models.ProgressTracking.tracking_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_progress_tracking_by_client_and_exercise(
    db: Session, client_id: int, exercise_id: int, skip: int = 0, limit: int = 100
) -> List[models.ProgressTracking]:
    return (
        db.query(models.ProgressTracking)
        .filter(
            models.ProgressTracking.client_id == client_id,
            models.ProgressTracking.exercise_id == exercise_id,
        )
        .order_by(models.ProgressTracking.tracking_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_progress_tracking_by_id(db: Session, tracking_id: int):
    return (
        db.query(models.ProgressTracking)
        .filter(models.ProgressTracking.id == tracking_id)
        .first()
    )


def update_progress_tracking(
    db: Session, tracking_id: int, tracking_data: schemas.ProgressTrackingUpdate
):
    db_tracking = get_progress_tracking_by_id(db, tracking_id)
    if not db_tracking:
        return None

    update_data = tracking_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tracking, field, value)

    db.commit()
    db.refresh(db_tracking)
    return db_tracking


def delete_progress_tracking(db: Session, tracking_id: int) -> bool:
    db_tracking = get_progress_tracking_by_id(db, tracking_id)
    if not db_tracking:
        return False

    db.delete(db_tracking)
    db.commit()
    return True


# Standalone Session CRUD operations
def create_standalone_session(
    db: Session, session_data: schemas.StandaloneSessionCreate
):
    db_session = models.StandaloneSession(**session_data.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_standalone_sessions(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSession]:
    return db.query(models.StandaloneSession).offset(skip).limit(limit).all()


def get_standalone_sessions_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSession]:
    return (
        db.query(models.StandaloneSession)
        .filter(models.StandaloneSession.client_id == client_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_standalone_sessions_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSession]:
    return (
        db.query(models.StandaloneSession)
        .filter(models.StandaloneSession.trainer_id == trainer_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_standalone_session(db: Session, session_id: int):
    return (
        db.query(models.StandaloneSession)
        .filter(models.StandaloneSession.id == session_id)
        .first()
    )


def update_standalone_session(
    db: Session, session_id: int, session_data: schemas.StandaloneSessionUpdate
):
    db_session = get_standalone_session(db, session_id)
    if not db_session:
        return None

    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)

    db.commit()
    db.refresh(db_session)
    return db_session


def delete_standalone_session(db: Session, session_id: int) -> bool:
    db_session = get_standalone_session(db, session_id)
    if not db_session:
        return False

    db.delete(db_session)
    db.commit()
    return True


# Standalone Session Exercise CRUD operations
def create_standalone_session_exercise(
    db: Session, exercise_data: schemas.StandaloneSessionExerciseCreate
):
    db_exercise = models.StandaloneSessionExercise(**exercise_data.model_dump())
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def get_standalone_session_exercises(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSessionExercise]:
    return db.query(models.StandaloneSessionExercise).offset(skip).limit(limit).all()


def get_standalone_session_exercises_by_session(
    db: Session, session_id: int, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSessionExercise]:
    return (
        db.query(models.StandaloneSessionExercise)
        .filter(models.StandaloneSessionExercise.standalone_session_id == session_id)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_standalone_session_exercise(db: Session, exercise_id: int):
    return (
        db.query(models.StandaloneSessionExercise)
        .filter(models.StandaloneSessionExercise.id == exercise_id)
        .first()
    )


def update_standalone_session_exercise(
    db: Session,
    exercise_id: int,
    exercise_data: schemas.StandaloneSessionExerciseUpdate,
):
    db_exercise = get_standalone_session_exercise(db, exercise_id)
    if not db_exercise:
        return None

    update_data = exercise_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exercise, field, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_standalone_session_exercise(db: Session, exercise_id: int) -> bool:
    db_exercise = get_standalone_session_exercise(db, exercise_id)
    if not db_exercise:
        return False

    db.delete(db_exercise)
    db.commit()
    return True


# Standalone Session Feedback CRUD operations
def create_standalone_session_feedback(
    db: Session, feedback_data: schemas.StandaloneSessionFeedbackCreate
):
    db_feedback = models.StandaloneSessionFeedback(**feedback_data.model_dump())
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def get_standalone_session_feedback(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.StandaloneSessionFeedback]:
    return db.query(models.StandaloneSessionFeedback).offset(skip).limit(limit).all()


def get_standalone_session_feedback_by_id(db: Session, feedback_id: int):
    return (
        db.query(models.StandaloneSessionFeedback)
        .filter(models.StandaloneSessionFeedback.id == feedback_id)
        .first()
    )


def get_standalone_session_feedback_by_session(db: Session, session_id: int):
    """Get feedback for a specific standalone session"""
    return (
        db.query(models.StandaloneSessionFeedback)
        .filter(models.StandaloneSessionFeedback.standalone_session_id == session_id)
        .first()
    )


def update_standalone_session_feedback(
    db: Session,
    feedback_id: int,
    feedback_data: schemas.StandaloneSessionFeedbackUpdate,
):
    db_feedback = get_standalone_session_feedback_by_id(db, feedback_id)
    if not db_feedback:
        return None

    update_data = feedback_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_feedback, field, value)

    db.commit()
    db.refresh(db_feedback)
    return db_feedback


def delete_standalone_session_feedback(db: Session, feedback_id: int) -> bool:
    db_feedback = get_standalone_session_feedback_by_id(db, feedback_id)
    if not db_feedback:
        return False

    db.delete(db_feedback)
    db.commit()
    return True


# Fatigue Analysis CRUD operations
def create_fatigue_analysis(
    db: Session,
    fatigue_data: schemas.FatigueAnalysisCreate,
    trainer_id: Optional[int] = None,
):
    """Create a new fatigue analysis record"""
    # Calculate derived metrics
    if (
        fatigue_data.pre_fatigue_level is not None
        and fatigue_data.post_fatigue_level is not None
    ):
        fatigue_data.fatigue_delta = (
            fatigue_data.post_fatigue_level - fatigue_data.pre_fatigue_level
        )

    if (
        fatigue_data.pre_energy_level is not None
        and fatigue_data.post_energy_level is not None
    ):
        fatigue_data.energy_delta = (
            fatigue_data.post_energy_level - fatigue_data.pre_energy_level
        )

    # Calculate risk level and recommendations
    risk_level, recommendations = _calculate_risk_level(fatigue_data)
    next_session_adjustment = _generate_fatigue_recommendations(fatigue_data)

    # Create the fatigue analysis record
    fatigue_dict = fatigue_data.model_dump()
    fatigue_dict.update(
        {
            "risk_level": risk_level,
            "recommendations": recommendations,
            "next_session_adjustment": next_session_adjustment,
        }
    )

    db_fatigue = models.FatigueAnalysis(**fatigue_dict)

    db.add(db_fatigue)
    db.commit()
    db.refresh(db_fatigue)

    # Automatically create a wellbeing/status alert for medium/high risk analyses.
    # This powers the trainer Alerts section for client status (wellbeing check-in).
    try:
        # Refresh to ensure we have the latest data including risk_level
        db.refresh(db_fatigue)
        import logging

        logging.info(
            f"Attempting to create wellbeing alert for fatigue analysis "
            f"{db_fatigue.id}, client_id={db_fatigue.client_id}, "
            f"risk_level={db_fatigue.risk_level}"
        )
        _maybe_create_wellbeing_alert(db, db_fatigue, trainer_id=trainer_id)
        logging.info(
            f"Completed wellbeing alert creation attempt for fatigue analysis "
            f"{db_fatigue.id}"
        )
    except Exception as e:
        # Best-effort: never block the main flow if alert creation fails.
        # Log the error for debugging but don't raise
        import logging

        logging.error(
            f"Failed to create wellbeing alert for fatigue analysis "
            f"{db_fatigue.id}: {e}",
            exc_info=True,
        )
        pass

    return db_fatigue


def _maybe_create_wellbeing_alert(
    db: Session, fatigue: models.FatigueAnalysis, trainer_id: Optional[int] = None
) -> None:
    """
    Create a wellbeing/status alert when fatigue analysis indicates medium/high risk.

    Maps directly to Adrián's 'Client Status (Wellbeing Check-In)' alerts:
    - Uses fatigue/risk metrics already stored in FatigueAnalysis
    - Creates a FatigueAlert for the responsible trainer
    """
    import logging

    # Only create alerts for medium or high risk
    if fatigue.risk_level not in ("medium", "high"):
        logging.debug(
            f"Skipping alert creation: risk_level={fatigue.risk_level} "
            f"(not medium/high)"
        )
        return

    # Resolve trainer_id from:
    # 1. Explicit trainer_id parameter (trainer who created the fatigue analysis)
    # 2. Linked session (training or standalone)
    # 3. Fallback: first trainer linked to this client

    if not trainer_id:
        if fatigue.session_type == "training" and fatigue.session_id:
            session = (
                db.query(models.TrainingSession)
                .filter(models.TrainingSession.id == fatigue.session_id)
                .first()
            )
            if session:
                trainer_id = session.trainer_id
        elif fatigue.session_type == "standalone" and fatigue.session_id:
            standalone = (
                db.query(models.StandaloneSession)
                .filter(models.StandaloneSession.id == fatigue.session_id)
                .first()
            )
            if standalone:
                trainer_id = standalone.trainer_id

    if not trainer_id:
        # Fallback: use first trainer linked to this client (if any)
        # Find trainer linked to this client - flush to ensure we see latest data
        db.flush()

        # Try direct TrainerClient query first
        tc = (
            db.query(models.TrainerClient)
            .filter(models.TrainerClient.client_id == fatigue.client_id)
            .first()
        )

        # If not found, try join query as fallback
        if not tc:
            trainer = (
                db.query(models.Trainer)
                .join(
                    models.TrainerClient,
                    models.TrainerClient.trainer_id == models.Trainer.id,
                )
                .filter(models.TrainerClient.client_id == fatigue.client_id)
                .first()
            )
            if trainer:
                trainer_id = trainer.id
            else:
                # No trainer linked - this is the actual problem
                # Let's verify by counting all TrainerClient links for this client
                count = (
                    db.query(models.TrainerClient)
                    .filter(models.TrainerClient.client_id == fatigue.client_id)
                    .count()
                )
                # Use print to ensure we see this in logs
                print(
                    f"ERROR: No trainer found for client {fatigue.client_id}. "
                    f"TrainerClient count: {count}. "
                    f"Cannot create alert for fatigue analysis {fatigue.id}"
                )
                import logging

                logging.error(
                    f"CRITICAL: No trainer found for client {fatigue.client_id}. "
                    f"TrainerClient count: {count}. "
                    f"Cannot create alert for fatigue analysis {fatigue.id}"
                )
                return
        else:
            trainer_id = tc.trainer_id

    # Double-check trainer_id is valid
    if not trainer_id:
        return

    # Get client name for nicer alert copy (optional)
    client = (
        db.query(models.ClientProfile)
        .filter(models.ClientProfile.id == fatigue.client_id)
        .first()
    )
    client_name = (
        f"{client.nombre} {client.apellidos}".strip()
        if client
        else f"Client {fatigue.client_id}"
    )

    if fatigue.risk_level == "high":
        alert_type = "recovery_needed"
        severity = "high"
        title = f"High fatigue for {client_name}"
    else:
        alert_type = "session_adjustment"
        severity = "medium"
        title = f"Moderate fatigue for {client_name}"

    message = fatigue.recommendations or (
        "Client wellbeing check indicates relevant fatigue; "
        "consider adjusting upcoming sessions."
    )
    recommendations = fatigue.next_session_adjustment

    # Ensure trainer_id is valid before creating alert
    if not trainer_id:
        import logging

        logging.warning(
            f"trainer_id is None for client {fatigue.client_id}, "
            f"cannot create alert for fatigue analysis {fatigue.id}"
        )
        return

    import logging

    print(
        f"DEBUG: Creating FatigueAlert: client_id={fatigue.client_id}, "
        f"trainer_id={trainer_id}, alert_type={alert_type}, "
        f"severity={severity}, fatigue_analysis_id={fatigue.id}"
    )
    logging.info(
        f"Creating FatigueAlert: client_id={fatigue.client_id}, "
        f"trainer_id={trainer_id}, alert_type={alert_type}, "
        f"severity={severity}"
    )

    alert = models.FatigueAlert(
        client_id=fatigue.client_id,
        trainer_id=trainer_id,
        fatigue_analysis_id=fatigue.id,
        alert_type=alert_type,
        severity=severity,
        title=title,
        message=message,
        recommendations=recommendations,
        is_read=False,
        is_resolved=False,
    )
    db.add(alert)
    try:
        db.commit()
        print(
            f"SUCCESS: Created FatigueAlert {alert.id} "
            f"for fatigue analysis {fatigue.id}"
        )
        logging.info(
            f"Successfully created FatigueAlert {alert.id} for "
            f"fatigue analysis {fatigue.id}"
        )
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to commit FatigueAlert: {e}")
        logging.error(
            f"Failed to commit FatigueAlert for fatigue analysis {fatigue.id}: {e}",
            exc_info=True,
        )
        raise


def get_fatigue_analysis(db: Session, analysis_id: int):
    """Get a specific fatigue analysis by ID"""
    return (
        db.query(models.FatigueAnalysis)
        .filter(models.FatigueAnalysis.id == analysis_id)
        .first()
    )


def get_fatigue_analysis_list(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.FatigueAnalysis]:
    """Get all fatigue analysis records"""
    return (
        db.query(models.FatigueAnalysis)
        .filter(models.FatigueAnalysis.is_active)
        .order_by(models.FatigueAnalysis.analysis_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_fatigue_analysis_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.FatigueAnalysis]:
    """Get fatigue analysis for a specific client"""
    return (
        db.query(models.FatigueAnalysis)
        .filter(
            models.FatigueAnalysis.client_id == client_id,
            models.FatigueAnalysis.is_active,
        )
        .order_by(models.FatigueAnalysis.analysis_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_fatigue_analysis(
    db: Session, analysis_id: int, fatigue_data: schemas.FatigueAnalysisUpdate
):
    """Update an existing fatigue analysis record"""
    db_fatigue = get_fatigue_analysis(db, analysis_id)
    if not db_fatigue:
        return None

    # Recalculate derived metrics if fatigue levels changed
    update_data = fatigue_data.model_dump(exclude_unset=True)

    if "pre_fatigue_level" in update_data or "post_fatigue_level" in update_data:
        pre_fatigue = update_data.get("pre_fatigue_level", db_fatigue.pre_fatigue_level)
        post_fatigue = update_data.get(
            "post_fatigue_level", db_fatigue.post_fatigue_level
        )
        if pre_fatigue is not None and post_fatigue is not None:
            update_data["fatigue_delta"] = post_fatigue - pre_fatigue

    if "pre_energy_level" in update_data or "post_energy_level" in update_data:
        pre_energy = update_data.get("pre_energy_level", db_fatigue.pre_energy_level)
        post_energy = update_data.get("post_energy_level", db_fatigue.post_energy_level)
        if pre_energy is not None and post_energy is not None:
            update_data["energy_delta"] = post_energy - pre_energy

    # Recalculate risk level and recommendations
    if any(
        key in update_data
        for key in [
            "pre_fatigue_level",
            "post_fatigue_level",
            "pre_energy_level",
            "post_energy_level",
        ]
    ):
        risk_level, recommendations = _calculate_risk_level(fatigue_data)
        next_session_adjustment = _generate_fatigue_recommendations(fatigue_data)
        update_data["risk_level"] = risk_level
        update_data["recommendations"] = recommendations
        update_data["next_session_adjustment"] = next_session_adjustment

    for field, value in update_data.items():
        setattr(db_fatigue, field, value)

    db.commit()
    db.refresh(db_fatigue)
    return db_fatigue


def delete_fatigue_analysis(db: Session, analysis_id: int) -> bool:
    """Delete a fatigue analysis record (soft delete)"""
    db_fatigue = get_fatigue_analysis(db, analysis_id)
    if not db_fatigue:
        return False

    db_fatigue.is_active = False
    db.commit()
    return True


# Fatigue Alert CRUD operations
def create_fatigue_alert(db: Session, alert_data: schemas.FatigueAlertCreate):
    """Create a new fatigue alert"""
    db_alert = models.FatigueAlert(**alert_data.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


def get_fatigue_alerts(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.FatigueAlert]:
    """Get all fatigue alerts"""
    return (
        db.query(models.FatigueAlert)
        .filter(models.FatigueAlert.is_active)
        .order_by(models.FatigueAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_fatigue_alerts_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.FatigueAlert]:
    """Get fatigue alerts for a specific trainer"""
    return (
        db.query(models.FatigueAlert)
        .filter(
            models.FatigueAlert.trainer_id == trainer_id,
            models.FatigueAlert.is_active,
        )
        .order_by(models.FatigueAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_unread_fatigue_alerts(
    db: Session, skip: int = 0, limit: int = 100
) -> List[models.FatigueAlert]:
    """Get unread fatigue alerts"""
    return (
        db.query(models.FatigueAlert)
        .filter(
            models.FatigueAlert.is_read.is_(False),
            models.FatigueAlert.is_active.is_(True),
        )
        .order_by(models.FatigueAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_fatigue_analysis_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.FatigueAnalysis]:
    """Get fatigue analysis for trainer's clients only"""
    return (
        db.query(models.FatigueAnalysis)
        .join(
            models.TrainerClient,
            models.TrainerClient.client_id == models.FatigueAnalysis.client_id,
        )
        .filter(
            models.TrainerClient.trainer_id == trainer_id,
            models.FatigueAnalysis.is_active,
        )
        .order_by(models.FatigueAnalysis.analysis_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_unread_fatigue_alerts_by_trainer(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.FatigueAlert]:
    """Get unread fatigue alerts for a specific trainer"""
    return (
        db.query(models.FatigueAlert)
        .filter(
            models.FatigueAlert.trainer_id == trainer_id,
            models.FatigueAlert.is_read.is_(False),
            models.FatigueAlert.is_active.is_(True),
        )
        .order_by(models.FatigueAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_workload_tracking_by_trainer_clients(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
) -> List[models.WorkloadTracking]:
    """Get workload tracking for trainer's clients only"""
    return (
        db.query(models.WorkloadTracking)
        .join(
            models.TrainerClient,
            models.TrainerClient.client_id == models.WorkloadTracking.client_id,
        )
        .filter(
            models.TrainerClient.trainer_id == trainer_id,
            models.WorkloadTracking.is_active,
        )
        .order_by(models.WorkloadTracking.tracking_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def mark_fatigue_alert_as_read(db: Session, alert_id: int):
    """Mark a fatigue alert as read"""
    db_alert = (
        db.query(models.FatigueAlert).filter(models.FatigueAlert.id == alert_id).first()
    )
    if not db_alert:
        return None

    db_alert.is_read = True
    db.commit()
    db.refresh(db_alert)
    return db_alert


def resolve_fatigue_alert(
    db: Session, alert_id: int, resolution_notes: Optional[str] = None
):
    """Resolve a fatigue alert"""
    db_alert = (
        db.query(models.FatigueAlert).filter(models.FatigueAlert.id == alert_id).first()
    )
    if not db_alert:
        return None

    db_alert.is_resolved = True
    db_alert.resolved_at = datetime.now(timezone.utc)
    if resolution_notes:
        db_alert.resolution_notes = resolution_notes

    db.commit()
    db.refresh(db_alert)
    return db_alert


# Workload Tracking CRUD operations
def create_workload_tracking(
    db: Session, workload_data: schemas.WorkloadTrackingCreate
):
    """Create a new workload tracking record"""
    db_workload = models.WorkloadTracking(**workload_data.model_dump())
    db.add(db_workload)
    db.commit()
    db.refresh(db_workload)
    return db_workload


def get_workload_tracking_by_client(
    db: Session, client_id: int, skip: int = 0, limit: int = 100
) -> List[models.WorkloadTracking]:
    """Get workload tracking for a specific client"""
    return (
        db.query(models.WorkloadTracking)
        .filter(
            models.WorkloadTracking.client_id == client_id,
            models.WorkloadTracking.is_active,
        )
        .order_by(models.WorkloadTracking.tracking_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_workload_tracking(
    db: Session, workload_id: int, workload_data: schemas.WorkloadTrackingUpdate
):
    """Update an existing workload tracking record"""
    db_workload = (
        db.query(models.WorkloadTracking)
        .filter(models.WorkloadTracking.id == workload_id)
        .first()
    )
    if not db_workload:
        return None

    update_data = workload_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_workload, field, value)

    db.commit()
    db.refresh(db_workload)
    return db_workload


def delete_workload_tracking(db: Session, workload_id: int) -> bool:
    """Delete a workload tracking record (soft delete)"""
    db_workload = (
        db.query(models.WorkloadTracking)
        .filter(models.WorkloadTracking.id == workload_id)
        .first()
    )
    if not db_workload:
        return False

    db_workload.is_active = False
    db.commit()
    return True


# Helper functions for fatigue analysis
def _calculate_risk_level(
    fatigue_data: schemas.FatigueAnalysisCreate,
) -> tuple[str, str]:
    """Calculate risk level based on fatigue metrics"""
    risk_level = "low"
    recommendations = "Continue with planned training intensity."

    # Check for high fatigue indicators
    if fatigue_data.post_fatigue_level and fatigue_data.post_fatigue_level >= 8:
        risk_level = "high"
        recommendations = (
            "High fatigue detected. Consider reducing next session intensity "
            "or adding recovery day."
        )
    elif fatigue_data.post_fatigue_level and fatigue_data.post_fatigue_level >= 6:
        risk_level = "medium"
        recommendations = "Moderate fatigue. Monitor closely and adjust if needed."

    # Check for energy depletion
    if fatigue_data.post_energy_level and fatigue_data.post_energy_level <= 3:
        risk_level = "high"
        recommendations = (
            "Low energy levels. Strongly recommend recovery or light session."
        )

    # Check for large fatigue delta
    if fatigue_data.fatigue_delta and fatigue_data.fatigue_delta >= 4:
        risk_level = "high"
        recommendations = "Significant fatigue increase. Reduce next session intensity."

    return risk_level, recommendations


def _generate_fatigue_recommendations(
    fatigue_data: schemas.FatigueAnalysisCreate,
) -> str:
    """Generate specific recommendations for next session"""
    if not fatigue_data.post_fatigue_level:
        return "Continue with planned training."

    if fatigue_data.post_fatigue_level >= 8:
        return "Reduce intensity by 30-40%. Focus on technique and recovery."
    elif fatigue_data.post_fatigue_level >= 6:
        return "Reduce intensity by 15-20%. Monitor fatigue closely."
    elif fatigue_data.post_fatigue_level <= 3:
        return "Can increase intensity if feeling good. Maintain good form."
    else:
        return "Continue with planned intensity. Monitor for any signs of fatigue."


# Session Programming Enhancement CRUD Operations


# Training Block Type CRUD
def create_training_block_type(
    db: Session,
    block_type_data: schemas.TrainingBlockTypeCreate,
    user_id: int = None,
):
    """Create a new training block type"""
    # Get trainer_id from user_id
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    trainer_id = trainer.id if trainer else None

    db_block_type = models.TrainingBlockType(
        **block_type_data.model_dump(), created_by_trainer_id=trainer_id
    )
    db.add(db_block_type)
    db.commit()
    db.refresh(db_block_type)
    return db_block_type


def get_training_block_types(
    db: Session, skip: int = 0, limit: int = 100, trainer_id: int = None
):
    """Get training block types, optionally filtered by trainer"""
    query = db.query(models.TrainingBlockType)

    if trainer_id:
        # Get predefined blocks + trainer's custom blocks
        query = query.filter(
            (models.TrainingBlockType.is_predefined.is_(True))
            | (models.TrainingBlockType.created_by_trainer_id == trainer_id)
        )
    else:
        # Get only predefined blocks
        query = query.filter(models.TrainingBlockType.is_predefined.is_(True))

    return query.offset(skip).limit(limit).all()


def get_training_block_type(db: Session, block_type_id: int):
    """Get a specific training block type"""
    return (
        db.query(models.TrainingBlockType)
        .filter(models.TrainingBlockType.id == block_type_id)
        .first()
    )


def update_training_block_type(
    db: Session, block_type_id: int, block_type_data: schemas.TrainingBlockTypeUpdate
):
    """Update a training block type"""
    db_block_type = get_training_block_type(db, block_type_id)
    if not db_block_type:
        return None

    update_data = block_type_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_block_type, field, value)

    db.commit()
    db.refresh(db_block_type)
    return db_block_type


def delete_training_block_type(db: Session, block_type_id: int) -> bool:
    """Delete a training block type"""
    db_block_type = get_training_block_type(db, block_type_id)
    if not db_block_type:
        return False

    db.delete(db_block_type)
    db.commit()
    return True


# Session Template CRUD
def create_session_template(
    db: Session, template_data: schemas.SessionTemplateCreate, user_id: int
):
    """Create a new session template"""
    # Get trainer_id from user_id
    trainer = db.query(models.Trainer).filter(models.Trainer.user_id == user_id).first()
    if not trainer:
        raise ValueError("User is not a trainer")

    db_template = models.SessionTemplate(
        **template_data.model_dump(), trainer_id=trainer.id
    )
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template


def get_session_templates(
    db: Session,
    trainer_id: int = None,
    skip: int = 0,
    limit: int = 100,
    admin_access: bool = False,
):
    """Get session templates, optionally filtered by trainer

    Args:
        trainer_id: If provided, get trainer's templates + public templates
        admin_access: If True, get all templates (admin override)
    """
    from sqlalchemy import func

    query = db.query(models.SessionTemplate)

    if admin_access:
        # Admin can see all templates
        pass  # No filter - get all templates
    elif trainer_id:
        # Get trainer's templates + public templates
        query = query.filter(
            (models.SessionTemplate.trainer_id == trainer_id)
            | (models.SessionTemplate.is_public.is_(True))
        )
    else:
        # Get only public templates
        query = query.filter(models.SessionTemplate.is_public.is_(True))

    templates = query.offset(skip).limit(limit).all()

    # Add exercise count to each template
    for template in templates:
        exercise_count = (
            db.query(func.count(models.SessionTemplateExercise.id))
            .join(models.SessionTemplateBlock)
            .filter(models.SessionTemplateBlock.template_id == template.id)
            .scalar()
            or 0
        )
        # Set as attribute - Pydantic will include it via model_config
        setattr(template, "exercise_count", exercise_count)

    return templates


def get_session_template(db: Session, template_id: int):
    """Get a specific session template"""
    return (
        db.query(models.SessionTemplate)
        .filter(models.SessionTemplate.id == template_id)
        .first()
    )


def update_session_template(
    db: Session, template_id: int, template_data: schemas.SessionTemplateUpdate
):
    """Update a session template"""
    db_template = get_session_template(db, template_id)
    if not db_template:
        return None

    update_data = template_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_template, field, value)

    db.commit()
    db.refresh(db_template)
    return db_template


def delete_session_template(db: Session, template_id: int) -> bool:
    """Delete a session template"""
    db_template = get_session_template(db, template_id)
    if not db_template:
        return False

    db.delete(db_template)
    db.commit()
    return True


def increment_template_usage(db: Session, template_id: int):
    """Increment the usage count of a session template"""
    db_template = get_session_template(db, template_id)
    if db_template:
        db_template.usage_count += 1
        db.commit()
        db.refresh(db_template)
    return db_template


# Session Block CRUD
def create_session_block(
    db: Session, block_data: schemas.SessionBlockCreate, session_id: int
):
    """Create a new session block"""
    db_block = models.SessionBlock(
        **block_data.model_dump(), training_session_id=session_id
    )
    db.add(db_block)
    db.commit()
    db.refresh(db_block)
    return db_block


def get_session_blocks(db: Session, session_id: int):
    """Get all blocks for a training session"""
    return (
        db.query(models.SessionBlock)
        .filter(models.SessionBlock.training_session_id == session_id)
        .order_by(models.SessionBlock.order_in_session)
        .all()
    )


def get_session_block(db: Session, block_id: int):
    """Get a specific session block"""
    return (
        db.query(models.SessionBlock).filter(models.SessionBlock.id == block_id).first()
    )


def update_session_block(
    db: Session, block_id: int, block_data: schemas.SessionBlockUpdate
):
    """Update a session block"""
    db_block = get_session_block(db, block_id)
    if not db_block:
        return None

    update_data = block_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_block, field, value)

    db.commit()
    db.refresh(db_block)
    return db_block


def delete_session_block(db: Session, block_id: int) -> bool:
    """Delete a session block"""
    db_block = get_session_block(db, block_id)
    if not db_block:
        return False

    db.delete(db_block)
    db.commit()
    return True


# Session Block Exercise CRUD
def create_session_block_exercise(
    db: Session, exercise_data: schemas.SessionBlockExerciseCreate, block_id: int
):
    """Create a new session block exercise"""
    db_exercise = models.SessionBlockExercise(
        **exercise_data.model_dump(), session_block_id=block_id
    )
    db.add(db_exercise)
    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def get_session_block_exercises(db: Session, block_id: int):
    """Get all exercises for a session block"""
    return (
        db.query(models.SessionBlockExercise)
        .filter(models.SessionBlockExercise.session_block_id == block_id)
        .order_by(models.SessionBlockExercise.order_in_block)
        .all()
    )


def get_session_block_exercise(db: Session, exercise_id: int):
    """Get a specific session block exercise"""
    return (
        db.query(models.SessionBlockExercise)
        .filter(models.SessionBlockExercise.id == exercise_id)
        .first()
    )


def update_session_block_exercise(
    db: Session, exercise_id: int, exercise_data: schemas.SessionBlockExerciseUpdate
):
    """Update a session block exercise"""
    db_exercise = get_session_block_exercise(db, exercise_id)
    if not db_exercise:
        return None

    update_data = exercise_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_exercise, field, value)

    db.commit()
    db.refresh(db_exercise)
    return db_exercise


def delete_session_block_exercise(db: Session, exercise_id: int) -> bool:
    """Delete a session block exercise"""
    db_exercise = get_session_block_exercise(db, exercise_id)
    if not db_exercise:
        return False

    db.delete(db_exercise)
    db.commit()
    return True


# Session Summary Calculation
def calculate_session_summary(
    db: Session, session_id: int
) -> schemas.SessionSummaryOut:
    """Calculate session summary metrics"""
    session = (
        db.query(models.TrainingSession)
        .filter(models.TrainingSession.id == session_id)
        .first()
    )
    if not session:
        return None

    # Get all blocks for the session
    blocks = get_session_blocks(db, session_id)

    # Calculate totals
    total_sets = 0
    estimated_duration = 0

    for block in blocks:
        # Add block estimated duration
        if block.estimated_duration:
            estimated_duration += block.estimated_duration

        # Get exercises for this block
        exercises = get_session_block_exercises(db, block.id)

        # Sum up sets
        for exercise in exercises:
            if exercise.planned_sets:
                total_sets += exercise.planned_sets

    return schemas.SessionSummaryOut(
        total_sets=total_sets,
        estimated_duration=estimated_duration or session.planned_duration or 0,
        blocks=len(blocks),
        planned_intensity=session.planned_intensity,
        planned_volume=session.planned_volume,
        actual_intensity=session.actual_intensity,
        actual_volume=session.actual_volume,
    )


# ---------------------------------------------------------------------------
# Temporary KPI helpers (mock data while analytics backend is pending)
# ---------------------------------------------------------------------------
def get_client_improvement_stats(db: Session, trainer_id: Optional[int] = None) -> Dict:
    """
    Calculate average client improvement from physical test results.
    Uses real data from PhysicalTestResult table and calculate_test_progress().
    """
    from datetime import datetime, timedelta, timezone

    # Get trainer's clients
    if trainer_id:
        client_ids = [
            tc.client_id
            for tc in db.query(models.TrainerClient.client_id)
            .filter(models.TrainerClient.trainer_id == trainer_id)
            .all()
        ]
    else:
        client_ids = [c.id for c in db.query(models.ClientProfile.id).all()]

    if not client_ids:
        return {
            "average": 0.0,
            "trend": "+0%",
            "sample_size": 0,
            "source": "database",
            "note": "No clients found",
        }

    # Get all non-baseline test results for these clients
    test_results = (
        db.query(models.PhysicalTestResult)
        .filter(
            models.PhysicalTestResult.client_id.in_(client_ids),
            models.PhysicalTestResult.is_baseline.is_(False),
            models.PhysicalTestResult.is_active.is_(True),
        )
        .all()
    )

    if not test_results:
        return {
            "average": 0.0,
            "trend": "+0%",
            "sample_size": 0,
            "source": "database",
            "note": "No test results found",
        }

    improvements = []
    for result in test_results:
        try:
            # Use existing function to calculate progress
            progress = calculate_test_progress(db, result.id)
            if progress and progress.get("progress_percentage") is not None:
                improvements.append(progress["progress_percentage"])
        except (ValueError, Exception):
            continue  # Skip if calculation fails

    if not improvements:
        return {
            "average": 0.0,
            "trend": "+0%",
            "sample_size": 0,
            "source": "database",
            "note": "No valid progress calculations",
        }

    avg_improvement = sum(improvements) / len(improvements)

    # Calculate trend (last 30 days vs previous 30 days)
    now = datetime.now(timezone.utc)
    last_30 = now - timedelta(days=30)
    prev_30_start = last_30 - timedelta(days=30)

    # Normalize datetimes to timezone-aware (UTC) for comparison
    def normalize_datetime(dt):
        """Ensure datetime is timezone-aware (UTC)"""
        if dt is None:
            return None
        if dt.tzinfo is None:
            # If naive, assume UTC
            return dt.replace(tzinfo=timezone.utc)
        return dt

    recent_results = [
        r
        for r in test_results
        if r.created_at and normalize_datetime(r.created_at) >= last_30
    ]
    previous_results = [
        r
        for r in test_results
        if r.created_at and prev_30_start <= normalize_datetime(r.created_at) < last_30
    ]

    recent_improvements = []
    for r in recent_results:
        try:
            progress = calculate_test_progress(db, r.id)
            if progress and progress.get("progress_percentage") is not None:
                recent_improvements.append(progress["progress_percentage"])
        except (ValueError, Exception):
            continue

    prev_improvements = []
    for r in previous_results:
        try:
            progress = calculate_test_progress(db, r.id)
            if progress and progress.get("progress_percentage") is not None:
                prev_improvements.append(progress["progress_percentage"])
        except (ValueError, Exception):
            continue

    recent_avg = (
        sum(recent_improvements) / len(recent_improvements)
        if recent_improvements
        else 0
    )
    prev_avg = (
        sum(prev_improvements) / len(prev_improvements) if prev_improvements else 0
    )

    trend_diff = recent_avg - prev_avg
    trend = f"{'+' if trend_diff >= 0 else ''}{trend_diff:.1f}%"

    return {
        "average": round(avg_improvement, 1),
        "trend": trend,
        "sample_size": len(improvements),
        "source": "database",
        "note": None,
    }


# Client Rating CRUD Functions
def create_client_rating(
    db: Session, rating_data: schemas.ClientRatingCreate
) -> models.ClientRating:
    """Create a new client rating"""
    rating = models.ClientRating(**rating_data.model_dump())
    db.add(rating)
    db.commit()
    db.refresh(rating)
    return rating


def get_client_ratings(
    db: Session,
    client_id: Optional[int] = None,
    trainer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> List[models.ClientRating]:
    """Get client ratings with optional filters"""
    query = db.query(models.ClientRating).filter(
        models.ClientRating.is_active.is_(True)
    )
    if client_id:
        query = query.filter(models.ClientRating.client_id == client_id)
    if trainer_id:
        query = query.filter(models.ClientRating.trainer_id == trainer_id)
    return (
        query.order_by(models.ClientRating.rating_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_client_rating(db: Session, rating_id: int) -> Optional[models.ClientRating]:
    """Get a specific client rating by ID"""
    return (
        db.query(models.ClientRating)
        .filter(
            models.ClientRating.id == rating_id, models.ClientRating.is_active.is_(True)
        )
        .first()
    )


def update_client_rating(
    db: Session, rating_id: int, rating_data: schemas.ClientRatingUpdate
) -> Optional[models.ClientRating]:
    """Update a client rating"""
    rating = get_client_rating(db, rating_id)
    if not rating:
        return None
    update_data = rating_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rating, field, value)
    db.commit()
    db.refresh(rating)
    return rating


def delete_client_rating(db: Session, rating_id: int) -> bool:
    """Delete (deactivate) a client rating"""
    rating = get_client_rating(db, rating_id)
    if not rating:
        return False
    rating.is_active = False
    db.commit()
    return True


def get_client_satisfaction_stats(
    db: Session, trainer_id: Optional[int] = None
) -> Dict:
    """
    Calculate client satisfaction stats from actual ratings.
    Falls back to mock if no ratings exist.
    """
    from sqlalchemy import func

    query = db.query(models.ClientRating).filter(
        models.ClientRating.is_active.is_(True)
    )
    if trainer_id:
        query = query.filter(models.ClientRating.trainer_id == trainer_id)

    # Calculate average rating and total count
    result = query.with_entities(
        func.avg(models.ClientRating.rating).label("avg_rating"),
        func.count(models.ClientRating.id).label("total_count"),
    ).first()

    if result and result.total_count > 0:
        avg_rating = float(result.avg_rating) if result.avg_rating else 0.0
        total_reviews = int(result.total_count)

        # Calculate trend (compare last 30 days vs previous 30 days)
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        last_30_days = now - timedelta(days=30)
        prev_30_days_start = last_30_days - timedelta(days=30)

        recent_ratings = (
            query.filter(models.ClientRating.rating_date >= last_30_days)
            .with_entities(func.avg(models.ClientRating.rating).label("avg"))
            .first()
        )
        previous_ratings = (
            query.filter(
                models.ClientRating.rating_date >= prev_30_days_start,
                models.ClientRating.rating_date < last_30_days,
            )
            .with_entities(func.avg(models.ClientRating.rating).label("avg"))
            .first()
        )

        trend = "+0.0"
        if recent_ratings and previous_ratings:
            if recent_ratings.avg and previous_ratings.avg:
                diff = float(recent_ratings.avg) - float(previous_ratings.avg)
                trend = f"{'+' if diff >= 0 else ''}{diff:.1f}"

        return {
            "rating": round(avg_rating, 2),
            "total_reviews": total_reviews,
            "trend": trend,
            "source": "database",
            "note": None,
        }

    # Fallback to mock if no ratings exist
    rating = 4.7
    total_reviews = 124
    if trainer_id:
        rating = max(3.5, min(5.0, rating + ((trainer_id % 7) - 3) * 0.05))
        total_reviews = max(10, total_reviews - (trainer_id % 11) * 3)
    return {
        "rating": round(rating, 2),
        "total_reviews": total_reviews,
        "trend": "+0.2",
        "source": "mock",
        "note": "No ratings found. Using mock data.",
    }


def get_fatigue_level_label(fatigue_value: Optional[int]) -> Optional[str]:
    """
    Convert numeric fatigue level (1-10) to label.
    Based on Figma: Perfect, Slightly Tired, Very Tired, Exhausted
    """
    if fatigue_value is None:
        return None
    if fatigue_value <= 2:
        return "Perfect"
    elif fatigue_value <= 4:
        return "Slightly Tired"
    elif fatigue_value <= 7:
        return "Very Tired"
    else:
        return "Exhausted"


def get_clients_with_metrics(
    db: Session,
    trainer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
) -> Tuple[List[Dict], int]:
    """
    Get client list with fatigue level and adherence percentage.
    Returns list of dicts with client info, fatigue, and adherence.
    """
    from datetime import date, timedelta

    # Base query for clients
    if trainer_id:
        # Get clients for this trainer
        query = (
            db.query(models.ClientProfile)
            .join(models.TrainerClient)
            .filter(models.TrainerClient.trainer_id == trainer_id)
            .filter(models.ClientProfile.is_active.is_(True))
        )
    else:
        query = db.query(models.ClientProfile).filter(
            models.ClientProfile.is_active.is_(True)
        )

    total = query.count()
    clients = (
        query.order_by(models.ClientProfile.apellidos, models.ClientProfile.nombre)
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Get last 30 days for adherence calculation
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    result = []
    for client in clients:
        # Get latest fatigue level from FatigueAnalysis
        latest_fatigue = (
            db.query(models.FatigueAnalysis)
            .filter(models.FatigueAnalysis.client_id == client.id)
            .order_by(models.FatigueAnalysis.analysis_date.desc())
            .first()
        )

        fatigue_level_numeric = None
        if latest_fatigue and latest_fatigue.pre_fatigue_level is not None:
            fatigue_level_numeric = latest_fatigue.pre_fatigue_level
        elif latest_fatigue and latest_fatigue.post_fatigue_level is not None:
            fatigue_level_numeric = latest_fatigue.post_fatigue_level

        fatigue_level = get_fatigue_level_label(fatigue_level_numeric)

        # Calculate adherence (last 30 days)
        sessions = (
            db.query(models.TrainingSession)
            .filter(
                models.TrainingSession.client_id == client.id,
                models.TrainingSession.session_date >= start_date,
                models.TrainingSession.session_date <= end_date,
                models.TrainingSession.is_active.is_(True),
            )
            .all()
        )

        planned_sessions = len([s for s in sessions if s.status != "skipped"])
        completed_sessions = len([s for s in sessions if s.status == "completed"])
        adherence_percentage = (
            (completed_sessions / planned_sessions * 100)
            if planned_sessions > 0
            else None
        )

        result.append(
            {
                "id": client.id,
                "nombre": client.nombre,
                "apellidos": client.apellidos,
                "mail": client.mail,
                "fatigue_level": fatigue_level,
                "fatigue_level_numeric": fatigue_level_numeric,
                "adherence_percentage": (
                    round(adherence_percentage, 1)
                    if adherence_percentage is not None
                    else None
                ),
            }
        )

    return result, total


def get_recent_activity(
    db: Session,
    trainer_id: Optional[int] = None,
    limit: int = 10,
) -> List[Dict]:
    """
    Get recent activity feed for trainer dashboard.
    Includes: completed sessions, new clients, scheduled sessions,
    goal achievements, test completions.
    """
    activities = []
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=7)  # Last 7 days
    cutoff_date_naive = cutoff_date.replace(
        tzinfo=None
    )  # For comparison with DB fields

    # 1. Completed sessions
    sessions_query = (
        db.query(models.TrainingSession, models.ClientProfile)
        .join(models.ClientProfile)
        .filter(
            models.TrainingSession.status == "completed",
            models.TrainingSession.updated_at >= cutoff_date_naive,
            models.TrainingSession.is_active.is_(True),
        )
    )
    if trainer_id:
        sessions_query = sessions_query.filter(
            models.TrainingSession.trainer_id == trainer_id
        )

    for session, client in (
        sessions_query.order_by(models.TrainingSession.updated_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(
            {
                "id": session.id,
                "type": "session_completed",
                "actor_name": f"{client.nombre} {client.apellidos}",
                "description": f"completed a {session.session_type} session",
                "timestamp": (
                    session.updated_at.replace(tzinfo=timezone.utc)
                    if session.updated_at.tzinfo is None
                    else session.updated_at
                ),
                "client_id": client.id,
                "session_id": session.id,
                "icon": "checkmark",
            }
        )

    # 2. New clients (joined in last 7 days)
    clients_query = (
        db.query(models.ClientProfile, models.TrainerClient)
        .join(models.TrainerClient)
        .filter(
            models.ClientProfile.fecha_alta >= cutoff_date.date(),
            models.ClientProfile.is_active.is_(True),
        )
    )
    if trainer_id:
        clients_query = clients_query.filter(
            models.TrainerClient.trainer_id == trainer_id
        )

    for client, tc in (
        clients_query.order_by(models.ClientProfile.fecha_alta.desc())
        .limit(limit)
        .all()
    ):
        activities.append(
            {
                "id": client.id,
                "type": "client_added",
                "actor_name": f"{client.nombre} {client.apellidos}",
                "description": "joined as a new client",
                "timestamp": datetime.combine(client.fecha_alta, time(0, 0, 0)).replace(
                    tzinfo=timezone.utc
                ),
                "client_id": client.id,
                "icon": "person_add",
            }
        )

    # 3. Scheduled sessions
    scheduled_query = (
        db.query(models.ScheduledSession, models.ClientProfile)
        .join(models.ClientProfile)
        .filter(
            models.ScheduledSession.created_at >= cutoff_date_naive,
            models.ScheduledSession.is_active.is_(True),
        )
    )
    if trainer_id:
        scheduled_query = scheduled_query.filter(
            models.ScheduledSession.trainer_id == trainer_id
        )

    for scheduled, client in (
        scheduled_query.order_by(models.ScheduledSession.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(
            {
                "id": scheduled.id,
                "type": "session_scheduled",
                "actor_name": f"{client.nombre} {client.apellidos}",
                "description": (
                    f"scheduled a session for "
                    f"{scheduled.scheduled_date.strftime('%B %d, %Y')}"
                ),
                "timestamp": (
                    scheduled.created_at.replace(tzinfo=timezone.utc)
                    if scheduled.created_at.tzinfo is None
                    else scheduled.created_at
                ),
                "client_id": client.id,
                "session_id": scheduled.id,
                "icon": "calendar",
            }
        )

    # 4. Test completions (recent physical test results)
    tests_query = (
        db.query(models.PhysicalTestResult, models.ClientProfile, models.PhysicalTest)
        .join(models.ClientProfile)
        .join(models.PhysicalTest)
        .filter(
            models.PhysicalTestResult.created_at >= cutoff_date_naive,
            models.PhysicalTestResult.is_active.is_(True),
        )
    )
    if trainer_id:
        # Filter by trainer's clients
        trainer_client_ids = [
            tc.client_id
            for tc in db.query(models.TrainerClient.client_id)
            .filter(models.TrainerClient.trainer_id == trainer_id)
            .all()
        ]
        if trainer_client_ids:
            tests_query = tests_query.filter(
                models.PhysicalTestResult.client_id.in_(trainer_client_ids)
            )
        else:
            # No clients for this trainer, skip test results
            pass

    for test_result, client, test in (
        tests_query.order_by(models.PhysicalTestResult.created_at.desc())
        .limit(limit)
        .all()
    ):
        activities.append(
            {
                "id": test_result.id,
                "type": "test_completed",
                "actor_name": f"{client.nombre} {client.apellidos}",
                "description": f"completed {test.name} test",
                "timestamp": (
                    test_result.created_at.replace(tzinfo=timezone.utc)
                    if test_result.created_at.tzinfo is None
                    else test_result.created_at
                ),
                "client_id": client.id,
                "icon": "trending_up",
            }
        )

    # Sort all activities by timestamp (most recent first) and limit
    activities.sort(key=lambda x: x["timestamp"], reverse=True)
    return activities[:limit]


def get_plan_adherence_stats(db: Session, trainer_id: Optional[int] = None) -> Dict:
    """
    Calculate plan adherence from actual session completion data.
    Uses real data from TrainingSession, TrainingPlan, and Microcycle tables.
    """
    from datetime import date, timedelta

    from sqlalchemy import func

    # Get trainer's clients
    if trainer_id:
        client_ids = [
            tc.client_id
            for tc in db.query(models.TrainerClient.client_id)
            .filter(models.TrainerClient.trainer_id == trainer_id)
            .all()
        ]
    else:
        client_ids = [c.id for c in db.query(models.ClientProfile.id).all()]

    if not client_ids:
        return {
            "adherence_percentage": 0.0,
            "trend": "+0%",
            "aligned_plans": 0,
            "total_plans": 0,
            "source": "database",
            "note": "No clients found",
        }

    # Get active training plans for these clients
    plans = (
        db.query(models.TrainingPlan)
        .filter(
            models.TrainingPlan.client_id.in_(client_ids),
            models.TrainingPlan.status == "active",
            models.TrainingPlan.is_active.is_(True),
        )
        .all()
    )

    if not plans:
        return {
            "adherence_percentage": 0.0,
            "trend": "+0%",
            "aligned_plans": 0,
            "total_plans": 0,
            "source": "database",
            "note": "No active plans found",
        }

    total_planned = 0
    total_completed = 0
    aligned_plans = 0

    for plan in plans:
        # Count planned sessions (microcycles in this plan)
        # Get all macrocycles for this plan
        macrocycles = (
            db.query(models.Macrocycle)
            .filter(models.Macrocycle.training_plan_id == plan.id)
            .all()
        )

        plan_planned = 0
        for macro in macrocycles:
            mesocycles = (
                db.query(models.Mesocycle)
                .filter(models.Mesocycle.macrocycle_id == macro.id)
                .all()
            )
            for meso in mesocycles:
                microcycles = (
                    db.query(models.Microcycle)
                    .filter(models.Microcycle.mesocycle_id == meso.id)
                    .all()
                )
                plan_planned += len(microcycles)

        total_planned += plan_planned

        # Count completed sessions that belong to microcycles in THIS plan
        # Get all microcycle IDs for this plan
        plan_microcycle_ids = []
        for macro in macrocycles:
            mesocycles = (
                db.query(models.Mesocycle)
                .filter(models.Mesocycle.macrocycle_id == macro.id)
                .all()
            )
            for meso in mesocycles:
                microcycles = (
                    db.query(models.Microcycle.id)
                    .filter(models.Microcycle.mesocycle_id == meso.id)
                    .all()
                )
                plan_microcycle_ids.extend([m.id for m in microcycles])

        # Count completed sessions linked to these microcycles
        completed = 0
        if plan_microcycle_ids:
            completed = (
                db.query(func.count(models.TrainingSession.id))
                .filter(
                    models.TrainingSession.microcycle_id.in_(plan_microcycle_ids),
                    models.TrainingSession.status == "completed",
                    models.TrainingSession.is_active.is_(True),
                )
                .scalar()
            ) or 0

        total_completed += completed

        # Check if this plan is aligned (>= 80% adherence)
        plan_adherence = (completed / plan_planned * 100) if plan_planned > 0 else 0
        if plan_adherence >= 80:
            aligned_plans += 1

    if total_planned > 0:
        adherence = (total_completed / total_planned) * 100

        # Calculate trend (last 30 days vs previous 30 days)
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        prev_start = start_date - timedelta(days=30)

        recent_completed = (
            db.query(func.count(models.TrainingSession.id))
            .filter(
                models.TrainingSession.client_id.in_(client_ids),
                models.TrainingSession.status == "completed",
                models.TrainingSession.session_date >= start_date,
                models.TrainingSession.session_date <= end_date,
                models.TrainingSession.is_active.is_(True),
            )
            .scalar()
        ) or 0

        prev_completed = (
            db.query(func.count(models.TrainingSession.id))
            .filter(
                models.TrainingSession.client_id.in_(client_ids),
                models.TrainingSession.status == "completed",
                models.TrainingSession.session_date >= prev_start,
                models.TrainingSession.session_date < start_date,
                models.TrainingSession.is_active.is_(True),
            )
            .scalar()
        ) or 0

        # Calculate trend percentage
        trend_pct = (
            ((recent_completed - prev_completed) / prev_completed * 100)
            if prev_completed > 0
            else 0
        )
        trend = f"{'+' if trend_pct >= 0 else ''}{trend_pct:.1f}%"

        return {
            "adherence_percentage": round(adherence, 1),
            "trend": trend,
            "aligned_plans": aligned_plans,
            "total_plans": len(plans),
            "source": "database",
            "note": None,
        }

    return {
        "adherence_percentage": 0.0,
        "trend": "+0%",
        "aligned_plans": 0,
        "total_plans": len(plans),
        "source": "database",
        "note": "No planned sessions found",
    }


def get_client_progress_category_stats(
    db: Session, trainer_id: Optional[int] = None
) -> Dict:
    """
    Classify clients into progress categories based on real metrics.
    Uses get_clients_with_metrics() to get adherence and fatigue data.
    """
    # Get trainer's clients with metrics (uses existing function!)
    clients_data, total = get_clients_with_metrics(
        db=db, trainer_id=trainer_id, skip=0, limit=1000
    )

    on_track = 0
    behind_schedule = 0
    need_attention = 0

    for client_data in clients_data:
        adherence = client_data.get("adherence_percentage")
        fatigue_numeric = client_data.get("fatigue_level_numeric")

        # Classification logic:
        # On Track: adherence >= 85 AND fatigue <= 4 (Perfect or Slightly Tired)
        # Behind Schedule: adherence >= 70 AND fatigue <= 6
        # Need Attention: everything else

        if adherence is not None and fatigue_numeric is not None:
            if adherence >= 85 and fatigue_numeric <= 4:
                on_track += 1
            elif adherence >= 70 and fatigue_numeric <= 6:
                behind_schedule += 1
            else:
                need_attention += 1
        elif adherence is not None:
            # If no fatigue data, use adherence only
            if adherence >= 85:
                on_track += 1
            elif adherence >= 70:
                behind_schedule += 1
            else:
                need_attention += 1
        else:
            # No data - classify as need attention
            need_attention += 1

    total_clients = len(clients_data)
    overall = (on_track / total_clients * 100) if total_clients > 0 else 0

    return {
        "on_track": on_track,
        "behind_schedule": behind_schedule,
        "need_attention": need_attention,
        "overall_percentage": round(overall, 1),
        "updated_at": datetime.now(timezone.utc),
        "source": "database",
        "note": None,
    }


def get_billing_stats(
    db: Session, period: str = "monthly", trainer_id: Optional[int] = None
) -> Dict:
    """
    Placeholder for billing stats (monthly or annual buckets).
    """
    period = period.lower()
    if period not in {"monthly", "annual"}:
        raise ValueError("period must be 'monthly' or 'annual'")

    currency = "EUR"
    items = []
    if period == "monthly":
        labels = [
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ]
        base_revenue = 18500.0
        for idx, label in enumerate(labels):
            modifier = ((idx % 4) - 1) * 750
            revenue = base_revenue + modifier
            clients = 35 + (idx % 6)
            growth = 2.5 + (idx % 3) * 0.5
            if trainer_id:
                revenue += (trainer_id % 5) * 100
                clients = max(10, clients - (trainer_id % 4))
            items.append(
                {
                    "label": label,
                    "revenue": round(revenue, 2),
                    "clients": clients,
                    "growth": round(growth, 2),
                    "currency": currency,
                }
            )
    else:  # annual
        current_year = datetime.now().year
        base_revenue = 210000.0
        for year in range(current_year - 3, current_year + 1):
            growth = 8.5 if year == current_year else 6.0
            revenue = base_revenue * (1 + 0.05 * (year - (current_year - 3)))
            clients = 120 + (year - (current_year - 3)) * 8
            if trainer_id:
                revenue += (trainer_id % 3) * 2500
            items.append(
                {
                    "label": str(year),
                    "revenue": round(revenue, 2),
                    "clients": clients,
                    "growth": round(growth, 2),
                    "currency": currency,
                }
            )

    return {
        "period": period,
        "items": items,
        "source": "mock",
        "note": "TODO: Replace with billing service integration",
    }


def compute_daily_coherence(
    db: Session,
    client_id: int,
    period_start: date,
    period_end: date,
    period_type: str = "week",
) -> Dict:
    """
    Compute daily coherence analytics for a client over a time period.

    Calculates:
    - Adherence: (Completed sessions / Planned sessions) × 100
    - sRPE scatter: Prescribed vs Perceived intensity
    - Monotony: Daily mean / Standard deviation of load
    - Strain: Weekly load × Monotony

    Args:
        db: Database session
        client_id: Client ID
        period_start: Start date of analysis period
        period_end: End date of analysis period
        period_type: "week", "month", "training_block", "year", or "all_time"

    Returns:
        Dict matching DailyCoherenceAnalyticsOut schema
    """
    from collections import defaultdict
    from statistics import mean, stdev

    # 1. Get all sessions for the client in the date range
    sessions = (
        db.query(models.TrainingSession)
        .filter(
            models.TrainingSession.client_id == client_id,
            models.TrainingSession.session_date >= period_start,
            models.TrainingSession.session_date <= period_end,
            models.TrainingSession.is_active.is_(True),
        )
        .order_by(models.TrainingSession.session_date)
        .all()
    )

    if not sessions:
        # Return empty structure if no sessions
        return {
            "client_id": client_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "period_type": period_type,
            "kpis": {
                "adherence_percentage": 0.0,
                "average_srpe": 0.0,
                "monotony": 0.0,
                "strain": 0.0,
            },
            "adherence_data": [],
            "srpe_scatter_data": [],
            "monotony_strain_data": [],
            "interpretive_summary": "No training sessions found for this period.",
            "key_recommendations": [],
        }

    # 2. Get feedback for these sessions
    session_ids = [s.id for s in sessions]
    feedback_records = (
        db.query(models.ClientFeedback)
        .filter(models.ClientFeedback.training_session_id.in_(session_ids))
        .all()
    )
    feedback_by_session = {f.training_session_id: f for f in feedback_records}

    # 3. Calculate adherence
    planned_sessions = len([s for s in sessions if s.status != "skipped"])
    completed_sessions = len([s for s in sessions if s.status == "completed"])
    adherence_percentage = (
        (completed_sessions / planned_sessions * 100) if planned_sessions > 0 else 0.0
    )

    # 4. Build sRPE scatter data (prescribed vs perceived)
    srpe_points = []
    srpe_values = []
    daily_loads = defaultdict(list)  # date -> [load values]

    for session in sessions:
        # Get prescribed intensity (convert from 0-100% to 0-10 scale if needed)
        prescribed = session.planned_intensity
        if prescribed is not None:
            if prescribed > 10:
                prescribed = prescribed / 10.0  # Convert 0-100 to 0-10

        # Get perceived sRPE from feedback
        feedback = feedback_by_session.get(session.id)
        perceived = None
        if feedback and feedback.perceived_effort is not None:
            perceived = float(feedback.perceived_effort)

        # Only add point if both values exist
        if prescribed is not None and perceived is not None:
            srpe_points.append(
                {
                    "prescribed_srpe": round(prescribed, 1),
                    "perceived_srpe": round(perceived, 1),
                    "session_date": session.session_date.isoformat(),
                    "session_id": session.id,
                }
            )
            srpe_values.append(perceived)

        # Calculate daily load: sRPE × Duration (min)
        # Use actual duration if available, otherwise planned
        duration = session.actual_duration or session.planned_duration or 0
        if perceived is not None and duration > 0:
            daily_load = perceived * duration
            daily_loads[session.session_date].append(daily_load)

    # Average sRPE
    average_srpe = round(mean(srpe_values), 1) if srpe_values else 0.0

    # 5. Calculate monotony and strain with multi-granularity support
    # Group daily loads by appropriate period based on period_type
    period_data = defaultdict(list)  # period_key -> [daily_loads]
    period_info = {}  # period_key -> (period_start, period_label)

    if period_type == "week":
        # Daily granularity for week view
        for day, loads in daily_loads.items():
            # Only include days within the requested range
            if period_start <= day <= period_end:
                period_key = day.isoformat()
                period_data[period_key].extend(loads)
                period_info[period_key] = (day, day.isoformat())
    elif period_type == "month":
        # Weekly granularity for month view
        for day, loads in daily_loads.items():
            # Only include days within the requested range
            if period_start <= day <= period_end:
                # Get Monday of ISO week
                wd = day.isoweekday()
                monday = day - timedelta(days=wd - 1)
                # Only include weeks that overlap with the requested range
                week_end = monday + timedelta(days=6)
                if monday <= period_end and week_end >= period_start:
                    period_key = monday.isoformat()
                    period_data[period_key].extend(loads)
                    week_num = monday.isocalendar()[1]
                    period_info[period_key] = (monday, f"W{week_num}")
    elif period_type == "year":
        # Monthly granularity for year view
        for day, loads in daily_loads.items():
            # Only include days within the requested range
            if period_start <= day <= period_end:
                # Group by calendar month
                month_start = day.replace(day=1)
                period_key = month_start.isoformat()
                period_data[period_key].extend(loads)
                month_label = month_start.strftime("%b %Y")
                period_info[period_key] = (month_start, month_label)
    elif period_type == "all_time":
        # Yearly granularity for all-time view
        for day, loads in daily_loads.items():
            # Only include days within the requested range
            if period_start <= day <= period_end:
                # Group by calendar year
                year_start = day.replace(month=1, day=1)
                period_key = year_start.isoformat()
                period_data[period_key].extend(loads)
                year_label = str(day.year)
                period_info[period_key] = (year_start, year_label)
    else:
        # training_block or other: use weekly granularity with range filtering
        for day, loads in daily_loads.items():
            # Only include days within the requested range
            if period_start <= day <= period_end:
                # Get Monday of ISO week
                wd = day.isoweekday()
                monday = day - timedelta(days=wd - 1)
                # Only include weeks that overlap with the requested range
                week_end = monday + timedelta(days=6)
                if monday <= period_end and week_end >= period_start:
                    period_key = monday.isoformat()
                    period_data[period_key].extend(loads)
                    week_num = monday.isocalendar()[1]
                    period_info[period_key] = (monday, f"W{week_num}")

    monotony_strain_data = []
    cumulative_strain = 0.0  # Running total for cumulative strain
    for period_key in sorted(period_data.keys()):
        period_loads = period_data[period_key]
        if not period_loads:
            continue

        period_start_date, period_label = period_info[period_key]

        # Calculate period load (sum of daily loads)
        period_load = sum(period_loads)

        # Calculate monotony: mean / std dev
        # If std dev is 0, set monotony to high value (no variability)
        if len(period_loads) > 1:
            load_mean = mean(period_loads)
            load_std = stdev(period_loads)
            monotony = (
                round(load_mean / load_std, 2) if load_std > 0 else 999.0
            )  # High monotony if no variation
        else:
            monotony = 999.0  # Single day = infinite monotony

        # Strain = period load × monotony
        strain = round(period_load * monotony, 1)

        # Calculate cumulative strain (running total)
        cumulative_strain += strain

        monotony_strain_data.append(
            {
                "period_start": period_start_date.isoformat(),
                "period_label": period_label,
                "monotony": monotony,
                "strain": strain,
                "period_load": round(period_load, 1),
                "cumulative_strain": round(cumulative_strain, 1),
            }
        )

    # Current period monotony and strain (most recent period)
    current_monotony = (
        monotony_strain_data[-1]["monotony"] if monotony_strain_data else 0.0
    )
    current_strain = monotony_strain_data[-1]["strain"] if monotony_strain_data else 0.0

    # 6. Build adherence data by period (for charts)
    adherence_data = []
    if period_type == "week":
        # Group by day
        day_adherence = defaultdict(lambda: {"planned": 0, "completed": 0})
        for session in sessions:
            if session.status != "skipped":
                day_adherence[session.session_date]["planned"] += 1
            if session.status == "completed":
                day_adherence[session.session_date]["completed"] += 1

        for day in sorted(day_adherence.keys()):
            planned = day_adherence[day]["planned"]
            completed = day_adherence[day]["completed"]
            adherence = (completed / planned * 100) if planned > 0 else 0.0
            adherence_data.append(
                {"period": day.isoformat(), "adherence": round(adherence, 1)}
            )
    elif period_type == "month":
        # Group by week (only weeks within the requested range)
        week_adherence = defaultdict(lambda: {"planned": 0, "completed": 0})
        for session in sessions:
            wd = session.session_date.isoweekday()
            monday = session.session_date - timedelta(days=wd - 1)
            week_end = monday + timedelta(days=6)
            # Only include weeks that overlap with the requested range
            if monday <= period_end and week_end >= period_start:
                if session.status != "skipped":
                    week_adherence[monday]["planned"] += 1
                if session.status == "completed":
                    week_adherence[monday]["completed"] += 1

        for week_start in sorted(week_adherence.keys()):
            planned = week_adherence[week_start]["planned"]
            completed = week_adherence[week_start]["completed"]
            adherence = (completed / planned * 100) if planned > 0 else 0.0
            adherence_data.append(
                {
                    "period": f"W{week_start.isocalendar()[1]}",
                    "adherence": round(adherence, 1),
                }
            )
    elif period_type == "year":
        # Group by month
        month_adherence = defaultdict(lambda: {"planned": 0, "completed": 0})
        for session in sessions:
            month_start = session.session_date.replace(day=1)
            if session.status != "skipped":
                month_adherence[month_start]["planned"] += 1
            if session.status == "completed":
                month_adherence[month_start]["completed"] += 1

        for month_start in sorted(month_adherence.keys()):
            planned = month_adherence[month_start]["planned"]
            completed = month_adherence[month_start]["completed"]
            adherence = (completed / planned * 100) if planned > 0 else 0.0
            month_label = month_start.strftime("%b %Y")
            adherence_data.append(
                {"period": month_label, "adherence": round(adherence, 1)}
            )
    elif period_type == "all_time":
        # Group by year
        year_adherence = defaultdict(lambda: {"planned": 0, "completed": 0})
        for session in sessions:
            year_start = session.session_date.replace(month=1, day=1)
            if session.status != "skipped":
                year_adherence[year_start]["planned"] += 1
            if session.status == "completed":
                year_adherence[year_start]["completed"] += 1

        for year_start in sorted(year_adherence.keys()):
            planned = year_adherence[year_start]["planned"]
            completed = year_adherence[year_start]["completed"]
            adherence = (completed / planned * 100) if planned > 0 else 0.0
            year_label = str(year_start.year)
            adherence_data.append(
                {"period": year_label, "adherence": round(adherence, 1)}
            )
    else:
        # training_block: Group by week (only weeks within the requested range)
        week_adherence = defaultdict(lambda: {"planned": 0, "completed": 0})
        for session in sessions:
            wd = session.session_date.isoweekday()
            monday = session.session_date - timedelta(days=wd - 1)
            week_end = monday + timedelta(days=6)
            # Only include weeks that overlap with the requested range
            if monday <= period_end and week_end >= period_start:
                if session.status != "skipped":
                    week_adherence[monday]["planned"] += 1
                if session.status == "completed":
                    week_adherence[monday]["completed"] += 1

        for week_start in sorted(week_adherence.keys()):
            planned = week_adherence[week_start]["planned"]
            completed = week_adherence[week_start]["completed"]
            adherence = (completed / planned * 100) if planned > 0 else 0.0
            week_num = week_start.isocalendar()[1]
            adherence_data.append(
                {
                    "period": f"W{week_num}",
                    "adherence": round(adherence, 1),
                }
            )

    # 7. Generate interpretive summary
    summary_parts = []
    if adherence_percentage >= 85:
        summary_parts.append(f"Excellent adherence ({adherence_percentage:.0f}%)")
    elif adherence_percentage >= 70:
        summary_parts.append(f"Good adherence ({adherence_percentage:.0f}%)")
    else:
        summary_parts.append(
            f"Adherence needs improvement ({adherence_percentage:.0f}%)"
        )

    # Check sRPE deviation
    if srpe_points:
        avg_prescribed = mean([p["prescribed_srpe"] for p in srpe_points])
        avg_perceived = mean([p["perceived_srpe"] for p in srpe_points])
        deviation = (
            abs(avg_perceived - avg_prescribed) / avg_prescribed * 100
            if avg_prescribed > 0
            else 0
        )

        if deviation > 20:
            summary_parts.append(
                f"Client perceives sessions {deviation:.0f}% harder than prescribed"
            )
        elif deviation < -20:
            summary_parts.append(
                f"Client perceives sessions {abs(deviation):.0f}% "
                f"easier than prescribed"
            )

    # Check monotony
    if current_monotony > 2.0:
        summary_parts.append(
            f"Weekly monotony is high ({current_monotony:.1f}): "
            f"consider adding more load variability"
        )
    elif current_monotony > 0:
        summary_parts.append(f"Weekly monotony is moderate ({current_monotony:.1f})")

    interpretive_summary = ". ".join(summary_parts) + "."

    # 8. Generate key recommendations
    recommendations = []
    if adherence_percentage < 70:
        recommendations.append("Focus on improving session completion rate")
    if current_monotony > 2.0:
        recommendations.append(
            "Increase training variability to reduce monotony and injury risk"
        )
    if not srpe_points:
        recommendations.append(
            "Encourage client to provide session feedback for better load monitoring"
        )

    return {
        "client_id": client_id,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "period_type": period_type,
        "kpis": {
            "adherence_percentage": round(adherence_percentage, 1),
            "average_srpe": average_srpe,
            "monotony": round(current_monotony, 2),
            "strain": round(current_strain, 1),
        },
        "adherence_data": adherence_data,
        "srpe_scatter_data": srpe_points,
        "monotony_strain_data": monotony_strain_data,
        "interpretive_summary": interpretive_summary,
        "key_recommendations": recommendations,
    }


# Physical Testing CRUD Operations
def create_physical_test(
    db: Session, test_data: schemas.PhysicalTestCreate, trainer_id: Optional[int] = None
):
    """Create a new physical test definition"""
    db_test = models.PhysicalTest(
        **test_data.model_dump(exclude_unset=True),
        created_by_trainer_id=trainer_id,
    )
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test


def get_physical_tests(
    db: Session,
    category: Optional[str] = None,
    is_standard: Optional[bool] = None,
    trainer_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
):
    """Get physical tests with optional filtering"""
    query = db.query(models.PhysicalTest).filter(
        models.PhysicalTest.is_active.is_(True)
    )

    if category:
        query = query.filter(models.PhysicalTest.category == category)
    if is_standard is not None:
        query = query.filter(models.PhysicalTest.is_standard == is_standard)
    if trainer_id:
        # Get standard tests + trainer's custom tests
        query = query.filter(
            (models.PhysicalTest.is_standard.is_(True))
            | (models.PhysicalTest.created_by_trainer_id == trainer_id)
        )

    return (
        query.order_by(models.PhysicalTest.category, models.PhysicalTest.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_physical_test(db: Session, test_id: int):
    """Get a specific physical test"""
    return (
        db.query(models.PhysicalTest).filter(models.PhysicalTest.id == test_id).first()
    )


def update_physical_test(
    db: Session, test_id: int, test_data: schemas.PhysicalTestUpdate
):
    """Update a physical test"""
    db_test = get_physical_test(db, test_id)
    if not db_test:
        return None

    update_data = test_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_test, field, value)

    db.commit()
    db.refresh(db_test)
    return db_test


def delete_physical_test(db: Session, test_id: int) -> bool:
    """Delete a physical test (soft delete)"""
    db_test = get_physical_test(db, test_id)
    if not db_test:
        return False

    db_test.is_active = False
    db.commit()
    return True


def create_physical_test_result(
    db: Session, result_data: schemas.PhysicalTestResultCreate
):
    """Create a new physical test result"""
    # Check if this is the first result for this client+test (baseline)
    existing_results = (
        db.query(models.PhysicalTestResult)
        .filter(
            models.PhysicalTestResult.client_id == result_data.client_id,
            models.PhysicalTestResult.test_id == result_data.test_id,
            models.PhysicalTestResult.is_active.is_(True),
        )
        .count()
    )

    # If no existing results, mark as baseline
    is_baseline = existing_results == 0 or result_data.is_baseline

    db_result = models.PhysicalTestResult(
        **result_data.model_dump(exclude_unset=True, exclude={"is_baseline"}),
        is_baseline=is_baseline,
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result


def get_physical_test_results(
    db: Session,
    client_id: Optional[int] = None,
    test_id: Optional[int] = None,
    category: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
):
    """Get physical test results with optional filtering"""
    query = db.query(models.PhysicalTestResult).filter(
        models.PhysicalTestResult.is_active.is_(True)
    )

    if client_id:
        query = query.filter(models.PhysicalTestResult.client_id == client_id)
    if test_id:
        query = query.filter(models.PhysicalTestResult.test_id == test_id)
    if category:
        query = query.join(models.PhysicalTest).filter(
            models.PhysicalTest.category == category
        )

    return (
        query.order_by(models.PhysicalTestResult.test_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_physical_test_result(db: Session, result_id: int):
    """Get a specific physical test result"""
    return (
        db.query(models.PhysicalTestResult)
        .filter(models.PhysicalTestResult.id == result_id)
        .first()
    )


def update_physical_test_result(
    db: Session, result_id: int, result_data: schemas.PhysicalTestResultUpdate
):
    """Update a physical test result"""
    db_result = get_physical_test_result(db, result_id)
    if not db_result:
        return None

    update_data = result_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_result, field, value)

    db.commit()
    db.refresh(db_result)
    return db_result


def delete_physical_test_result(db: Session, result_id: int) -> bool:
    """Delete a physical test result (soft delete)"""
    db_result = get_physical_test_result(db, result_id)
    if not db_result:
        return False

    db_result.is_active = False
    db.commit()
    return True


def calculate_test_progress(db: Session, result_id: int) -> Dict:
    """
    Calculate progress metrics for a test result compared to baseline.

    Returns:
        Dict with baseline_value, baseline_date, progress_percentage, trend
    """
    result = get_physical_test_result(db, result_id)
    if not result:
        raise ValueError(f"Test result {result_id} not found")

    # Get baseline result for this client+test
    baseline = (
        db.query(models.PhysicalTestResult)
        .filter(
            models.PhysicalTestResult.client_id == result.client_id,
            models.PhysicalTestResult.test_id == result.test_id,
            models.PhysicalTestResult.is_baseline.is_(True),
            models.PhysicalTestResult.is_active.is_(True),
        )
        .order_by(models.PhysicalTestResult.test_date.asc())
        .first()
    )

    if not baseline or baseline.id == result.id:
        # This is the baseline or no baseline exists
        return {
            "baseline_value": result.value,
            "baseline_date": result.test_date.isoformat(),
            "progress_percentage": 0.0,
            "trend": "baseline",
        }

    # Calculate progress percentage
    # For tests where lower is better (time, etc.), reverse the calculation
    test = get_physical_test(db, result.test_id)
    is_lower_better = test and test.category in ["speed", "anaerobic"]

    if is_lower_better:
        # For time-based tests: % improvement = (baseline - current) / baseline * 100
        progress = (
            ((baseline.value - result.value) / baseline.value * 100)
            if baseline.value > 0
            else 0.0
        )
    else:
        # For distance/weight/height: % improvement
        # = (current - baseline) / baseline * 100
        progress = (
            ((result.value - baseline.value) / baseline.value * 100)
            if baseline.value > 0
            else 0.0
        )

    # Determine trend
    if abs(progress) < 2.0:  # SWC (Smallest Worthwhile Change) threshold
        trend = "stable"
    elif progress > 0:
        trend = "improving"
    else:
        trend = "declining"

    return {
        "baseline_value": baseline.value,
        "baseline_date": baseline.test_date.isoformat(),
        "progress_percentage": round(progress, 1),
        "trend": trend,
    }


def get_client_testing_summary(db: Session, client_id: int) -> Dict:
    """
    Get comprehensive testing summary for a client.

    Returns:
        Physical quality profile, latest tests, upcoming tests, analysis
    """
    # Get all test results for the client
    all_results = (
        db.query(models.PhysicalTestResult)
        .join(models.PhysicalTest)
        .filter(
            models.PhysicalTestResult.client_id == client_id,
            models.PhysicalTestResult.is_active.is_(True),
        )
        .order_by(models.PhysicalTestResult.test_date.desc())
        .all()
    )

    # Group by category and get latest result per category
    latest_by_category = {}
    categories = ["strength", "power", "speed", "aerobic", "anaerobic", "mobility"]

    for category in categories:
        try:
            category_results = [
                r for r in all_results if r.test and r.test.category == category
            ]
            if category_results:
                latest = category_results[0]
                try:
                    progress = calculate_test_progress(db, latest.id)
                except (ValueError, Exception):
                    # If progress calculation fails, use default values
                    progress = {
                        "baseline_value": None,
                        "baseline_date": None,
                        "progress_percentage": None,
                        "trend": "unknown",
                    }
                # Return structure matching TestResultWithProgress schema
                latest_by_category[category] = {
                    "id": latest.id,
                    "client_id": latest.client_id,
                    "test_id": latest.test_id,
                    "trainer_id": latest.trainer_id,
                    "test_date": latest.test_date,
                    "value": latest.value,
                    "unit": latest.unit,
                    "is_baseline": latest.is_baseline,
                    "notes": latest.notes,
                    "surface": latest.surface,
                    "conditions": latest.conditions,
                    "created_at": latest.created_at,
                    "updated_at": latest.updated_at,
                    "is_active": latest.is_active,
                    **progress,
                }
            else:
                latest_by_category[category] = None
        except Exception:
            # If there's an error processing this category, set to None
            latest_by_category[category] = None

    # Calculate physical quality profile scores (0-100)
    # Based on progress percentages from baseline
    # Score = 50 (baseline) + progress_percentage (capped at 0-100)
    profile = {}
    for category in categories:
        category_data = latest_by_category.get(category)
        if category_data and category_data.get("progress_percentage") is not None:
            # Start at 50 (baseline) and add progress
            # Cap between 0 and 100
            base_score = 50.0
            progress = category_data.get("progress_percentage", 0.0)
            score = base_score + (progress * 0.5)  # Scale progress to 0-50 range
            profile[category] = max(0.0, min(100.0, round(score, 1)))
        else:
            # No test data for this category - default to 50 (neutral)
            profile[category] = 50.0

    # Generate profile analysis
    strong_qualities = []
    weak_qualities = []
    improving_qualities = []
    declining_qualities = []

    for cat, data in latest_by_category.items():
        if data:
            trend = data.get("trend", "unknown")
            progress = data.get("progress_percentage", 0.0)

            if trend == "improving" and progress > 5.0:
                improving_qualities.append(cat)
            elif trend == "declining" and progress < -5.0:
                declining_qualities.append(cat)

            # Strong/weak based on absolute score
            score = profile.get(cat, 50.0)
            if score >= 70.0:
                strong_qualities.append(cat)
            elif score <= 30.0:
                weak_qualities.append(cat)

    analysis_parts = []
    if improving_qualities:
        analysis_parts.append(
            f"Showing improvement in {', '.join(improving_qualities)}"
        )
    if declining_qualities:
        declining_str = ", ".join(declining_qualities)
        analysis_parts.append(
            f"Declining performance in {declining_str} - consider intervention"
        )
    if strong_qualities and not improving_qualities:
        analysis_parts.append(f"Strong baseline in {', '.join(strong_qualities)}")
    if weak_qualities and not declining_qualities:
        analysis_parts.append(
            f"Focus areas for development: {', '.join(weak_qualities)}"
        )
    if not analysis_parts:
        analysis_parts.append("Profile is balanced across all physical qualities")

    profile_analysis = ". ".join(analysis_parts) + "."

    # Get upcoming tests (tests due for repetition)
    upcoming_tests = []
    for result in all_results:
        try:
            test = result.test
            if test and test.default_frequency_weeks:
                next_due_date = result.test_date + timedelta(
                    weeks=test.default_frequency_weeks
                )
                if next_due_date <= date.today() + timedelta(
                    days=7
                ):  # Due within 7 days
                    upcoming_tests.append(
                        {
                            "test_id": test.id,
                            "test_name": test.name,
                            "category": test.category,
                            "last_test_date": result.test_date.isoformat(),
                            "next_due_date": next_due_date.isoformat(),
                        }
                    )
        except Exception:
            # Skip this result if there's an error
            continue

    # Build trend data for each category (for charts)
    category_trends = []
    for category in categories:
        # Get all test results for this category, ordered by date
        category_results = [
            r for r in all_results if r.test and r.test.category == category
        ]

        if not category_results:
            continue

        # Group by test (same test_id) to show trends per test
        tests_by_id = {}
        for result in category_results:
            test_id = result.test_id
            if test_id not in tests_by_id:
                tests_by_id[test_id] = []
            tests_by_id[test_id].append(result)

        # For each test in this category, create trend data
        for test_id, test_results in tests_by_id.items():
            # Sort by date
            test_results.sort(key=lambda r: r.test_date)

            # Get test info
            test = test_results[0].test
            if not test:
                continue

            # Find baseline
            baseline_result = next(
                (r for r in test_results if r.is_baseline), test_results[0]
            )
            baseline_value = baseline_result.value
            baseline_date = baseline_result.test_date

            # Build trend points
            trend_points = []
            for result in test_results:
                try:
                    progress = calculate_test_progress(db, result.id)
                    progress_pct = progress.get("progress_percentage")
                except (ValueError, Exception):
                    progress_pct = None

                trend_points.append(
                    {
                        "test_date": result.test_date,
                        "value": result.value,
                        "unit": result.unit,
                        "progress_percentage": progress_pct,
                        "test_name": test.name,
                        "test_id": test.id,
                    }
                )

            # Only add if we have at least 2 points (for trend visualization)
            if len(trend_points) >= 1:
                # Get surface from most recent test result
                latest_result = test_results[-1]  # Most recent (already sorted by date)
                latest_surface = latest_result.surface if latest_result else None

                # Check for repetitions in the latest test session
                # Group results by test_date to find repetitions
                latest_date = latest_result.test_date
                latest_session_results = [
                    r for r in test_results if r.test_date == latest_date
                ]

                latest_repetitions = None
                latest_fatigue_analysis = None

                # If there are multiple results on the same date, treat as repetitions
                if len(latest_session_results) > 1:
                    # Sort by value (for time-based tests, lower is better)
                    # For RSA and similar tests, assume lower values are better
                    sorted_reps = sorted(latest_session_results, key=lambda r: r.value)
                    best_value = sorted_reps[0].value
                    worst_value = sorted_reps[-1].value

                    # Create repetition data
                    latest_repetitions = [
                        {
                            "repetition_number": i + 1,
                            "value": r.value,
                            "unit": r.unit,
                        }
                        for i, r in enumerate(
                            sorted(
                                latest_session_results,
                                key=lambda r: r.created_at or r.test_date,
                            )
                        )
                    ]

                    # Calculate Fatigue Index: ((worst - best) / best) * 100
                    if best_value > 0:
                        fatigue_index = ((worst_value - best_value) / best_value) * 100
                        # Determine acceptable range (typically < 10% is acceptable)
                        acceptable_range = (
                            "acceptable range"
                            if fatigue_index < 10
                            else (
                                "high fatigue"
                                if fatigue_index > 15
                                else "moderate fatigue"
                            )
                        )

                        latest_fatigue_analysis = {
                            "best_value": best_value,
                            "worst_value": worst_value,
                            "fatigue_index_percentage": round(fatigue_index, 1),
                            "acceptable_range": acceptable_range,
                        }

                category_trends.append(
                    {
                        "category": category,
                        "test_name": test.name,
                        "test_id": test.id,
                        "trend_points": trend_points,
                        "baseline_value": baseline_value,
                        "baseline_date": baseline_date,
                        "test_frequency_weeks": test.default_frequency_weeks,
                        "latest_surface": latest_surface,
                        "latest_repetitions": latest_repetitions,
                        "latest_fatigue_analysis": latest_fatigue_analysis,
                    }
                )

    # Build bilateral comparison for mobility tests (Joint ROM Left vs Right)
    bilateral_comparison = []
    mobility_results = [
        r for r in all_results if r.test and r.test.category == "mobility"
    ]

    if mobility_results:
        # Group by joint and side
        # Extract joint and side from test names
        # e.g., "Hip ROM (R)" -> joint: "Hip", side: "R"
        joint_data = (
            {}
        )  # {joint: {"L": {value, date}, "R": {value, date}, "unit": unit}}

        for result in mobility_results:
            test_name = result.test.name
            # Try to extract joint and side from test name
            # Patterns: "Hip ROM (R)", "Hip ROM (L)", "Ankle ROM Left", etc.
            # Match patterns like "Joint ROM (L/R)" or "Joint ROM Left/Right"
            match = re.search(
                r"(\w+)\s*ROM\s*[\(]?([LR]|Left|Right)[\)]?", test_name, re.IGNORECASE
            )
            if match:
                joint = match.group(1).title()  # e.g., "Hip", "Ankle"
                side_str = match.group(2).upper()
                side = "L" if side_str in ["L", "LEFT"] else "R"

                if joint not in joint_data:
                    joint_data[joint] = {
                        "L": {"value": None, "date": None},
                        "R": {"value": None, "date": None},
                        "unit": result.unit,
                    }

                # Use the latest value for each side
                current_side_data = joint_data[joint][side]
                if (
                    current_side_data["value"] is None
                    or result.test_date > current_side_data["date"]
                ):
                    joint_data[joint][side] = {
                        "value": result.value,
                        "date": result.test_date,
                    }
                    joint_data[joint]["unit"] = result.unit

        # Convert to bilateral comparison points
        for joint, data in joint_data.items():
            if data["L"]["value"] is not None or data["R"]["value"] is not None:
                bilateral_comparison.append(
                    {
                        "joint": joint,
                        "left_value": data["L"]["value"],
                        "right_value": data["R"]["value"],
                        "unit": data["unit"],
                    }
                )

    return {
        "client_id": client_id,
        "physical_quality_profile": profile,
        "latest_tests_by_category": latest_by_category,
        "category_trends": category_trends,
        "upcoming_tests": upcoming_tests,
        "profile_analysis": profile_analysis,
        "bilateral_comparison": bilateral_comparison if bilateral_comparison else None,
    }


def get_training_plan_alignment(
    db: Session,
    plan_id: int,
    mesocycle_id: Optional[int] = None,
    microcycle_id: Optional[int] = None,
) -> Dict:
    """
    Get alignment data for a training plan.

    Shows parent cycle values when planning at child levels:
    - When planning monthly (mesocycle), shows yearly (macrocycle) values
    - When planning weekly (microcycle), shows monthly (mesocycle) values

    Also provides all cycles for graph visualization.

    Args:
        db: Database session
        plan_id: Training plan ID
        mesocycle_id: Optional - if provided, shows parent macrocycle values
        microcycle_id: Optional - if provided, shows parent mesocycle values

    Returns:
        Dict matching TrainingPlanAlignmentOut schema
    """
    # Get the training plan
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    # Get all macrocycles for the plan
    macrocycles = (
        db.query(models.Macrocycle)
        .filter(
            models.Macrocycle.training_plan_id == plan_id,
            models.Macrocycle.is_active.is_(True),
        )
        .order_by(models.Macrocycle.start_date)
        .all()
    )

    # Build alignment graph with all cycles
    alignment_graph = []
    yearly_values = None
    monthly_values = None

    # Process macrocycles (yearly)
    for macro in macrocycles:
        alignment_graph.append(
            {
                "cycle_id": macro.id,
                "cycle_type": "macrocycle",
                "cycle_name": macro.name,
                "date": macro.start_date,
                "physical_quality": macro.physical_quality,
                "volume": macro.volume,
                "intensity": macro.intensity,
            }
        )

        # If we're planning a mesocycle, get parent macrocycle values
        if mesocycle_id:
            mesocycle = (
                db.query(models.Mesocycle)
                .filter(models.Mesocycle.id == mesocycle_id)
                .first()
            )
            if mesocycle and mesocycle.macrocycle_id == macro.id:
                yearly_values = {
                    "physical_quality": macro.physical_quality,
                    "volume": macro.volume,
                    "intensity": macro.intensity,
                    "cycle_name": macro.name,
                    "start_date": macro.start_date,
                    "end_date": macro.end_date,
                }

        # Process mesocycles (monthly)
        for meso in macro.mesocycles:
            if meso.is_active:
                alignment_graph.append(
                    {
                        "cycle_id": meso.id,
                        "cycle_type": "mesocycle",
                        "cycle_name": meso.name,
                        "date": meso.start_date,
                        "physical_quality": meso.physical_quality,
                        "volume": meso.volume,
                        "intensity": meso.intensity,
                    }
                )

                # If we're planning a microcycle, get parent mesocycle values
                if microcycle_id:
                    microcycle = (
                        db.query(models.Microcycle)
                        .filter(models.Microcycle.id == microcycle_id)
                        .first()
                    )
                    if microcycle and microcycle.mesocycle_id == meso.id:
                        monthly_values = {
                            "physical_quality": meso.physical_quality,
                            "volume": meso.volume,
                            "intensity": meso.intensity,
                            "cycle_name": meso.name,
                            "start_date": meso.start_date,
                            "end_date": meso.end_date,
                        }

                # Process microcycles (weekly)
                for micro in meso.microcycles:
                    if micro.is_active:
                        alignment_graph.append(
                            {
                                "cycle_id": micro.id,
                                "cycle_type": "microcycle",
                                "cycle_name": micro.name,
                                "date": micro.start_date,
                                "physical_quality": micro.physical_quality,
                                "volume": micro.volume,
                                "intensity": micro.intensity,
                            }
                        )

    # Sort alignment graph by date
    alignment_graph.sort(key=lambda x: x["date"])

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "yearly_values": yearly_values,
        "monthly_values": monthly_values,
        "alignment_graph": alignment_graph,
    }


# Scheduling CRUD Functions
def create_trainer_availability(
    db: Session, availability_data: schemas.TrainerAvailabilityCreate
):
    """Create a new trainer availability slot"""
    db_availability = models.TrainerAvailability(**availability_data.model_dump())
    db.add(db_availability)
    db.commit()
    db.refresh(db_availability)
    return db_availability


def get_trainer_availability(
    db: Session, trainer_id: int, skip: int = 0, limit: int = 100
):
    """Get trainer availability slots"""
    return (
        db.query(models.TrainerAvailability)
        .filter(
            models.TrainerAvailability.trainer_id == trainer_id,
            models.TrainerAvailability.is_active.is_(True),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_trainer_availability(
    db: Session,
    availability_id: int,
    availability_data: schemas.TrainerAvailabilityUpdate,
):
    """Update trainer availability slot"""
    db_availability = (
        db.query(models.TrainerAvailability)
        .filter(models.TrainerAvailability.id == availability_id)
        .first()
    )
    if not db_availability:
        return None

    update_data = availability_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_availability, field, value)

    db.commit()
    db.refresh(db_availability)
    return db_availability


def delete_trainer_availability(db: Session, availability_id: int):
    """Delete (deactivate) trainer availability slot"""
    db_availability = (
        db.query(models.TrainerAvailability)
        .filter(models.TrainerAvailability.id == availability_id)
        .first()
    )
    if not db_availability:
        return False

    db_availability.is_active = False
    db.commit()
    return True


def check_scheduling_conflict(
    db: Session,
    trainer_id: int,
    scheduled_date: date,
    start_time: time,
    end_time: time,
    exclude_session_id: Optional[int] = None,
) -> Dict:
    """Check for scheduling conflicts"""
    from datetime import datetime

    # Convert date and time to datetime for comparison
    start_datetime = datetime.combine(scheduled_date, start_time)
    end_datetime = datetime.combine(scheduled_date, end_time)

    # Query for conflicting sessions
    query = db.query(models.ScheduledSession).filter(
        models.ScheduledSession.trainer_id == trainer_id,
        models.ScheduledSession.scheduled_date == scheduled_date,
        models.ScheduledSession.is_active.is_(True),
        models.ScheduledSession.status.in_(["scheduled", "confirmed"]),
    )

    if exclude_session_id:
        query = query.filter(models.ScheduledSession.id != exclude_session_id)

    conflicting_sessions = []
    for session in query.all():
        session_start = datetime.combine(session.scheduled_date, session.start_time)
        session_end = datetime.combine(session.scheduled_date, session.end_time)

        # Check for overlap
        if not (end_datetime <= session_start or start_datetime >= session_end):
            conflicting_sessions.append(session)

    return {
        "has_conflict": len(conflicting_sessions) > 0,
        "conflicts": conflicting_sessions,  # Pydantic will serialize these
        "available": len(conflicting_sessions) == 0,
    }


def get_available_slots(db: Session, trainer_id: int, target_date: date) -> List[Dict]:
    """Get available time slots for a trainer on a specific date"""
    from datetime import datetime, timedelta

    # Get day of week (0=Monday, 6=Sunday)
    day_of_week = target_date.weekday()

    # Get recurring availability for this day of week
    recurring_availability = (
        db.query(models.TrainerAvailability)
        .filter(
            models.TrainerAvailability.trainer_id == trainer_id,
            models.TrainerAvailability.day_of_week == day_of_week,
            models.TrainerAvailability.is_recurring.is_(True),
            models.TrainerAvailability.is_active.is_(True),
        )
        .all()
    )

    # Get one-time availability for this specific date
    one_time_availability = (
        db.query(models.TrainerAvailability)
        .filter(
            models.TrainerAvailability.trainer_id == trainer_id,
            models.TrainerAvailability.specific_date == target_date,
            models.TrainerAvailability.is_recurring.is_(False),
            models.TrainerAvailability.is_active.is_(True),
        )
        .all()
    )

    # Combine all availability
    all_availability = list(recurring_availability) + list(one_time_availability)

    # Get existing scheduled sessions for this date
    scheduled_sessions = (
        db.query(models.ScheduledSession)
        .filter(
            models.ScheduledSession.trainer_id == trainer_id,
            models.ScheduledSession.scheduled_date == target_date,
            models.ScheduledSession.is_active.is_(True),
            models.ScheduledSession.status.in_(["scheduled", "confirmed"]),
        )
        .order_by(models.ScheduledSession.start_time)
        .all()
    )

    # Calculate available slots (simplified - 1 hour slots)
    available_slots = []
    slot_duration = timedelta(hours=1)

    for avail in all_availability:
        current_time = datetime.combine(target_date, avail.start_time)
        end_time = datetime.combine(target_date, avail.end_time)

        while current_time + slot_duration <= end_time:
            # Check if this slot conflicts with any scheduled session
            slot_start = current_time.time()
            slot_end = (current_time + slot_duration).time()

            has_conflict = False
            for session in scheduled_sessions:
                if not (
                    slot_end <= session.start_time or slot_start >= session.end_time
                ):
                    has_conflict = True
                    break

            if not has_conflict:
                available_slots.append(
                    {
                        "start_time": slot_start,
                        "end_time": slot_end,
                        "duration_minutes": 60,
                    }
                )

            current_time += slot_duration

    return available_slots


def create_scheduled_session(db: Session, session_data: schemas.ScheduledSessionCreate):
    """Create a new scheduled session"""
    # Check for conflicts first
    conflict_check = check_scheduling_conflict(
        db=db,
        trainer_id=session_data.trainer_id,
        scheduled_date=session_data.scheduled_date,
        start_time=session_data.start_time,
        end_time=session_data.end_time,
    )

    if conflict_check["has_conflict"]:
        conflict_count = len(conflict_check["conflicts"])
        raise ValueError(
            f"Time slot conflicts with existing session(s). "
            f"Conflicts: {conflict_count}"
        )

    db_session = models.ScheduledSession(**session_data.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


def get_scheduled_sessions(
    db: Session,
    trainer_id: Optional[int] = None,
    client_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    """Get scheduled sessions with optional filters"""
    query = db.query(models.ScheduledSession).filter(
        models.ScheduledSession.is_active.is_(True)
    )

    if trainer_id:
        query = query.filter(models.ScheduledSession.trainer_id == trainer_id)
    if client_id:
        query = query.filter(models.ScheduledSession.client_id == client_id)
    if start_date:
        query = query.filter(models.ScheduledSession.scheduled_date >= start_date)
    if end_date:
        query = query.filter(models.ScheduledSession.scheduled_date <= end_date)

    return (
        query.order_by(
            models.ScheduledSession.scheduled_date, models.ScheduledSession.start_time
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def update_scheduled_session(
    db: Session, session_id: int, session_data: schemas.ScheduledSessionUpdate
):
    """Update a scheduled session"""
    db_session = (
        db.query(models.ScheduledSession)
        .filter(models.ScheduledSession.id == session_id)
        .first()
    )
    if not db_session:
        return None

    # If time/date is being changed, check for conflicts
    update_data = session_data.model_dump(exclude_unset=True)
    if (
        "scheduled_date" in update_data
        or "start_time" in update_data
        or "end_time" in update_data
    ):
        scheduled_date = update_data.get("scheduled_date", db_session.scheduled_date)
        start_time = update_data.get("start_time", db_session.start_time)
        end_time = update_data.get("end_time", db_session.end_time)

        conflict_check = check_scheduling_conflict(
            db=db,
            trainer_id=db_session.trainer_id,
            scheduled_date=scheduled_date,
            start_time=start_time,
            end_time=end_time,
            exclude_session_id=session_id,
        )

        if conflict_check["has_conflict"]:
            conflict_count = len(conflict_check["conflicts"])
            raise ValueError(
                f"Time slot conflicts with existing session(s). "
                f"Conflicts: {conflict_count}"
            )

    for field, value in update_data.items():
        setattr(db_session, field, value)

    db.commit()
    db.refresh(db_session)
    return db_session


def delete_scheduled_session(db: Session, session_id: int):
    """Cancel (deactivate) a scheduled session"""
    db_session = (
        db.query(models.ScheduledSession)
        .filter(models.ScheduledSession.id == session_id)
        .first()
    )
    if not db_session:
        return False

    # Capture details before deactivation
    client_id = db_session.client_id
    trainer_id = db_session.trainer_id
    scheduled_date = db_session.scheduled_date
    start_time = db_session.start_time

    db_session.is_active = False
    db_session.status = "cancelled"

    # Create an attendance alert for the trainer when a session is cancelled
    try:
        client = db_session.client
        client_name = (
            f"{client.nombre} {client.apellidos}".strip()
            if client
            else f"Client {client_id}"
        )
        date_str = (
            scheduled_date.isoformat() if scheduled_date is not None else "unknown date"
        )
        time_str = (
            start_time.strftime("%H:%M") if start_time is not None else "unknown time"
        )
        title = f"Session cancelled for {client_name}"
        message = (
            f"The session scheduled on {date_str} at {time_str} was cancelled. "
            "Review attendance and reschedule if needed."
        )

        alert = models.FatigueAlert(
            client_id=client_id,
            trainer_id=trainer_id,
            fatigue_analysis_id=None,
            alert_type="attendance",
            severity="medium",
            title=title,
            message=message,
            recommendations=None,
            is_read=False,
            is_resolved=False,
        )
        db.add(alert)
    except Exception:
        # If alert creation fails, still complete the cancellation
        pass

    db.commit()
    return True


def _maybe_create_plan_deviation_alert(
    db: Session, session: models.TrainingSession
) -> None:
    """
    Create a 'plan deviation' alert when a completed session's actual
    intensity/volume differ significantly from the planned values.

    Maps directly to Adrián's 'Plan Deviation Alerts':
    - Example: planned intensity 8/10 but client logs 10/10 or 5/10 (out of range).
    """
    if session.status != "completed":
        return

    print(
        f"DEBUG: Checking plan deviation for session {session.id}, "
        f"planned_intensity={session.planned_intensity}, "
        f"actual_intensity={session.actual_intensity}, "
        f"planned_volume={session.planned_volume}, "
        f"actual_volume={session.actual_volume}"
    )

    # Require at least intensity information to evaluate deviation
    planned_intensity = session.planned_intensity
    actual_intensity = session.actual_intensity
    planned_volume = session.planned_volume
    actual_volume = session.actual_volume

    intensity_diff = None
    volume_diff = None

    if planned_intensity is not None and actual_intensity is not None:
        intensity_diff = abs(actual_intensity - planned_intensity)

    if planned_volume is not None and actual_volume is not None:
        volume_diff = abs(actual_volume - planned_volume)

    # Thresholds are in percentage points (0-100 scale)
    intensity_threshold = 20.0
    volume_threshold = 20.0

    over_threshold = False
    reasons = []

    if intensity_diff is not None and intensity_diff >= intensity_threshold:
        over_threshold = True
        reasons.append(
            "intensity deviated by "
            f"{intensity_diff:.1f} points (planned {planned_intensity or 0:.1f}, "
            f"actual {actual_intensity or 0:.1f})"
        )

    if volume_diff is not None and volume_diff >= volume_threshold:
        over_threshold = True
        reasons.append(
            "volume deviated by "
            f"{volume_diff:.1f} points (planned {planned_volume or 0:.1f}, "
            f"actual {actual_volume or 0:.1f})"
        )

    if not over_threshold:
        print(
            f"DEBUG: No plan deviation alert - intensity_diff={intensity_diff}, "
            f"volume_diff={volume_diff}, thresholds not met"
        )
        return

    # Severity: high if very large deviation, otherwise medium
    max_diff = max(
        d for d in [intensity_diff or 0.0, volume_diff or 0.0] if d is not None
    )
    severity = "high" if max_diff >= 40.0 else "medium"

    print(
        f"DEBUG: Creating plan deviation alert for session {session.id}, "
        f"intensity_diff={intensity_diff}, volume_diff={volume_diff}, "
        f"severity={severity}"
    )

    client = session.client
    client_name = (
        f"{client.nombre} {client.apellidos}".strip()
        if client
        else f"Client {session.client_id}"
    )
    date_str = (
        session.session_date.isoformat()
        if session.session_date is not None
        else "unspecified date"
    )

    title = f"Plan deviation for {client_name}"
    message = (
        f"Session on {date_str} has significant deviation from the planned load: "
        + "; ".join(reasons)
        + ". Review this session and adjust future planning if necessary."
    )

    alert = models.FatigueAlert(
        client_id=session.client_id,
        trainer_id=session.trainer_id,
        fatigue_analysis_id=None,
        alert_type="plan_deviation",
        severity=severity,
        title=title,
        message=message,
        recommendations=None,
        is_read=False,
        is_resolved=False,
    )
    db.add(alert)
    try:
        db.commit()
        print(
            f"SUCCESS: Created plan deviation alert {alert.id} for "
            f"session {session.id}, trainer_id={session.trainer_id}"
        )
    except Exception as e:
        db.rollback()
        print(f"ERROR: Failed to commit plan deviation alert: {e}")
        raise


# Report Generation Functions
def generate_client_progress_report(
    db: Session,
    client_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict:
    """Generate client progress report"""
    # Get client
    client = get_client_profile(db, client_id)
    if not client:
        raise ValueError(f"Client {client_id} not found")

    # Get training sessions in date range
    sessions_query = db.query(models.TrainingSession).filter(
        models.TrainingSession.client_id == client_id,
        models.TrainingSession.is_active.is_(True),
    )

    if start_date:
        sessions_query = sessions_query.filter(
            models.TrainingSession.session_date >= start_date
        )
    if end_date:
        sessions_query = sessions_query.filter(
            models.TrainingSession.session_date <= end_date
        )

    sessions = sessions_query.all()

    # Calculate statistics
    total_sessions = len(sessions)
    completed_sessions = len([s for s in sessions if s.status == "completed"])
    adherence = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0

    # Get physical test results
    test_results = (
        db.query(models.PhysicalTestResult)
        .filter(
            models.PhysicalTestResult.client_id == client_id,
            models.PhysicalTestResult.is_active.is_(True),
        )
        .order_by(models.PhysicalTestResult.test_date.desc())
        .limit(10)
        .all()
    )

    return {
        "client_id": client_id,
        "client_name": f"{client.nombre} {client.apellidos}",
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "statistics": {
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "adherence_percentage": round(adherence, 2),
        },
        "recent_tests": [
            {
                "test_date": tr.test_date.isoformat(),
                "test_name": tr.test.name if tr.test else "Unknown",
                "value": tr.value,
                "unit": tr.unit,
            }
            for tr in test_results
        ],
    }


def generate_training_summary_report(
    db: Session,
    trainer_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> Dict:
    """Generate training summary report for trainer"""
    # Get all clients for this trainer
    clients = (
        db.query(models.ClientProfile)
        .join(models.TrainerClient)
        .filter(models.TrainerClient.trainer_id == trainer_id)
        .all()
    )

    summary = {
        "trainer_id": trainer_id,
        "period": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
        },
        "total_clients": len(clients),
        "client_summaries": [],
    }

    for client in clients:
        sessions_query = db.query(models.TrainingSession).filter(
            models.TrainingSession.client_id == client.id,
            models.TrainingSession.trainer_id == trainer_id,
            models.TrainingSession.is_active.is_(True),
        )

        if start_date:
            sessions_query = sessions_query.filter(
                models.TrainingSession.session_date >= start_date
            )
        if end_date:
            sessions_query = sessions_query.filter(
                models.TrainingSession.session_date <= end_date
            )

        sessions = sessions_query.all()
        completed = len([s for s in sessions if s.status == "completed"])

        summary["client_summaries"].append(
            {
                "client_id": client.id,
                "client_name": f"{client.nombre} {client.apellidos}",
                "total_sessions": len(sessions),
                "completed_sessions": completed,
            }
        )

    return summary


def generate_report(db: Session, report_request: schemas.ReportRequest) -> Dict:
    """Generate a report based on request"""
    report_id = f"{report_request.report_type}_{datetime.now(timezone.utc).timestamp()}"

    if report_request.report_type == schemas.ReportType.client_progress:
        if not report_request.client_id:
            raise ValueError("client_id required for client_progress report")
        data = generate_client_progress_report(
            db=db,
            client_id=report_request.client_id,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
        )
    elif report_request.report_type == schemas.ReportType.training_summary:
        if not report_request.trainer_id:
            raise ValueError("trainer_id required for training_summary report")
        data = generate_training_summary_report(
            db=db,
            trainer_id=report_request.trainer_id,
            start_date=report_request.start_date,
            end_date=report_request.end_date,
        )
    elif report_request.report_type == schemas.ReportType.daily_coherence:
        if not report_request.client_id:
            raise ValueError("client_id required for daily_coherence report")
        if not report_request.start_date or not report_request.end_date:
            raise ValueError(
                "start_date and end_date required for daily_coherence report"
            )
        # Generate daily coherence analytics
        data = compute_daily_coherence(
            db=db,
            client_id=report_request.client_id,
            period_start=report_request.start_date,
            period_end=report_request.end_date,
            period_type="week",  # Default to week, can be made configurable
        )
    else:
        # Placeholder for other report types
        data = {
            "message": f"Report type {report_request.report_type} not yet implemented",
            "report_type": report_request.report_type,
        }

    # For PDF format, return data with note that PDF generation requires frontend
    # or a PDF library (reportlab, weasyprint, etc.)
    download_url = None
    if report_request.format == "pdf":
        # TODO: Implement PDF generation using reportlab or weasyprint
        # For now, return JSON data with note
        data["_note"] = (
            "PDF generation not yet implemented. "
            "Data is returned in JSON format. "
            "Frontend can generate PDF from this data."
        )

    return {
        "report_id": report_id,
        "report_type": report_request.report_type.value,
        "generated_at": datetime.now(timezone.utc),
        "download_url": download_url,
        "format": report_request.format,
        "data": data,
    }


# Planning Endpoints CRUD Functions
def get_planning_yearly(
    db: Session,
    plan_id: int,
    year: Optional[int] = None,
) -> Dict:
    """Get yearly planning view for a training plan"""
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    year_value = year or datetime.utcnow().year
    year_start = date(year_value, 1, 1)
    year_end = date(year_value, 12, 31)

    # Get all macrocycles for this plan in the year
    macrocycles = get_macrocycles_by_plan(db, plan_id)
    year_macros = [
        m
        for m in macrocycles
        if m.is_active and m.start_date <= year_end and m.end_date >= year_start
    ]

    # Build cycles list
    cycles = []
    cycle_ids = []
    for macro in year_macros:
        cycles.append(
            {
                "cycle_id": macro.id,
                "cycle_type": "macrocycle",
                "name": macro.name,
                "start_date": macro.start_date,
                "end_date": macro.end_date,
                "physical_quality": macro.physical_quality or macro.focus,
                "volume": macro.volume,
                "intensity": macro.intensity,
                "has_values": macro.volume is not None and macro.intensity is not None,
                "inherited": False,  # Macrocycles are top-level, no inheritance
            }
        )
        cycle_ids.append(macro.id)

    # Calculate distribution
    distribution_dict = defaultdict(float)
    total_days = 0
    for macro in year_macros:
        overlap = _count_overlap_days(
            macro.start_date, macro.end_date, year_start, year_end
        )
        if overlap > 0:
            quality = macro.physical_quality or macro.focus
            distribution_dict[quality] += overlap
            total_days += overlap

    distribution = []
    for quality, days in sorted(
        distribution_dict.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round((days / total_days * 100), 2) if total_days > 0 else 0.0
        distribution.append(
            {
                "name": quality,
                "percentage": pct,
                "cycle_ids": [
                    m.id
                    for m in year_macros
                    if (m.physical_quality or m.focus) == quality
                ],
            }
        )

    # Calculate training load
    load = _aggregate_load(year_macros, year_start, year_end, db=db)

    # Monthly progression
    monthly_progression = []
    for month in range(1, 13):
        month_start = date(year_value, month, 1)
        month_end = date(year_value, month, calendar.monthrange(year_value, month)[1])
        month_macros = [
            m
            for m in year_macros
            if m.start_date <= month_end and m.end_date >= month_start
        ]
        month_dist = _aggregate_distribution(month_macros, month_start, month_end)
        month_load = _aggregate_load(month_macros, month_start, month_end, db=db)
        monthly_progression.append(
            {
                "month": month,
                "distribution": month_dist,
                "training_load": month_load,
            }
        )

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "year": year_value,
        "distribution": distribution,
        "training_load": {
            "volume_level": load["volume_level"],
            "intensity_level": load["intensity_level"],
            "cycle_ids": cycle_ids,
        },
        "cycles": cycles,
        "monthly_progression": monthly_progression,
    }


def get_planning_monthly(
    db: Session,
    plan_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
) -> Dict:
    """Get monthly planning view for a training plan"""
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    today = datetime.utcnow().date()
    year_value = year or today.year
    month_value = month or today.month
    month_start = date(year_value, month_value, 1)
    month_end = date(
        year_value, month_value, calendar.monthrange(year_value, month_value)[1]
    )

    # Get macrocycles for this month
    macrocycles = get_macrocycles_by_plan(db, plan_id)
    month_macros = [
        m
        for m in macrocycles
        if m.is_active and m.start_date <= month_end and m.end_date >= month_start
    ]

    # Get all mesocycles for these macros
    cycles = []
    cycle_ids = []
    for macro in month_macros:
        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)
        for meso in mesocycles:
            if (
                meso.is_active
                and meso.start_date <= month_end
                and meso.end_date >= month_start
            ):
                # Check if values are inherited
                has_values = meso.volume is not None and meso.intensity is not None
                inherited = not has_values and (
                    macro.volume is not None or macro.intensity is not None
                )

                cycles.append(
                    {
                        "cycle_id": meso.id,
                        "cycle_type": "mesocycle",
                        "name": meso.name,
                        "start_date": meso.start_date,
                        "end_date": meso.end_date,
                        "physical_quality": meso.physical_quality or meso.primary_focus,
                        "volume": meso.volume or macro.volume,
                        "intensity": meso.intensity or macro.intensity,
                        "has_values": has_values,
                        "inherited": inherited,
                    }
                )
                cycle_ids.append(meso.id)

    # Calculate distribution from mesocycles
    distribution_dict = defaultdict(float)
    total_days = 0
    for macro in month_macros:
        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)
        for meso in mesocycles:
            if (
                meso.is_active
                and meso.start_date <= month_end
                and meso.end_date >= month_start
            ):
                overlap = _count_overlap_days(
                    meso.start_date, meso.end_date, month_start, month_end
                )
                if overlap > 0:
                    quality = (
                        meso.physical_quality
                        or meso.primary_focus
                        or macro.physical_quality
                        or macro.focus
                    )
                    distribution_dict[quality] += overlap
                    total_days += overlap

    distribution = []
    for quality, days in sorted(
        distribution_dict.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round((days / total_days * 100), 2) if total_days > 0 else 0.0
        distribution.append(
            {
                "name": quality,
                "percentage": pct,
                "cycle_ids": [
                    c["cycle_id"] for c in cycles if c["physical_quality"] == quality
                ],
            }
        )

    # Calculate training load
    load = _aggregate_load(month_macros, month_start, month_end, db=db)

    # Weekly progression
    weekly_progression = []
    current_date = month_start
    week_num = 1
    while current_date <= month_end and week_num <= 5:
        week_end = min(current_date + timedelta(days=6), month_end)
        week_mesos = [
            c
            for c in cycles
            if c["start_date"] <= week_end and c["end_date"] >= current_date
        ]
        weekly_progression.append(
            {
                "week": week_num,
                "start_date": current_date,
                "end_date": week_end,
                "cycles_count": len(week_mesos),
            }
        )
        current_date = week_end + timedelta(days=1)
        week_num += 1

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "year": year_value,
        "month": month_value,
        "distribution": distribution,
        "training_load": {
            "volume_level": load["volume_level"],
            "intensity_level": load["intensity_level"],
            "cycle_ids": cycle_ids,
        },
        "cycles": cycles,
        "weekly_progression": weekly_progression,
    }


def get_planning_weekly(
    db: Session,
    plan_id: int,
    week_start: Optional[date] = None,
) -> Dict:
    """Get weekly planning view for a training plan"""
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    today = datetime.utcnow().date()
    week_start_date = week_start or (today - timedelta(days=today.weekday()))
    week_end_date = week_start_date + timedelta(days=6)

    # Get macrocycles and mesocycles for this week
    macrocycles = get_macrocycles_by_plan(db, plan_id)
    week_macros = [
        m
        for m in macrocycles
        if m.is_active
        and m.start_date <= week_end_date
        and m.end_date >= week_start_date
    ]

    # Get all microcycles for this week
    cycles = []
    cycle_ids = []
    for macro in week_macros:
        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)
        for meso in mesocycles:
            if (
                meso.is_active
                and meso.start_date <= week_end_date
                and meso.end_date >= week_start_date
            ):
                microcycles = get_microcycles_by_mesocycle(db, meso.id)
                for micro in microcycles:
                    if (
                        micro.is_active
                        and micro.start_date <= week_end_date
                        and micro.end_date >= week_start_date
                    ):
                        # Check inheritance
                        has_values = (
                            micro.volume is not None and micro.intensity is not None
                        )
                        inherited = not has_values and (
                            (meso.volume is not None and meso.intensity is not None)
                            or (
                                macro.volume is not None and macro.intensity is not None
                            )
                        )

                        cycles.append(
                            {
                                "cycle_id": micro.id,
                                "cycle_type": "microcycle",
                                "name": micro.name,
                                "start_date": micro.start_date,
                                "end_date": micro.end_date,
                                "physical_quality": micro.physical_quality
                                or meso.physical_quality
                                or meso.primary_focus,
                                "volume": micro.volume or meso.volume or macro.volume,
                                "intensity": micro.intensity
                                or meso.intensity
                                or macro.intensity,
                                "has_values": has_values,
                                "inherited": inherited,
                            }
                        )
                        cycle_ids.append(micro.id)

    # Calculate distribution from microcycles
    distribution_dict = defaultdict(float)
    total_days = 0
    for macro in week_macros:
        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)
        for meso in mesocycles:
            if (
                meso.is_active
                and meso.start_date <= week_end_date
                and meso.end_date >= week_start_date
            ):
                microcycles = get_microcycles_by_mesocycle(db, meso.id)
                for micro in microcycles:
                    if (
                        micro.is_active
                        and micro.start_date <= week_end_date
                        and micro.end_date >= week_start_date
                    ):
                        overlap = _count_overlap_days(
                            micro.start_date,
                            micro.end_date,
                            week_start_date,
                            week_end_date,
                        )
                        if overlap > 0:
                            quality = (
                                micro.physical_quality
                                or meso.physical_quality
                                or meso.primary_focus
                                or macro.physical_quality
                                or macro.focus
                            )
                            distribution_dict[quality] += overlap
                            total_days += overlap

    distribution = []
    for quality, days in sorted(
        distribution_dict.items(), key=lambda x: x[1], reverse=True
    ):
        pct = round((days / total_days * 100), 2) if total_days > 0 else 0.0
        distribution.append(
            {
                "name": quality,
                "percentage": pct,
                "cycle_ids": [
                    c["cycle_id"] for c in cycles if c["physical_quality"] == quality
                ],
            }
        )

    # Calculate training load
    load = _aggregate_load(week_macros, week_start_date, week_end_date, db=db)

    # Daily progression
    daily_progression = []
    current_date = week_start_date
    for day_idx in range(7):
        day_cycles = [
            c for c in cycles if c["start_date"] <= current_date <= c["end_date"]
        ]
        daily_progression.append(
            {
                "day": current_date.strftime("%A"),
                "date": current_date,
                "cycles_count": len(day_cycles),
            }
        )
        current_date += timedelta(days=1)

    return {
        "plan_id": plan_id,
        "plan_name": plan.name,
        "week_start": week_start_date,
        "week_end": week_end_date,
        "distribution": distribution,
        "training_load": {
            "volume_level": load["volume_level"],
            "intensity_level": load["intensity_level"],
            "cycle_ids": cycle_ids,
        },
        "cycles": cycles,
        "daily_progression": daily_progression,
    }


def update_planning_distribution(
    db: Session,
    plan_id: int,
    update_request: schemas.DistributionUpdateRequest,
) -> Dict:
    """Update physical qualities distribution for multiple cycles"""
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    # Validate cycle IDs belong to this plan
    all_cycles = []
    for cycle_id in update_request.cycle_ids:
        # Try macrocycle
        macro = get_macrocycle(db, cycle_id)
        if macro and macro.training_plan_id == plan_id:
            all_cycles.append(("macrocycle", macro))
            continue

        # Try mesocycle
        meso = get_mesocycle(db, cycle_id)
        if meso:
            macro = get_macrocycle(db, meso.macrocycle_id)
            if macro and macro.training_plan_id == plan_id:
                all_cycles.append(("mesocycle", meso))
                continue

        # Try microcycle
        micro = get_microcycle(db, cycle_id)
        if micro:
            meso = get_mesocycle(db, micro.mesocycle_id)
            if meso:
                macro = get_macrocycle(db, meso.macrocycle_id)
                if macro and macro.training_plan_id == plan_id:
                    all_cycles.append(("microcycle", micro))
                    continue

        raise ValueError(
            f"Cycle {cycle_id} not found or doesn't belong to plan {plan_id}"
        )

    # Calculate total days per quality
    quality_days = defaultdict(float)
    total_days = 0
    for cycle_type, cycle in all_cycles:
        days = (cycle.end_date - cycle.start_date).days + 1
        quality_days[cycle.physical_quality or cycle.focus] += days
        total_days += days

    # Distribute percentages across cycles proportionally
    updated_count = 0
    for dist_item in update_request.distribution:
        # Find cycles with this quality or assign to cycles
        cycles_for_quality = [
            (t, c)
            for t, c in all_cycles
            if (
                c.physical_quality
                or getattr(c, "focus", None)
                or getattr(c, "primary_focus", None)
            )
            == dist_item.name
        ]

        if not cycles_for_quality:
            # Assign to first cycle if no match
            if all_cycles:
                cycles_for_quality = [all_cycles[0]]

        # Update cycles
        for cycle_type, cycle in cycles_for_quality:
            if cycle_type == "macrocycle":
                cycle.physical_quality = dist_item.name
                db.commit()
                updated_count += 1
            elif cycle_type == "mesocycle":
                cycle.physical_quality = dist_item.name
                db.commit()
                updated_count += 1
            elif cycle_type == "microcycle":
                cycle.physical_quality = dist_item.name
                db.commit()
                updated_count += 1

            # Cascade to children if requested
            if update_request.cascade:
                if cycle_type == "macrocycle":
                    mesocycles = get_mesocycles_by_macrocycle(db, cycle.id)
                    for meso in mesocycles:
                        if meso.physical_quality is None:
                            meso.physical_quality = dist_item.name
                            db.commit()
                            # Cascade to microcycles
                            microcycles = get_microcycles_by_mesocycle(db, meso.id)
                            for micro in microcycles:
                                if micro.physical_quality is None:
                                    micro.physical_quality = dist_item.name
                                    db.commit()
                elif cycle_type == "mesocycle":
                    microcycles = get_microcycles_by_mesocycle(db, cycle.id)
                    for micro in microcycles:
                        if micro.physical_quality is None:
                            micro.physical_quality = dist_item.name
                            db.commit()

    return {
        "plan_id": plan_id,
        "updated_cycles": updated_count,
        "distribution": update_request.distribution,
        "cascade_applied": update_request.cascade,
    }


def update_planning_load(
    db: Session,
    plan_id: int,
    update_request: schemas.LoadUpdateRequest,
) -> Dict:
    """Update volume/intensity for multiple cycles"""
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    # Validate cycle IDs belong to this plan
    all_cycles = []
    for cycle_id in update_request.cycle_ids:
        # Try macrocycle
        macro = get_macrocycle(db, cycle_id)
        if macro and macro.training_plan_id == plan_id:
            all_cycles.append(("macrocycle", macro))
            continue

        # Try mesocycle
        meso = get_mesocycle(db, cycle_id)
        if meso:
            macro = get_macrocycle(db, meso.macrocycle_id)
            if macro and macro.training_plan_id == plan_id:
                all_cycles.append(("mesocycle", meso))
                continue

        # Try microcycle
        micro = get_microcycle(db, cycle_id)
        if micro:
            meso = get_mesocycle(db, micro.mesocycle_id)
            if meso:
                macro = get_macrocycle(db, meso.macrocycle_id)
                if macro and macro.training_plan_id == plan_id:
                    all_cycles.append(("microcycle", micro))
                    continue

        raise ValueError(
            f"Cycle {cycle_id} not found or doesn't belong to plan {plan_id}"
        )

    # Filter by physical quality if specified
    if update_request.physical_quality:
        all_cycles = [
            (t, c)
            for t, c in all_cycles
            if (
                c.physical_quality
                or getattr(c, "focus", None)
                or getattr(c, "primary_focus", None)
            )
            == update_request.physical_quality
        ]

    # Update cycles
    updated_count = 0
    for cycle_type, cycle in all_cycles:
        if update_request.volume is not None:
            cycle.volume = update_request.volume
        if update_request.intensity is not None:
            cycle.intensity = update_request.intensity
        db.commit()
        updated_count += 1

        # Cascade to children if requested
        if update_request.cascade:
            if cycle_type == "macrocycle":
                mesocycles = get_mesocycles_by_macrocycle(db, cycle.id)
                for meso in mesocycles:
                    if update_request.volume is not None and meso.volume is None:
                        meso.volume = update_request.volume
                    if update_request.intensity is not None and meso.intensity is None:
                        meso.intensity = update_request.intensity
                    db.commit()
                    # Cascade to microcycles
                    microcycles = get_microcycles_by_mesocycle(db, meso.id)
                    for micro in microcycles:
                        if update_request.volume is not None and micro.volume is None:
                            micro.volume = update_request.volume
                        if (
                            update_request.intensity is not None
                            and micro.intensity is None
                        ):
                            micro.intensity = update_request.intensity
                        db.commit()
            elif cycle_type == "mesocycle":
                microcycles = get_microcycles_by_mesocycle(db, cycle.id)
                for micro in microcycles:
                    if update_request.volume is not None and micro.volume is None:
                        micro.volume = update_request.volume
                    if update_request.intensity is not None and micro.intensity is None:
                        micro.intensity = update_request.intensity
                    db.commit()

    return {
        "plan_id": plan_id,
        "updated_cycles": updated_count,
        "volume": update_request.volume,
        "intensity": update_request.intensity,
        "physical_quality": update_request.physical_quality,
        "cascade_applied": update_request.cascade,
    }


# ============================================================================
# Bottom-Up Sync Function (Full Plan Recalculation)
# ============================================================================


def sync_plan_bottom_up(
    db: Session,
    plan_id: int,
) -> Dict:
    """
    Synchronize entire training plan from bottom-up (micro → meso → macro).

    This function:
    1. Recalculates all mesocycles from their child microcycles
    2. Recalculates all macrocycles from their child mesocycles

    Use this when a trainer has made multiple micro-level changes and wants
    to propagate all changes upward at once.

    Args:
        db: Database session
        plan_id: ID of the training plan to sync

    Returns:
        Dict with sync results including all recalculations performed
    """
    plan = get_training_plan(db, plan_id)
    if not plan:
        raise ValueError(f"Training plan {plan_id} not found")

    recalculations = []
    mesocycles_updated = 0
    macrocycles_updated = 0

    # Get all macrocycles for the plan
    macrocycles = get_macrocycles_by_plan(db, plan_id)

    # Phase 1: Recalculate all mesocycles from microcycles
    for macro in macrocycles:
        if not macro.is_active:
            continue

        mesocycles = get_mesocycles_by_macrocycle(db, macro.id)
        for meso in mesocycles:
            if not meso.is_active:
                continue

            result = _recalculate_mesocycle_from_microcycles(db, meso.id)
            if "error" not in result:
                recalculations.append(result)
                if result.get("changed", False):
                    mesocycles_updated += 1

    # Phase 2: Recalculate all macrocycles from mesocycles
    for macro in macrocycles:
        if not macro.is_active:
            continue

        result = _recalculate_macrocycle_from_mesocycles(db, macro.id)
        if "error" not in result:
            recalculations.append(result)
            if result.get("changed", False):
                macrocycles_updated += 1

    total_changes = mesocycles_updated + macrocycles_updated

    return {
        "plan_id": plan_id,
        "mesocycles_updated": mesocycles_updated,
        "macrocycles_updated": macrocycles_updated,
        "total_changes": total_changes,
        "recalculations": recalculations,
        "message": (
            f"Bottom-up sync completed: {mesocycles_updated} mesocycles and "
            f"{macrocycles_updated} macrocycles updated from child values."
            if total_changes > 0
            else "No changes needed - all parent cycles are already in sync."
        ),
    }


# =============================================================================
# EXERCISE SELECTION RECOMMENDATIONS (70% Multi-joint / 30% Single-joint)
# =============================================================================

# Exercise types classified as multi-joint (compound movements)
MULTI_JOINT_TYPES = {"Multiarticular", "Multicomplejo", "Complejo"}

# Exercise types classified as single-joint (isolation movements)
SINGLE_JOINT_TYPES = {"Monoarticular", "Accesorio"}


def get_exercise_selection_recommendation(total_exercises: int) -> Dict:
    """
    Get recommended exercise type distribution for a session.

    Based on Adrián's guideline (1/12/2025):
    - 70% multi-joint exercises (Multiarticular, Multicomplejo, Complejo)
    - 30% single-joint exercises (Monoarticular, Accesorio)

    Args:
        total_exercises: Total number of exercises planned for the session

    Returns:
        Dict with recommended counts and percentages
    """
    if total_exercises <= 0:
        return {
            "total_exercises": 0,
            "recommended_multi_joint": 0,
            "recommended_single_joint": 0,
            "multi_joint_percentage": 70.0,
            "single_joint_percentage": 30.0,
            "explanation": "No exercises planned.",
        }

    # Calculate recommended counts (70/30 split)
    recommended_multi = round(total_exercises * 0.70)
    recommended_single = total_exercises - recommended_multi

    # Ensure at least 1 of each if total >= 2
    if total_exercises >= 2:
        if recommended_multi == 0:
            recommended_multi = 1
            recommended_single = total_exercises - 1
        elif recommended_single == 0:
            recommended_single = 1
            recommended_multi = total_exercises - 1

    explanation = (
        f"For {total_exercises} exercises, recommend {recommended_multi} multi-joint "
        f"({int(recommended_multi/total_exercises*100)}%) and {recommended_single} "
        f"single-joint ({int(recommended_single/total_exercises*100)}%) exercises."
    )

    return {
        "total_exercises": total_exercises,
        "recommended_multi_joint": recommended_multi,
        "recommended_single_joint": recommended_single,
        "multi_joint_percentage": 70.0,
        "single_joint_percentage": 30.0,
        "explanation": explanation,
    }


def analyze_session_exercise_types(db: Session, session_id: int) -> Dict:
    """
    Analyze the exercise type distribution in a training session.

    Compares actual distribution against recommended 70/30 split.

    Args:
        db: Database session
        session_id: ID of the training session to analyze

    Returns:
        Dict with analysis results and suggestions
    """
    # Get session exercises
    session_exercises = (
        db.query(models.SessionExercise)
        .filter(models.SessionExercise.session_id == session_id)
        .all()
    )

    if not session_exercises:
        return {
            "session_id": session_id,
            "total_exercises": 0,
            "multi_joint_count": 0,
            "single_joint_count": 0,
            "other_count": 0,
            "actual_multi_joint_percentage": 0.0,
            "actual_single_joint_percentage": 0.0,
            "recommended_multi_joint": 0,
            "recommended_single_joint": 0,
            "is_balanced": True,
            "deviation_message": "No exercises in session.",
            "suggestions": [],
        }

    # Count by exercise type
    multi_joint_count = 0
    single_joint_count = 0
    other_count = 0
    type_breakdown = {}

    for se in session_exercises:
        exercise = (
            db.query(models.Exercise)
            .filter(models.Exercise.id == se.exercise_id)
            .first()
        )
        if exercise:
            tipo = exercise.tipo
            type_breakdown[tipo] = type_breakdown.get(tipo, 0) + 1

            if tipo in MULTI_JOINT_TYPES:
                multi_joint_count += 1
            elif tipo in SINGLE_JOINT_TYPES:
                single_joint_count += 1
            else:
                other_count += 1

    total = len(session_exercises)
    actual_multi_pct = (multi_joint_count / total * 100) if total > 0 else 0
    actual_single_pct = (single_joint_count / total * 100) if total > 0 else 0

    # Get recommendations
    recommendation = get_exercise_selection_recommendation(total)
    recommended_multi = recommendation["recommended_multi_joint"]
    recommended_single = recommendation["recommended_single_joint"]

    # Check if balanced (within ±15% tolerance)
    multi_diff = abs(actual_multi_pct - 70)
    is_balanced = multi_diff <= 15

    # Generate suggestions
    suggestions = []
    deviation_message = None

    if not is_balanced:
        if actual_multi_pct < 55:  # Less than 55% multi-joint
            deficit = recommended_multi - multi_joint_count
            deviation_message = (
                f"⚠️ Too few multi-joint exercises "
                f"({actual_multi_pct:.0f}% vs 70% recommended)"
            )
            suggestions.append(
                f"Add {deficit} more multi-joint exercises "
                "(Multiarticular, Complejo)"
            )
            suggestions.append(
                "Consider: Squats, Deadlifts, Bench Press, " "Rows, Pull-ups, Lunges"
            )
        elif actual_multi_pct > 85:  # More than 85% multi-joint
            excess = multi_joint_count - recommended_multi
            deviation_message = (
                f"⚠️ Too many multi-joint exercises "
                f"({actual_multi_pct:.0f}% vs 70% recommended)"
            )
            suggestions.append(
                f"Replace {excess} multi-joint exercises " "with single-joint exercises"
            )
            suggestions.append(
                "Consider adding: Bicep Curls, Tricep Extensions, "
                "Lateral Raises, Leg Curls"
            )
    else:
        deviation_message = f"✅ Good balance! ({actual_multi_pct:.0f}% multi-joint)"

    return {
        "session_id": session_id,
        "total_exercises": total,
        "multi_joint_count": multi_joint_count,
        "single_joint_count": single_joint_count,
        "other_count": other_count,
        "actual_multi_joint_percentage": round(actual_multi_pct, 1),
        "actual_single_joint_percentage": round(actual_single_pct, 1),
        "recommended_multi_joint": recommended_multi,
        "recommended_single_joint": recommended_single,
        "is_balanced": is_balanced,
        "deviation_message": deviation_message,
        "suggestions": suggestions,
        "type_breakdown": type_breakdown,
    }


def get_exercise_suggestions_by_type(
    db: Session,
    exercise_type: str,
    limit: int = 10,
    equipment: str = None,
    level: str = None,
) -> List[Dict]:
    """
    Get exercise suggestions filtered by type (multi-joint or single-joint).

    Args:
        db: Database session
        exercise_type: "multi_joint" or "single_joint"
        limit: Maximum number of suggestions
        equipment: Optional filter by equipment
        level: Optional filter by level (beginner, intermediate, advanced)

    Returns:
        List of exercise suggestions
    """
    if exercise_type == "multi_joint":
        type_filter = MULTI_JOINT_TYPES
    elif exercise_type == "single_joint":
        type_filter = SINGLE_JOINT_TYPES
    else:
        type_filter = None

    query = db.query(models.Exercise).filter(models.Exercise.is_active.is_(True))

    if type_filter:
        query = query.filter(models.Exercise.tipo.in_(type_filter))

    if equipment:
        query = query.filter(models.Exercise.equipo == equipment)

    if level:
        query = query.filter(models.Exercise.nivel == level)

    exercises = query.limit(limit).all()

    return [
        {
            "id": ex.id,
            "exercise_id": ex.exercise_id,
            "nombre": ex.nombre,
            "nombre_ingles": ex.nombre_ingles,
            "tipo": ex.tipo,
            "equipo": ex.equipo,
            "musculatura_principal": ex.musculatura_principal,
            "nivel": ex.nivel,
        }
        for ex in exercises
    ]


# =============================================================================
# NEW EXCEL STRUCTURE CRUD FUNCTIONS
# =============================================================================


# Movement Pattern CRUD
def create_movement_pattern(
    db: Session, pattern_data: schemas.MovementPatternCreate
) -> models.MovementPattern:
    """Create a new movement pattern"""
    db_pattern = models.MovementPattern(**pattern_data.model_dump())
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)
    return db_pattern


def get_movement_patterns(
    db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = True
) -> List[models.MovementPattern]:
    """Get all movement patterns"""
    query = db.query(models.MovementPattern)
    if is_active is not None:
        query = query.filter(models.MovementPattern.is_active.is_(is_active))
    return query.offset(skip).limit(limit).all()


def get_movement_pattern(
    db: Session, pattern_id: int
) -> Optional[models.MovementPattern]:
    """Get a specific movement pattern"""
    return (
        db.query(models.MovementPattern)
        .filter(models.MovementPattern.id == pattern_id)
        .first()
    )


def update_movement_pattern(
    db: Session, pattern_id: int, pattern_data: schemas.MovementPatternUpdate
) -> Optional[models.MovementPattern]:
    """Update a movement pattern"""
    db_pattern = get_movement_pattern(db, pattern_id)
    if not db_pattern:
        return None

    update_data = pattern_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_pattern, field, value)

    db.commit()
    db.refresh(db_pattern)
    return db_pattern


def delete_movement_pattern(db: Session, pattern_id: int) -> bool:
    """Delete (soft delete) a movement pattern"""
    db_pattern = get_movement_pattern(db, pattern_id)
    if not db_pattern:
        return False

    db_pattern.is_active = False
    db.commit()
    return True


# Muscle Group CRUD
def create_muscle_group(
    db: Session, group_data: schemas.MuscleGroupCreate
) -> models.MuscleGroup:
    """Create a new muscle group"""
    db_group = models.MuscleGroup(**group_data.model_dump())
    db.add(db_group)
    db.commit()
    db.refresh(db_group)
    return db_group


def get_muscle_groups(
    db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = True
) -> List[models.MuscleGroup]:
    """Get all muscle groups"""
    query = db.query(models.MuscleGroup)
    if is_active is not None:
        query = query.filter(models.MuscleGroup.is_active.is_(is_active))
    return query.offset(skip).limit(limit).all()


def get_muscle_group(db: Session, group_id: int) -> Optional[models.MuscleGroup]:
    """Get a specific muscle group"""
    return (
        db.query(models.MuscleGroup).filter(models.MuscleGroup.id == group_id).first()
    )


def update_muscle_group(
    db: Session, group_id: int, group_data: schemas.MuscleGroupUpdate
) -> Optional[models.MuscleGroup]:
    """Update a muscle group"""
    db_group = get_muscle_group(db, group_id)
    if not db_group:
        return None

    update_data = group_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_group, field, value)

    db.commit()
    db.refresh(db_group)
    return db_group


def delete_muscle_group(db: Session, group_id: int) -> bool:
    """Delete (soft delete) a muscle group"""
    db_group = get_muscle_group(db, group_id)
    if not db_group:
        return False

    db_group.is_active = False
    db.commit()
    return True


# Equipment CRUD
def create_equipment(
    db: Session, equipment_data: schemas.EquipmentCreate
) -> models.Equipment:
    """Create a new equipment"""
    db_equipment = models.Equipment(**equipment_data.model_dump())
    db.add(db_equipment)
    db.commit()
    db.refresh(db_equipment)
    return db_equipment


def get_equipment_list(
    db: Session, skip: int = 0, limit: int = 100, is_active: Optional[bool] = True
) -> List[models.Equipment]:
    """Get all equipment"""
    query = db.query(models.Equipment)
    if is_active is not None:
        query = query.filter(models.Equipment.is_active.is_(is_active))
    return query.offset(skip).limit(limit).all()


def get_equipment(db: Session, equipment_id: int) -> Optional[models.Equipment]:
    """Get a specific equipment"""
    return (
        db.query(models.Equipment).filter(models.Equipment.id == equipment_id).first()
    )


def update_equipment(
    db: Session, equipment_id: int, equipment_data: schemas.EquipmentUpdate
) -> Optional[models.Equipment]:
    """Update an equipment"""
    db_equipment = get_equipment(db, equipment_id)
    if not db_equipment:
        return None

    update_data = equipment_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_equipment, field, value)

    db.commit()
    db.refresh(db_equipment)
    return db_equipment


def delete_equipment(db: Session, equipment_id: int) -> bool:
    """Delete (soft delete) an equipment"""
    db_equipment = get_equipment(db, equipment_id)
    if not db_equipment:
        return False

    db_equipment.is_active = False
    db.commit()
    return True


# Tag CRUD
def create_tag(db: Session, tag_data: schemas.TagCreate) -> models.Tag:
    """Create a new tag"""
    db_tag = models.Tag(**tag_data.model_dump())
    db.add(db_tag)
    db.commit()
    db.refresh(db_tag)
    return db_tag


def get_tags(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
) -> List[models.Tag]:
    """Get all tags"""
    query = db.query(models.Tag)
    if is_active is not None:
        query = query.filter(models.Tag.is_active.is_(is_active))
    if category:
        query = query.filter(models.Tag.category == category)
    return query.offset(skip).limit(limit).all()


def get_tag(db: Session, tag_id: int) -> Optional[models.Tag]:
    """Get a specific tag"""
    return db.query(models.Tag).filter(models.Tag.id == tag_id).first()


def update_tag(
    db: Session, tag_id: int, tag_data: schemas.TagUpdate
) -> Optional[models.Tag]:
    """Update a tag"""
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return None

    update_data = tag_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_tag, field, value)

    db.commit()
    db.refresh(db_tag)
    return db_tag


def delete_tag(db: Session, tag_id: int) -> bool:
    """Delete (soft delete) a tag"""
    db_tag = get_tag(db, tag_id)
    if not db_tag:
        return False

    db_tag.is_active = False
    db.commit()
    return True


# Exercise Variant CRUD
def create_exercise_variant(
    db: Session, variant_data: schemas.ExerciseVariantCreate
) -> models.ExerciseVariant:
    """Create a new exercise variant"""
    db_variant = models.ExerciseVariant(**variant_data.model_dump())
    db.add(db_variant)
    db.commit()
    db.refresh(db_variant)
    return db_variant


def get_exercise_variants(
    db: Session,
    base_exercise_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = True,
) -> List[models.ExerciseVariant]:
    """Get all exercise variants"""
    query = db.query(models.ExerciseVariant)
    if is_active is not None:
        query = query.filter(models.ExerciseVariant.is_active.is_(is_active))
    if base_exercise_id:
        query = query.filter(
            models.ExerciseVariant.base_exercise_id == base_exercise_id
        )
    return query.offset(skip).limit(limit).all()


def get_exercise_variant(
    db: Session, variant_id: int
) -> Optional[models.ExerciseVariant]:
    """Get a specific exercise variant"""
    return (
        db.query(models.ExerciseVariant)
        .filter(models.ExerciseVariant.id == variant_id)
        .first()
    )


def update_exercise_variant(
    db: Session, variant_id: int, variant_data: schemas.ExerciseVariantUpdate
) -> Optional[models.ExerciseVariant]:
    """Update an exercise variant"""
    db_variant = get_exercise_variant(db, variant_id)
    if not db_variant:
        return None

    update_data = variant_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_variant, field, value)

    db.commit()
    db.refresh(db_variant)
    return db_variant


def delete_exercise_variant(db: Session, variant_id: int) -> bool:
    """Delete (soft delete) an exercise variant"""
    db_variant = get_exercise_variant(db, variant_id)
    if not db_variant:
        return False

    db_variant.is_active = False
    db.commit()
    return True


# Mapping Table CRUD Functions
def create_exercise_movement_pattern(
    db: Session, mapping_data: schemas.ExerciseMovementPatternCreate
) -> models.ExerciseMovementPattern:
    """Create exercise to movement pattern mapping"""
    db_mapping = models.ExerciseMovementPattern(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_exercise_movement_patterns(
    db: Session, exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.ExerciseMovementPattern]:
    """Get exercise to movement pattern mappings"""
    query = db.query(models.ExerciseMovementPattern)
    if exercise_id:
        query = query.filter(models.ExerciseMovementPattern.exercise_id == exercise_id)
    return query.offset(skip).limit(limit).all()


def create_exercise_muscle(
    db: Session, mapping_data: schemas.ExerciseMuscleCreate
) -> models.ExerciseMuscle:
    """Create exercise to muscle mapping"""
    db_mapping = models.ExerciseMuscle(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_exercise_muscles(
    db: Session, exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.ExerciseMuscle]:
    """Get exercise to muscle mappings"""
    query = db.query(models.ExerciseMuscle)
    if exercise_id:
        query = query.filter(models.ExerciseMuscle.exercise_id == exercise_id)
    return query.offset(skip).limit(limit).all()


def create_exercise_equipment(
    db: Session, mapping_data: schemas.ExerciseEquipmentCreate
) -> models.ExerciseEquipment:
    """Create exercise to equipment mapping"""
    db_mapping = models.ExerciseEquipment(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_exercise_equipment_list(
    db: Session, exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.ExerciseEquipment]:
    """Get exercise to equipment mappings"""
    query = db.query(models.ExerciseEquipment)
    if exercise_id:
        query = query.filter(models.ExerciseEquipment.exercise_id == exercise_id)
    return query.offset(skip).limit(limit).all()


def create_exercise_tag(
    db: Session, mapping_data: schemas.ExerciseTagCreate
) -> models.ExerciseTag:
    """Create exercise to tag mapping"""
    db_mapping = models.ExerciseTag(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_exercise_tags(
    db: Session, exercise_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.ExerciseTag]:
    """Get exercise to tag mappings"""
    query = db.query(models.ExerciseTag)
    if exercise_id:
        query = query.filter(models.ExerciseTag.exercise_id == exercise_id)
    return query.offset(skip).limit(limit).all()


def delete_exercise_mapping(db: Session, mapping_id: int, mapping_type: str) -> bool:
    """Delete an exercise mapping (movement pattern, muscle, equipment, or tag)"""
    mapping_classes = {
        "movement_pattern": models.ExerciseMovementPattern,
        "muscle": models.ExerciseMuscle,
        "equipment": models.ExerciseEquipment,
        "tag": models.ExerciseTag,
    }

    if mapping_type not in mapping_classes:
        return False

    MappingClass = mapping_classes[mapping_type]
    db_mapping = db.query(MappingClass).filter(MappingClass.id == mapping_id).first()
    if not db_mapping:
        return False

    db.delete(db_mapping)
    db.commit()
    return True


# =============================================================================
# VARIANT MAPPING CRUD FUNCTIONS
# =============================================================================


def create_variant_equipment(
    db: Session, mapping_data: schemas.VariantEquipmentCreate
) -> models.VariantEquipment:
    """Create variant to equipment mapping"""
    db_mapping = models.VariantEquipment(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_variant_equipment(
    db: Session, variant_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.VariantEquipment]:
    """Get variant to equipment mappings"""
    query = db.query(models.VariantEquipment)
    if variant_id:
        query = query.filter(models.VariantEquipment.variant_id == variant_id)
    return query.filter(models.VariantEquipment.is_active.is_(True)).offset(skip).limit(limit).all()


def create_variant_joint_action(
    db: Session, mapping_data: schemas.VariantJointActionCreate
) -> models.VariantJointAction:
    """Create variant to joint action mapping"""
    db_mapping = models.VariantJointAction(**mapping_data.model_dump())
    db.add(db_mapping)
    db.commit()
    db.refresh(db_mapping)
    return db_mapping


def get_variant_joint_actions(
    db: Session, variant_id: Optional[int] = None, skip: int = 0, limit: int = 100
) -> List[models.VariantJointAction]:
    """Get variant to joint action mappings"""
    query = db.query(models.VariantJointAction)
    if variant_id:
        query = query.filter(models.VariantJointAction.variant_id == variant_id)
    return query.filter(models.VariantJointAction.is_active.is_(True)).offset(skip).limit(limit).all()
