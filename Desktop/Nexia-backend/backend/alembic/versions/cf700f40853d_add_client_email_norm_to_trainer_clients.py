"""add client_email_norm to trainer_clients

Revision ID: cf700f40853d
Revises: 7f1b2b0e9abc
Create Date: 2025-08-19 10:55:09.912037

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "cf700f40853d"
down_revision: Union[str, Sequence[str], None] = "7f1b2b0e9abc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add the normalized email column
    with op.batch_alter_table("trainer_clients") as batch_op:
        batch_op.add_column(
            sa.Column("client_email_norm", sa.String(length=255), nullable=True)
        )

    # Backfill normalized emails from client_profiles.mail (lowercased)
    op.execute(
        """
        UPDATE trainer_clients AS tc
        SET client_email_norm = LOWER(cp.mail)
        FROM client_profiles AS cp
        WHERE cp.id = tc.client_id
        """
    )

    # Create unique index per trainer on normalized email
    op.create_index(
        "uq_trainer_client_email_per_trainer",
        "trainer_clients",
        ["trainer_id", "client_email_norm"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_trainer_client_email_per_trainer", table_name="trainer_clients")
    with op.batch_alter_table("trainer_clients") as batch_op:
        batch_op.drop_column("client_email_norm")
