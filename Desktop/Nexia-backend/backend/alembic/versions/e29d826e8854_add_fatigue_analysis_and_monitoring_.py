"""Add fatigue analysis and monitoring tables

Revision ID: e29d826e8854
Revises: 1760c194fd15
Create Date: 2025-09-01 16:22:01.073488

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e29d826e8854"
down_revision: Union[str, Sequence[str], None] = "1760c194fd15"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Create fatigue_analysis table
    op.create_table(
        "fatigue_analysis",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("session_type", sa.String(length=50), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        # Pre-session metrics
        sa.Column("pre_fatigue_level", sa.Integer(), nullable=True),
        sa.Column("pre_energy_level", sa.Integer(), nullable=True),
        sa.Column("pre_motivation_level", sa.Integer(), nullable=True),
        sa.Column("pre_sleep_quality", sa.Integer(), nullable=True),
        sa.Column("pre_stress_level", sa.Integer(), nullable=True),
        sa.Column("pre_muscle_soreness", sa.String(length=255), nullable=True),
        # Post-session metrics
        sa.Column("post_fatigue_level", sa.Integer(), nullable=True),
        sa.Column("post_energy_level", sa.Integer(), nullable=True),
        sa.Column("post_motivation_level", sa.Integer(), nullable=True),
        sa.Column("post_muscle_soreness", sa.String(length=255), nullable=True),
        # Calculated metrics
        sa.Column("fatigue_delta", sa.Integer(), nullable=True),
        sa.Column("energy_delta", sa.Integer(), nullable=True),
        sa.Column("workload_score", sa.Float(), nullable=True),
        sa.Column("recovery_need_score", sa.Float(), nullable=True),
        # Analysis results
        sa.Column("risk_level", sa.String(length=50), nullable=True),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("next_session_adjustment", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create fatigue_alerts table
    op.create_table(
        "fatigue_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=False),
        sa.Column("fatigue_analysis_id", sa.Integer(), nullable=True),
        sa.Column("alert_type", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=True),
        sa.Column("is_read", sa.Boolean(), default=False, nullable=True),
        sa.Column("is_resolved", sa.Boolean(), default=False, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.Integer(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create workload_tracking table
    op.create_table(
        "workload_tracking",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column("tracking_date", sa.Date(), nullable=False),
        # Daily workload metrics
        sa.Column("total_volume", sa.Float(), nullable=True),
        sa.Column("total_duration", sa.Integer(), nullable=True),
        sa.Column("intensity_score", sa.Float(), nullable=True),
        sa.Column("perceived_exertion_avg", sa.Float(), nullable=True),
        # Weekly cumulative metrics
        sa.Column("weekly_volume", sa.Float(), nullable=True),
        sa.Column("weekly_intensity", sa.Float(), nullable=True),
        sa.Column("weekly_fatigue", sa.Float(), nullable=True),
        # Training stress balance
        sa.Column("acute_workload", sa.Float(), nullable=True),
        sa.Column("chronic_workload", sa.Float(), nullable=True),
        sa.Column("training_stress_balance", sa.Float(), nullable=True),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add foreign key constraints
    op.create_foreign_key(
        "fk_fatigue_analysis_client",
        "fatigue_analysis",
        "client_profiles",
        ["client_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_fatigue_alerts_client",
        "fatigue_alerts",
        "client_profiles",
        ["client_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_fatigue_alerts_trainer",
        "fatigue_alerts",
        "trainers",
        ["trainer_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_fatigue_alerts_analysis",
        "fatigue_alerts",
        "fatigue_analysis",
        ["fatigue_analysis_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_workload_tracking_client",
        "workload_tracking",
        "client_profiles",
        ["client_id"],
        ["id"],
    )

    # Add indexes for performance
    op.create_index(
        "idx_fatigue_analysis_client_date",
        "fatigue_analysis",
        ["client_id", "analysis_date"],
    )
    op.create_index(
        "idx_fatigue_analysis_session",
        "fatigue_analysis",
        ["session_id", "session_type"],
    )
    op.create_index("idx_fatigue_analysis_risk", "fatigue_analysis", ["risk_level"])
    op.create_index(
        "idx_fatigue_alert_client_trainer",
        "fatigue_alerts",
        ["client_id", "trainer_id"],
    )
    op.create_index(
        "idx_fatigue_alert_type_severity", "fatigue_alerts", ["alert_type", "severity"]
    )
    op.create_index(
        "idx_fatigue_alert_unread", "fatigue_alerts", ["is_read", "is_resolved"]
    )
    op.create_index(
        "idx_workload_tracking_client_date",
        "workload_tracking",
        ["client_id", "tracking_date"],
    )
    op.create_index(
        "idx_workload_tracking_tsb", "workload_tracking", ["training_stress_balance"]
    )


def downgrade() -> None:
    """Downgrade schema."""

    # Drop indexes
    op.drop_index("idx_workload_tracking_tsb", "workload_tracking")
    op.drop_index("idx_workload_tracking_client_date", "workload_tracking")
    op.drop_index("idx_fatigue_alert_unread", "fatigue_alerts")
    op.drop_index("idx_fatigue_alert_type_severity", "fatigue_alerts")
    op.drop_index("idx_fatigue_alert_client_trainer", "fatigue_alerts")
    op.drop_index("idx_fatigue_analysis_risk", "fatigue_analysis")
    op.drop_index("idx_fatigue_analysis_session", "fatigue_analysis")
    op.drop_index("idx_fatigue_analysis_client_date", "fatigue_analysis")

    # Drop foreign key constraints
    op.drop_constraint(
        "fk_workload_tracking_client", "workload_tracking", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_fatigue_alerts_analysis", "fatigue_alerts", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_fatigue_alerts_trainer", "fatigue_alerts", type_="foreignkey"
    )
    op.drop_constraint("fk_fatigue_alerts_client", "fatigue_alerts", type_="foreignkey")
    op.drop_constraint(
        "fk_fatigue_analysis_client", "fatigue_analysis", type_="foreignkey"
    )

    # Drop tables
    op.drop_table("workload_tracking")
    op.drop_table("fatigue_alerts")
    op.drop_table("fatigue_analysis")
