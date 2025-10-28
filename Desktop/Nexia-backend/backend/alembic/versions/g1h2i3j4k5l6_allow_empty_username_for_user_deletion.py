"""allow_empty_username_for_user_deletion

Revision ID: g1h2i3j4k5l6
Revises: 441abc484588
Create Date: 2025-09-18 20:45:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "g1h2i3j4k5l6"
down_revision = "441abc484588"
branch_labels = None
depends_on = None


def upgrade():
    # Allow NULL values for username field to enable user deletion
    op.alter_column("users", "username", existing_type=sa.String(100), nullable=True)


def downgrade():
    # Revert username field to NOT NULL
    op.alter_column("users", "username", existing_type=sa.String(100), nullable=False)
