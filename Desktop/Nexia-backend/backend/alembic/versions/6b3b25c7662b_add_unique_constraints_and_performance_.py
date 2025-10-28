"""add_unique_constraints_and_performance_indexes

Revision ID: 6b3b25c7662b
Revises: 4ac25bdb723e
Create Date: 2025-08-13 14:27:02.137549

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b3b25c7662b"
down_revision: Union[str, Sequence[str], None] = "4ac25bdb723e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Add unique constraint to client_progress table
    op.create_unique_constraint(
        "idx_client_progress_unique", "client_progress", ["client_id", "fecha_registro"]
    )

    # Add unique constraint to progress_tracking table
    op.create_unique_constraint(
        "idx_progress_tracking_unique",
        "progress_tracking",
        ["client_id", "exercise_id", "tracking_date"],
    )

    # Add performance indexes for training_sessions table
    op.create_index(
        "idx_training_session_coach_client",
        "training_sessions",
        ["trainer_id", "client_id"],
    )
    op.create_index("idx_training_session_date", "training_sessions", ["session_date"])
    op.create_index("idx_training_session_status", "training_sessions", ["status"])

    # Add performance indexes for standalone_sessions table
    op.create_index(
        "idx_standalone_session_coach_client",
        "standalone_sessions",
        ["trainer_id", "client_id"],
    )
    op.create_index(
        "idx_standalone_session_date", "standalone_sessions", ["session_date"]
    )
    op.create_index("idx_standalone_session_status", "standalone_sessions", ["status"])

    # Trainer-client: add normalized email column and unique index per trainer
    with op.batch_alter_table("trainer_clients") as batch_op:
        batch_op.add_column(
            sa.Column("client_email_norm", sa.String(length=255), nullable=True)
        )

    # Backfill normalized email from client_profiles.mail
    op.execute(
        """
        UPDATE trainer_clients AS tc
        SET client_email_norm = LOWER(cp.mail)
        FROM client_profiles AS cp
        WHERE cp.id = tc.client_id
        """
    )

    # Create unique index to enforce per-trainer unique email
    op.create_index(
        "uq_trainer_client_email_per_trainer",
        "trainer_clients",
        ["trainer_id", "client_email_norm"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Remove performance indexes for standalone_sessions table
    op.drop_index("idx_standalone_session_status", "standalone_sessions")
    op.drop_index("idx_standalone_session_date", "standalone_sessions")
    op.drop_index("idx_standalone_session_coach_client", "standalone_sessions")

    # Remove performance indexes for training_sessions table
    op.drop_index("idx_training_session_status", "training_sessions")
    op.drop_index("idx_training_session_date", "training_sessions")
    op.drop_index("idx_training_session_coach_client", "training_sessions")

    # Remove unique constraints
    op.drop_index("uq_trainer_client_email_per_trainer", table_name="trainer_clients")
    with op.batch_alter_table("trainer_clients") as batch_op:
        batch_op.drop_column("client_email_norm")
    op.drop_constraint(
        "idx_progress_tracking_unique", "progress_tracking", type_="unique"
    )
    op.drop_constraint("idx_client_progress_unique", "client_progress", type_="unique")
