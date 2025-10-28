from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/catalogs", tags=["catalogs"])


# Minimal, non-breaking static catalogs. These can be replaced with DB-backed
# sources later without changing the API surface.

COUNTRIES = [
    {"code": "ES", "name": "España"},
    {"code": "US", "name": "United States"},
    {"code": "GB", "name": "United Kingdom"},
    {"code": "FR", "name": "France"},
]

CITIES_BY_COUNTRY = {
    "ES": ["Madrid", "Barcelona", "Valencia", "Sevilla"],
    "US": ["New York", "San Francisco", "Austin", "Miami"],
    "GB": ["London", "Manchester", "Birmingham"],
    "FR": ["Paris", "Lyon", "Marseille"],
}


TRAINER_OCCUPATIONS = [
    "personal_trainer",
    "strength_conditioning_coach",
    "physiotherapist",
    "nutrition_coach",
]

TRAINING_MODALITIES = [
    "in_person",
    "online",
    "hybrid",
]

TRAINER_SPECIALTIES = [
    "weight_loss",
    "muscle_gain",
    "rehabilitation",
    "performance",
]


@router.get("/countries")
def list_countries():
    return COUNTRIES


@router.get("/cities")
def list_cities(country: str = Query(..., description="ISO country code, e.g., ES")):
    country = country.upper()
    if country not in CITIES_BY_COUNTRY:
        raise HTTPException(status_code=404, detail="Country not found")
    return {"country": country, "cities": CITIES_BY_COUNTRY[country]}


@router.get("/trainer/occupations")
def list_trainer_occupations():
    return TRAINER_OCCUPATIONS


@router.get("/trainer/modalities")
def list_training_modalities():
    return TRAINING_MODALITIES


@router.get("/trainer/specialties")
def list_trainer_specialties():
    return TRAINER_SPECIALTIES
