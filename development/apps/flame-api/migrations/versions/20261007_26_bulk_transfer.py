"""Durable administrator-owned bulk previews and duplicate identities."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "20261007_26"
down_revision = "20261007_25"
branch_labels = depends_on = None


def upgrade():
    op.create_table("bulk_imports", sa.Column("id", UUID(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False), sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False), sa.Column("payload", JSONB(), nullable=False),
        sa.Column("preview", JSONB(), nullable=False), sa.Column("token", sa.String(64), nullable=False),
        sa.Column("status", sa.String(24), nullable=False), sa.Column("result", JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()), schema="flame")
    op.create_table("bulk_identities", sa.Column("id", UUID(), primary_key=True),
        sa.Column("kind", sa.String(24), nullable=False), sa.Column("record_key", sa.String(255), nullable=False),
        sa.Column("entity_id", UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("kind", "record_key", name="uq_bulk_identity_key"), schema="flame")


def downgrade():
    op.drop_table("bulk_identities", schema="flame")
    op.drop_table("bulk_imports", schema="flame")
