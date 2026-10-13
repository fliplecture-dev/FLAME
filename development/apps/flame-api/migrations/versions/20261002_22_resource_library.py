"""Resource library update timestamps and original upload names."""
from alembic import op
import sqlalchemy as sa
revision = "20261002_22"
down_revision = "20261002_21"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("resources", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), schema="flame")
    op.execute("UPDATE flame.resources SET updated_at = created_at")
    op.add_column("resource_uploads", sa.Column("file_name", sa.String(255)), schema="flame")

def downgrade():
    op.drop_column("resource_uploads", "file_name", schema="flame")
    op.drop_column("resources", "updated_at", schema="flame")
