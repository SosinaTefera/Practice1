"""merge heads (prod)

Revision ID: c85ca65a9134
Revises: add_trainer_professional_fields, d2e1beb82132
Create Date: 2025-09-25 08:43:55.960707

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "c85ca65a9134"
down_revision: Union[str, Sequence[str], None] = (
    "add_trainer_professional_fields",
    "d2e1beb82132",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
