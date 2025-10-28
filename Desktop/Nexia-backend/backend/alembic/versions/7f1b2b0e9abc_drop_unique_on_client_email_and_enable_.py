"""Drop unique on client email and enable unaccent

Revision ID: 7f1b2b0e9abc
Revises: 2795bee61c86
Create Date: 2025-08-14 10:05:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7f1b2b0e9abc"
down_revision: Union[str, Sequence[str], None] = "2795bee61c86"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name

    # Safely drop unique constraint/index on client_profiles.mail if present
    if dialect == "postgresql":
        # Drop constraint if it exists (default name when using unique=True on a column)
        conn.execute(
            sa.text(
                "ALTER TABLE client_profiles DROP CONSTRAINT IF EXISTS "
                "client_profiles_mail_key"
            )
        )
        # Also drop any unique index by that name if lingering
        conn.execute(sa.text("DROP INDEX IF EXISTS client_profiles_mail_key"))
        # Ensure a non-unique index exists for performance
        conn.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS idx_client_email ON client_profiles (mail)"
            )
        )
        # Try to enable unaccent; ignore insufficient privileges or missing extension
        conn.execute(
            sa.text(
                "DO $$ BEGIN \n"
                "  BEGIN \n"
                "    CREATE EXTENSION IF NOT EXISTS unaccent; \n"
                "  EXCEPTION WHEN insufficient_privilege THEN \n"
                "    RAISE NOTICE 'Skipping unaccent (insufficient privileges)'; \n"
                "  WHEN undefined_file THEN \n"
                "    RAISE NOTICE 'Skipping unaccent (extension not available)'; \n"
                "  END; \n"
                "END $$;"
            )
        )
    else:
        # For other dialects, attempt via Alembic helpers without failing build
        try:
            op.drop_constraint(
                "client_profiles_mail_key", "client_profiles", type_="unique"
            )
        except Exception:
            pass
        try:
            op.drop_index("client_profiles_mail_key", table_name="client_profiles")
        except Exception:
            pass
        try:
            op.create_index(
                "idx_client_email", "client_profiles", ["mail"], unique=False
            )
        except Exception:
            pass


def downgrade() -> None:
    conn = op.get_bind()
    dialect = conn.dialect.name
    # Remove non-unique index (optional)
    try:
        op.drop_index("idx_client_email", table_name="client_profiles")
    except Exception:
        pass
    # Do not recreate a unique constraint to avoid conflicts with existing data
    if dialect == "postgresql":
        try:
            conn.execute(sa.text("DROP EXTENSION IF EXISTS unaccent"))
        except Exception:
            pass
