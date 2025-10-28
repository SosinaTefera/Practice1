"""link users to trainers and clients (add user_id FKs)

Revision ID: 1760c194fd15
Revises: d03ab5db88c2
Create Date: 2025-08-19 15:58:50.132734

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1760c194fd15"
down_revision: Union[str, Sequence[str], None] = "d03ab5db88c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add user_id to trainers if missing
    with op.batch_alter_table("trainers") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_trainers_user_id", ["user_id"])
        batch_op.create_foreign_key("fk_trainers_user_id", "users", ["user_id"], ["id"])

    # Add user_id to client_profiles if missing
    with op.batch_alter_table("client_profiles") as batch_op:
        batch_op.add_column(sa.Column("user_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_client_profiles_user_id", ["user_id"])
        batch_op.create_foreign_key(
            "fk_client_profiles_user_id", "users", ["user_id"], ["id"]
        )


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("client_profiles") as batch_op:
        batch_op.drop_constraint("fk_client_profiles_user_id", type_="foreignkey")
        batch_op.drop_constraint("uq_client_profiles_user_id", type_="unique")
        batch_op.drop_column("user_id")

    with op.batch_alter_table("trainers") as batch_op:
        batch_op.drop_constraint("fk_trainers_user_id", type_="foreignkey")
        batch_op.drop_constraint("uq_trainers_user_id", type_="unique")
        batch_op.drop_column("user_id")
