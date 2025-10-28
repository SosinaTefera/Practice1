"""add_session_programming_models

Revision ID: 2025_01_09_session_programming
Revises: 2025_10_03_user_tos_otp
Create Date: 2025-01-09 12:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "2025_01_09_session_programming"
down_revision = "2025_10_03_user_tos_otp"
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types (check if they already exist)
    connection = op.get_bind()

    # Check if settypeenum exists
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'settypeenum'")
    ).fetchone()
    if not result:
        set_type_enum = postgresql.ENUM(
            "single_set", "superset", "dropset", name="settypeenum"
        )
        set_type_enum.create(connection)

    # Check if effortcharacterenum exists
    result = connection.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = 'effortcharacterenum'")
    ).fetchone()
    if not result:
        effort_character_enum = postgresql.ENUM(
            "rpe", "rir", "velocity_loss", name="effortcharacterenum"
        )
        effort_character_enum.create(connection)

    # Create training_block_types table
    op.create_table(
        "training_block_types",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_predefined", sa.Boolean(), nullable=True),
        sa.Column("created_by_trainer_id", sa.Integer(), nullable=True),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by_trainer_id"],
            ["trainers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_block_type_name", "training_block_types", ["name"], unique=False
    )
    op.create_index(
        "idx_block_type_predefined",
        "training_block_types",
        ["is_predefined"],
        unique=False,
    )
    op.create_index(
        "idx_block_type_trainer",
        "training_block_types",
        ["created_by_trainer_id"],
        unique=False,
    )

    # Create session_templates table
    op.create_table(
        "session_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("trainer_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("session_type", sa.String(length=100), nullable=False),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("difficulty_level", sa.String(length=20), nullable=True),
        sa.Column("target_muscles", sa.Text(), nullable=True),
        sa.Column("equipment_needed", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["trainer_id"],
            ["trainers.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_session_template_trainer",
        "session_templates",
        ["trainer_id"],
        unique=False,
    )
    op.create_index(
        "idx_session_template_name", "session_templates", ["name"], unique=False
    )
    op.create_index(
        "idx_session_template_public", "session_templates", ["is_public"], unique=False
    )
    op.create_index(
        "idx_session_template_type", "session_templates", ["session_type"], unique=False
    )

    # Create session_template_blocks table
    op.create_table(
        "session_template_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("block_type_id", sa.Integer(), nullable=False),
        sa.Column("order_in_template", sa.Integer(), nullable=False),
        sa.Column("planned_intensity", sa.Float(), nullable=True),
        sa.Column("planned_volume", sa.Float(), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["block_type_id"],
            ["training_block_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["session_templates.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_template_block_template",
        "session_template_blocks",
        ["template_id"],
        unique=False,
    )
    op.create_index(
        "idx_template_block_order",
        "session_template_blocks",
        ["template_id", "order_in_template"],
        unique=False,
    )

    # Create unique index for training_block_types name
    op.create_index(
        "idx_training_block_types_name",
        "training_block_types",
        ["name"],
        unique=True,
    )

    # Create session_template_exercises table
    op.create_table(
        "session_template_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("template_block_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("order_in_block", sa.Integer(), nullable=False),
        sa.Column(
            "set_type",
            postgresql.ENUM(
                "single_set",
                "superset",
                "dropset",
                name="settypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("planned_sets", sa.Integer(), nullable=True),
        sa.Column("planned_reps", sa.String(length=20), nullable=True),
        sa.Column("planned_weight", sa.Float(), nullable=True),
        sa.Column("planned_duration", sa.Integer(), nullable=True),
        sa.Column("planned_distance", sa.Float(), nullable=True),
        sa.Column("planned_rest", sa.Integer(), nullable=True),
        sa.Column(
            "effort_character",
            postgresql.ENUM(
                "rpe",
                "rir",
                "velocity_loss",
                name="effortcharacterenum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("effort_value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["template_block_id"],
            ["session_template_blocks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_template_exercise_block",
        "session_template_exercises",
        ["template_block_id"],
        unique=False,
    )
    op.create_index(
        "idx_template_exercise_order",
        "session_template_exercises",
        ["template_block_id", "order_in_block"],
        unique=False,
    )

    # Create session_blocks table
    op.create_table(
        "session_blocks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("training_session_id", sa.Integer(), nullable=False),
        sa.Column("block_type_id", sa.Integer(), nullable=False),
        sa.Column("order_in_session", sa.Integer(), nullable=False),
        sa.Column("planned_intensity", sa.Float(), nullable=True),
        sa.Column("planned_volume", sa.Float(), nullable=True),
        sa.Column("actual_intensity", sa.Float(), nullable=True),
        sa.Column("actual_volume", sa.Float(), nullable=True),
        sa.Column("estimated_duration", sa.Integer(), nullable=True),
        sa.Column("actual_duration", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["block_type_id"],
            ["training_block_types.id"],
        ),
        sa.ForeignKeyConstraint(
            ["training_session_id"],
            ["training_sessions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_session_block_session",
        "session_blocks",
        ["training_session_id"],
        unique=False,
    )
    op.create_index(
        "idx_session_block_order",
        "session_blocks",
        ["training_session_id", "order_in_session"],
        unique=False,
    )

    # Create session_block_exercises table
    op.create_table(
        "session_block_exercises",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("session_block_id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("order_in_block", sa.Integer(), nullable=False),
        sa.Column(
            "set_type",
            postgresql.ENUM(
                "single_set",
                "superset",
                "dropset",
                name="settypeenum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("superset_group_id", sa.Integer(), nullable=True),
        sa.Column("dropset_sequence", sa.Integer(), nullable=True),
        sa.Column("planned_sets", sa.Integer(), nullable=True),
        sa.Column("planned_reps", sa.String(length=20), nullable=True),
        sa.Column("planned_weight", sa.Float(), nullable=True),
        sa.Column("planned_duration", sa.Integer(), nullable=True),
        sa.Column("planned_distance", sa.Float(), nullable=True),
        sa.Column("planned_rest", sa.Integer(), nullable=True),
        sa.Column(
            "effort_character",
            postgresql.ENUM(
                "rpe",
                "rir",
                "velocity_loss",
                name="effortcharacterenum",
                create_type=False,
            ),
            nullable=True,
        ),
        sa.Column("effort_value", sa.Float(), nullable=True),
        sa.Column("actual_sets", sa.Integer(), nullable=True),
        sa.Column("actual_reps", sa.String(length=20), nullable=True),
        sa.Column("actual_weight", sa.Float(), nullable=True),
        sa.Column("actual_duration", sa.Integer(), nullable=True),
        sa.Column("actual_distance", sa.Float(), nullable=True),
        sa.Column("actual_rest", sa.Integer(), nullable=True),
        sa.Column("actual_effort_value", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
        ),
        sa.ForeignKeyConstraint(
            ["session_block_id"],
            ["session_blocks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_block_exercise_block",
        "session_block_exercises",
        ["session_block_id"],
        unique=False,
    )
    op.create_index(
        "idx_block_exercise_order",
        "session_block_exercises",
        ["session_block_id", "order_in_block"],
        unique=False,
    )
    op.create_index(
        "idx_block_exercise_superset",
        "session_block_exercises",
        ["superset_group_id"],
        unique=False,
    )
    op.create_index(
        "idx_block_exercise_set_type",
        "session_block_exercises",
        ["set_type"],
        unique=False,
    )

    # Add new columns to training_sessions table
    op.add_column(
        "training_sessions", sa.Column("planned_intensity", sa.Float(), nullable=True)
    )
    op.add_column(
        "training_sessions", sa.Column("planned_volume", sa.Float(), nullable=True)
    )
    op.add_column(
        "training_sessions", sa.Column("actual_intensity", sa.Float(), nullable=True)
    )
    op.add_column(
        "training_sessions", sa.Column("actual_volume", sa.Float(), nullable=True)
    )

    # Insert predefined training block types
    op.execute(
        """
        INSERT INTO training_block_types (
            name, description, is_predefined, color, icon,
            created_at, updated_at, is_active
        )
        VALUES
        ('Warm Up', 'Preparation and activation exercises', true,
         '#FF6B6B', 'warmup', NOW(), NOW(), true),
        ('Core', 'Core strengthening and stability exercises', true,
         '#4ECDC4', 'core', NOW(), NOW(), true),
        ('Conditioning', 'Cardiovascular and endurance training', true,
         '#45B7D1', 'conditioning', NOW(), NOW(), true),
        ('Maximum Strength', 'Heavy strength training for maximal force', true,
         '#96CEB4', 'strength', NOW(), NOW(), true),
        ('Strength-Speed', 'Power and explosive strength training', true,
         '#FFEAA7', 'power', NOW(), NOW(), true),
        ('Hypertrophy Strength', 'Muscle building and size training', true,
         '#DDA0DD', 'hypertrophy', NOW(), NOW(), true),
        ('Plyometrics', 'Explosive jumping and reactive training', true,
         '#98D8C8', 'plyo', NOW(), NOW(), true),
        ('Intensive Aerobic', 'High-intensity aerobic training', true,
         '#F7DC6F', 'aerobic', NOW(), NOW(), true),
        ('Extensive Aerobic', 'Low-intensity aerobic training', true,
         '#BB8FCE', 'aerobic', NOW(), NOW(), true)
    """
    )


def downgrade():
    # Drop tables in reverse order
    op.drop_table("session_block_exercises")
    op.drop_table("session_blocks")
    op.drop_table("session_template_exercises")
    op.drop_table("session_template_blocks")
    op.drop_table("session_templates")
    op.drop_table("training_block_types")

    # Remove columns from training_sessions table
    op.drop_column("training_sessions", "actual_volume")
    op.drop_column("training_sessions", "actual_intensity")
    op.drop_column("training_sessions", "planned_volume")
    op.drop_column("training_sessions", "planned_intensity")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS effortcharacterenum")
    op.execute("DROP TYPE IF EXISTS settypeenum")
