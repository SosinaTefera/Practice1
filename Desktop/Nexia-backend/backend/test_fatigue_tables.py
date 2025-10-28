#!/usr/bin/env python3
"""Test script to check if fatigue analysis tables exist"""

from sqlalchemy import text

from app.db.session import engine


def test_fatigue_tables():
    """Check if the new fatigue analysis tables exist"""
    try:
        with engine.connect() as connection:
            # Check for the new tables
            result = connection.execute(
                text(
                    """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name IN (
                    'fatigue_analysis', 'fatigue_alerts', 'workload_tracking'
                )
                ORDER BY table_name
            """
                )
            )

            tables = [row[0] for row in result]

            print("✅ Database connection successful!")
            print(f"📊 New tables found: {tables}")

            if len(tables) == 3:
                print("🎉 All fatigue analysis tables are working!")
                return True
            else:
                print(f"⚠️  Missing tables. Expected 3, found {len(tables)}")
                return False

    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False


if __name__ == "__main__":
    test_fatigue_tables()
