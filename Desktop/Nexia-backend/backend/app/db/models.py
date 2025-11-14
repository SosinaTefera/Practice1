import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .session import Base


# Session Programming Enums
class SetTypeEnum(str, enum.Enum):
    single_set = "single_set"
    superset = "superset"
    dropset = "dropset"


class EffortCharacterEnum(str, enum.Enum):
    rpe = "rpe"
    rir = "rir"
    velocity_loss = "velocity_loss"


class GenderEnum(str, enum.Enum):
    MASCULINO = "Masculino"
    FEMENINO = "Femenino"


class TrainingGoalEnum(str, enum.Enum):
    AUMENTAR_MASA_MUSCULAR = "Aumentar masa muscular"
    PERDIDA_DE_PESO = "Pérdida de peso"
    RENDIMIENTO_DEPORTIVO = "Rendimiento deportivo"


class ExperienceEnum(str, enum.Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


class WeeklyFrequencyEnum(str, enum.Enum):
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"


class ExperienceLevelEnum(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TrainingFrequencyEnum(str, enum.Enum):
    LOW_1_2 = "low_1_2"
    MEDIUM_3_5 = "medium_3_5"
    HIGH_6_7 = "high_6_7"


class SessionDurationEnum(str, enum.Enum):
    SHORT_LT_1H = "short_lt_1h"
    MEDIUM_1H_TO_1H30 = "medium_1h_to_1h30"
    LONG_GT_1H30 = "long_gt_1h30"


class ExerciseTypeEnum(str, enum.Enum):
    ACCESORIO = "Accesorio"
    COMPLEJO = "Complejo"
    MONOARTICULAR = "Monoarticular"
    MULTIARTICULAR = "Multiarticular"
    MULTICOMPLEJO = "Multicomplejo"


class ExerciseClassificationEnum(str, enum.Enum):
    ACCESORIO = "Accesorio"
    BASICO = "Básico"
    GUIADO_MAQUINA = "Guiado en máquina"
    OLIMPICO = "Olímpico"
    PESO_CORPORAL = "Peso corporal"
    PLIOMETRIA = "Pliometría"


class ExerciseLevelEnum(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class LoadTypeEnum(str, enum.Enum):
    BODYWEIGHT = "bodyweight"
    EXTERNAL = "external"
    MIXED = "mixed"


class EquipmentEnum(str, enum.Enum):
    BARBELL = "barbell"
    DUMBBELLS = "dumbbells"
    KETTLEBELL = "kettlebell"
    MACHINE = "machine"
    MANCUERNA = "mancuerna"
    MANCUERNAS_LIGERAS_O_BANDA = "mancuernas ligeras o banda"
    MANCUERNAS_LIGERAS_O_PESO_CORPORAL = "mancuernas ligeras o peso corporal"
    MAT_OR_ANCHORED_BENCH = "mat or anchored bench"
    NONE = "none"
    NONE_OR_LIGHT_IMPLEMENT = "none or light implement"
    PESO_CORPORAL_O_BANDA = "peso corporal o banda"
    RESISTANCE_BAND = "resistance band"
    VARIABLE = "variable"


class MovementPatternEnum(str, enum.Enum):
    BISAGRA_DE_CADERA = "bisagra de cadera"
    COMPLEJO = "complejo"
    CORE = "core"
    CORE_ESTABILIDAD = "core/estabilidad"
    DOMINANTE_DE_RODILLA = "dominante de rodilla"
    ELEVACION = "elevación"
    EMPUJE = "empuje"
    EQUILIBRIO_CORE = "equilibrio/core"
    EXPLOSIVO_SALTO = "explosivo/salto"
    EXTENSION_DE_CODO = "extensión de codo"
    FLEXION_DE_CODO = "flexión de codo"
    OTROS = "otros"
    ROTACION_EXTERNA = "rotación externa"
    ROTACION_EXTERNA_Y_ELEVACION = "rotación externa y elevación"
    ROTACION_EXTERNA_Y_RETRACCION_ESCAPULAR = "rotación externa y retracción escapular"
    TIRON_TRIPLE_EXTENSION = "tirón triple extensión"
    TRACCION = "tracción"


class BaseModel(Base):
    """Base model with common fields"""

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active = Column(Boolean, default=True, nullable=False)


class ClientProfile(BaseModel):
    __tablename__ = "client_profiles"

    # Personal Information
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    nombre = Column(String(100), nullable=False, index=True)
    apellidos = Column(String(100), nullable=False, index=True)
    mail = Column(String(255), nullable=False, index=True)
    telefono = Column(String(20), nullable=True)
    sexo = Column(Enum(GenderEnum), nullable=True)
    fecha_alta = Column(Date, default=func.current_date())
    observaciones = Column(Text, nullable=True)

    # Additional Personal Information
    id_passport = Column(String(50), nullable=True)
    birthdate = Column(Date, nullable=True)

    # Physical Attributes
    edad = Column(Integer, nullable=True)
    peso = Column(Float, nullable=True)  # in kg
    altura = Column(Float, nullable=True)  # in cm (changed from meters)
    imc = Column(Float, nullable=True)  # calculated field

    # Anthropometric Data - Skinfolds (in mm)
    skinfold_triceps = Column(Float, nullable=True)
    skinfold_subscapular = Column(Float, nullable=True)
    skinfold_biceps = Column(Float, nullable=True)
    skinfold_iliac_crest = Column(Float, nullable=True)
    skinfold_supraspinal = Column(Float, nullable=True)
    skinfold_abdominal = Column(Float, nullable=True)
    skinfold_thigh = Column(Float, nullable=True)
    skinfold_calf = Column(Float, nullable=True)

    # Anthropometric Data - Girths (in cm)
    girth_relaxed_arm = Column(Float, nullable=True)
    girth_flexed_contracted_arm = Column(Float, nullable=True)
    girth_waist_minimum = Column(Float, nullable=True)
    girth_hips_maximum = Column(Float, nullable=True)
    girth_medial_thigh = Column(Float, nullable=True)
    girth_maximum_calf = Column(Float, nullable=True)

    # Anthropometric Data - Diameters (in cm)
    diameter_humerus_biepicondylar = Column(Float, nullable=True)
    diameter_femur_bicondylar = Column(Float, nullable=True)
    diameter_bi_styloid_wrist = Column(Float, nullable=True)

    # Training Goals
    objetivo_entrenamiento = Column(Enum(TrainingGoalEnum), nullable=True)
    fecha_definicion_objetivo = Column(Date, nullable=True)
    descripcion_objetivos = Column(Text, nullable=True)

    # Experience and Health
    experiencia = Column(Enum(ExperienceEnum), nullable=True)
    lesiones_relevantes = Column(Text, nullable=True)

    # Training Frequency
    frecuencia_semanal = Column(Enum(WeeklyFrequencyEnum), nullable=True)

    # Program Meta Fields (from Hussein's design)
    objective = Column(String(100), nullable=True)  # Free text objective
    session_duration = Column(
        String(20), nullable=True
    )  # short_lt_1h, medium_1h_to_1h30, long_gt_1h30
    notes_1 = Column(Text, nullable=True)
    notes_2 = Column(Text, nullable=True)
    notes_3 = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", back_populates="client_profile")
    routines = relationship("ClientRoutine", back_populates="client")
    progress_records = relationship("ClientProgress", back_populates="client")
    training_plans = relationship("TrainingPlan", back_populates="client")
    training_sessions = relationship("TrainingSession", back_populates="client")
    standalone_sessions = relationship("StandaloneSession", back_populates="client")
    feedback = relationship("ClientFeedback", back_populates="client")
    standalone_session_feedback = relationship(
        "StandaloneSessionFeedback", back_populates="client"
    )
    progress_tracking = relationship("ProgressTracking", back_populates="client")
    fatigue_analysis = relationship("FatigueAnalysis", back_populates="client")
    training_plan_instances = relationship(
        "TrainingPlanInstance", back_populates="client"
    )

    # Indexes
    __table_args__ = (
        Index("idx_client_email", "mail"),
        Index("idx_client_name", "nombre", "apellidos"),
    )


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)
    nombre = Column(String(100), nullable=False, index=True)
    apellidos = Column(String(100), nullable=False, index=True)
    mail = Column(String(255), nullable=False, unique=True, index=True)
    telefono = Column(String(20), nullable=True)
    # Professional profile (MVP)
    occupation = Column(String(100), nullable=True)
    training_modality = Column(String(50), nullable=True)  # in_person | online | hybrid
    location_country = Column(String(100), nullable=True)
    location_city = Column(String(100), nullable=True)
    billing_id = Column(String(100), nullable=True)  # tax/VAT id
    billing_address = Column(String(255), nullable=True)
    billing_postal_code = Column(String(20), nullable=True)
    # Optional
    specialty = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="trainer_profile")
    clients = relationship("ClientProfile", secondary="trainer_clients")
    routines = relationship("ClientRoutine", back_populates="trainer")
    training_plans = relationship("TrainingPlan", back_populates="trainer")
    training_plan_templates = relationship(
        "TrainingPlanTemplate", back_populates="trainer"
    )
    training_plan_instances = relationship(
        "TrainingPlanInstance", back_populates="trainer"
    )
    training_sessions = relationship("TrainingSession", back_populates="trainer")
    standalone_sessions = relationship("StandaloneSession", back_populates="trainer")
    # New session programming relationships
    session_templates = relationship("SessionTemplate", back_populates="trainer")
    custom_block_types = relationship(
        "TrainingBlockType", back_populates="created_by_trainer"
    )


class TrainerClient(Base):
    """Association table for trainer-client relationships"""

    __tablename__ = "trainer_clients"

    trainer_id = Column(Integer, ForeignKey("trainers.id"), primary_key=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), primary_key=True)
    assigned_at = Column(DateTime, default=func.now())
    # Denormalized lowercased email to enforce per-trainer uniqueness at DB level
    client_email_norm = Column(String(255), nullable=True)

    __table_args__ = (
        # Enforce unique email per trainer (case-insensitive via normalized value)
        Index(
            "uq_trainer_client_email_per_trainer",
            "trainer_id",
            "client_email_norm",
            unique=True,
        ),
    )


