"""merge heads

Revision ID: fc69e4bf5ba4
Revises: 20250131_add_token_monitoring, 20250131_initial
Create Date: 2025-02-01 06:44:20.059283+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc69e4bf5ba4'
down_revision: Union[str, None] = ('20250131_add_token_monitoring', '20250131_initial')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
