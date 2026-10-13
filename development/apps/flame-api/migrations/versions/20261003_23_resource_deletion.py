"""Retained deletion records for resources; media and history stay intact."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20261003_23"
down_revision = "20261002_22"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("resources", sa.Column("deleted_at", sa.DateTime(timezone=True)), schema="flame")
    op.add_column("resources", sa.Column("deleted_by", sa.String(255)), schema="flame")
    op.add_column("resources", sa.Column("deletion_snapshot", JSONB()), schema="flame")

def downgrade():
    op.drop_column("resources", "deletion_snapshot", schema="flame")
    op.drop_column("resources", "deleted_by", schema="flame")
    op.drop_column("resources", "deleted_at", schema="flame")
