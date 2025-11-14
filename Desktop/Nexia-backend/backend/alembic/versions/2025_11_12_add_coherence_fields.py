"""Add coherence fields to cycles

Revision ID: 2025_11_12_coherence
Revises: 4d15b8543e9d
Create Date: 2025-11-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2025_11_12_coherence"
down_revision: Union[str, None] = "4d15b8543e9d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add coherence fields (physical_quality, volume, intensity) to cycles."""
    
    # Add to macrocycles
    op.add_column("macrocycles", sa.Column("physical_quality", sa.String(length=255), nullable=True))
    op.add_column("macrocycles", sa.Column("volume", sa.Float(), nullable=True))
    op.add_column("macrocycles", sa.Column("intensity", sa.Float(), nullable=True))
    
    # Add to mesocycles
    op.add_column("mesocycles", sa.Column("physical_quality", sa.String(length=255), nullable=True))
    op.add_column("mesocycles", sa.Column("volume", sa.Float(), nullable=True))
    op.add_column("mesocycles", sa.Column("intensity", sa.Float(), nullable=True))
    
    # Add to microcycles
    op.add_column("microcycles", sa.Column("physical_quality", sa.String(length=255), nullable=True))
    op.add_column("microcycles", sa.Column("volume", sa.Float(), nullable=True))
    op.add_column("microcycles", sa.Column("intensity", sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove coherence fields from cycles."""
    
    op.drop_column("microcycles", "intensity")
    op.drop_column("microcycles", "volume")
    op.drop_column("microcycles", "physical_quality")
    
    op.drop_column("mesocycles", "intensity")
    op.drop_column("mesocycles", "volume")
    op.drop_column("mesocycles", "physical_quality")
    
    op.drop_column("macrocycles", "intensity")
    op.drop_column("macrocycles", "volume")
    op.drop_column("macrocycles", "physical_quality")