class Exercise(Base):
    """Exercise database based on Excel data from Ejercicios2 sheet"""

    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True)
    # Core identification
    exercise_id = Column(
        String(50), nullable=False, unique=True, index=True
    )  # e.g., "back_squat"
    nombre = Column(String(100), nullable=False, index=True)  # Spanish name
    nombre_ingles = Column(String(100), nullable=True)  # English name if available

    # Classification and type
    tipo = Column(String(50), nullable=False)  # Multiarticular, Monoarticular, etc.
    categoria = Column(String(50), nullable=False)  # Básico, Intermedio, Avanzado
    nivel = Column(String(20), nullable=False)  # beginner, intermediate, advanced

    # Equipment and movement
    equipo = Column(String(50), nullable=False)  # barbell, dumbbell, etc.
    patron_movimiento = Column(String(50), nullable=False)  # dominante de rodilla, etc.
    tipo_carga = Column(String(20), nullable=False)  # external, bodyweight, resistance

    # Muscles involved
    musculatura_principal = Column(Text, nullable=False)  # Can be comma-separated list
    musculatura_secundaria = Column(Text, nullable=True)  # Can be comma-separated list

    # Additional information
    descripcion = Column(Text, nullable=True)
    instrucciones = Column(Text, nullable=True)
    notas = Column(Text, nullable=True)  # Additional notes or tips
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)

    # Indexes for better performance
    __table_args__ = (
        Index("idx_exercise_id", "exercise_id"),
        Index("idx_exercise_nombre", "nombre"),
        Index("idx_exercise_tipo", "tipo"),
        Index("idx_exercise_categoria", "categoria"),
        Index("idx_exercise_nivel", "nivel"),
        Index("idx_exercise_equipo", "equipo"),
    )

    # Relationships
    routine_exercises = relationship("RoutineExercise", back_populates="exercise")
    session_exercises = relationship("SessionExercise", back_populates="exercise")
    progress_tracking = relationship("ProgressTracking", back_populates="exercise")
    standalone_session_exercises = relationship(
        "StandaloneSessionExercise", back_populates="exercise"
    )


