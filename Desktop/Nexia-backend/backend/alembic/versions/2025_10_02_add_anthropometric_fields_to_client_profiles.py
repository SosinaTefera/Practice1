"""add_anthropometric_fields_to_client_profiles

Revision ID: 2025_10_02_anthropometric
Revises: c85ca65a9134
Create Date: 2025-10-02 20:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2025_10_02_anthropometric"
down_revision = "c85ca65a9134"
branch_labels = None
depends_on = None


def upgrade():
    # Add anthropometric fields to client_profiles table
    op.add_column(
        "client_profiles", sa.Column("id_passport", sa.String(50), nullable=True)
    )
    op.add_column("client_profiles", sa.Column("birthdate", sa.Date(), nullable=True))

    # Skinfolds (in mm)
    op.add_column(
        "client_profiles", sa.Column("skinfold_triceps", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_subscapular", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_biceps", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_iliac_crest", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_supraspinal", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_abdominal", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_thigh", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("skinfold_calf", sa.Float(), nullable=True)
    )

    # Girths (in cm)
    op.add_column(
        "client_profiles", sa.Column("girth_relaxed_arm", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles",
        sa.Column("girth_flexed_contracted_arm", sa.Float(), nullable=True),
    )
    op.add_column(
        "client_profiles", sa.Column("girth_waist_minimum", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("girth_hips_maximum", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("girth_medial_thigh", sa.Float(), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("girth_maximum_calf", sa.Float(), nullable=True)
    )

    # Diameters (in cm)
    op.add_column(
        "client_profiles",
        sa.Column("diameter_humerus_biepicondylar", sa.Float(), nullable=True),
    )
    op.add_column(
        "client_profiles",
        sa.Column("diameter_femur_bicondylar", sa.Float(), nullable=True),
    )
    op.add_column(
        "client_profiles",
        sa.Column("diameter_bi_styloid_wrist", sa.Float(), nullable=True),
    )

    # Program meta fields
    op.add_column(
        "client_profiles", sa.Column("objective", sa.String(100), nullable=True)
    )
    op.add_column(
        "client_profiles", sa.Column("session_duration", sa.String(20), nullable=True)
    )
    op.add_column("client_profiles", sa.Column("notes_1", sa.Text(), nullable=True))
    op.add_column("client_profiles", sa.Column("notes_2", sa.Text(), nullable=True))
    op.add_column("client_profiles", sa.Column("notes_3", sa.Text(), nullable=True))

    # Change altura from meters to cm for consistency with UI
    op.alter_column(
        "client_profiles",
        "altura",
        existing_type=sa.Float(),
        comment="Height in centimeters",
    )


def downgrade():
    # Remove anthropometric fields
    op.drop_column("client_profiles", "notes_3")
    op.drop_column("client_profiles", "notes_2")
    op.drop_column("client_profiles", "notes_1")
    op.drop_column("client_profiles", "session_duration")
    op.drop_column("client_profiles", "objective")
    op.drop_column("client_profiles", "diameter_bi_styloid_wrist")
    op.drop_column("client_profiles", "diameter_femur_bicondylar")
    op.drop_column("client_profiles", "diameter_humerus_biepicondylar")
    op.drop_column("client_profiles", "girth_maximum_calf")
    op.drop_column("client_profiles", "girth_medial_thigh")
    op.drop_column("client_profiles", "girth_hips_maximum")
    op.drop_column("client_profiles", "girth_waist_minimum")
    op.drop_column("client_profiles", "girth_flexed_contracted_arm")
    op.drop_column("client_profiles", "girth_relaxed_arm")
    op.drop_column("client_profiles", "skinfold_calf")
    op.drop_column("client_profiles", "skinfold_thigh")
    op.drop_column("client_profiles", "skinfold_abdominal")
    op.drop_column("client_profiles", "skinfold_supraspinal")
    op.drop_column("client_profiles", "skinfold_iliac_crest")
    op.drop_column("client_profiles", "skinfold_biceps")
    op.drop_column("client_profiles", "skinfold_subscapular")
    op.drop_column("client_profiles", "skinfold_triceps")
    op.drop_column("client_profiles", "birthdate")
    op.drop_column("client_profiles", "id_passport")
