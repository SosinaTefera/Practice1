"""merge heads

Revision ID: d2e1beb82132
Revises: ee5e6b0506b1, g1h2i3j4k5l6
Create Date: 2025-09-19 08:00:00.000000

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision = "d2e1beb82132"
down_revision: Union[str, Sequence[str], None] = ("ee5e6b0506b1", "g1h2i3j4k5l6")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
