from datetime import date, datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator

# Import enums from models
from .db.models import (
    EffortCharacterEnum,
    ExperienceEnum,
    GenderEnum,
    SetTypeEnum,
    TrainingGoalEnum,
    WeeklyFrequencyEnum,
)


class UnitEnum(str, Enum):
    metric = "metric"  # kg + meters
    imperial = "imperial"  # lbs + inches


class ClientProfileBase(BaseModel):
    nombre: str
    apellidos: str
    mail: EmailStr
    telefono: Optional[str] = None
    sexo: Optional[GenderEnum] = None
    observaciones: Optional[str] = None
    edad: Optional[int] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    objetivo_entrenamiento: Optional[TrainingGoalEnum] = None
    fecha_definicion_objetivo: Optional[date] = None
    descripcion_objetivos: Optional[str] = None
    experiencia: Optional[ExperienceEnum] = None
    lesiones_relevantes: Optional[str] = None
    frecuencia_semanal: Optional[WeeklyFrequencyEnum] = None

    # Additional Personal Information
    id_passport: Optional[str] = None
    birthdate: Optional[date] = None

    # Anthropometric Data - Skinfolds (in mm)
    skinfold_triceps: Optional[float] = None
    skinfold_subscapular: Optional[float] = None
    skinfold_biceps: Optional[float] = None
    skinfold_iliac_crest: Optional[float] = None
    skinfold_supraspinal: Optional[float] = None
    skinfold_abdominal: Optional[float] = None
    skinfold_thigh: Optional[float] = None
    skinfold_calf: Optional[float] = None

    # Anthropometric Data - Girths (in cm)
    girth_relaxed_arm: Optional[float] = None
    girth_flexed_contracted_arm: Optional[float] = None
    girth_waist_minimum: Optional[float] = None
    girth_hips_maximum: Optional[float] = None
    girth_medial_thigh: Optional[float] = None
    girth_maximum_calf: Optional[float] = None

    # Anthropometric Data - Diameters (in cm)
    diameter_humerus_biepicondylar: Optional[float] = None
    diameter_femur_bicondylar: Optional[float] = None
    diameter_bi_styloid_wrist: Optional[float] = None

    # Program Meta Fields
    objective: Optional[str] = None
    session_duration: Optional[str] = None
    notes_1: Optional[str] = None
    notes_2: Optional[str] = None
    notes_3: Optional[str] = None

    @field_validator("edad")
    @classmethod
    def validate_age(cls, v):
        if v is not None and (v < 13 or v > 100):
            raise ValueError("Age must be between 13 and 100 years")
        return v

    @field_validator("peso")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError("Weight must be between 20 and 300 kg")
        return v

    @field_validator("altura")
    @classmethod
    def validate_height(cls, v):
        if v is not None and (v < 100 or v > 250):
            raise ValueError("Height must be between 100 and 250 cm")
        return v

    @field_validator("telefono")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            # Remove all non-digit characters
            digits_only = "".join(filter(str.isdigit, v))
            if len(digits_only) < 7 or len(digits_only) > 15:
                raise ValueError("Phone number must have between 7 and 15 digits")
        return v

    @field_validator(
        "skinfold_triceps",
        "skinfold_subscapular",
        "skinfold_biceps",
        "skinfold_iliac_crest",
        "skinfold_supraspinal",
        "skinfold_abdominal",
        "skinfold_thigh",
        "skinfold_calf",
    )
    @classmethod
    def validate_skinfolds(cls, v):
        if v is not None and (v < 0 or v > 50):
            raise ValueError("Skinfold measurements must be between 0 and 50 mm")
        return v

    @field_validator(
        "girth_relaxed_arm",
        "girth_flexed_contracted_arm",
        "girth_waist_minimum",
        "girth_hips_maximum",
        "girth_medial_thigh",
        "girth_maximum_calf",
    )
    @classmethod
    def validate_girths(cls, v):
        if v is not None and (v < 10 or v > 200):
            raise ValueError("Girth measurements must be between 10 and 200 cm")
        return v

    @field_validator(
        "diameter_humerus_biepicondylar",
        "diameter_femur_bicondylar",
        "diameter_bi_styloid_wrist",
    )
    @classmethod
    def validate_diameters(cls, v):
        if v is not None and (v < 3 or v > 20):
            raise ValueError("Diameter measurements must be between 3 and 20 cm")
        return v

    @field_validator("session_duration")
    @classmethod
    def validate_session_duration(cls, v):
        if v is not None and v not in [
            "short_lt_1h",
            "medium_1h_to_1h30",
            "long_gt_1h30",
        ]:
            raise ValueError(
                "Session duration must be one of: short_lt_1h, "
                "medium_1h_to_1h30, long_gt_1h30"
            )
        return v


