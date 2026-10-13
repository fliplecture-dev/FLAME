"""Persist owned conversation image decisions and displayed versions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261002_21"
down_revision = "20261002_20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("recommendation_sets", sa.Column("image_decision", JSONB(), nullable=True), schema="flame")


def downgrade():
    op.drop_column("recommendation_sets", "image_decision", schema="flame")