class TrainingRoutine(BaseModel):
    """Training routine template"""

    __tablename__ = "training_routines"

    nombre = Column(String(100), nullable=False, index=True)
    descripcion = Column(Text, nullable=True)
    tipo_rutina = Column(String(50), nullable=False)  # Full Body, Upper/Lower, etc.
    frecuencia = Column(Enum(WeeklyFrequencyEnum), nullable=False)
    experiencia_requerida = Column(Enum(ExperienceEnum), nullable=False)
    volumen = Column(String(20), nullable=False)  # Bajo, Media, Alto
    intensidad = Column(String(20), nullable=False)  # Baja, Media, Alta

    # Relationships
    exercises = relationship("RoutineExercise", back_populates="routine")
    client_routines = relationship("ClientRoutine", back_populates="routine_template")


class RoutineExercise(BaseModel):
    """Association table for routine-exercise relationships"""

    __tablename__ = "routine_exercises"

    routine_id = Column(Integer, ForeignKey("training_routines.id"), primary_key=True)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), primary_key=True)
    series = Column(Integer, nullable=False, default=3)
    repeticiones = Column(String(20), nullable=False, default="8-12")
    descanso = Column(String(20), nullable=True)  # e.g., "90 segundos"
    orden = Column(Integer, nullable=False, default=1)

    # Relationships
    routine = relationship("TrainingRoutine", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="routine_exercises")


class ClientRoutine(BaseModel):
    """Client's assigned routine"""

    __tablename__ = "client_routines"

    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    routine_template_id = Column(
        Integer, ForeignKey("training_routines.id"), nullable=False
    )
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    activa = Column(Boolean, default=True)

    # Relationships
    client = relationship("ClientProfile", back_populates="routines")
    routine_template = relationship("TrainingRoutine", back_populates="client_routines")
    trainer = relationship("Trainer", back_populates="routines")


class ClientProgress(BaseModel):
    """Client progress tracking"""

    __tablename__ = "client_progress"

    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    fecha_registro = Column(Date, nullable=False, default=func.current_date())
    peso = Column(Float, nullable=True)
    altura = Column(Float, nullable=True)
    unidad = Column(
        String(20), nullable=True, default="metric"
    )  # Input unit (metric/imperial)
    imc = Column(Float, nullable=True)
    notas = Column(Text, nullable=True)
    fecha_inicio_prueba = Column(Date, nullable=True)

    # Anthropometric Data - Skinfolds (in mm)
    skinfold_triceps = Column(Float, nullable=True)
    skinfold_subscapular = Column(Float, nullable=True)
    skinfold_biceps = Column(Float, nullable=True)
    skinfold_iliac_crest = Column(Float, nullable=True)
    skinfold_supraspinal = Column(Float, nullable=True)
    skinfold_abdominal = Column(Float, nullable=True)
    skinfold_thigh = Column(Float, nullable=True)
    skinfold_calf = Column(Float, nullable=True)

    # Anthropometric Data - Girths (in cm)
    girth_relaxed_arm = Column(Float, nullable=True)
    girth_flexed_contracted_arm = Column(Float, nullable=True)
    girth_waist_minimum = Column(Float, nullable=True)
    girth_hips_maximum = Column(Float, nullable=True)
    girth_medial_thigh = Column(Float, nullable=True)
    girth_maximum_calf = Column(Float, nullable=True)

    # Anthropometric Data - Diameters (in cm)
    diameter_humerus_biepicondylar = Column(Float, nullable=True)
    diameter_femur_bicondylar = Column(Float, nullable=True)
    diameter_bi_styloid_wrist = Column(Float, nullable=True)

    # Body Composition Calculated Fields
    body_fat_percentage = Column(Float, nullable=True)
    muscle_mass_kg = Column(Float, nullable=True)
    fat_free_mass_kg = Column(Float, nullable=True)

    # Relationships
    client = relationship("ClientProfile", back_populates="progress_records")

    # Add unique constraint to prevent duplicate entries per client per day
    __table_args__ = (
        Index("idx_client_progress_unique", "client_id", "fecha_registro", unique=True),
    )


# Training Planning Models
class MilestoneTypeEnum(str, enum.Enum):
    start = "start"
    test = "test"
    competition = "competition"
    end = "end"
    custom = "custom"


