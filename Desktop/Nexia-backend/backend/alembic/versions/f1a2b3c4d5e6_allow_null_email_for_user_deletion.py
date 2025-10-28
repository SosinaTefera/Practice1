"""allow_null_email_for_user_deletion

Revision ID: f1a2b3c4d5e6
Revises: e29d826e8854
Create Date: 2024-01-01 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "f1a2b3c4d5e6"
down_revision = "e29d826e8854"
branch_labels = None
depends_on = None


def upgrade():
    # Allow NULL values for email field to enable user deletion with email clearing
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=True)


def downgrade():
    # Revert email field to NOT NULL
    op.alter_column("users", "email", existing_type=sa.String(255), nullable=False)
