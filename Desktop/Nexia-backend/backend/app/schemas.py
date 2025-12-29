from datetime import date, datetime, time
from enum import Enum
from typing import Dict, List, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_serializer,
    model_validator,
)

# Import enums from models
from .db.models import (
    EffortCharacterEnum,
    ExperienceEnum,
    GenderEnum,
    MilestoneTypeEnum,
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
    # Exact training frequency
    exact_training_frequency: Optional[int] = Field(
        None, ge=1, le=7, description="Exact number of training days per week (1-7)"
    )
    # Specific training days
    training_days: Optional[List[str]] = Field(
        None,
        description=(
            "Optional: Specific days of the week to train "
            "(e.g., ['Monday', 'Wednesday', 'Friday'])"
        ),
    )

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

    # Somatotype (Heath-Carter method, values 1.0-7.0 for each component)
    # Auto-calculated from anthropometric data, but can be manually overridden
    somatotype_endomorph: Optional[float] = Field(
        None, description="Endomorphic component of somatotype (1-7)"
    )
    somatotype_mesomorph: Optional[float] = Field(
        None, description="Mesomorphic component of somatotype (1-7)"
    )
    somatotype_ectomorph: Optional[float] = Field(
        None, description="Ectomorphic component of somatotype (1-7)"
    )

    @field_validator(
        "somatotype_endomorph",
        "somatotype_mesomorph",
        "somatotype_ectomorph",
        mode="before",
    )
    @classmethod
    def validate_somatotype_range(cls, v):
        """Validate somatotype values are in range 1.0-7.0, or None."""
        if v is not None:
            if not isinstance(v, (int, float)):
                raise ValueError("Somatotype value must be a number")
            if not (1.0 <= float(v) <= 7.0):
                raise ValueError("Somatotype values must be between 1.0 and 7.0")
        return v

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

    @field_validator("training_days")
    @classmethod
    def validate_training_days(cls, v):
        """Validate training days are valid day names."""
        if v is None:
            return v
        valid_days = {
            "Monday",
            "Tuesday",
            "Wednesday",
            "Thursday",
            "Friday",
            "Saturday",
            "Sunday",
            "Mon",
            "Tue",
            "Wed",
            "Thu",
            "Fri",
            "Sat",
            "Sun",
        }
        for day in v:
            if day not in valid_days and day.lower() not in [
                d.lower() for d in valid_days
            ]:
                raise ValueError(
                    f"Invalid day name: {day}. Must be one of: "
                    f"Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, Sunday "
                    f"(or Mon, Tue, Wed, Thu, Fri, Sat, Sun)"
                )
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
    # Exact training frequency
    exact_training_frequency: Optional[int] = Field(
        None, ge=1, le=7, description="Exact number of training days per week (1-7)"
    )
    # Specific training days
    training_days: Optional[List[str]] = Field(
        None,
        description=(
            "Optional: Specific days of the week to train "
            "(e.g., ['Monday', 'Wednesday', 'Friday'])"
        ),
    )

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


class ClientPreviewResponse(BaseModel):
    """Response for client preview endpoint (calculated values only)"""

    bmi: Optional[float] = Field(
        None,
        description=(
            "Calculated BMI (Body Mass Index) - only if weight and height provided"
        ),
    )
    somatotype: Dict[str, Optional[float]] = Field(
        ...,
        description="Calculated somatotype values (endomorph, mesomorph, ectomorph)",
    )


class ClientProfileOut(ClientProfileBase):
    id: int
    fecha_alta: date
    imc: Optional[float] = None
    # Override mail to allow placeholder emails (e.g., deleted_*@deleted.local)
    mail: str  # Changed from EmailStr to str to allow placeholder emails
    # Override altura to remove validation
    # (output schema should accept any value from DB)
    altura: Optional[float] = (
        None  # Accept both meters and centimeters from old records
    )
    model_config = {"from_attributes": True}

    @field_validator("altura", mode="before")
    @classmethod
    def validate_height_output_before(cls, v):
        """Convert height from meters to centimeters if needed.

        Old records have height in meters (1.75, 1.78), new records in cm (175, 178).
        Convert meters to cm so parent validator passes.
        """
        if v is not None:
            # If value is less than 3, assume it's in meters and convert to cm
            if v < 3:
                return v * 100
        return v


class ClientListResponse(BaseModel):
    items: List[ClientProfileOut]
    total: int
    page: int
    page_size: int
    has_more: bool
    model_config = {"from_attributes": True}


# Enhanced Client List with Fatigue and Adherence
class ClientListItem(BaseModel):
    """Client list item with fatigue and adherence for dashboard view"""

    id: int
    nombre: str
    apellidos: str
    mail: str
    fatigue_level: Optional[str] = (
        None  # "Perfect", "Exhausted", "Slightly Tired", "Very Tired"
    )
    fatigue_level_numeric: Optional[int] = None  # 1-10 scale for sorting
    adherence_percentage: Optional[float] = None  # 0-100
    model_config = {"from_attributes": True}


class ClientListWithMetricsResponse(BaseModel):
    """Client list response with fatigue and adherence metrics"""

    items: List[ClientListItem]
    total: int
    page: int
    page_size: int
    has_more: bool


# Recent Activity Feed
class RecentActivityItem(BaseModel):
    """Single activity item in the feed"""

    id: int
    type: str  # "session_completed", "client_added", "session_scheduled",
    # "goal_achieved", "test_completed"
    actor_name: str  # Client or trainer name
    description: str  # Human-readable description
    timestamp: datetime
    client_id: Optional[int] = None
    session_id: Optional[int] = None
    icon: Optional[str] = None  # Icon identifier for UI


class RecentActivityResponse(BaseModel):
    """Recent activity feed response"""

    items: List[RecentActivityItem]
    total: int


class ClientImprovementStats(BaseModel):
    average: float
    trend: str
    sample_size: Optional[int] = None
    source: str = "mock"
    note: Optional[str] = None


class ClientSatisfactionStats(BaseModel):
    rating: float
    total_reviews: int
    trend: str
    source: str = "mock"
    note: Optional[str] = None


# Client Rating Schemas
class ClientRatingBase(BaseModel):
    client_id: int
    trainer_id: Optional[int] = None
    rating: int  # 1-5 scale
    comment: Optional[str] = None
    rating_type: str = "general"  # "general", "session", "program", "trainer"
    session_id: Optional[int] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v

    @field_validator("rating_type")
    @classmethod
    def validate_rating_type(cls, v):
        allowed_types = ["general", "session", "program", "trainer"]
        if v not in allowed_types:
            raise ValueError(f"rating_type must be one of {allowed_types}")
        return v


class ClientRatingCreate(ClientRatingBase):
    pass


class ClientRatingUpdate(BaseModel):
    rating: Optional[int] = None
    comment: Optional[str] = None

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v):
        if v is not None and (v < 1 or v > 5):
            raise ValueError("Rating must be between 1 and 5")
        return v


class ClientRatingOut(ClientRatingBase):
    id: int
    rating_date: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class PlanAdherenceStats(BaseModel):
    adherence_percentage: float
    trend: str
    aligned_plans: Optional[int] = None
    total_plans: Optional[int] = None
    source: str = "mock"
    note: Optional[str] = None


class ClientProgressCategoryStats(BaseModel):
    on_track: int
    behind_schedule: int
    need_attention: int
    overall_percentage: float
    updated_at: datetime
    source: str = "mock"
    note: Optional[str] = None


class BillingStatBucket(BaseModel):
    label: str
    revenue: float
    clients: int
    growth: float
    currency: str = "EUR"