class TrainingPlanTemplate(BaseModel):
    """Reusable training plan templates without client assignment"""

    __tablename__ = "training_plan_templates"

    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    goal = Column(
        String(255), nullable=False
    )  # e.g., "Muscle Gain", "Fat Loss", "Performance"
    category = Column(String(100), nullable=True)  # e.g., "hipertrofia", "fuerza"
    tags = Column(JSON, nullable=True)  # e.g., ["principiante", "casa", "gimnasio"]
    estimated_duration_weeks = Column(Integer, nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)
    success_rate = Column(Float, nullable=True)  # Percentage of success (0-100)
    is_template = Column(Boolean, default=True, nullable=False)
    is_public = Column(
        Boolean, default=False, nullable=False
    )  # Share with other trainers

    # Relationships
    trainer = relationship("Trainer", back_populates="training_plan_templates")
    macrocycles = relationship(
        "Macrocycle",
        foreign_keys="[Macrocycle.template_id]",
        back_populates="template",
        cascade="all, delete-orphan",
    )
    instances = relationship(
        "TrainingPlanInstance", back_populates="template", cascade="all, delete-orphan"
    )


class TrainingPlan(BaseModel):
    __tablename__ = "training_plans"

    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    client_id = Column(
        Integer, ForeignKey("client_profiles.id"), nullable=True
    )  # Made optional
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    goal = Column(
        String(255), nullable=False
    )  # e.g., "Muscle Gain", "Fat Loss", "Performance"
    status = Column(String(50), default="active")  # active, completed, paused
    # New fields for template system
    template_id = Column(
        Integer, ForeignKey("training_plan_templates.id"), nullable=True
    )
    is_template = Column(Boolean, default=False, nullable=False)
    can_be_reused = Column(Boolean, default=True, nullable=False)
    was_converted_to_template = Column(Boolean, default=False, nullable=False)

    # Relationships
    trainer = relationship("Trainer", back_populates="training_plans")
    client = relationship("ClientProfile", back_populates="training_plans")
    template = relationship("TrainingPlanTemplate", foreign_keys=[template_id])
    instances = relationship(
        "TrainingPlanInstance",
        foreign_keys="TrainingPlanInstance.source_plan_id",
        back_populates="source_plan",
    )
    macrocycles = relationship(
        "Macrocycle", back_populates="training_plan", cascade="all, delete-orphan"
    )
    milestones = relationship(
        "Milestone", back_populates="training_plan", cascade="all, delete-orphan"
    )


class TrainingPlanInstance(BaseModel):
    """Active training plan instances assigned to clients"""

    __tablename__ = "training_plan_instances"

    # References (one or the other, not both)
    template_id = Column(
        Integer, ForeignKey("training_plan_templates.id"), nullable=True
    )
    source_plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=True)
    # Client and trainer
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    # Information specific to this client
    name = Column(String(255), nullable=False)  # Can be different from original
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)  # Customized dates
    end_date = Column(Date, nullable=False)
    goal = Column(String(255), nullable=False)
    status = Column(String(50), default="active")  # active, completed, paused
    # Personalizations
    customizations = Column(JSON, nullable=True)  # Client-specific changes
    assigned_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    template = relationship("TrainingPlanTemplate", back_populates="instances")
    source_plan = relationship("TrainingPlan", foreign_keys=[source_plan_id])
    client = relationship("ClientProfile", back_populates="training_plan_instances")
    trainer = relationship("Trainer", back_populates="training_plan_instances")
    macrocycles = relationship(
        "Macrocycle",
        foreign_keys="[Macrocycle.instance_id]",
        back_populates="instance",
        cascade="all, delete-orphan",
    )


class Macrocycle(BaseModel):
    __tablename__ = "macrocycles"

    id = Column(Integer, primary_key=True, index=True)
    # Support for templates, instances, and regular plans (Option B)
    training_plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=True)
    template_id = Column(
        Integer, ForeignKey("training_plan_templates.id"), nullable=True
    )
    instance_id = Column(
        Integer, ForeignKey("training_plan_instances.id"), nullable=True
    )
    name = Column(
        String(255), nullable=False
    )  # e.g., "Preparation Phase", "Competition Phase"
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    focus = Column(
        String(255), nullable=False
    )  # e.g., "Strength", "Endurance", "Power"
    # Coherence system fields (Adrián's requirement)
    physical_quality = Column(
        String(255), nullable=True
    )  # e.g., "Fuerza", "Power", "Aerobic", "Mobility" (replaces focus in coherence)
    volume = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    intensity = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    volume_intensity_ratio = Column(
        String(50), nullable=True
    )  # e.g., "High Volume, Low Intensity" (kept for backward compatibility)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    training_plan = relationship("TrainingPlan", back_populates="macrocycles")
    template = relationship("TrainingPlanTemplate", back_populates="macrocycles")
    instance = relationship("TrainingPlanInstance", back_populates="macrocycles")
    mesocycles = relationship(
        "Mesocycle", back_populates="macrocycle", cascade="all, delete-orphan"
    )