class ClientProfileCreate(ClientProfileBase):
    pass


class ClientProfileUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    mail: Optional[EmailStr] = None
    telefono: Optional[str] = None
    sexo: Optional[GenderEnum] = None
    observaciones: Optional[str] = None
    edad: Optional[int] = None
    peso: Optional[float] = None
    altura: Optional[float] = None
    objetivo_entrenamiento: Optional[TrainingGoalEnum] = None
    fecha_definicion_objetivo: Optional[date] = None
    descripcion_objetivos: Optional[str] = None
    experiencia: Optional[ExperienceEnum] = None
    lesiones_relevantes: Optional[str] = None
    frecuencia_semanal: Optional[WeeklyFrequencyEnum] = None

    # Additional Personal Information
    id_passport: Optional[str] = None
    birthdate: Optional[date] = None

    # Anthropometric Data - Skinfolds (in mm)
    skinfold_triceps: Optional[float] = None
    skinfold_subscapular: Optional[float] = None
    skinfold_biceps: Optional[float] = None
    skinfold_iliac_crest: Optional[float] = None
    skinfold_supraspinal: Optional[float] = None
    skinfold_abdominal: Optional[float] = None
    skinfold_thigh: Optional[float] = None
    skinfold_calf: Optional[float] = None

    # Anthropometric Data - Girths (in cm)
    girth_relaxed_arm: Optional[float] = None
    girth_flexed_contracted_arm: Optional[float] = None
    girth_waist_minimum: Optional[float] = None
    girth_hips_maximum: Optional[float] = None
    girth_medial_thigh: Optional[float] = None
    girth_maximum_calf: Optional[float] = None

    # Anthropometric Data - Diameters (in cm)
    diameter_humerus_biepicondylar: Optional[float] = None
    diameter_femur_bicondylar: Optional[float] = None
    diameter_bi_styloid_wrist: Optional[float] = None

    # Program Meta Fields
    objective: Optional[str] = None
    session_duration: Optional[str] = None
    notes_1: Optional[str] = None
    notes_2: Optional[str] = None
    notes_3: Optional[str] = None

    @field_validator("edad")
    @classmethod
    def validate_age(cls, v):
        if v is not None and (v < 13 or v > 100):
            raise ValueError("Age must be between 13 and 100 years")
        return v

    @field_validator("peso")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError("Weight must be between 20 and 300 kg")
        return v

    @field_validator("altura")
    @classmethod
    def validate_height(cls, v):
        if v is not None and (v < 100 or v > 250):
            raise ValueError("Height must be between 100 and 250 cm")
        return v

    @field_validator(
        "skinfold_triceps",
        "skinfold_subscapular",
        "skinfold_biceps",
        "skinfold_iliac_crest",
        "skinfold_supraspinal",
        "skinfold_abdominal",
        "skinfold_thigh",
        "skinfold_calf",
    )
    @classmethod
    def validate_skinfolds(cls, v):
        if v is not None and (v < 0 or v > 50):
            raise ValueError("Skinfold measurements must be between 0 and 50 mm")
        return v

    @field_validator(
        "girth_relaxed_arm",
        "girth_flexed_contracted_arm",
        "girth_waist_minimum",
        "girth_hips_maximum",
        "girth_medial_thigh",
        "girth_maximum_calf",
    )
    @classmethod
    def validate_girths(cls, v):
        if v is not None and (v < 10 or v > 200):
            raise ValueError("Girth measurements must be between 10 and 200 cm")
        return v

    @field_validator(
        "diameter_humerus_biepicondylar",
        "diameter_femur_bicondylar",
        "diameter_bi_styloid_wrist",
    )
    @classmethod
    def validate_diameters(cls, v):
        if v is not None and (v < 3 or v > 20):
            raise ValueError("Diameter measurements must be between 3 and 20 cm")
        return v

    @field_validator("session_duration")
    @classmethod
    def validate_session_duration(cls, v):
        if v is not None and v not in [
            "short_lt_1h",
            "medium_1h_to_1h30",
            "long_gt_1h30",
        ]:
            raise ValueError(
                "Session duration must be one of: short_lt_1h, "
                "medium_1h_to_1h30, long_gt_1h30"
            )
        return v