class BillingStatsResponse(BaseModel):
    period: str
    items: List[BillingStatBucket]
    source: str = "mock"
    note: Optional[str] = None


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
    # Override mail to allow placeholder emails (e.g., deleted_*@deleted.local)
    mail: str  # Changed from EmailStr to str to allow placeholder emails
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
    laterality: Optional[str] = None  # bilateral, unilateral, alternating
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

    @field_validator("tipo")
    @classmethod
    def validate_tipo(cls, v):
        """Validate exercise category (tipo) - must be one of:
        monoarticular, multiarticular, complex
        """
        if not v:
            raise ValueError("Exercise type (tipo) cannot be empty")
        v_clean = v.strip().lower()
        valid_types = ["monoarticular", "multiarticular", "complex"]
        if v_clean not in valid_types:
            raise ValueError(
                f"Exercise type must be one of: {', '.join(valid_types)}. Got: {v}"
            )
        # Return the lowercase value for consistency
        return v_clean

    @field_validator("laterality")
    @classmethod
    def validate_laterality(cls, v):
        """Validate laterality - must be one of: bilateral, unilateral, alternating"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_laterality = ["bilateral", "unilateral", "alternating"]
        if v_clean not in valid_laterality:
            raise ValueError(
                f"Laterality must be one of: {', '.join(valid_laterality)}. Got: {v}"
            )
        return v_clean


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
    laterality: Optional[str] = None
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
    fecha_inicio_prueba: Optional[date] = None
    peso: Optional[float] = None
    altura: Optional[float] = None  # Height in centimeters (same as Onboarding)
    imc: Optional[float] = None
    notas: Optional[str] = None

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

    # Body Composition Calculated Fields (read-only, calculated by backend)
    body_fat_percentage: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    fat_free_mass_kg: Optional[float] = None

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

    @field_validator("altura")
    @classmethod
    def validate_height(cls, v):
        """Validate height in centimeters (same as Onboarding)"""
        if v is not None and (v < 100 or v > 250):
            raise ValueError("Height must be between 100 and 250 cm")
        return v

    @field_validator("peso")
    @classmethod
    def validate_weight(cls, v):
        """Validate weight in kilograms"""
        if v is not None and (v < 20 or v > 300):
            raise ValueError("Weight must be between 20 and 300 kg")
        return v

    @model_validator(mode="after")
    def calculate_bmi(self):
        """Calculate BMI from weight (kg) and height (cm)"""
        # Height is in cm, convert to meters for BMI calculation
        if self.peso is not None and self.altura is not None:
            altura_m = self.altura / 100  # Convert cm to meters
            bmi = self.peso / (altura_m**2)
            self.imc = round(bmi, 2)  # Store with 2 decimal places
        elif self.peso is not None and self.altura is None:
            # If only weight is provided, clear BMI (can't calculate)
            self.imc = None
        elif self.altura is not None and self.peso is None:
            # If only height is provided, clear BMI (can't calculate)
            self.imc = None

        # Validate BMI range
        if self.imc is not None and (self.imc < 10 or self.imc > 60):
            raise ValueError("BMI must be between 10 and 60")
        return self


class ClientProgressCreate(ClientProgressBase):
    pass


class ClientProgressUpdate(BaseModel):
    fecha_inicio_prueba: Optional[date] = None
    peso: Optional[float] = None
    altura: Optional[float] = None  # Height in centimeters (same as Onboarding)
    imc: Optional[float] = None
    notas: Optional[str] = None

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

    @field_validator("peso")
    @classmethod
    def validate_weight(cls, v):
        if v is not None and (v < 20 or v > 300):
            raise ValueError("Weight must be between 20 and 300 kg")
        return v

    @field_validator("altura")
    @classmethod
    def validate_height(cls, v):
        """Validate height in centimeters (same as Onboarding)"""
        if v is not None and (v < 100 or v > 250):
            raise ValueError("Height must be between 100 and 250 cm")
        return v

    @model_validator(mode="after")
    def calculate_bmi(self):
        """Calculate BMI from weight (kg) and height (cm) if both provided"""
        # Height is in cm, convert to meters for BMI calculation
        if self.peso is not None and self.altura is not None:
            altura_m = self.altura / 100  # Convert cm to meters
            bmi = self.peso / (altura_m**2)
            self.imc = round(bmi, 2)
        elif self.peso is not None and self.altura is None:
            self.imc = None
        elif self.altura is not None and self.peso is None:
            self.imc = None

        # Validate BMI range
        if self.imc is not None and (self.imc < 10 or self.imc > 60):
            raise ValueError("BMI must be between 10 and 60")
        return self

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


class ClientProgressOut(BaseModel):
    id: int
    client_id: int
    fecha_registro: date
    fecha_inicio_prueba: Optional[date] = None
    peso: Optional[float] = None
    altura: Optional[float] = None  # Height in centimeters
    unidad: Optional[str] = None
    imc: Optional[float] = None
    notas: Optional[str] = None

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

    # Body Composition Calculated Fields
    body_fat_percentage: Optional[float] = None
    muscle_mass_kg: Optional[float] = None
    fat_free_mass_kg: Optional[float] = None

    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)

    @model_serializer(mode="plain")
    def serialize_model(self):
        """Custom serializer that safely excludes 'client' relationship.

        Uses mode='plain' to manually build dict from model fields only,
        avoiding any SQLAlchemy relationship access.
        """
        # Build dict manually from model fields only
        result = {}
        for field_name in self.model_fields.keys():
            if field_name != "client":  # Explicitly exclude relationship
                try:
                    value = object.__getattribute__(self, field_name)
                    result[field_name] = value
                except (AttributeError, Exception):
                    # Skip if field doesn't exist or can't be accessed
                    pass
        return result


# Training Plan Schemas
# Training Plan Template Schemas
class TrainingPlanTemplateBase(BaseModel):
    trainer_id: int
    name: str
    description: Optional[str] = None
    goal: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_duration_weeks: Optional[int] = None
    # Generic plan duration support
    duration_value: Optional[int] = Field(
        None, ge=1, description="Duration value (e.g., 3)"
    )
    duration_unit: Optional[str] = Field(
        None, description="Duration unit: 'days', 'weeks', or 'months'"
    )
    # Folder hierarchy and classification (Requirement A)
    folder_name: Optional[str] = Field(
        None, max_length=100, description="Folder/organization by objective"
    )
    level: Optional[str] = Field(
        None,
        description="Level classification: 'beginner', 'intermediate', or 'advanced'",
    )
    training_days_per_week: Optional[int] = Field(
        None, ge=1, le=7, description="Number of training days per week"
    )
    # Generic plan flag (Requirement C)
    is_generic: bool = Field(
        default=False,
        description="If True, template includes training sessions (generic plan)",
    )

    @field_validator("duration_unit")
    @classmethod
    def validate_duration_unit(cls, v):
        if v is not None and v not in ["days", "weeks", "months"]:
            raise ValueError("duration_unit must be 'days', 'weeks', or 'months'")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        if v is not None and v not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("level must be 'beginner', 'intermediate', or 'advanced'")
        return v


class TrainingPlanTemplateCreate(TrainingPlanTemplateBase):
    pass


class TrainingPlanTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    estimated_duration_weeks: Optional[int] = None
    is_public: Optional[bool] = None
    # Generic plan duration support
    duration_value: Optional[int] = Field(
        None, ge=1, description="Duration value (e.g., 3)"
    )
    duration_unit: Optional[str] = Field(
        None, description="Duration unit: 'days', 'weeks', or 'months'"
    )
    # Folder hierarchy and classification (Requirement A)
    folder_name: Optional[str] = Field(
        None, max_length=100, description="Folder/organization by objective"
    )
    level: Optional[str] = Field(
        None,
        description="Level classification: 'beginner', 'intermediate', or 'advanced'",
    )
    training_days_per_week: Optional[int] = Field(
        None, ge=1, le=7, description="Number of training days per week"
    )
    # Generic plan flag (Requirement C)
    is_generic: Optional[bool] = Field(
        None,
        description="If True, template includes training sessions (generic plan)",
    )

    @field_validator("duration_unit")
    @classmethod
    def validate_duration_unit(cls, v):
        if v is not None and v not in ["days", "weeks", "months"]:
            raise ValueError("duration_unit must be 'days', 'weeks', or 'months'")
        return v

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        if v is not None and v not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("level must be 'beginner', 'intermediate', or 'advanced'")
        return v


class TrainingPlanTemplateOut(TrainingPlanTemplateBase):
    id: int
    usage_count: int
    success_rate: Optional[float] = None
    is_template: bool
    is_public: bool
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


# Training Plan Instance Schemas
class TrainingPlanInstanceBase(BaseModel):
    template_id: Optional[int] = None
    source_plan_id: Optional[int] = None
    client_id: int
    trainer_id: int
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    goal: str
    status: str = "active"
    customizations: Optional[Dict] = None


class TrainingPlanInstanceCreate(TrainingPlanInstanceBase):
    pass


class TrainingPlanInstanceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    customizations: Optional[Dict] = None


class TrainingPlanInstanceOut(TrainingPlanInstanceBase):
    id: int
    assigned_at: datetime
    created_at: datetime
    updated_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}


# Training Plan Schemas (Modified)
class TrainingPlanBase(BaseModel):
    trainer_id: int
    client_id: Optional[int] = None  # Made optional
    name: str
    description: Optional[str] = None
    start_date: date
    end_date: date
    goal: str
    status: str = "active"
    tags: Optional[List[str]] = None


class TrainingPlanCreate(TrainingPlanBase):
    pass


class TrainingPlanUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    goal: Optional[str] = None
    status: Optional[str] = None
    tags: Optional[List[str]] = None


class TrainingPlanOut(TrainingPlanBase):
    id: int
    template_id: Optional[int] = None
    is_template: bool = False
    can_be_reused: bool = True
    was_converted_to_template: bool = False
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Milestone Schemas
class MilestoneBase(BaseModel):
    title: str
    milestone_date: date
    type: MilestoneTypeEnum = MilestoneTypeEnum.custom
    notes: Optional[str] = None
    importance: str = "medium"  # low, medium, high
    reminder_offset_days: Optional[int] = None
    done: bool = False

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError("importance must be low, medium, or high")
        return v


class MilestoneCreate(MilestoneBase):
    training_plan_id: Optional[int] = None  # Will be set from path


class MilestoneUpdate(BaseModel):
    title: Optional[str] = None
    milestone_date: Optional[date] = None
    type: Optional[MilestoneTypeEnum] = None
    notes: Optional[str] = None
    importance: Optional[str] = None
    reminder_offset_days: Optional[int] = None
    done: Optional[bool] = None

    @field_validator("importance")
    @classmethod
    def validate_importance(cls, v):
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError("importance must be low, medium, or high")
        return v


class MilestoneOut(MilestoneBase):
    id: int
    training_plan_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class TrainingPlanDistributionItem(BaseModel):
    name: str
    percentage: float


class TrainingLoadSummary(BaseModel):
    volume_level: float
    intensity_level: float


class MonthlyTrainingProgress(BaseModel):
    month: int  # 1-12
    qualities: List[TrainingPlanDistributionItem]
    volume_level: float
    intensity_level: float


class TrainingPlanSummaryStats(BaseModel):
    total_sessions_planned: int
    sessions_completed: int
    adherence_rate: float
    narrative: str


class ClientTrainingPlanSummary(BaseModel):
    client_id: int
    year: int
    has_active_plan: bool
    plan_name: Optional[str] = None
    plan_goal: Optional[str] = None
    distribution: List[TrainingPlanDistributionItem]
    physical_qualities: List[TrainingPlanDistributionItem]
    training_load: TrainingLoadSummary
    yearly_progression: List[MonthlyTrainingProgress]
    summary: TrainingPlanSummaryStats
    milestones: List[MilestoneOut] = Field(default_factory=list)


class TrainingPlanQualityAverage(BaseModel):
    name: str
    planned_percentage: float
    actual_percentage: float
    status: str  # "on_track" (green) or "below_target" (red)


class PlannedVsActualComparison(BaseModel):
    planned_volume: float
    actual_volume: float
    volume_status: str  # "on_track" (green) or "below_target" (red)
    planned_intensity: float
    actual_intensity: float
    intensity_status: str  # "on_track" (green) or "below_target" (red)
    qualities: List[TrainingPlanQualityAverage]


class MonthlyWeekBreakdown(BaseModel):
    week: int
    start_date: date
    end_date: date
    qualities: List[TrainingPlanDistributionItem]
    volume_level: float
    intensity_level: float


class TrainingPlanMonthlySummary(BaseModel):
    client_id: int
    year: int
    month: int
    has_active_plan: bool
    plan_name: Optional[str] = None
    plan_goal: Optional[str] = None
    distribution: List[TrainingPlanDistributionItem]
    physical_qualities: List[TrainingPlanDistributionItem]
    training_load: TrainingLoadSummary
    plan_alignment: float
    planned_vs_actual: PlannedVsActualComparison
    weeks: List[MonthlyWeekBreakdown]
    summary: TrainingPlanSummaryStats


class WeeklySessionEntry(BaseModel):
    session_id: int
    session_date: date
    session_name: str
    session_type: Optional[str] = None
    status: str
    planned_volume: Optional[float] = None
    planned_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
    actual_intensity: Optional[float] = None


class DailyProgressionPoint(BaseModel):
    """Daily breakdown for weekly progression chart (Mon-Sun)"""

    day_name: str  # "Mon", "Tue", etc.
    date: date
    qualities: List[TrainingPlanDistributionItem]  # For stacked bars
    volume_level: float  # For volume line graph
    intensity_level: float  # For intensity line graph


class TrainingPlanWeeklySummary(BaseModel):
    client_id: int
    week_start: date
    week_end: date
    has_active_plan: bool
    plan_name: Optional[str] = None
    plan_goal: Optional[str] = None
    distribution: List[TrainingPlanDistributionItem]
    physical_qualities: List[TrainingPlanDistributionItem]
    training_load: TrainingLoadSummary
    plan_alignment: float
    daily_progression: List[DailyProgressionPoint]
    planned_vs_actual: PlannedVsActualComparison
    sessions: List[WeeklySessionEntry]
    summary: TrainingPlanSummaryStats


# Macrocycle Schemas
# Macrocycle Schemas (1 Macrocycle = 1 Year = 12 months)
class MacrocycleBase(BaseModel):
    training_plan_id: Optional[int] = None
    template_id: Optional[int] = None
    instance_id: Optional[int] = None
    name: str  # e.g., "2025"
    description: Optional[str] = None
    start_date: date  # First day of year (e.g., Jan 1)
    end_date: date  # Last day of year (e.g., Dec 31)
    focus: str
    # Coherence system fields
    physical_quality: Optional[str] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None
    volume_intensity_ratio: Optional[str] = None

    @model_validator(mode="after")
    def validate_calendar_year(self):
        """1 Macrocycle = 1 Year (365-366 days)"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
            days = (self.end_date - self.start_date).days + 1
            if days < 365 or days > 366:
                raise ValueError(
                    f"Macrocycle must be 1 year (365-366 days). Got {days} days"
                )
        return self


