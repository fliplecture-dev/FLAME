"""Pinned conversation shortcuts.

Revision ID: 20261001_19
Revises: 20260930_18
"""
from alembic import op
import sqlalchemy as sa

revision = "20261001_19"
down_revision = "20260930_18"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("pinned", sa.Boolean(),
        nullable=False, server_default=sa.text("false")), schema="flame")


def downgrade():
    op.drop_column("sessions", "pinned", schema="flame")