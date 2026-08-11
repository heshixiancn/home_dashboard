"""relax timeout minimum

Revision ID: 202608100002
Revises: 202608100001
Create Date: 2026-08-10
"""
from typing import Sequence, Union

from alembic import op

revision: str = "202608100002"
down_revision: Union[str, None] = "202608100001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("ck_service_timeout", "service_entries", type_="check")
    op.create_check_constraint("ck_service_timeout", "service_entries", "timeout_ms between 100 and 30000")


def downgrade() -> None:
    op.drop_constraint("ck_service_timeout", "service_entries", type_="check")
    op.create_check_constraint("ck_service_timeout", "service_entries", "timeout_ms between 500 and 30000")
