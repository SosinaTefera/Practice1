"""add users, roles, permissions for auth

Revision ID: d03ab5db88c2
Revises: cf700f40853d
Create Date: 2025-08-19 15:35:15.198871

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d03ab5db88c2"
down_revision: Union[str, Sequence[str], None] = "cf700f40853d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "email", sa.String(length=255), nullable=False, unique=True, index=True
        ),
        sa.Column(
            "username", sa.String(length=100), nullable=False, unique=True, index=True
        ),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "name", sa.String(length=100), nullable=False, unique=True, index=True
        ),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "name", sa.String(length=100), nullable=False, unique=True, index=True
        ),
        sa.Column("resource", sa.String(length=100), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )

    op.create_table(
        "user_roles",
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("roles.id"), primary_key=True),
    )

    # Add user_id column to trainers (nullable initially)
    with op.batch_alter_table("trainers") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=True, unique=True)
        )
        batch_op.create_foreign_key("fk_trainers_user_id", "users", ["user_id"], ["id"])

    # Add user_id column to client_profiles (nullable initially)
    with op.batch_alter_table("client_profiles") as batch_op:
        batch_op.add_column(
            sa.Column("user_id", sa.Integer(), nullable=True, unique=True)
        )
        batch_op.create_foreign_key(
            "fk_client_profiles_user_id", "users", ["user_id"], ["id"]
        )

    # seed roles
    op.execute(
        """
        INSERT INTO roles (name, description) VALUES
        ('admin', 'System administrator'),
        ('trainer', 'Coach/Trainer'),
        ('athlete', 'Client/Athlete')
        ON CONFLICT (name) DO NOTHING
    """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")
    op.drop_table("users")
