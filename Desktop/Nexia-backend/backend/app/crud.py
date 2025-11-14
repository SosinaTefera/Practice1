from datetime import date, datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy import func, or_, text
from sqlalchemy.orm import Session, noload

from . import schemas
from .auth import models as auth_models
from .auth import schemas as auth_schemas
from .auth import utils as auth_utils
from .core.config import settings
from .db import models


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

    db_profile = models.ClientProfile(
        **profile_data.model_dump(exclude_unset=True), imc=imc
    )
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
        template_duration = (template_macrocycles[-1].end_date - template_macrocycles[0].start_date).days
        instance_duration = (end_date - start_date).days
        date_ratio = instance_duration / template_duration if template_duration > 0 else 1.0
        template_start = template_macrocycles[0].start_date

        # 4. Duplicate cycles recursively
        macrocycle_mapping: Dict[int, int] = {}  # template_macro_id -> instance_macro_id
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
                days_from_macro_start = (template_meso.start_date - template_macro.start_date).days
                meso_start = new_start + timedelta(days=int(days_from_macro_start * date_ratio))
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
                template_microcycles = get_microcycles_by_mesocycle(db, template_meso.id)

                for template_micro in template_microcycles:
                    # Calculate new dates for microcycle
                    days_from_meso_start = (template_micro.start_date - template_meso.start_date).days
                    micro_start = meso_start + timedelta(days=int(days_from_meso_start * date_ratio))
                    micro_end_days = (template_micro.end_date - template_micro.start_date).days
                    micro_end = micro_start + timedelta(days=int(micro_end_days * date_ratio))

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

    # Commit everything
    db.commit()
    db.refresh(instance)

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
        template_duration = (plan_macrocycles[-1].end_date - plan_macrocycles[0].start_date).days
        instance_duration = (end_date - start_date).days
        date_ratio = instance_duration / template_duration if template_duration > 0 else 1.0
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
                days_from_macro_start = (plan_meso.start_date - plan_macro.start_date).days
                meso_start = new_start + timedelta(days=int(days_from_macro_start * date_ratio))
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
                    days_from_meso_start = (plan_micro.start_date - plan_meso.start_date).days
                    micro_start = meso_start + timedelta(days=int(days_from_meso_start * date_ratio))
                    micro_end_days = (plan_micro.end_date - plan_micro.start_date).days
                    micro_end = micro_start + timedelta(days=int(micro_end_days * date_ratio))

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


# Coherence Calculation System (Adrián's requirement)
def calculate_plan_coherence(
    db: Session,
    plan_id: int,
    deviation_threshold: float = 20.0,  # Percentage threshold for warnings
) -> Dict:
    """
    Calculate coherence between month (Macrocycle) → week (Mesocycle) → day (Microcycle).
    
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
        month_coherence.append({
            "macrocycle_id": macro.id,
            "macrocycle_name": macro.name,
            "physical_quality": macro.physical_quality or macro.focus,
            "planned_volume": macro.volume,
            "planned_intensity": macro.intensity,
            "coherence_percentage": 100.0,
            "deviation_warning": False,
        })

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
            volume_deviation = abs(meso_volume - macro.volume) / macro.volume * 100 if macro.volume > 0 else 0
            intensity_deviation = abs(meso_intensity - macro.intensity) / macro.intensity * 100 if macro.intensity > 0 else 0
            avg_deviation = (volume_deviation + intensity_deviation) / 2
            coherence_pct = max(0, 100 - avg_deviation)

            week_coherence.append({
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
            })
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
                volume_deviation = abs(micro_volume - meso_volume) / meso_volume * 100 if meso_volume > 0 else 0
                intensity_deviation = abs(micro_intensity - meso_intensity) / meso_intensity * 100 if meso_intensity > 0 else 0
                avg_deviation = (volume_deviation + intensity_deviation) / 2
                coherence_pct = max(0, 100 - avg_deviation)

                day_coherence.append({
                    "microcycle_id": micro.id,
                    "microcycle_name": micro.name,
                    "mesocycle_id": meso.id,
                    "physical_quality": micro.physical_quality or meso.primary_focus,
                    "planned_volume": micro_volume,
                    "planned_intensity": micro_intensity,
                    "week_volume": meso_volume,
                    "week_intensity": meso_intensity,
                    "coherence_percentage": coherence_pct,
                    "deviation_warning": avg_deviation > deviation_threshold,
                    "inherited": inherited,
                })
                overall_coherences.append(coherence_pct)

    # Calculate overall coherence
    overall_coherence = sum(overall_coherences) / len(overall_coherences) if overall_coherences else 100.0

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


def update_mesocycle(
    db: Session, mesocycle_id: int, mesocycle_data: schemas.MesocycleUpdate
):
    db_mesocycle = get_mesocycle(db, mesocycle_id)
    if not db_mesocycle:
        return None

    update_data = mesocycle_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_mesocycle, field, value)

    db.commit()
    db.refresh(db_mesocycle)
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

    update_data = microcycle_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_microcycle, field, value)

    db.commit()
    db.refresh(db_microcycle)
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
    db_session = models.TrainingSession(**session_data.model_dump())
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session


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

    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_session, field, value)

    db.commit()
    db.refresh(db_session)
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
def create_fatigue_analysis(db: Session, fatigue_data: schemas.FatigueAnalysisCreate):
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
    return db_fatigue


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
        .filter(models.FatigueAlert.is_read is False, models.FatigueAlert.is_active)
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
            models.FatigueAlert.is_read is False,
            models.FatigueAlert.is_active,
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
    db: Session, trainer_id: int = None, skip: int = 0, limit: int = 100
):
    """Get session templates, optionally filtered by trainer"""
    query = db.query(models.SessionTemplate)

    if trainer_id:
        # Get trainer's templates + public templates
        query = query.filter(
            (models.SessionTemplate.trainer_id == trainer_id)
            | (models.SessionTemplate.is_public.is_(True))
        )
    else:
        # Get only public templates
        query = query.filter(models.SessionTemplate.is_public.is_(True))

    return query.offset(skip).limit(limit).all()


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
