"""merge heads

Revision ID: ee5e6b0506b1
Revises: ab12cd34ef56, f1a2b3c4d5e6
Create Date: 2025-09-18 22:48:34.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = "ee5e6b0506b1"
down_revision: Union[str, Sequence[str], None] = ("ab12cd34ef56", "f1a2b3c4d5e6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
