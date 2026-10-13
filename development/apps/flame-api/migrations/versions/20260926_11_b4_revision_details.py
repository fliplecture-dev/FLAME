"""B4 revision details retain versioned admin changes."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260926_11"
down_revision = "20260926_10"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("curriculum_revisions", sa.Column("details", JSONB(), nullable=True), schema="flame")


def downgrade():
    op.drop_column("curriculum_revisions", "details", schema="flame")