class Mesocycle(BaseModel):
    __tablename__ = "mesocycles"

    id = Column(Integer, primary_key=True)
    macrocycle_id = Column(Integer, ForeignKey("macrocycles.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Week 1-4: Strength Foundation"
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_weeks = Column(Integer, nullable=False)
    primary_focus = Column(
        String(255), nullable=False
    )  # e.g., "Maximal Strength", "Muscular Endurance"
    secondary_focus = Column(String(255), nullable=True)
    # Coherence system fields (Adrián's requirement)
    physical_quality = Column(
        String(255), nullable=True
    )  # e.g., "Fuerza", "Power", "Aerobic", "Mobility"
    volume = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    intensity = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    target_volume = Column(String(50), nullable=True)  # e.g., "High", "Medium", "Low" (kept for backward compatibility)
    target_intensity = Column(
        String(50), nullable=True
    )  # e.g., "High", "Medium", "Low" (kept for backward compatibility)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    macrocycle = relationship("Macrocycle", back_populates="mesocycles")
    microcycles = relationship(
        "Microcycle", back_populates="mesocycle", cascade="all, delete-orphan"
    )


class Microcycle(BaseModel):
    __tablename__ = "microcycles"

    id = Column(Integer, primary_key=True)
    mesocycle_id = Column(Integer, ForeignKey("mesocycles.id"), nullable=False)
    name = Column(String(255), nullable=False)  # e.g., "Week 1: Introduction"
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    duration_days = Column(Integer, nullable=False, default=7)
    training_frequency = Column(Integer, nullable=False, default=3)  # sessions per week
    deload_week = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    # Coherence system fields (Adrián's requirement)
    physical_quality = Column(
        String(255), nullable=True
    )  # e.g., "Fuerza", "Power", "Aerobic", "Mobility"
    volume = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    intensity = Column(Float, nullable=True)  # Float 1-10 for coherence calculation
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    mesocycle = relationship("Mesocycle", back_populates="microcycles")
    training_sessions = relationship(
        "TrainingSession", back_populates="microcycle", cascade="all, delete-orphan"
    )


class TrainingSession(BaseModel):
    __tablename__ = "training_sessions"

    id = Column(Integer, primary_key=True)
    microcycle_id = Column(Integer, ForeignKey("microcycles.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    session_name = Column(String(255), nullable=False)  # e.g., "Upper Body Strength"
    session_type = Column(
        String(100), nullable=False
    )  # e.g., "Strength", "Cardio", "Recovery"
    planned_duration = Column(Integer, nullable=True)  # in minutes
    actual_duration = Column(Integer, nullable=True)  # in minutes
    # Session programming enhancements
    planned_intensity = Column(Float, nullable=True)  # 0-100%
    planned_volume = Column(Float, nullable=True)  # 0-100%
    actual_intensity = Column(Float, nullable=True)  # 0-100%
    actual_volume = Column(Float, nullable=True)  # 0-100%
    status = Column(
        String(50), default="planned"
    )  # planned, completed, skipped, modified
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    microcycle = relationship("Microcycle", back_populates="training_sessions")
    client = relationship("ClientProfile", back_populates="training_sessions")
    trainer = relationship("Trainer", back_populates="training_sessions")
    exercises = relationship(
        "SessionExercise",
        back_populates="training_session",
        cascade="all, delete-orphan",
    )
    client_feedback = relationship(
        "ClientFeedback",
        back_populates="training_session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    # New session programming relationships
    blocks = relationship(
        "SessionBlock",
        back_populates="training_session",
        cascade="all, delete-orphan",
    )

    # Add performance indexes for coach filtering
    __table_args__ = (
        Index("idx_training_session_coach_client", "trainer_id", "client_id"),
        Index("idx_training_session_date", "session_date"),
        Index("idx_training_session_status", "status"),
    )


class Milestone(BaseModel):
    __tablename__ = "milestones"

    training_plan_id = Column(Integer, ForeignKey("training_plans.id"), nullable=False)
    title = Column(String(255), nullable=False)
    milestone_date = Column(Date, nullable=False)
    type = Column(
        Enum(MilestoneTypeEnum), nullable=False, default=MilestoneTypeEnum.custom
    )
    notes = Column(Text, nullable=True)
    importance = Column(String(50), default="medium")  # low, medium, high
    reminder_offset_days = Column(Integer, nullable=True)  # days before to remind
    done = Column(Boolean, default=False)

    # Relationships
    training_plan = relationship("TrainingPlan", back_populates="milestones")

    # Indexes
    __table_args__ = (
        Index("idx_milestone_plan_date", "training_plan_id", "milestone_date"),
        Index("idx_milestone_done", "done"),
    )


class SessionExercise(BaseModel):
    __tablename__ = "session_exercises"

    id = Column(Integer, primary_key=True)
    training_session_id = Column(
        Integer, ForeignKey("training_sessions.id"), nullable=False
    )
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_in_session = Column(Integer, nullable=False)
    planned_sets = Column(Integer, nullable=True)
    planned_reps = Column(Integer, nullable=True)
    planned_weight = Column(Float, nullable=True)  # in kg
    planned_duration = Column(Integer, nullable=True)  # in seconds
    planned_distance = Column(Float, nullable=True)  # in meters
    planned_rest = Column(Integer, nullable=True)  # rest time in seconds
    actual_sets = Column(Integer, nullable=True)
    actual_reps = Column(Integer, nullable=True)
    actual_weight = Column(Float, nullable=True)
    actual_duration = Column(Integer, nullable=True)
    actual_distance = Column(Float, nullable=True)
    actual_rest = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    training_session = relationship("TrainingSession", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="session_exercises")


class ClientFeedback(BaseModel):
    __tablename__ = "client_feedback"

    id = Column(Integer, primary_key=True)
    training_session_id = Column(
        Integer, ForeignKey("training_sessions.id"), nullable=False
    )
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    perceived_effort = Column(Integer, nullable=True)  # 1-10 scale
    fatigue_level = Column(Integer, nullable=True)  # 1-10 scale
    sleep_quality = Column(Integer, nullable=True)  # 1-10 scale
    stress_level = Column(Integer, nullable=True)  # 1-10 scale
    motivation_level = Column(Integer, nullable=True)  # 1-10 scale
    energy_level = Column(Integer, nullable=True)  # 1-10 scale
    muscle_soreness = Column(
        String(255), nullable=True
    )  # e.g., "Upper body", "Lower body", "Full body"
    pain_or_discomfort = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    feedback_date = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    training_session = relationship("TrainingSession", back_populates="client_feedback")
    client = relationship("ClientProfile", back_populates="feedback")


class ProgressTracking(BaseModel):
    __tablename__ = "progress_tracking"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    tracking_date = Column(Date, nullable=False)
    max_weight = Column(Float, nullable=True)  # 1RM or max weight lifted
    max_reps = Column(Integer, nullable=True)
    max_duration = Column(Integer, nullable=True)  # in seconds
    max_distance = Column(Float, nullable=True)  # in meters
    estimated_1rm = Column(Float, nullable=True)  # calculated 1RM
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_active = Column(Boolean, default=True)

    # Relationships
    client = relationship("ClientProfile", back_populates="progress_tracking")
    exercise = relationship("Exercise", back_populates="progress_tracking")

    # Add unique constraint to prevent duplicate entries per client per exercise per day
    __table_args__ = (
        Index(
            "idx_progress_tracking_unique",
            "client_id",
            "exercise_id",
            "tracking_date",
            unique=True,
        ),
    )


class StandaloneSession(BaseModel):
    """Standalone training session without full planning hierarchy"""

    __tablename__ = "standalone_sessions"

    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    session_date = Column(Date, nullable=False)
    session_name = Column(String(255), nullable=False)  # e.g., "Quick Upper Body"
    session_type = Column(
        String(100), nullable=False
    )  # e.g., "Strength", "Cardio", "Recovery"
    planned_duration = Column(Integer, nullable=True)  # in minutes
    actual_duration = Column(Integer, nullable=True)  # in minutes
    status = Column(
        String(50), default="planned"
    )  # planned, completed, skipped, modified
    notes = Column(Text, nullable=True)

    # Relationships
    trainer = relationship("Trainer", back_populates="standalone_sessions")
    client = relationship("ClientProfile", back_populates="standalone_sessions")
    exercises = relationship(
        "StandaloneSessionExercise",
        back_populates="standalone_session",
        cascade="all, delete-orphan",
    )
    client_feedback = relationship(
        "StandaloneSessionFeedback",
        back_populates="standalone_session",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Add performance indexes for coach filtering
    __table_args__ = (
        Index("idx_standalone_session_coach_client", "trainer_id", "client_id"),
        Index("idx_standalone_session_date", "session_date"),
        Index("idx_standalone_session_status", "status"),
    )


class StandaloneSessionExercise(BaseModel):
    """Exercises within a standalone session"""

    __tablename__ = "standalone_session_exercises"

    standalone_session_id = Column(
        Integer, ForeignKey("standalone_sessions.id"), nullable=False
    )
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_in_session = Column(Integer, nullable=False)
    planned_sets = Column(Integer, nullable=True)
    planned_reps = Column(Integer, nullable=True)
    planned_weight = Column(Float, nullable=True)  # in kg
    planned_duration = Column(Integer, nullable=True)  # in seconds
    planned_distance = Column(Float, nullable=True)  # in meters
    planned_rest = Column(Integer, nullable=True)  # rest time in seconds
    actual_sets = Column(Integer, nullable=True)
    actual_reps = Column(Integer, nullable=True)
    actual_weight = Column(Float, nullable=True)
    actual_duration = Column(Integer, nullable=True)
    actual_distance = Column(Float, nullable=True)
    actual_rest = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    standalone_session = relationship("StandaloneSession", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="standalone_session_exercises")


class StandaloneSessionFeedback(BaseModel):
    """Client feedback for standalone sessions"""

    __tablename__ = "standalone_session_feedback"

    standalone_session_id = Column(
        Integer, ForeignKey("standalone_sessions.id"), nullable=False
    )
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    perceived_effort = Column(Integer, nullable=True)  # 1-10 scale
    fatigue_level = Column(Integer, nullable=True)  # 1-10 scale
    sleep_quality = Column(Integer, nullable=True)  # 1-10 scale
    stress_level = Column(Integer, nullable=True)  # 1-10 scale
    motivation_level = Column(Integer, nullable=True)  # 1-10 scale
    energy_level = Column(Integer, nullable=True)  # 1-10 scale
    muscle_soreness = Column(
        String(255), nullable=True
    )  # e.g., "Upper body", "Lower body", "Full body"
    pain_or_discomfort = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    feedback_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    standalone_session = relationship(
        "StandaloneSession", back_populates="client_feedback"
    )
    client = relationship("ClientProfile", back_populates="standalone_session_feedback")


# Fatigue Analysis Models
class FatigueAnalysis(BaseModel):
    __tablename__ = "fatigue_analysis"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    session_id = Column(Integer, nullable=True)
    session_type = Column(String(50), nullable=False)  # "training" or "standalone"
    analysis_date = Column(Date, nullable=False)

    # Pre-session metrics
    pre_fatigue_level = Column(Integer, nullable=True)  # 1-10 scale
    pre_energy_level = Column(Integer, nullable=True)  # 1-10 scale
    pre_motivation_level = Column(Integer, nullable=True)  # 1-10 scale
    pre_sleep_quality = Column(Integer, nullable=True)  # 1-10 scale
    pre_stress_level = Column(Integer, nullable=True)  # 1-10 scale
    pre_muscle_soreness = Column(String(255), nullable=True)

    # Post-session metrics
    post_fatigue_level = Column(Integer, nullable=True)  # 1-10 scale
    post_energy_level = Column(Integer, nullable=True)  # 1-10 scale
    post_motivation_level = Column(Integer, nullable=True)  # 1-10 scale
    post_muscle_soreness = Column(String(255), nullable=True)

    # Calculated metrics
    fatigue_delta = Column(Integer, nullable=True)  # post - pre fatigue
    energy_delta = Column(Integer, nullable=True)  # post - pre energy
    workload_score = Column(Float, nullable=True)  # calculated from session intensity
    recovery_need_score = Column(
        Float, nullable=True
    )  # calculated recovery requirement

    # Analysis results
    risk_level = Column(String(20), nullable=True)  # "low", "medium", "high"
    recommendations = Column(Text, nullable=True)
    next_session_adjustment = Column(Text, nullable=True)

    # Relationships
    client = relationship("ClientProfile", back_populates="fatigue_analysis")
    alerts = relationship("FatigueAlert", back_populates="fatigue_analysis")

    # Indexes for performance
    __table_args__ = (
        Index("idx_fatigue_analysis_client_date", "client_id", "analysis_date"),
        Index("idx_fatigue_analysis_session", "session_id", "session_type"),
        Index("idx_fatigue_analysis_risk", "risk_level"),
    )


class FatigueAlert(BaseModel):
    __tablename__ = "fatigue_alerts"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    fatigue_analysis_id = Column(
        Integer, ForeignKey("fatigue_analysis.id"), nullable=True
    )
    alert_type = Column(
        String(50), nullable=False
    )  # "overtraining", "recovery_needed", "session_adjustment"
    severity = Column(String(20), nullable=False)  # "low", "medium", "high", "critical"
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    recommendations = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(Integer, nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Relationships
    client = relationship("ClientProfile")
    trainer = relationship("Trainer")
    fatigue_analysis = relationship("FatigueAnalysis", back_populates="alerts")

    # Indexes for performance
    __table_args__ = (
        Index("idx_fatigue_alert_client", "client_id"),
        Index("idx_fatigue_alert_trainer", "trainer_id"),
        Index("idx_fatigue_alert_type", "alert_type"),
        Index("idx_fatigue_alert_severity", "severity"),
        Index("idx_fatigue_alert_unread", "is_read"),
    )


class WorkloadTracking(BaseModel):
    __tablename__ = "workload_tracking"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey("client_profiles.id"), nullable=False)
    tracking_date = Column(Date, nullable=False)

    # Daily workload metrics
    total_volume = Column(Float, nullable=True)  # total sets * reps * weight
    total_duration = Column(Integer, nullable=True)  # total training time in minutes
    intensity_score = Column(Float, nullable=True)  # calculated intensity rating
    perceived_exertion_avg = Column(Float, nullable=True)  # average RPE for the day

    # Weekly cumulative metrics (calculated)
    weekly_volume = Column(Float, nullable=True)
    weekly_intensity = Column(Float, nullable=True)
    weekly_fatigue = Column(Float, nullable=True)

    # Training stress balance
    acute_workload = Column(Float, nullable=True)  # 7-day workload
    chronic_workload = Column(Float, nullable=True)  # 28-day workload
    training_stress_balance = Column(Float, nullable=True)  # acute/chronic ratio

    # Relationships
    client = relationship("ClientProfile")

    # Indexes for performance
    __table_args__ = (
        Index("idx_workload_tracking_client_date", "client_id", "tracking_date"),
        Index("idx_workload_tracking_date", "tracking_date"),
    )


# Session Programming Enhancement Models


class TrainingBlockType(BaseModel):
    """Training block types for session programming"""

    __tablename__ = "training_block_types"

    name = Column(
        String(100), nullable=False, unique=True, index=True
    )  # e.g., "Warm Up", "Core"
    description = Column(Text, nullable=True)
    is_predefined = Column(
        Boolean, default=True
    )  # True for system-defined, False for custom
    created_by_trainer_id = Column(
        Integer, ForeignKey("trainers.id"), nullable=True
    )  # For custom blocks
    color = Column(String(7), nullable=True)  # Hex color code for UI
    icon = Column(String(50), nullable=True)  # Icon identifier for UI

    # Relationships
    created_by_trainer = relationship("Trainer")
    session_blocks = relationship("SessionBlock", back_populates="block_type")

    # Indexes
    __table_args__ = (
        Index("idx_block_type_name", "name"),
        Index("idx_block_type_predefined", "is_predefined"),
        Index("idx_block_type_trainer", "created_by_trainer_id"),
    )


class SessionTemplate(BaseModel):
    """Reusable session templates for quick session creation"""

    __tablename__ = "session_templates"

    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    session_type = Column(
        String(100), nullable=False
    )  # e.g., "Strength", "Cardio", "Recovery"
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    difficulty_level = Column(
        String(20), nullable=True
    )  # "beginner", "intermediate", "advanced"
    target_muscles = Column(Text, nullable=True)  # comma-separated muscle groups
    equipment_needed = Column(Text, nullable=True)  # comma-separated equipment list
    is_public = Column(Boolean, default=False)  # Can be shared with other trainers
    usage_count = Column(Integer, default=0)  # Track how often template is used

    # Relationships
    trainer = relationship("Trainer")
    blocks = relationship(
        "SessionTemplateBlock", back_populates="template", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_session_template_trainer", "trainer_id"),
        Index("idx_session_template_name", "name"),
        Index("idx_session_template_public", "is_public"),
        Index("idx_session_template_type", "session_type"),
    )


class SessionTemplateBlock(BaseModel):
    """Blocks within a session template"""

    __tablename__ = "session_template_blocks"

    template_id = Column(Integer, ForeignKey("session_templates.id"), nullable=False)
    block_type_id = Column(
        Integer, ForeignKey("training_block_types.id"), nullable=False
    )
    order_in_template = Column(Integer, nullable=False)
    planned_intensity = Column(Float, nullable=True)  # 0-100%
    planned_volume = Column(Float, nullable=True)  # 0-100%
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    notes = Column(Text, nullable=True)

    # Relationships
    template = relationship("SessionTemplate", back_populates="blocks")
    block_type = relationship("TrainingBlockType")
    exercises = relationship(
        "SessionTemplateExercise",
        back_populates="template_block",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_template_block_template", "template_id"),
        Index("idx_template_block_order", "template_id", "order_in_template"),
    )


class SessionTemplateExercise(BaseModel):
    """Exercises within a session template block"""

    __tablename__ = "session_template_exercises"

    template_block_id = Column(
        Integer, ForeignKey("session_template_blocks.id"), nullable=False
    )
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_in_block = Column(Integer, nullable=False)
    set_type = Column(Enum(SetTypeEnum), nullable=False, default=SetTypeEnum.single_set)
    planned_sets = Column(Integer, nullable=True)
    planned_reps = Column(String(20), nullable=True)  # e.g., "8-12", "5", "10-15"
    planned_weight = Column(Float, nullable=True)  # in kg
    planned_duration = Column(Integer, nullable=True)  # in seconds
    planned_distance = Column(Float, nullable=True)  # in meters
    planned_rest = Column(Integer, nullable=True)  # rest time in seconds
    effort_character = Column(Enum(EffortCharacterEnum), nullable=True)
    effort_value = Column(
        Float, nullable=True
    )  # RPE value, RIR value, or Velocity Loss %
    notes = Column(Text, nullable=True)

    # Relationships
    template_block = relationship("SessionTemplateBlock", back_populates="exercises")
    exercise = relationship("Exercise")

    # Indexes
    __table_args__ = (
        Index("idx_template_exercise_block", "template_block_id"),
        Index("idx_template_exercise_order", "template_block_id", "order_in_block"),
    )


class SessionBlock(BaseModel):
    """Training blocks within a session"""

    __tablename__ = "session_blocks"

    training_session_id = Column(
        Integer, ForeignKey("training_sessions.id"), nullable=False
    )
    block_type_id = Column(
        Integer, ForeignKey("training_block_types.id"), nullable=False
    )
    order_in_session = Column(Integer, nullable=False)
    planned_intensity = Column(Float, nullable=True)  # 0-100%
    planned_volume = Column(Float, nullable=True)  # 0-100%
    actual_intensity = Column(Float, nullable=True)  # 0-100%
    actual_volume = Column(Float, nullable=True)  # 0-100%
    estimated_duration = Column(Integer, nullable=True)  # in minutes
    actual_duration = Column(Integer, nullable=True)  # in minutes
    notes = Column(Text, nullable=True)

    # Relationships
    training_session = relationship("TrainingSession")
    block_type = relationship("TrainingBlockType", back_populates="session_blocks")
    exercises = relationship(
        "SessionBlockExercise",
        back_populates="session_block",
        cascade="all, delete-orphan",
    )

    # Indexes
    __table_args__ = (
        Index("idx_session_block_session", "training_session_id"),
        Index("idx_session_block_order", "training_session_id", "order_in_session"),
    )


class SessionBlockExercise(BaseModel):
    """Exercises within a session block with enhanced set types"""

    __tablename__ = "session_block_exercises"

    session_block_id = Column(Integer, ForeignKey("session_blocks.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    order_in_block = Column(Integer, nullable=False)
    set_type = Column(Enum(SetTypeEnum), nullable=False, default=SetTypeEnum.single_set)
    superset_group_id = Column(Integer, nullable=True)  # For grouping supersets
    dropset_sequence = Column(Integer, nullable=True)  # For dropset ordering

    # Planned metrics
    planned_sets = Column(Integer, nullable=True)
    planned_reps = Column(String(20), nullable=True)  # e.g., "8-12", "5", "10-15"
    planned_weight = Column(Float, nullable=True)  # in kg
    planned_duration = Column(Integer, nullable=True)  # in seconds
    planned_distance = Column(Float, nullable=True)  # in meters
    planned_rest = Column(Integer, nullable=True)  # rest time in seconds

    # Effort character metrics
    effort_character = Column(Enum(EffortCharacterEnum), nullable=True)
    effort_value = Column(
        Float, nullable=True
    )  # RPE value, RIR value, or Velocity Loss %

    # Actual metrics
    actual_sets = Column(Integer, nullable=True)
    actual_reps = Column(String(20), nullable=True)
    actual_weight = Column(Float, nullable=True)
    actual_duration = Column(Integer, nullable=True)
    actual_distance = Column(Float, nullable=True)
    actual_rest = Column(Integer, nullable=True)
    actual_effort_value = Column(Float, nullable=True)

    notes = Column(Text, nullable=True)

    # Relationships
    session_block = relationship("SessionBlock", back_populates="exercises")
    exercise = relationship("Exercise")

    # Indexes
    __table_args__ = (
        Index("idx_block_exercise_block", "session_block_id"),
        Index("idx_block_exercise_order", "session_block_id", "order_in_block"),
        Index("idx_block_exercise_superset", "superset_group_id"),
        Index("idx_block_exercise_set_type", "set_type"),
    )