class MacrocycleCreate(MacrocycleBase):
    pass


class MacrocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    focus: Optional[str] = None
    volume_intensity_ratio: Optional[str] = None
    # Coherence system fields (bottom-up planning support)
    physical_quality: Optional[str] = None
    volume: Optional[float] = Field(None, ge=1.0, le=10.0)
    intensity: Optional[float] = Field(None, ge=1.0, le=10.0)


class MacrocycleOut(MacrocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Mesocycle Schemas (1 Mesocycle = 1 Calendar Month)
class MesocycleBase(BaseModel):
    macrocycle_id: int
    name: str  # e.g., "January 2025"
    description: Optional[str] = None
    start_date: date  # First day of month (e.g., Jan 1)
    end_date: date  # Last day of month (e.g., Jan 31)
    duration_weeks: int = 4  # ~4 weeks per month
    primary_focus: str
    secondary_focus: Optional[str] = None
    # Coherence system fields
    physical_quality: Optional[str] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None
    target_volume: Optional[str] = None
    target_intensity: Optional[str] = None

    @model_validator(mode="after")
    def validate_calendar_month(self):
        """1 Mesocycle = 1 Calendar Month (28-31 days)"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
            days = (self.end_date - self.start_date).days + 1
            if days < 28 or days > 31:
                raise ValueError(
                    f"Mesocycle must be 1 calendar month (28-31 days). Got {days} days"
                )
        return self


class MesocycleCreate(MesocycleBase):
    macrocycle_id: Optional[int] = None


class MesocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    duration_weeks: Optional[int] = None
    primary_focus: Optional[str] = None
    secondary_focus: Optional[str] = None
    target_volume: Optional[str] = None
    target_intensity: Optional[str] = None
    # Coherence system fields (bottom-up planning support)
    physical_quality: Optional[str] = None
    volume: Optional[float] = Field(None, ge=1.0, le=10.0)
    intensity: Optional[float] = Field(None, ge=1.0, le=10.0)
    # Bottom-up propagation: recalculate parent macrocycle from all mesocycles
    propagate_up: bool = False


class MesocycleOut(MesocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Microcycle Schemas (1 Microcycle = 1 Week = 7 days)
class MicrocycleBase(BaseModel):
    mesocycle_id: int
    name: str  # e.g., "Week 1", "Jan 6-12"
    description: Optional[str] = None
    start_date: date  # First day of week (e.g., Monday)
    end_date: date  # Last day of week (e.g., Sunday)
    duration_days: int = 7  # Always 7 days
    training_frequency: int = Field(default=3, ge=1, le=7)  # Sessions per week
    deload_week: bool = False
    notes: Optional[str] = None
    # Coherence system fields
    physical_quality: Optional[str] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None

    @model_validator(mode="after")
    def validate_calendar_week(self):
        """1 Microcycle = 1 Week = exactly 7 days"""
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("end_date must be after start_date")
            days = (self.end_date - self.start_date).days + 1
            if days != 7:
                raise ValueError(
                    f"Microcycle must be exactly 7 days (1 week). Got {days} days"
                )
        if self.duration_days != 7:
            raise ValueError("duration_days must be 7 (1 week)")
        return self


class MicrocycleCreate(MicrocycleBase):
    mesocycle_id: Optional[int] = None


class MicrocycleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    end_date: Optional[date] = None
    # duration_days is fixed to 7, not editable
    training_frequency: Optional[int] = Field(None, ge=1, le=7)
    deload_week: Optional[bool] = None
    notes: Optional[str] = None
    # Coherence system fields
    physical_quality: Optional[str] = None
    volume: Optional[float] = Field(None, ge=1.0, le=10.0)
    intensity: Optional[float] = Field(None, ge=1.0, le=10.0)
    propagate_up: bool = False


class MicrocycleOut(MicrocycleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Aggregated cycles response
class AllCyclesResponse(BaseModel):
    macrocycles: List[MacrocycleOut]
    mesocycles: List[MesocycleOut]
    microcycles: List[MicrocycleOut]


class BatchCyclesRequest(BaseModel):
    plan_ids: List[int]


class BatchCyclesResponse(BaseModel):
    cycles: dict[int, AllCyclesResponse]  # plan_id -> cycles
    errors: dict[int, str] = {}  # plan_id -> error message


# Training Plan Alignment Schemas
class CycleAlignmentPoint(BaseModel):
    """Single point in alignment graph: physical quality, volume, intensity."""

    cycle_id: int
    cycle_type: str  # "macrocycle", "mesocycle", "microcycle"
    cycle_name: str
    date: date
    physical_quality: Optional[str] = None
    volume: Optional[float] = None  # 1-10
    intensity: Optional[float] = None  # 1-10


class ParentCycleValues(BaseModel):
    """Parent cycle values shown when planning at child level"""

    physical_quality: Optional[str] = None
    volume: Optional[float] = None
    intensity: Optional[float] = None
    cycle_name: str
    start_date: date
    end_date: date


class TrainingPlanAlignmentOut(BaseModel):
    """Alignment data for training plan showing parent values and all cycles"""

    plan_id: int
    plan_name: str
    # Parent values for monthly planning (from yearly/macrocycle)
    yearly_values: Optional[ParentCycleValues] = None
    # Parent values for weekly planning (from monthly/mesocycle)
    monthly_values: Optional[ParentCycleValues] = None
    # All cycles for graph visualization
    alignment_graph: List[CycleAlignmentPoint]


# Planning Endpoints Schemas
class PlanningCycleItem(BaseModel):
    """Single cycle in planning view with editable fields"""

    cycle_id: int
    cycle_type: str  # "macrocycle", "mesocycle", "microcycle"
    name: str
    start_date: date
    end_date: date
    physical_quality: Optional[str] = None
    volume: Optional[float] = None  # 1-10
    intensity: Optional[float] = None  # 1-10
    has_values: bool  # True if volume/intensity are set
    inherited: bool  # True if values are inherited from parent


class PlanningDistributionItem(BaseModel):
    """Physical quality distribution item"""

    name: str
    percentage: float  # 0-100
    cycle_ids: List[int]  # IDs of cycles with this quality


class PlanningLoadSummary(BaseModel):
    """Volume and intensity summary"""

    volume_level: float  # 1-10
    intensity_level: float  # 1-10
    cycle_ids: List[int]  # IDs of cycles included in calculation


class PlanningYearlyResponse(BaseModel):
    """Yearly planning view"""

    plan_id: int
    plan_name: str
    year: int
    distribution: List[PlanningDistributionItem]
    training_load: PlanningLoadSummary
    cycles: List[PlanningCycleItem]  # All macrocycles for the year
    monthly_progression: List[Dict]  # Month-by-month breakdown


class PlanningMonthlyResponse(BaseModel):
    """Monthly planning view"""

    plan_id: int
    plan_name: str
    year: int
    month: int
    distribution: List[PlanningDistributionItem]
    training_load: PlanningLoadSummary
    cycles: List[PlanningCycleItem]  # All mesocycles for the month
    weekly_progression: List[Dict]  # Week-by-week breakdown


class PlanningWeeklyResponse(BaseModel):
    """Weekly planning view"""

    plan_id: int
    plan_name: str
    week_start: date
    week_end: date
    distribution: List[PlanningDistributionItem]
    training_load: PlanningLoadSummary
    cycles: List[PlanningCycleItem]  # All microcycles for the week
    daily_progression: List[Dict]  # Day-by-day breakdown


class DistributionUpdateItem(BaseModel):
    """Single physical quality distribution update"""

    name: str
    percentage: float  # 0-100


class DistributionUpdateRequest(BaseModel):
    """Request to update physical qualities distribution"""

    cycle_ids: List[int]  # IDs of cycles to update
    distribution: List[DistributionUpdateItem]  # Must sum to 100%
    cascade: bool = True  # If True, update child cycles too

    @field_validator("distribution")
    def validate_distribution_sum(cls, v):
        total = sum(item.percentage for item in v)
        if abs(total - 100.0) > 0.01:  # Allow small floating point errors
            raise ValueError(f"Distribution percentages must sum to 100%, got {total}%")
        return v


class LoadUpdateRequest(BaseModel):
    """Request to update volume/intensity"""

    cycle_ids: List[int]  # IDs of cycles to update
    physical_quality: Optional[str] = None  # Optional: filter by quality
    volume: Optional[float] = Field(None, ge=1.0, le=10.0)
    intensity: Optional[float] = Field(None, ge=1.0, le=10.0)
    cascade: bool = True  # If True, update child cycles too


# Bottom-Up Sync Schemas
class CycleRecalculationResult(BaseModel):
    """Result of recalculating a single cycle from its children"""

    cycle_id: int
    cycle_type: str  # "mesocycle" or "macrocycle"
    cycle_name: str
    previous_volume: Optional[float] = None
    previous_intensity: Optional[float] = None
    new_volume: Optional[float] = None
    new_intensity: Optional[float] = None
    children_count: int
    changed: bool


class BottomUpSyncResponse(BaseModel):
    """Response from bottom-up sync operation"""

    plan_id: int
    mesocycles_updated: int
    macrocycles_updated: int
    total_changes: int
    recalculations: List[CycleRecalculationResult]
    message: str


# Scheduling Schemas
class TrainerAvailabilityBase(BaseModel):
    trainer_id: int
    day_of_week: int  # 0=Monday, 1=Tuesday, ..., 6=Sunday
    start_time: time  # e.g., 09:00
    end_time: time  # e.g., 17:00
    is_recurring: bool = True
    specific_date: Optional[date] = None


class TrainerAvailabilityCreate(TrainerAvailabilityBase):
    pass


class TrainerAvailabilityUpdate(BaseModel):
    day_of_week: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    is_recurring: Optional[bool] = None
    specific_date: Optional[date] = None
    is_active: Optional[bool] = None


class TrainerAvailabilityOut(TrainerAvailabilityBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


class ScheduledSessionBase(BaseModel):
    trainer_id: int
    client_id: int
    scheduled_date: date
    start_time: time
    end_time: time
    duration_minutes: int
    session_type: str  # "training", "consultation", "assessment"
    notes: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class ScheduledSessionCreate(ScheduledSessionBase):
    pass


class ScheduledSessionUpdate(BaseModel):
    scheduled_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_minutes: Optional[int] = None
    session_type: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    meeting_link: Optional[str] = None


class ScheduledSessionOut(ScheduledSessionBase):
    id: int
    status: str
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class ConflictCheckRequest(BaseModel):
    trainer_id: int
    scheduled_date: date
    start_time: time
    end_time: time
    exclude_session_id: Optional[int] = None  # For updates


class ConflictCheckResponse(BaseModel):
    has_conflict: bool
    conflicts: List[ScheduledSessionOut] = []
    available: bool


class AvailableSlotsRequest(BaseModel):
    trainer_id: int
    date: date


class AvailableSlot(BaseModel):
    start_time: time
    end_time: time
    duration_minutes: int


class AvailableSlotsResponse(BaseModel):
    date: date
    available_slots: List[AvailableSlot]


# Report Generation Schemas
class ReportType(str, Enum):
    client_progress = "client_progress"
    training_summary = "training_summary"
    daily_coherence = "daily_coherence"
    billing_summary = "billing_summary"
    attendance_report = "attendance_report"


class ReportRequest(BaseModel):
    report_type: ReportType
    client_id: Optional[int] = None
    trainer_id: Optional[int] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    format: str = "json"  # "json" or "pdf"


class ReportResponse(BaseModel):
    report_id: str
    report_type: str
    generated_at: datetime
    download_url: Optional[str] = None
    format: str  # "json" or "pdf"
    data: Optional[Dict] = None


# Metrics Schemas (Training Load & Planning)


# Strength Load Calculation
class StrengthIntensityIn(BaseModel):
    """Intensity input for strength training - one of RIR, %1RM, or RPE."""

    method: str  # "rir", "percent_1rm", "rpe"
    value: float  # RIR (0-5), %1RM (65-100), or RPE (6-10)

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        if v not in ["rir", "percent_1rm", "rpe"]:
            raise ValueError("method must be rir, percent_1rm, or rpe")
        return v


class StrengthIntensityOut(BaseModel):
    """Normalized intensity (0-1) from strength input."""

    intensidad_normalizada: float  # 0-1
    original_value: float
    method: str


class StrengthCalcIn(BaseModel):
    volumen_relativo: float  # 0-1 (series per muscle group per week, normalized)
    intensidad_method: str  # "rir", "percent_1rm", "rpe"
    intensidad_value: float  # RIR (0-5), %1RM (65-100), or RPE (6-10)

    @field_validator("volumen_relativo")
    @classmethod
    def _v01(cls, v):
        if v < 0 or v > 1:
            raise ValueError("volumen_relativo must be between 0 and 1")
        return v

    @field_validator("intensidad_method")
    @classmethod
    def _method(cls, v):
        if v not in ["rir", "percent_1rm", "rpe"]:
            raise ValueError("intensidad_method must be rir, percent_1rm, or rpe")
        return v


class StrengthCalcOut(BaseModel):
    carga_fuerza: float  # 0-100


# Intensity Normalization Helpers
class IntensityNormalizeIn(BaseModel):
    """Convert various intensity inputs to normalized 0-1 scale."""

    # Methods: rpe, percent_fcmax, percent_vvo2max, zona_aerobica, rir,
    # percent_1rm, percent_vmax, zona_anaerobica
    method: str
    value: float  # Value to normalize
    zona: Optional[str] = None  # Required for zona_aerobica or zona_anaerobica

    @field_validator("method")
    @classmethod
    def validate_method(cls, v):
        valid_methods = [
            "rpe",
            "percent_fcmax",
            "percent_vvo2max",
            "zona_aerobica",
            "rir",
            "percent_1rm",
            "percent_vmax",
            "zona_anaerobica",
        ]
        if v not in valid_methods:
            raise ValueError(f"method must be one of {valid_methods}")
        return v


class IntensityNormalizeOut(BaseModel):
    intensidad_normalizada: float  # 0-1
    original_value: float
    method: str
    zona: Optional[str] = None


class AerobicCalcIn(BaseModel):
    volumen_relativo: float  # 0-1
    intensidad_normalizada: float  # 0-1
    zona: str  # Z1-Z5

    @field_validator("volumen_relativo", "intensidad_normalizada")
    @classmethod
    def _v01(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Value must be between 0 and 1")
        return v

    @field_validator("zona")
    @classmethod
    def _vz(cls, v):
        if v not in ["Z1", "Z2", "Z3", "Z4", "Z5"]:
            raise ValueError("zona must be one of Z1-Z5")
        return v


class AerobicCalcOut(BaseModel):
    carga_aerobica: float  # 0-100


class AnaerobicCalcIn(BaseModel):
    volumen_relativo: float  # 0-1
    intensidad_normalizada: float  # 0-1
    k_densidad: float = 1.0  # 1.0-1.5 typical
    zona: str  # Z6 or Z7

    @field_validator("volumen_relativo", "intensidad_normalizada")
    @classmethod
    def _v01(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Value must be between 0 and 1")
        return v

    @field_validator("zona")
    @classmethod
    def _vz(cls, v):
        if v not in ["Z6", "Z7"]:
            raise ValueError("zona must be Z6 or Z7")
        return v


class AnaerobicCalcOut(BaseModel):
    carga_anaerobica: float  # 0-100


class CIDCalcIn(BaseModel):
    volumen_level: float  # 1.0-10.0 (accepts decimals like 6.5, 7.8)
    intensidad_level: float  # 1.0-10.0 (accepts decimals like 6.5, 7.8)
    # k_fase: Descarga=0.8, Acumulacion=1.0, Intensificacion=1.2, Competicion=1.3
    k_fase: float = 1.0
    # k_experiencia: Beginner=0.8, Intermediate=1.0, Advanced=1.1
    k_experiencia: float = 1.0
    p: float = 1.0  # Exponent 1.0-1.3 (higher = more weight on intensity)

    @field_validator("volumen_level", "intensidad_level")
    @classmethod
    def _levels(cls, v):
        if v < 1.0 or v > 10.0:
            raise ValueError("Levels must be between 1.0 and 10.0")
        return round(float(v), 1)  # Limit to 1 decimal for consistency

    @field_validator("k_experiencia")
    @classmethod
    def _k_exp_range(cls, v):
        if v < 0.7 or v > 1.2:
            raise ValueError("k_experiencia must be between 0.7 and 1.2")
        return v


class CIDCalcOut(BaseModel):
    cid_0_100: float


class DailyCIDItem(BaseModel):
    date: date
    input: CIDCalcIn
    cid_0_100: float


class DailyMetricsRequest(BaseModel):
    items: List[CIDCalcIn]
    start_date: date


class DailyMetricsResponse(BaseModel):
    days: List[DailyCIDItem]


# Aggregated per-trainer plans with cycles
class PlanWithCycles(BaseModel):
    plan: TrainingPlanOut
    macrocycles: List[MacrocycleOut]
    mesocycles: List[MesocycleOut]
    microcycles: List[MicrocycleOut]
    model_config = {"from_attributes": True}


class PlansWithCyclesResponse(BaseModel):
    items: List[PlanWithCycles]


# Aggregation Schemas (weekly/monthly) and Total Load
class WeeklyBucket(BaseModel):
    week_start: date  # Monday (ISO)
    cid_sum: float
    cid_avg: float


class WeeklyAggregateIn(BaseModel):
    items: List[CIDCalcIn]
    start_date: date


class WeeklyAggregateOut(BaseModel):
    buckets: List[WeeklyBucket]


class MonthlyBucket(BaseModel):
    month: int  # 1-12
    cid_sum: float
    cid_avg: float


class MonthlyAggregateIn(BaseModel):
    items: List[CIDCalcIn]
    start_date: date
    w_fase: Optional[float] = 1.0  # Phase weight for monthly aggregation (0.6-1.3)


class MonthlyAggregateOut(BaseModel):
    buckets: List[MonthlyBucket]


# Volume Normalization Helpers (BLOQUE 4 - VOLUMEN GLOBAL ADAPTATIVO)
class VolumeNormalizeIn(BaseModel):
    """Convert volume level (1-10) to actual units based on experience."""

    volume_level: int  # 1-10
    experience: str  # "beginner", "intermediate", "advanced"
    modality: str  # "strength", "aerobic", "anaerobic"
    weekly_objective: Optional[float] = None  # Required for aerobic/anaerobic

    @field_validator("volume_level")
    @classmethod
    def _level(cls, v):
        if v < 1 or v > 10:
            raise ValueError("volume_level must be 1-10")
        return v

    @field_validator("experience")
    @classmethod
    def _exp(cls, v):
        if v not in ["beginner", "intermediate", "advanced"]:
            raise ValueError("experience must be beginner, intermediate, or advanced")
        return v

    @field_validator("modality")
    @classmethod
    def _mod(cls, v):
        if v not in ["strength", "aerobic", "anaerobic"]:
            raise ValueError("modality must be strength, aerobic, or anaerobic")
        return v


class VolumeNormalizeOut(BaseModel):
    """Normalized volume output."""

    volume_level: int
    volumen_relativo: float  # 0-1 normalized value
    actual_units: (
        float  # Series per week (strength), minutes (aerobic), seconds (anaerobic)
    )
    unit_type: str  # "series", "minutes", "seconds"
    percentage_of_base: float  # Percentage of base range (20-100%)


class TotalLoadIn(BaseModel):
    c_fuerza: float  # 0-100
    c_aerobica: float  # 0-100
    c_anaerobica: float  # 0-100
    p_fuerza: float  # 0-1
    p_aerobica: float  # 0-1
    p_anaerobica: float  # 0-1

    @field_validator("c_fuerza", "c_aerobica", "c_anaerobica")
    @classmethod
    def _v0100(cls, v):
        if v < 0 or v > 100:
            raise ValueError("Load must be 0-100")
        return v

    @field_validator("p_fuerza", "p_aerobica", "p_anaerobica")
    @classmethod
    def _v01(cls, v):
        if v < 0 or v > 1:
            raise ValueError("Weight must be 0-1")
        return v


class TotalLoadOut(BaseModel):
    ct_0_100: float
    breakdown: dict


# Alert Threshold Detection Schemas
class ThresholdAlert(BaseModel):
    type: str  # "daily_high", "weekly_high", "consecutive_high"
    severity: str  # "medium", "high", "critical"
    message: str
    value: float
    threshold: float
    date: Optional[date] = None


class ThresholdCheckIn(BaseModel):
    items: List[CIDCalcIn]
    start_date: date
    daily_threshold: float = 80.0  # Alert if daily CID > this
    weekly_threshold: float = 450.0  # Alert if weekly CID sum > this
    consecutive_threshold: float = 70.0  # Alert if consecutive days > this
    consecutive_days: int = 3  # Number of consecutive days to check
    # Optional: create FatigueAlert records in database
    create_alerts: bool = False
    client_id: Optional[int] = None  # Required if create_alerts=True
    trainer_id: Optional[int] = None  # Required if create_alerts=True


class ThresholdCheckOut(BaseModel):
    alerts: List[ThresholdAlert]
    has_alerts: bool
    daily_max: float
    weekly_max: float
    consecutive_max: int
    created_fatigue_alerts: Optional[int] = (
        None  # Count of FatigueAlert records created
    )


# Training Session Schemas
class TrainingSessionBase(BaseModel):
    microcycle_id: int
    client_id: int
    trainer_id: int
    session_date: Optional[date] = None  # Nullable for generic plans
    session_name: str
    session_type: str
    # Generic plan support
    training_day_number: Optional[int] = Field(
        None, ge=1, description="Day number for generic plans (Day 1, Day 2, etc.)"
    )
    is_generic_session: Optional[bool] = Field(
        default=False, description="True = day number, False = real date"
    )

    @field_validator("is_generic_session", mode="before")
    @classmethod
    def convert_none_to_false(cls, v):
        """Convert NULL from database to False"""
        return v if v is not None else False

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
    # Allow changing session date for drag-drop functionality
    session_date: Optional[date] = None
    training_day_number: Optional[int] = Field(
        None, ge=1, description="Day number for generic plans"
    )
    planned_duration: Optional[int] = None
    actual_duration: Optional[int] = None
    planned_intensity: Optional[float] = None
    planned_volume: Optional[float] = None
    actual_intensity: Optional[float] = None
    actual_volume: Optional[float] = None
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


class ClientFeedbackCreate(BaseModel):
    # training_session_id is set from URL, so make it optional here
    training_session_id: Optional[int] = None
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
    model_config = ConfigDict(from_attributes=True)

    @model_serializer(mode="plain")
    def serialize_model(self):
        """Custom serializer that safely excludes relationships.
        Uses mode='plain' to manually build dict from model fields only,
        avoiding any SQLAlchemy relationship access.
        """
        result = {}
        for field_name in self.model_fields.keys():
            if field_name not in ["client", "training_session"]:
                try:
                    value = object.__getattribute__(self, field_name)
                    result[field_name] = value
                except (AttributeError, Exception):
                    pass
        return result


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
    # overtraining/recovery/session_adjustment already existed; attendance and
    # plan_deviation extend this model to cover Adrián's Alerts section.
    # See _validate_alert_type for the full list of allowed values.
    alert_type: str
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
        valid_types = [
            "overtraining",
            "recovery_needed",
            "session_adjustment",
            "attendance",
            "plan_deviation",
        ]
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
    exercise_count: Optional[int] = None  # Number of exercises in template
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


# Daily Coherence Analytics Schemas
class SRPEPoint(BaseModel):
    """Single point in sRPE scatter plot"""

    prescribed_srpe: float  # X-axis: planned intensity (0-10)
    perceived_srpe: float  # Y-axis: perceived effort from feedback (0-10)
    session_date: date
    session_id: int


class WeeklyMonotonyStrain(BaseModel):
    """Weekly monotony and strain metrics"""

    week_start: date
    monotony: float  # Daily mean / Standard deviation
    strain: float  # Weekly load × Monotony
    weekly_load: float  # Sum of daily loads for the week
    cumulative_strain: float  # Running total of strain across weeks


class MonotonyStrainDataPoint(BaseModel):
    """Flexible monotony and strain metrics for any granularity"""

    period_start: date  # Start of the period (day/week/month/year)
    period_label: (
        str  # Human-readable label (e.g., "2025-01-15", "W3", "Jan 2025", "2025")
    )
    monotony: float  # Mean / Standard deviation
    strain: float  # Period load × Monotony
    period_load: float  # Sum of daily loads for the period
    cumulative_strain: float  # Running total of strain across periods


class DailyCoherenceKPIs(BaseModel):
    """KPI cards for Daily Coherence tab"""

    adherence_percentage: float  # (Completed / Planned) × 100
    average_srpe: float  # Average perceived sRPE
    monotony: float  # Current week monotony
    strain: float  # Current week strain


class DailyCoherenceAnalyticsOut(BaseModel):
    """Complete coherence analytics response"""

    client_id: int
    period_start: date
    period_end: date
    period_type: str  # "week", "month", "training_block", "year"
    kpis: DailyCoherenceKPIs
    adherence_data: List[Dict]  # For donut/bar chart: [{period: str, adherence: float}]
    srpe_scatter_data: List[SRPEPoint]  # For scatter plot
    monotony_strain_data: List[
        MonotonyStrainDataPoint
    ]  # For line/area chart (granularity depends on period_type)
    interpretive_summary: str  # Auto-generated text analysis
    key_recommendations: List[str]  # Actionable recommendations


# Physical Testing Schemas (Testing Tab)
class PhysicalTestBase(BaseModel):
    name: str
    category: str  # "strength", "power", "speed", "aerobic", "anaerobic", "mobility"
    description: Optional[str] = None
    unit: str  # "kg", "cm", "s", "ml/kg/min", "°"
    is_standard: bool = True
    default_frequency_weeks: Optional[int] = None
    formula: Optional[str] = None
    notes: Optional[str] = None


class PhysicalTestCreate(PhysicalTestBase):
    created_by_trainer_id: Optional[int] = None


class PhysicalTestUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    unit: Optional[str] = None
    default_frequency_weeks: Optional[int] = None
    formula: Optional[str] = None
    notes: Optional[str] = None


class PhysicalTestOut(PhysicalTestBase):
    id: int
    created_by_trainer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class PhysicalTestResultBase(BaseModel):
    client_id: int
    test_id: int
    trainer_id: int
    test_date: date
    value: float
    unit: str
    is_baseline: bool = False
    notes: Optional[str] = None
    surface: Optional[str] = None
    conditions: Optional[str] = None


class PhysicalTestResultCreate(PhysicalTestResultBase):
    pass


class PhysicalTestResultUpdate(BaseModel):
    test_date: Optional[date] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    is_baseline: Optional[bool] = None
    notes: Optional[str] = None
    surface: Optional[str] = None
    conditions: Optional[str] = None


class PhysicalTestResultOut(PhysicalTestResultBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class TestResultWithProgress(PhysicalTestResultOut):
    """Test result with progress calculations"""

    baseline_value: Optional[float] = None
    baseline_date: Optional[date] = None
    progress_percentage: Optional[float] = None  # % change from baseline
    trend: Optional[str] = None  # "improving", "stable", "declining"


class PhysicalQualityProfile(BaseModel):
    """Radar chart data for physical qualities"""

    strength: float  # 0-100 score
    power: float
    speed: float
    aerobic: float
    anaerobic: float
    mobility: float


class TestTrendPoint(BaseModel):
    """Single point in a test trend chart"""

    test_date: date
    value: float
    unit: str
    progress_percentage: Optional[float] = None
    test_name: str
    test_id: int


class RepetitionData(BaseModel):
    """Data for a single repetition in a test session"""

    repetition_number: int  # 1, 2, 3, etc.
    value: float
    unit: str


class FatigueAnalysis(BaseModel):
    """Fatigue analysis for tests with multiple repetitions"""

    best_value: float
    worst_value: float
    fatigue_index_percentage: float  # ((worst - best) / best) * 100
    acceptable_range: Optional[str] = None  # e.g., "acceptable range", "high fatigue"


class CategoryTrendData(BaseModel):
    """Trend data for a test category"""

    category: str
    test_name: str
    test_id: int
    trend_points: List[TestTrendPoint]
    baseline_value: Optional[float] = None
    baseline_date: Optional[date] = None
    test_frequency_weeks: Optional[int] = None  # Default frequency for this test
    latest_surface: Optional[str] = (
        None  # Surface from most recent test result (e.g., "Track", "Treadmill")
    )
    latest_repetitions: Optional[List[RepetitionData]] = (
        None  # For tests with multiple reps (e.g., RSA)
    )
    latest_fatigue_analysis: Optional[FatigueAnalysis] = (
        None  # Calculated from latest repetitions
    )


class BilateralComparisonPoint(BaseModel):
    """Bilateral comparison data for a joint"""

    joint: str  # e.g., "Ankle", "Knee", "Hip", "Shoulder", "Elbow"
    left_value: Optional[float] = None
    right_value: Optional[float] = None
    unit: str  # e.g., "°"


class ClientTestingSummary(BaseModel):
    """Summary of all test results for a client"""

    client_id: int
    physical_quality_profile: PhysicalQualityProfile
    latest_tests_by_category: Dict[str, Optional[TestResultWithProgress]]
    category_trends: List[CategoryTrendData]  # Trend data for charts
    upcoming_tests: List[Dict]  # Tests due for repetition
    profile_analysis: str  # Auto-generated analysis text
    bilateral_comparison: Optional[List[BilateralComparisonPoint]] = (
        None  # For mobility tests: joint ROM left vs right
    )


# =============================================================================
# GYM & EQUIPMENT INVENTORY SCHEMAS
# =============================================================================


class GymBase(BaseModel):
    name: str
    address: Optional[str] = None


class GymCreate(GymBase):
    pass


class GymUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None


class GymOut(GymBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# --- Trainer-Gym Assignment (many-to-many) ---


class TrainerGymAssign(BaseModel):
    """Assign a trainer to a gym"""

    trainer_id: int
    gym_id: int
    role: Optional[str] = None  # e.g., "employee", "contractor"


class TrainerGymOut(BaseModel):
    """Trainer-Gym relationship output"""

    trainer_id: int
    gym_id: int
    assigned_at: datetime
    role: Optional[str] = None
    is_active: bool
    model_config = {"from_attributes": True}


class InventoryItemBase(BaseModel):
    name: str
    quantity: int = 1
    condition: Optional[str] = None  # "New", "Worn", etc.
    is_available: bool = True


class InventoryItemCreate(InventoryItemBase):
    gym_id: Optional[int] = None
    trainer_id: Optional[int] = None


class InventoryItemUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    condition: Optional[str] = None
    is_available: Optional[bool] = None


class InventoryItemOut(InventoryItemBase):
    id: int
    gym_id: Optional[int] = None
    trainer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class ClientEquipmentBase(BaseModel):
    name: str
    quantity: int = 1
    condition: Optional[str] = None
    is_available: bool = True
    notes: Optional[str] = None


class ClientEquipmentCreate(ClientEquipmentBase):
    trainer_id: Optional[int] = None  # Admin can specify; trainers are auto-resolved


class ClientEquipmentUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[int] = None
    condition: Optional[str] = None
    is_available: Optional[bool] = None
    notes: Optional[str] = None


class ClientEquipmentOut(ClientEquipmentBase):
    id: int
    client_id: int
    trainer_id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# =============================================================================
# JOINT & INJURY SYSTEM SCHEMAS (Biomechanical Model)
# =============================================================================


class JointBase(BaseModel):
    name: str  # e.g., "Knee", "Shoulder", "Hip"
    name_es: Optional[str] = None  # e.g., "Rodilla", "Hombro", "Cadera"


class JointCreate(JointBase):
    pass


class JointOut(JointBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class JointMovementBase(BaseModel):
    # Kept for backward compatibility
    name: str  # e.g., "Flexion", "Extension", "Abduction"
    # Primary English name
    name_en: str  # e.g., "Flexion", "Extension", "Abduction"
    name_es: Optional[str] = None  # e.g., "Flexión", "Extensión", "Abducción"


class JointMovementCreate(JointMovementBase):
    pass


class JointMovementOut(JointMovementBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class MuscleBase(BaseModel):
    name: str  # e.g., "Quadriceps", "Hamstrings"
    name_es: Optional[str] = None  # e.g., "Cuádriceps", "Isquiotibiales"
    joint_id: Optional[int] = None  # Primary joint this muscle acts on


class MuscleCreate(MuscleBase):
    pass


class MuscleOut(MuscleBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class MuscleActionBase(BaseModel):
    muscle_id: int
    action_type: str  # "concentric", "eccentric", "isometric"
    is_primary: bool = True


class MuscleActionCreate(MuscleActionBase):
    pass


class MuscleActionOut(MuscleActionBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class ExerciseJointActionBase(BaseModel):
    exercise_id: int
    joint_id: int
    joint_movement_id: int
    action_id: Optional[int] = None
    muscle_id: Optional[int] = None
    role: Optional[str] = None  # primary, secondary

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class ExerciseJointActionCreate(ExerciseJointActionBase):
    pass


class ExerciseJointActionOut(ExerciseJointActionBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Client Injury (Structured - NO free text for joint/action)
class ClientInjuryBase(BaseModel):
    client_id: int
    joint_id: int  # Select from dropdown
    painful_movement_id: int  # Select from dropdown
    pain_level: int = Field(ge=1, le=5)  # 1-5 scale
    severity: str  # "mild", "moderate", "severe"
    restrictions: Optional[List[str]] = None  # Actions to avoid
    notes: Optional[str] = None
    is_active: bool = True


class ClientInjuryCreate(ClientInjuryBase):
    pass


class ClientInjuryUpdate(BaseModel):
    joint_id: Optional[int] = None
    painful_movement_id: Optional[int] = None
    pain_level: Optional[int] = Field(None, ge=1, le=5)
    severity: Optional[str] = None
    restrictions: Optional[List[str]] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ClientInjuryOut(ClientInjuryBase):
    id: int
    start_date: date
    created_at: datetime
    updated_at: datetime
    model_config = {"from_attributes": True}


# Injury with related data (for display)
class ClientInjuryWithDetails(ClientInjuryOut):
    joint_name: Optional[str] = None
    joint_name_es: Optional[str] = None
    movement_name: Optional[str] = None
    movement_name_es: Optional[str] = None


# =============================================================================
# EXERCISE ALTERNATIVES SCHEMAS
# =============================================================================


class ExerciseAlternativeBase(BaseModel):
    exercise_id: int
    alternative_exercise_id: int
    priority: int = 1  # 1 = first choice, 2 = second choice, etc.
    notes: Optional[str] = None


class ExerciseAlternativeCreate(ExerciseAlternativeBase):
    pass


class ExerciseAlternativeUpdate(BaseModel):
    priority: Optional[int] = None
    notes: Optional[str] = None


class ExerciseAlternativeOut(ExerciseAlternativeBase):
    id: int
    created_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Alternative with exercise details (for display)
class ExerciseAlternativeWithDetails(ExerciseAlternativeOut):
    alternative_exercise_name: Optional[str] = None
    alternative_exercise_equipo: Optional[str] = None


# =============================================================================
# INJURY ALERT SCHEMAS
# =============================================================================


class InjuryAlertCheck(BaseModel):
    """Request to check if an exercise conflicts with client injuries"""

    client_id: int
    exercise_id: int


class InjuryAlert(BaseModel):
    """Alert when exercise conflicts with client injury"""

    has_conflict: bool
    severity: Optional[str] = None  # "warning", "danger"
    message: Optional[str] = None
    injury_details: Optional[ClientInjuryWithDetails] = None
    conflicting_movement: Optional[str] = None


# =============================================================================
# EXERCISE SELECTION RECOMMENDATIONS (70% Multi-joint / 30% Single-joint)
# =============================================================================


class ExerciseSelectionRecommendation(BaseModel):
    """
    Recommendation for exercise type distribution in a session.
    Based on Adrián's guideline: 70% multi-joint / 30% single-joint
    """

    total_exercises: int
    recommended_multi_joint: int  # 70% of total
    recommended_single_joint: int  # 30% of total
    multi_joint_percentage: float = 70.0
    single_joint_percentage: float = 30.0
    explanation: str


class SessionExerciseAnalysis(BaseModel):
    """Analysis of exercise types in a session"""

    session_id: Optional[int] = None
    total_exercises: int
    multi_joint_count: int
    single_joint_count: int
    other_count: int  # Complejo, Accesorio, etc.
    actual_multi_joint_percentage: float
    actual_single_joint_percentage: float
    recommended_multi_joint: int
    recommended_single_joint: int
    is_balanced: bool  # True if within acceptable range (±10%)
    deviation_message: Optional[str] = None
    suggestions: List[str] = []


class ExerciseTypeCount(BaseModel):
    """Count of exercises by type"""

    tipo: str
    count: int
    percentage: float


# =============================================================================
# NEW EXCEL STRUCTURE SCHEMAS
# =============================================================================


# Movement Pattern Schemas
class MovementPatternBase(BaseModel):
    name_en: str
    name_es: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name_en")
    @classmethod
    def validate_name_en(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("English name cannot be empty")
        return v.strip()


class MovementPatternCreate(MovementPatternBase):
    pass


class MovementPatternUpdate(BaseModel):
    name_en: Optional[str] = None
    name_es: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MovementPatternOut(MovementPatternBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Muscle Group Schemas
class MuscleGroupBase(BaseModel):
    name_en: str
    name_es: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name_en")
    @classmethod
    def validate_name_en(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("English name cannot be empty")
        return v.strip()


class MuscleGroupCreate(MuscleGroupBase):
    pass


class MuscleGroupUpdate(BaseModel):
    name_en: Optional[str] = None
    name_es: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MuscleGroupOut(MuscleGroupBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Equipment Schemas
class EquipmentBase(BaseModel):
    name_en: str
    name_es: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name_en")
    @classmethod
    def validate_name_en(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("English name cannot be empty")
        return v.strip()


class EquipmentCreate(EquipmentBase):
    pass


class EquipmentUpdate(BaseModel):
    name_en: Optional[str] = None
    name_es: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class EquipmentOut(EquipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Tag Schemas
class TagBase(BaseModel):
    name_en: str
    name_es: Optional[str] = None
    category: Optional[str] = None  # e.g., "difficulty", "goal"

    @field_validator("name_en")
    @classmethod
    def validate_name_en(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("English name cannot be empty")
        return v.strip()


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    name_en: Optional[str] = None
    name_es: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class TagOut(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Exercise Variant Schemas
class ExerciseVariantBase(BaseModel):
    base_exercise_id: int
    # variant_type: equipment, grip, stance, position, tempo,
    # range_of_motion, load_type, assistance, execution_style, pause
    variant_type: str
    name_en: str
    name_es: Optional[str] = None
    description: Optional[str] = None

    @field_validator("variant_type")
    @classmethod
    def validate_variant_type(cls, v):
        """Validate variant type - must be one of the allowed types from Excel"""
        if not v:
            raise ValueError("Variant type cannot be empty")
        v_clean = v.strip().lower()
        valid_types = [
            "equipment",
            "grip",
            "stance",
            "position",
            "tempo",
            "range_of_motion",
            "load_type",
            "assistance",
            "execution_style",
            "pause",
        ]
        if v_clean not in valid_types:
            raise ValueError(
                f"Variant type must be one of: {', '.join(valid_types)}. Got: {v}"
            )
        return v_clean

    @field_validator("name_en")
    @classmethod
    def validate_name_en(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("English name cannot be empty")
        return v.strip()


class ExerciseVariantCreate(ExerciseVariantBase):
    pass


class ExerciseVariantUpdate(BaseModel):
    variant_type: Optional[str] = None
    name_en: Optional[str] = None
    name_es: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("variant_type")
    @classmethod
    def validate_variant_type(cls, v):
        """Validate variant type - must be one of the allowed types from Excel"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_types = [
            "equipment",
            "grip",
            "stance",
            "position",
            "tempo",
            "range_of_motion",
            "load_type",
            "assistance",
            "execution_style",
            "pause",
        ]
        if v_clean not in valid_types:
            raise ValueError(
                f"Variant type must be one of: {', '.join(valid_types)}. Got: {v}"
            )
        return v_clean


