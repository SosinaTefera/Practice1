"""add_user_tos_otp_lockout

Revision ID: 2025_10_03_user_tos_otp
Revises: 2025_10_02_anthropometric
Create Date: 2025-10-03 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "2025_10_03_user_tos_otp"
down_revision = "2025_10_02_anthropometric"
branch_labels = None
depends_on = None


def upgrade():
    # Add TOS and OTP/lockout fields to users table
    op.add_column(
        "users", sa.Column("tos_accepted_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "users", sa.Column("tos_version", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "users", sa.Column("email_otp_hash", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("email_otp_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "failed_login_attempts", sa.Integer(), server_default="0", nullable=False
        ),
    )
    op.add_column(
        "users", sa.Column("lockout_until", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade():
    op.drop_column("users", "lockout_until")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "email_otp_expires_at")
    op.drop_column("users", "email_otp_hash")
    op.drop_column("users", "tos_version")
    op.drop_column("users", "tos_accepted_at")
