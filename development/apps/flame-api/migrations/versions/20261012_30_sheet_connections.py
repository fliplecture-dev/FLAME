"""Persistent resource spreadsheet connections and successfully synchronized row identities."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID
revision = "20261012_30"
down_revision = "20261011_29"
branch_labels = depends_on = None


def upgrade():
    op.create_table("google_sheet_connections", sa.Column("id", UUID(), primary_key=True),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("spreadsheet_id", sa.String(100), nullable=False),
        sa.Column("bindings", JSONB(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("spreadsheet_id",name="uq_google_sheet_connections_spreadsheet_id"),schema="flame")


def downgrade():
    op.drop_table("google_sheet_connections",schema="flame")
