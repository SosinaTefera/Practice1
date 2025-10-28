"""add trainer professional fields

Revision ID: add_trainer_professional_fields
Revises: f1a2b3c4d5e6
Create Date: 2025-09-24 15:00:00
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_trainer_professional_fields"
down_revision = "f1a2b3c4d5e6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("trainers") as batch_op:
        batch_op.add_column(
            sa.Column("occupation", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("training_modality", sa.String(length=50), nullable=True)
        )
        batch_op.add_column(
            sa.Column("location_country", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("location_city", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("billing_id", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("billing_address", sa.String(length=255), nullable=True)
        )
        batch_op.add_column(
            sa.Column("billing_postal_code", sa.String(length=20), nullable=True)
        )
        batch_op.add_column(
            sa.Column("specialty", sa.String(length=100), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("trainers") as batch_op:
        batch_op.drop_column("specialty")
        batch_op.drop_column("billing_postal_code")
        batch_op.drop_column("billing_address")
        batch_op.drop_column("billing_id")
        batch_op.drop_column("location_city")
        batch_op.drop_column("location_country")
        batch_op.drop_column("training_modality")
        batch_op.drop_column("occupation")
