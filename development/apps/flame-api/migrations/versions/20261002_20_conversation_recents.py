"""Conversation opening history, separate from saved messages.

Revision ID: 20261002_20
Revises: 20261001_19
"""
from alembic import op
import sqlalchemy as sa

revision = "20261002_20"
down_revision = "20261001_19"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("sessions", sa.Column("recent_at", sa.DateTime(timezone=True), nullable=True), schema="flame")
    op.execute("UPDATE flame.sessions SET recent_at = updated_at")


def downgrade():
    op.drop_column("sessions", "recent_at", schema="flame")
