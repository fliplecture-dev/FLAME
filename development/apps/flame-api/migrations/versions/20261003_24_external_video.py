"""Validated external-video metadata, separate from provider playback approval."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
revision = "20261003_24"
down_revision = "20261003_23"
branch_labels = None
depends_on = None
def upgrade():
    op.add_column("resources", sa.Column("external_video", JSONB()), schema="flame")
def downgrade():
    op.drop_column("resources", "external_video", schema="flame")
