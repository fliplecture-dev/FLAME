"""Opaque browser sessions. Provider credentials remain encrypted server-side."""
from alembic import op
import sqlalchemy as sa

revision = "20260926_07"
down_revision = "20260925_06"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "browser_sessions",
        sa.Column("id_hash", sa.String(64), primary_key=True),
        sa.Column("auth_subject", sa.String(255), nullable=False),
        sa.Column("access_token", sa.LargeBinary(), nullable=False),
        sa.Column("refresh_token", sa.LargeBinary(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        schema="flame",
    )
    op.create_index("ix_browser_sessions_auth_subject", "browser_sessions", ["auth_subject"], schema="flame")


def downgrade():
    op.drop_index("ix_browser_sessions_auth_subject", table_name="browser_sessions", schema="flame")
    op.drop_table("browser_sessions", schema="flame")
