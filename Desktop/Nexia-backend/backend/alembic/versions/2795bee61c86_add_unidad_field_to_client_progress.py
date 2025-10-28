"""add_unidad_field_to_client_progress

Revision ID: 2795bee61c86
Revises: 6b3b25c7662b
Create Date: 2025-08-13 14:49:12.123456

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2795bee61c86"
down_revision: Union[str, Sequence[str], None] = "6b3b25c7662b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add unidad column to client_progress table
    op.add_column(
        "client_progress",
        sa.Column("unidad", sa.String(20), nullable=True, server_default="metric"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove unidad column from client_progress table
    op.drop_column("client_progress", "unidad")
