#!/usr/bin/env python3
"""
Clean duplicate data before applying unique constraints.
This script removes duplicate entries to prepare for the migration.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# sessionmaker imported previously; not needed here

# Load environment variables
load_dotenv()


def get_database_url():
    """Get database URL from environment or use default"""
    return os.getenv("DATABASE_URL", "sqlite:///./nexia.db")


def clean_duplicate_data():
    """Clean duplicate data from progress tables"""

    # Create database connection
    database_url = get_database_url()
    engine = create_engine(database_url)

    print(f"🔗 Connecting to database: {database_url}")

    try:
        with engine.connect() as conn:
            print("✅ Database connection successful")

            # Clean client_progress duplicates
            print("\n🧹 Cleaning client_progress duplicates...")

            # Find duplicates in client_progress
            duplicate_query = """
            SELECT client_id, fecha_registro, COUNT(*) as count
            FROM client_progress
            GROUP BY client_id, fecha_registro
            HAVING COUNT(*) > 1
            ORDER BY client_id, fecha_registro
            """

            duplicates = conn.execute(text(duplicate_query)).fetchall()

            if duplicates:
                print(f"Found {len(duplicates)} duplicate groups:")
                for dup in duplicates:
                    print(
                        f"  - Client {dup.client_id} on {dup.fecha_registro}: {dup.count} entries"
                    )

                # Keep the most recent entry for each duplicate group
                clean_query = """
                DELETE FROM client_progress
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM client_progress
                    GROUP BY client_id, fecha_registro
                )
                """

                result = conn.execute(text(clean_query))
                print(
                    f"✅ Removed {result.rowcount} duplicate entries from client_progress"
                )

            else:
                print("✅ No duplicates found in client_progress")

            # Clean progress_tracking duplicates
            print("\n🧹 Cleaning progress_tracking duplicates...")

            # Find duplicates in progress_tracking
            duplicate_query = """
            SELECT client_id, exercise_id, tracking_date, COUNT(*) as count
            FROM progress_tracking
            GROUP BY client_id, exercise_id, tracking_date
            HAVING COUNT(*) > 1
            ORDER BY client_id, exercise_id, tracking_date
            """

            duplicates = conn.execute(text(duplicate_query)).fetchall()

            if duplicates:
                print(f"Found {len(duplicates)} duplicate groups:")
                for dup in duplicates:
                    print(
                        f"  - Client {dup.client_id}, Exercise {dup.exercise_id} on {dup.tracking_date}: {dup.count} entries"
                    )

                # Keep the most recent entry for each duplicate group
                clean_query = """
                DELETE FROM progress_tracking
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM progress_tracking
                    GROUP BY client_id, exercise_id, tracking_date
                )
                """

                result = conn.execute(text(clean_query))
                print(
                    f"✅ Removed {result.rowcount} duplicate entries from progress_tracking"
                )

            else:
                print("✅ No duplicates found in progress_tracking")

            # Commit changes
            conn.commit()
            print("\n✅ All duplicate data cleaned successfully!")

    except Exception as e:
        print(f"❌ Error cleaning data: {e}")
        sys.exit(1)

    finally:
        engine.dispose()


if __name__ == "__main__":
    print("🧹 Nexia Database Cleanup Script")
    print("=" * 40)

    # Ask for confirmation
    response = input("\n⚠️  This will remove duplicate data. Continue? (y/N): ")

    if response.lower() in ["y", "yes"]:
        clean_duplicate_data()
        print("\n🎉 Database cleanup completed!")
        print("You can now run: alembic upgrade head")
    else:
        print("❌ Cleanup cancelled.")