class ExerciseVariantOut(ExerciseVariantBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Variant Mapping Table Schemas
class VariantEquipmentBase(BaseModel):
    variant_id: int
    equipment_id: int
    role: Optional[str] = None  # primary, secondary

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantEquipmentCreate(VariantEquipmentBase):
    pass


class VariantEquipmentUpdate(BaseModel):
    variant_id: Optional[int] = None
    equipment_id: Optional[int] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantEquipmentOut(VariantEquipmentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class VariantJointActionBase(BaseModel):
    variant_id: int
    joint_id: int
    action_id: Optional[int] = None
    role: Optional[str] = None  # primary, secondary

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantJointActionCreate(VariantJointActionBase):
    pass


class VariantJointActionUpdate(BaseModel):
    variant_id: Optional[int] = None
    joint_id: Optional[int] = None
    action_id: Optional[int] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantJointActionOut(VariantJointActionBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class VariantMovementPatternBase(BaseModel):
    variant_id: int
    movement_pattern_id: int
    role: Optional[str] = None  # primary, secondary

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantMovementPatternCreate(VariantMovementPatternBase):
    pass


class VariantMovementPatternUpdate(BaseModel):
    variant_id: Optional[int] = None
    movement_pattern_id: Optional[int] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantMovementPatternOut(VariantMovementPatternBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class VariantMuscleBase(BaseModel):
    variant_id: int
    muscle_id: int
    role: str  # prime_mover, synergist, stabilizer

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be prime_mover, synergist, or stabilizer"""
        if v is None:
            raise ValueError("Role is required for variant-muscle mappings")
        v_clean = v.strip().lower()
        valid_roles = ["prime_mover", "synergist", "stabilizer"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantMuscleCreate(VariantMuscleBase):
    pass


class VariantMuscleUpdate(BaseModel):
    variant_id: Optional[int] = None
    muscle_id: Optional[int] = None
    role: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be prime_mover, synergist, or stabilizer"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["prime_mover", "synergist", "stabilizer"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class VariantMuscleOut(VariantMuscleBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


class VariantTagBase(BaseModel):
    variant_id: int
    tag_id: int


class VariantTagCreate(VariantTagBase):
    pass


class VariantTagUpdate(BaseModel):
    variant_id: Optional[int] = None
    tag_id: Optional[int] = None


class VariantTagOut(VariantTagBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_active: bool
    model_config = {"from_attributes": True}


# Mapping Table Schemas
class ExerciseMovementPatternBase(BaseModel):
    exercise_id: int
    movement_pattern_id: int
    role: Optional[str] = None  # primary, secondary

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be primary or secondary"""
        if v is None:
            return None
        v_clean = v.strip().lower()
        valid_roles = ["primary", "secondary"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class ExerciseMovementPatternCreate(ExerciseMovementPatternBase):
    pass


class ExerciseMovementPatternOut(ExerciseMovementPatternBase):
    id: int
    model_config = {"from_attributes": True}


class ExerciseMuscleBase(BaseModel):
    exercise_id: int
    muscle_id: int
    role: str  # prime_mover, synergist, stabilizer

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        """Validate role - must be prime_mover, synergist, or stabilizer"""
        if not v:
            raise ValueError("Role cannot be empty")
        v_clean = v.strip().lower()
        valid_roles = ["prime_mover", "synergist", "stabilizer"]
        if v_clean not in valid_roles:
            raise ValueError(f"Role must be one of: {', '.join(valid_roles)}. Got: {v}")
        return v_clean


class ExerciseMuscleCreate(ExerciseMuscleBase):
    pass


class ExerciseMuscleOut(ExerciseMuscleBase):
    id: int
    model_config = {"from_attributes": True}


class ExerciseEquipmentBase(BaseModel):
    exercise_id: int
    equipment_id: int


class ExerciseEquipmentCreate(ExerciseEquipmentBase):
    pass


class ExerciseEquipmentOut(ExerciseEquipmentBase):
    id: int
    model_config = {"from_attributes": True}


class ExerciseTagBase(BaseModel):
    exercise_id: int
    tag_id: int


class ExerciseTagCreate(ExerciseTagBase):
    pass


class ExerciseTagOut(ExerciseTagBase):
    id: int
    model_config = {"from_attributes": True}
