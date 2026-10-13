"""Private static thumbnails for uploaded videos; retain all existing media."""
from alembic import op
import sqlalchemy as sa
revision = "20261009_28"
down_revision = "20261008_27"
branch_labels = depends_on = None
def upgrade():
    op.add_column("resources", sa.Column("thumbnail_storage_key", sa.String(1024), nullable=True), schema="flame")
def downgrade():
    op.drop_column("resources", "thumbnail_storage_key", schema="flame")
