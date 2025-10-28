#!/usr/bin/env python3
"""
Professional Exercise Import Script
Imports exercise data from "Ejercicios2" sheet of "Pantallas app.xlsx" into the database.

This script:
1. Reads the Excel file with proper error handling
2. Validates and cleans the data
3. Maps Excel columns to database fields
4. Handles enum conversions
5. Provides detailed logging and progress tracking
6. Supports both initial import and data updates
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

# Add the backend directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "backend"))

from app.db.models import (
    EquipmentEnum,
    Exercise,
    ExerciseClassificationEnum,
    ExerciseLevelEnum,
    ExerciseTypeEnum,
    LoadTypeEnum,
    MovementPatternEnum,
)
from app.db.session import SessionLocal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("exercise_import.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)


class ExerciseImporter:
    """Professional exercise data importer"""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.session: Optional[Session] = None

    def _map_excel_to_db_columns(self) -> Dict[str, str]:
        """Map Excel column names to database field names"""
        return {
            "ID": "exercise_id",
            "Name": "nombre",
            "Type": "tipo",
            "Category": "categoria",
            "Equipment": "equipo",
            "Movement Pattern": "patron_movimiento",
            "Level": "nivel",
            "Primary Muscles": "musculatura_principal",
            "Secondary Muscles": "musculatura_secundaria",
            "Load Type": "tipo_carga",
        }

    def _convert_enum_value(self, value: str, enum_class) -> Optional[str]:
        """Convert string value to enum value with error handling"""
        if pd.isna(value) or value == "":
            return None
        value = str(value).strip()
        # Try direct match
        for enum_member in enum_class:
            if value.lower() == enum_member.value.lower():
                return enum_member.value
        # Try match ignoring accents/case
        import unicodedata

        def normalize(s):
            return (
                unicodedata.normalize("NFKD", s)
                .encode("ASCII", "ignore")
                .decode("ASCII")
                .lower()
            )

        for enum_member in enum_class:
            if normalize(value) == normalize(enum_member.value):
                return enum_member.value
        logger.warning(f"Could not map value '{value}' to enum {enum_class.__name__}")
        return None

    def _clean_muscle_data(self, muscle_data: str) -> str:
        """Clean and standardize muscle data"""
        if pd.isna(muscle_data) or muscle_data == "":
            return ""

        # Clean the data
        cleaned = str(muscle_data).strip()
        # Remove extra spaces and standardize separators
        cleaned = ", ".join([muscle.strip() for muscle in cleaned.split(",")])
        return cleaned

    def _prepare_exercise_data(self, row: pd.Series) -> Dict[str, Any]:
        """Prepare exercise data from Excel row"""
        column_mapping = self._map_excel_to_db_columns()

        exercise_data = {}

        for excel_col, db_field in column_mapping.items():
            if excel_col in row.index:
                value = row[excel_col]

                if pd.isna(value) or value == "":
                    continue

                # Handle specific field conversions
                if db_field == "exercise_id":
                    exercise_data[db_field] = str(value).strip()
                elif db_field == "nombre":
                    exercise_data[db_field] = str(value).strip()
                elif db_field == "tipo":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, ExerciseTypeEnum
                    )
                elif db_field == "categoria":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, ExerciseClassificationEnum
                    )
                elif db_field == "nivel":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, ExerciseLevelEnum
                    )
                elif db_field == "equipo":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, EquipmentEnum
                    )
                elif db_field == "patron_movimiento":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, MovementPatternEnum
                    )
                elif db_field == "tipo_carga":
                    exercise_data[db_field] = self._convert_enum_value(
                        value, LoadTypeEnum
                    )
                elif db_field == "musculatura_principal":
                    exercise_data[db_field] = self._clean_muscle_data(value)
                elif db_field == "musculatura_secundaria":
                    exercise_data[db_field] = self._clean_muscle_data(value)
                else:
                    exercise_data[db_field] = str(value).strip()

        return exercise_data

    def import_exercises(self, update_existing: bool = False) -> Dict[str, int]:
        """Import exercises from Excel file"""
        logger.info(f"Starting exercise import from {self.file_path}")

        try:
            # Read Excel file
            df = pd.read_excel(self.file_path, sheet_name="Ejercicios2", header=2)
            logger.info(f"Successfully read {len(df)} rows from Ejercicios2 sheet")

            # Initialize database session
            self.session = SessionLocal()

            stats = {
                "total_rows": len(df),
                "imported": 0,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
            }

            for index, row in df.iterrows():
                try:
                    # Skip empty rows
                    if pd.isna(row["ID"]) or str(row["ID"]).strip() == "":
                        stats["skipped"] += 1
                        continue

                    exercise_data = self._prepare_exercise_data(row)

                    # Validate required fields
                    required_fields = [
                        "exercise_id",
                        "nombre",
                        "tipo",
                        "categoria",
                        "nivel",
                        "equipo",
                        "patron_movimiento",
                        "tipo_carga",
                        "musculatura_principal",
                    ]
                    missing_fields = [
                        field
                        for field in required_fields
                        if field not in exercise_data or exercise_data[field] is None
                    ]

                    if missing_fields:
                        logger.warning(
                            f"Row {index + 2}: Missing required fields: {missing_fields}"
                        )
                        stats["errors"] += 1
                        continue

                    # Check if exercise already exists
                    existing_exercise = (
                        self.session.query(Exercise)
                        .filter(Exercise.exercise_id == exercise_data["exercise_id"])
                        .first()
                    )

                    if existing_exercise:
                        if update_existing:
                            # Update existing exercise
                            for field, value in exercise_data.items():
                                setattr(existing_exercise, field, value)
                            stats["updated"] += 1
                            logger.info(f"Updated exercise: {exercise_data['nombre']}")
                        else:
                            # Skip existing exercise
                            stats["skipped"] += 1
                            logger.info(
                                f"Skipped existing exercise: {exercise_data['nombre']}"
                            )
                    else:
                        # Create new exercise
                        exercise = Exercise(**exercise_data)
                        self.session.add(exercise)
                        stats["imported"] += 1
                        logger.info(f"Imported exercise: {exercise_data['nombre']}")

                    # Commit every 10 records for better performance
                    if (stats["imported"] + stats["updated"]) % 10 == 0:
                        self.session.commit()
                        logger.info(
                            f"Progress: {stats['imported'] + stats['updated']} exercises processed"
                        )

                except Exception as e:
                    logger.error(f"Error processing row {index + 2}: {str(e)}")
                    stats["errors"] += 1
                    continue

            # Final commit
            self.session.commit()

            logger.info("Import completed successfully!")
            logger.info(f"Statistics: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Import failed: {str(e)}")
            if self.session:
                self.session.rollback()
            raise
        finally:
            if self.session:
                self.session.close()


def main():
    """Main function to run the import (automatic, no prompt)"""
    file_path = "../Pantallas app.xlsx"

    if not os.path.exists(file_path):
        logger.error(f"Excel file not found: {file_path}")
        sys.exit(1)

    importer = ExerciseImporter(file_path)
    try:
        stats = importer.import_exercises(update_existing=False)
        print("\n" + "=" * 50)
        print("IMPORT RESULTS")
        print("=" * 50)
        print(f"Total rows processed: {stats['total_rows']}")
        print(f"New exercises imported: {stats['imported']}")
        print(f"Existing exercises updated: {stats['updated']}")
        print(f"Exercises skipped: {stats['skipped']}")
        print(f"Errors encountered: {stats['errors']}")
        print("=" * 50)
    except KeyboardInterrupt:
        print("\nImport cancelled by user.")
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
