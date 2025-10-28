"""merge heads

Revision ID: 441abc484588
Revises: ab12cd34ef56, f1a2b3c4d5e6
Create Date: 2025-09-18 22:48:34.877875

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "441abc484588"
down_revision: Union[str, Sequence[str], None] = ("ab12cd34ef56", "f1a2b3c4d5e6")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
