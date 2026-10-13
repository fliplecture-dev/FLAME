"""Allow optional topic-level learning outcomes.

Revision ID: 20260925_05
Revises: 20260925_04
"""
from alembic import op
import sqlalchemy as sa

revision = "20260925_05"
down_revision = "20260925_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("topics", sa.Column("learning_outcome", sa.String(length=2000), nullable=True), schema="flame")


def downgrade() -> None:
    op.drop_column("topics", "learning_outcome", schema="flame")