class ClientProfileOut(ClientProfileBase):
    id: int
    fecha_alta: date
    imc: Optional[float] = None
    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    items: List[ClientProfileOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    model_config = {"from_attributes": True}


class TrainerBase(BaseModel):
    nombre: str
    apellidos: str
    mail: EmailStr
    telefono: Optional[str] = None

    @field_validator("telefono")
    @classmethod
    def validate_phone(cls, v):
        if v is not None:
            # Remove all non-digit characters
            digits_only = "".join(filter(str.isdigit, v))
            if len(digits_only) < 7 or len(digits_only) > 15:
                raise ValueError("Phone number must have between 7 and 15 digits")
        return v


class TrainerCreate(TrainerBase):
    pass


class TrainerUpdate(BaseModel):
    nombre: Optional[str] = None
    apellidos: Optional[str] = None
    mail: Optional[EmailStr] = None
    telefono: Optional[str] = None
    # Professional profile (MVP)
    occupation: Optional[str] = None
    training_modality: Optional[str] = None  # in_person | online | hybrid
    location_country: Optional[str] = None
    location_city: Optional[str] = None
    billing_id: Optional[str] = None
    billing_address: Optional[str] = None
    billing_postal_code: Optional[str] = None
    # Optional
    specialty: Optional[str] = None


class TrainerOut(TrainerBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    # Professional profile fields
    occupation: Optional[str] = None
    training_modality: Optional[str] = None
    location_country: Optional[str] = None
    location_city: Optional[str] = None
    billing_id: Optional[str] = None
    billing_address: Optional[str] = None
    billing_postal_code: Optional[str] = None
    specialty: Optional[str] = None
    model_config = {"from_attributes": True}


# Trainer Client Schemas
class TrainerClientBase(BaseModel):
    trainer_id: int
    client_id: int


class TrainerClientCreate(TrainerClientBase):
    pass


class TrainerClientUpdate(BaseModel):
    trainer_id: Optional[int] = None
    client_id: Optional[int] = None


class TrainerClientOut(TrainerClientBase):
    assigned_at: datetime
    model_config = {"from_attributes": True}


# Exercise Schemas
class ExerciseBase(BaseModel):
    exercise_id: str
    nombre: str
    nombre_ingles: Optional[str] = None
    tipo: str
    categoria: str
    nivel: str
    equipo: str
    patron_movimiento: str
    tipo_carga: str
    musculatura_principal: str
    musculatura_secundaria: Optional[str] = None
    descripcion: Optional[str] = None
    instrucciones: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("exercise_id")
    @classmethod
    def validate_exercise_id(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Exercise ID cannot be empty")
        return v.strip()

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Exercise name cannot be empty")
        return v.strip()

    @field_validator("musculatura_principal")
    @classmethod
    def validate_musculatura_principal(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Primary muscles cannot be empty")
        return v.strip()


class ExerciseCreate(ExerciseBase):
    pass


class ExerciseUpdate(BaseModel):
    exercise_id: Optional[str] = None
    nombre: Optional[str] = None
    nombre_ingles: Optional[str] = None
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    nivel: Optional[str] = None
    equipo: Optional[str] = None
    patron_movimiento: Optional[str] = None
    tipo_carga: Optional[str] = None
    musculatura_principal: Optional[str] = None
    musculatura_secundaria: Optional[str] = None
    descripcion: Optional[str] = None
    instrucciones: Optional[str] = None
    notas: Optional[str] = None


class ExerciseOut(ExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Exercise Filter Schemas
class ExerciseFilter(BaseModel):
    tipo: Optional[str] = None
    categoria: Optional[str] = None
    nivel: Optional[str] = None
    equipo: Optional[str] = None
    patron_movimiento: Optional[str] = None
    tipo_carga: Optional[str] = None
    search: Optional[str] = (
        None  # Search in nombre, nombre_ingles, musculatura_principal
    )
    skip: int = 0
    limit: int = 100

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v):
        if v > 1000:
            raise ValueError("Limit cannot exceed 1000")
        return v


# Exercise List Response
class ExerciseListResponse(BaseModel):
    exercises: List[ExerciseOut]
    total: int
    skip: int
    limit: int
    has_more: bool
    model_config = {"from_attributes": True}


# Training Routine Schemas
class TrainingRoutineBase(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    tipo_rutina: str
    frecuencia: WeeklyFrequencyEnum
    experiencia_requerida: ExperienceEnum
    volumen: str
    intensidad: str


class TrainingRoutineCreate(TrainingRoutineBase):
    pass


class TrainingRoutineUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    tipo_rutina: Optional[str] = None
    frecuencia: Optional[WeeklyFrequencyEnum] = None
    experiencia_requerida: Optional[ExperienceEnum] = None
    volumen: Optional[str] = None
    intensidad: Optional[str] = None


class TrainingRoutineOut(TrainingRoutineBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Routine Exercise Schemas
class RoutineExerciseBase(BaseModel):
    routine_id: int
    exercise_id: int
    series: int = 3
    repeticiones: str = "8-12"
    descanso: Optional[str] = None
    orden: int = 1


class RoutineExerciseCreate(RoutineExerciseBase):
    pass


class RoutineExerciseUpdate(BaseModel):
    series: Optional[int] = None
    repeticiones: Optional[str] = None
    descanso: Optional[str] = None
    orden: Optional[int] = None


class RoutineExerciseOut(RoutineExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Client Routine Schemas
class ClientRoutineBase(BaseModel):
    client_id: int
    routine_template_id: int
    trainer_id: Optional[int] = None
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    activa: bool = True


class ClientRoutineCreate(ClientRoutineBase):
    pass


class ClientRoutineUpdate(BaseModel):
    fecha_fin: Optional[date] = None
    activa: Optional[bool] = None


class ClientRoutineOut(ClientRoutineBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Client Progress Schemas
class ClientProgressBase(BaseModel):
    client_id: int
    fecha_registro: date
    peso: Optional[float] = None
    altura: Optional[float] = None
    unidad: str = "metric"  # Default to metric
    imc: Optional[float] = None
    notas: Optional[str] = None

    @model_validator(mode="after")
    def convert_and_validate_units(self):
        """Convert imperial units to metric and validate ranges"""
        # Ensure unidad has a value
        if self.unidad is None:
            self.unidad = "metric"

        if self.peso is not None and self.unidad == "imperial":
            # Convert pounds to kg
            self.peso = round(self.peso * 0.453592, 2)
        if self.altura is not None and self.unidad == "imperial":
            # Convert inches to meters
            self.altura = round(self.altura * 0.0254, 3)

        # Calculate BMI automatically whenever weight or height is provided
        if self.peso is not None and self.altura is not None:
            bmi = self.peso / (self.altura**2)
            self.imc = round(bmi, 2)  # Store with 2 decimal places
        elif self.peso is not None and self.altura is None:
            # If only weight is provided, clear BMI (can't calculate)
            self.imc = None
        elif self.altura is not None and self.peso is None:
            # If only height is provided, clear BMI (can't calculate)
            self.imc = None

        # Validate final metric values
        if self.peso is not None and (self.peso < 20 or self.peso > 300):
            raise ValueError("Weight must be between 20 and 300 kg (after conversion)")
        if self.altura is not None and (self.altura < 0.5 or self.altura > 3.0):
            raise ValueError(
                "Height must be between 0.5 and 3.0 meters (after conversion)"
            )
        if self.imc is not None and (self.imc < 10 or self.imc > 60):
            raise ValueError("BMI must be between 10 and 60")
        return self


class ClientProgressCreate(ClientProgressBase):
    pass


class ClientProgressUpdate(BaseModel):
    peso: Optional[float] = None
    altura: Optional[float] = None
    unidad: Optional[UnitEnum] = None
    imc: Optional[float] = None
    notas: Optional[str] = None

    @field_validator("peso")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (v < 0 or v > 500):
            raise ValueError("Weight must be between 0 and 500 kg")
        return v

    @field_validator("altura")
    @classmethod
    def validate_height(cls, v):
        if v is not None and (v < 0.5 or v > 3.0):
            raise ValueError("Height must be between 0.5 and 3.0 meters")
        return v


class ClientProgressOut(BaseModel):
    id: int
    client_id: int
    fecha_registro: date
    peso: Optional[float] = None
    altura: Optional[float] = None
    unidad: Optional[str] = None
    imc: Optional[float] = None
    notas: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Training Plan Schemas
class TrainingPlanBase(BaseModel):
    trainer_id: int
    client_id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    goal: str
    status: str = "active"


class TrainingPlanCreate(TrainingPlanBase):
    pass


class TrainingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    status: Optional[str] = None


class TrainingPlanOut(TrainingPlanBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Macrocycle Schemas
class MacrocycleBase(BaseModel):
    training_plan_id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    focus: str
    volume_intensity_ratio: Optional[str] = None


class MacrocycleCreate(MacrocycleBase):
    pass


class MacrocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    focus: Optional[str] = None
    volume_intensity_ratio: Optional[str] = None


class MacrocycleOut(MacrocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Mesocycle Schemas
class MesocycleBase(BaseModel):
    macrocycle_id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    duration_weeks: int
    primary_focus: str
    secondary_focus: Optional[str] = None
    target_volume: Optional[str] = None
    target_intensity: Optional[str] = None


class MesocycleCreate(MesocycleBase):
    pass


class MesocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    duration_weeks: Optional[int] = None
    primary_focus: Optional[str] = None
    secondary_focus: Optional[str] = None
    target_volume: Optional[str] = None
    target_intensity: Optional[str] = None


class MesocycleOut(MesocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Microcycle Schemas
class MicrocycleBase(BaseModel):
    mesocycle_id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    duration_days: int = 7
    training_frequency: int = 3
    deload_week: bool = False
    notes: Optional[str] = None


class MicrocycleCreate(MicrocycleBase):
    pass


class MicrocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    duration_days: Optional[int] = None
    training_frequency: Optional[int] = None
    deload_week: Optional[bool] = None
    notes: Optional[str] = None


class MicrocycleOut(MicrocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Training Session Schemas
class TrainingSessionBase(BaseModel):
    microcycle_id: int
    client_id: int
    trainer_id: int
    session_date: date
    session_name: str
    session_type: str
    planned_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    # Session programming enhancements
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    actual_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
    status: str = "planned"
    notes: Optional[str] = None


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionUpdate(BaseModel):
    session_name: Optional[str] = None
    session_type: Optional[str] = None
    planned_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class TrainingSessionOut(TrainingSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Exercise Schemas
class SessionExerciseBase(BaseModel):
    training_session_id: int
    exercise_id: int
    order_in_session: int
    planned_sets: Optional[int] = None
    planned_reps: Optional[int] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    notes: Optional[str] = None


class SessionExerciseCreate(SessionExerciseBase):
    pass


class SessionExerciseUpdate(BaseModel):
    order_in_session: Optional[int] = None
    planned_sets: Optional[int] = None
    planned_reps: Optional[int] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight: Optional[float] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    notes: Optional[str] = None


class SessionExerciseOut(SessionExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Client Feedback Schemas
class ClientFeedbackBase(BaseModel):
    training_session_id: int
    client_id: int
    perceived_effort: Optional[int] = None
    fatigue_level: Optional[int] = None
    sleep_quality: Optional[int] = None
    stress_level: Optional[int] = None
    motivation_level: Optional[int] = None
    energy_level: Optional[int] = None
    muscle_soreness: Optional[str] = None
    pain_or_discomfort: Optional[str] = None
    notes: Optional[str] = None
    feedback_date: datetime

    @field_validator(
        "perceived_effort",
        "fatigue_level",
        "sleep_quality",
        "stress_level",
        "motivation_level",
        "energy_level",
    )
    @classmethod
    def validate_scale_scores(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Scale scores must be between 1 and 10")
        return v


class ClientFeedbackCreate(ClientFeedbackBase):
    pass


class ClientFeedbackUpdate(BaseModel):
    perceived_effort: Optional[int] = None
    fatigue_level: Optional[int] = None
    sleep_quality: Optional[int] = None
    stress_level: Optional[int] = None
    motivation_level: Optional[int] = None
    energy_level: Optional[int] = None
    muscle_soreness: Optional[str] = None
    pain_or_discomfort: Optional[str] = None
    notes: Optional[str] = None


class ClientFeedbackOut(ClientFeedbackBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Progress Tracking Schemas
class ProgressTrackingBase(BaseModel):
    client_id: int
    exercise_id: int
    tracking_date: date
    max_weight: Optional[float] = None
    max_reps: Optional[int] = None
    max_duration: Optional[int] = None
    max_distance: Optional[float] = None
    estimated_1rm: Optional[float] = None
    notes: Optional[str] = None

    @field_validator("max_weight")
    @classmethod
    def validate_max_weight(cls, v):
        if v is not None and (v < 0 or v > 1000):
            raise ValueError("Max weight must be between 0 and 1000 kg")
        return v

    @field_validator("max_reps")
    @classmethod
    def validate_max_reps(cls, v):
        if v is not None and (v < 1 or v > 1000):
            raise ValueError("Max reps must be between 1 and 1000")
        return v

    @field_validator("max_duration")
    @classmethod
    def validate_max_duration(cls, v):
        if v is not None and (v < 1 or v > 1440):
            raise ValueError(
                "Max duration must be between 1 and 1440 minutes (24 hours)"
            )
        return v

    @field_validator("max_distance")
    @classmethod
    def validate_max_distance(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError("Max distance must be between 0 and 100 km")
        return v


class ProgressTrackingCreate(ProgressTrackingBase):
    pass


class ProgressTrackingUpdate(BaseModel):
    max_weight: Optional[float] = None
    max_reps: Optional[int] = None
    max_duration: Optional[int] = None
    max_distance: Optional[float] = None
    estimated_1rm: Optional[float] = None
    notes: Optional[str] = None


class ProgressTrackingOut(ProgressTrackingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Standalone Session Schemas
class StandaloneSessionBase(BaseModel):
    trainer_id: int
    client_id: int
    session_date: date
    session_name: str
    session_type: str
    planned_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    status: str = "planned"
    notes: Optional[str] = None

    @field_validator("planned_duration", "actual_duration")
    @classmethod
    def validate_duration(cls, v):
        if v is not None and (v < 1 or v > 480):
            raise ValueError("Duration must be between 1 and 480 minutes (8 hours)")
        return v


class StandaloneSessionCreate(StandaloneSessionBase):
    pass


class StandaloneSessionUpdate(BaseModel):
    session_name: Optional[str] = None
    session_type: Optional[str] = None
    planned_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class StandaloneSessionOut(StandaloneSessionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Standalone Session Exercise Schemas
class StandaloneSessionExerciseBase(BaseModel):
    standalone_session_id: int
    exercise_id: int
    order_in_session: int
    planned_sets: Optional[int] = None
    planned_reps: Optional[int] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight: Optional[int] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    notes: Optional[str] = None


class StandaloneSessionExerciseCreate(StandaloneSessionExerciseBase):
    pass


class StandaloneSessionExerciseUpdate(BaseModel):
    order_in_session: Optional[int] = None
    planned_sets: Optional[int] = None
    planned_reps: Optional[int] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[int] = None
    actual_weight: Optional[int] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    notes: Optional[str] = None


class StandaloneSessionExerciseOut(StandaloneSessionExerciseBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Standalone Session Feedback Schemas
class StandaloneSessionFeedbackBase(BaseModel):
    standalone_session_id: int
    client_id: int
    perceived_effort: Optional[int] = None
    fatigue_level: Optional[int] = None
    sleep_quality: Optional[int] = None
    stress_level: Optional[int] = None
    motivation_level: Optional[int] = None
    energy_level: Optional[int] = None
    muscle_soreness: Optional[str] = None
    pain_or_discomfort: Optional[str] = None
    notes: Optional[str] = None
    feedback_date: datetime

    @field_validator(
        "perceived_effort",
        "fatigue_level",
        "sleep_quality",
        "stress_level",
        "motivation_level",
        "energy_level",
    )
    @classmethod
    def _validate_scale_scores(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Scale scores must be between 1 and 10")
        return v


class StandaloneSessionFeedbackCreate(StandaloneSessionFeedbackBase):
    pass


class StandaloneSessionFeedbackUpdate(BaseModel):
    perceived_effort: Optional[int] = None
    fatigue_level: Optional[int] = None
    sleep_quality: Optional[int] = None
    stress_level: Optional[int] = None
    motivation_level: Optional[int] = None
    energy_level: Optional[int] = None
    muscle_soreness: Optional[str] = None
    pain_or_discomfort: Optional[str] = None
    notes: Optional[str] = None


class StandaloneSessionFeedbackOut(StandaloneSessionFeedbackBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Fatigue Analysis Schemas
class FatigueAnalysisBase(BaseModel):
    client_id: int
    session_id: Optional[int] = None
    session_type: str  # "training" or "standalone"
    analysis_date: date

    # Pre-session metrics
    pre_fatigue_level: Optional[int] = None  # 1-10 scale
    pre_energy_level: Optional[int] = None  # 1-10 scale
    pre_motivation_level: Optional[int] = None  # 1-10 scale
    pre_sleep_quality: Optional[int] = None  # 1-10 scale
    pre_stress_level: Optional[int] = None  # 1-10 scale
    pre_muscle_soreness: Optional[str] = None

    # Post-session metrics
    post_fatigue_level: Optional[int] = None  # 1-10 scale
    post_energy_level: Optional[int] = None  # 1-10 scale
    post_motivation_level: Optional[int] = None  # 1-10 scale
    post_muscle_soreness: Optional[str] = None

    # Calculated metrics
    fatigue_delta: Optional[int] = None  # post - pre fatigue
    energy_delta: Optional[int] = None  # post - pre energy
    workload_score: Optional[float] = None  # calculated from session intensity
    recovery_need_score: Optional[float] = None  # calculated recovery requirement

    # Analysis results
    risk_level: Optional[str] = None  # "low", "medium", "high"
    recommendations: Optional[str] = None
    next_session_adjustment: Optional[str] = None

    @field_validator(
        "pre_fatigue_level",
        "pre_energy_level",
        "pre_motivation_level",
        "pre_sleep_quality",
        "pre_stress_level",
        "post_fatigue_level",
        "post_energy_level",
        "post_motivation_level",
    )
    @classmethod
    def _validate_scale_scores(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("Scale scores must be between 1 and 10")
        return v

    @field_validator("session_type")
    @classmethod
    def _validate_session_type(cls, v):
        if v not in ["training", "standalone"]:
            raise ValueError("Session type must be 'training' or 'standalone'")
        return v

    @field_validator("risk_level")
    @classmethod
    def _validate_risk_level(cls, v):
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError("Risk level must be 'low', 'medium', or 'high'")
        return v


class FatigueAnalysisCreate(FatigueAnalysisBase):
    pass


class FatigueAnalysisUpdate(BaseModel):
    session_id: Optional[int] = None
    session_type: Optional[str] = None
    analysis_date: Optional[date] = None

    # Pre-session metrics
    pre_fatigue_level: Optional[int] = None
    pre_energy_level: Optional[int] = None
    pre_motivation_level: Optional[int] = None
    pre_sleep_quality: Optional[int] = None
    pre_stress_level: Optional[int] = None
    pre_muscle_soreness: Optional[str] = None

    # Post-session metrics
    post_fatigue_level: Optional[int] = None
    post_energy_level: Optional[int] = None
    post_motivation_level: Optional[int] = None
    post_muscle_soreness: Optional[str] = None

    # Calculated metrics
    fatigue_delta: Optional[int] = None
    energy_delta: Optional[int] = None
    workload_score: Optional[float] = None
    recovery_need_score: Optional[float] = None

    # Analysis results
    risk_level: Optional[str] = None
    recommendations: Optional[str] = None
    next_session_adjustment: Optional[str] = None


class FatigueAnalysisOut(FatigueAnalysisBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Fatigue Alert Schemas
class FatigueAlertBase(BaseModel):
    client_id: int
    trainer_id: int
    fatigue_analysis_id: Optional[int] = None
    alert_type: str  # "overtraining", "recovery_needed", "session_adjustment"
    severity: str  # "low", "medium", "high", "critical"
    title: str
    message: str
    recommendations: Optional[str] = None
    is_read: bool = False
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None

    @field_validator("alert_type")
    @classmethod
    def _validate_alert_type(cls, v):
        valid_types = ["overtraining", "recovery_needed", "session_adjustment"]
        if v not in valid_types:
            raise ValueError(f"Alert type must be one of: {valid_types}")
        return v

    @field_validator("severity")
    @classmethod
    def _validate_severity(cls, v):
        valid_severities = ["low", "medium", "high", "critical"]
        if v not in valid_severities:
            raise ValueError(f"Severity must be one of: {valid_severities}")
        return v


class FatigueAlertCreate(FatigueAlertBase):
    pass


class FatigueAlertUpdate(BaseModel):
    alert_type: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    message: Optional[str] = None
    recommendations: Optional[str] = None
    is_read: Optional[bool] = None
    is_resolved: Optional[bool] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[int] = None
    resolution_notes: Optional[str] = None


class FatigueAlertOut(FatigueAlertBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Workload Tracking Schemas
class WorkloadTrackingBase(BaseModel):
    client_id: int
    tracking_date: date

    # Daily workload metrics
    total_volume: Optional[float] = None  # total sets * reps * weight
    total_duration: Optional[int] = None  # total training time in minutes
    intensity_score: Optional[float] = None  # calculated intensity rating
    perceived_exertion_avg: Optional[float] = None  # average RPE for the day

    # Weekly cumulative metrics (calculated)
    weekly_volume: Optional[float] = None
    weekly_intensity: Optional[float] = None
    weekly_fatigue: Optional[float] = None

    # Training stress balance
    acute_workload: Optional[float] = None  # 7-day workload
    chronic_workload: Optional[float] = None  # 28-day workload
    training_stress_balance: Optional[float] = None  # acute/chronic ratio

    @field_validator("perceived_exertion_avg")
    @classmethod
    def _validate_rpe(cls, v):
        if v is not None and (v < 1 or v > 10):
            raise ValueError("RPE must be between 1 and 10")
        return v

    @field_validator("total_duration")
    @classmethod
    def _validate_duration(cls, v):
        if v is not None and v < 0:
            raise ValueError("Duration cannot be negative")
        return v


class WorkloadTrackingCreate(WorkloadTrackingBase):
    pass


class WorkloadTrackingUpdate(BaseModel):
    tracking_date: Optional[date] = None
    total_volume: Optional[float] = None
    total_duration: Optional[int] = None
    intensity_score: Optional[float] = None
    perceived_exertion_avg: Optional[float] = None
    weekly_volume: Optional[float] = None
    weekly_intensity: Optional[float] = None
    weekly_fatigue: Optional[float] = None
    acute_workload: Optional[float] = None
    chronic_workload: Optional[float] = None
    training_stress_balance: Optional[float] = None


class WorkloadTrackingOut(WorkloadTrackingBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Programming Enhancement Schemas


# Training Block Type Schemas
class TrainingBlockTypeBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_predefined: bool = True
    color: Optional[str] = None
    icon: Optional[str] = None


class TrainingBlockTypeCreate(TrainingBlockTypeBase):
    pass


class TrainingBlockTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None


class TrainingBlockTypeOut(TrainingBlockTypeBase):
    id: int
    created_by_trainer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Template Schemas
class SessionTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    session_type: str
    estimated_duration: Optional[int] = None
    difficulty_level: Optional[str] = None
    target_muscles: Optional[str] = None
    equipment_needed: Optional[str] = None
    is_public: bool = False


class SessionTemplateCreate(SessionTemplateBase):
    pass


class SessionTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    session_type: Optional[str] = None
    estimated_duration: Optional[int] = None
    difficulty_level: Optional[str] = None
    target_muscles: Optional[str] = None
    equipment_needed: Optional[str] = None
    is_public: Optional[bool] = None


class SessionTemplateOut(SessionTemplateBase):
    id: int
    trainer_id: int
    usage_count: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Template Block Schemas
class SessionTemplateBlockBase(BaseModel):
    block_type_id: int
    order_in_template: int
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    estimated_duration: Optional[int] = None
    notes: Optional[str] = None


class SessionTemplateBlockCreate(SessionTemplateBlockBase):
    pass


class SessionTemplateBlockOut(SessionTemplateBlockBase):
    id: int
    template_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Template Exercise Schemas
class SessionTemplateExerciseBase(BaseModel):
    exercise_id: int
    order_in_block: int
    set_type: SetTypeEnum = SetTypeEnum.single_set
    planned_sets: Optional[int] = None
    planned_reps: Optional[str] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    effort_character: Optional[EffortCharacterEnum] = None
    effort_value: Optional[float] = None
    notes: Optional[str] = None


class SessionTemplateExerciseCreate(SessionTemplateExerciseBase):
    pass


class SessionTemplateExerciseOut(SessionTemplateExerciseBase):
    id: int
    template_block_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Block Schemas
class SessionBlockBase(BaseModel):
    block_type_id: int
    order_in_session: int
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    actual_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    notes: Optional[str] = None


class SessionBlockCreate(SessionBlockBase):
    pass


class SessionBlockUpdate(BaseModel):
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    actual_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
    estimated_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    notes: Optional[str] = None


class SessionBlockOut(SessionBlockBase):
    id: int
    training_session_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Block Exercise Schemas
class SessionBlockExerciseBase(BaseModel):
    exercise_id: int
    order_in_block: int
    set_type: SetTypeEnum = SetTypeEnum.single_set
    superset_group_id: Optional[int] = None
    dropset_sequence: Optional[int] = None
    planned_sets: Optional[int] = None
    planned_reps: Optional[str] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    effort_character: Optional[EffortCharacterEnum] = None
    effort_value: Optional[float] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[str] = None
    actual_weight: Optional[float] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    actual_effort_value: Optional[float] = None
    notes: Optional[str] = None


class SessionBlockExerciseCreate(SessionBlockExerciseBase):
    pass


class SessionBlockExerciseUpdate(BaseModel):
    planned_sets: Optional[int] = None
    planned_reps: Optional[str] = None
    planned_weight: Optional[float] = None
    planned_duration: Optional[int] = None
    planned_distance: Optional[float] = None
    planned_rest: Optional[int] = None
    effort_character: Optional[EffortCharacterEnum] = None
    effort_value: Optional[float] = None
    actual_sets: Optional[int] = None
    actual_reps: Optional[str] = None
    actual_weight: Optional[float] = None
    actual_duration: Optional[int] = None
    actual_distance: Optional[float] = None
    actual_rest: Optional[int] = None
    actual_effort_value: Optional[float] = None
    notes: Optional[str] = None


class SessionBlockExerciseOut(SessionBlockExerciseBase):
    id: int
    session_block_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Session Summary Schemas
class SessionSummaryOut(BaseModel):
    total_sets: int
    estimated_duration: int  # in minutes
    blocks: int
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    actual_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
