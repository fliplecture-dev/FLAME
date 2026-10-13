"""Persist Curiosity clarification questions and candidate paths."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260926_13"
down_revision = "20260926_12"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pending_clarifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.String(4000), nullable=False),
        sa.Column("candidates", postgresql.JSONB(), nullable=False),
        sa.Column("selected_path", postgresql.JSONB()),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["flame.student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id", "student_id"], ["flame.sessions.id", "flame.sessions.student_id"], ondelete="RESTRICT"),
        sa.CheckConstraint("status IN ('pending', 'resolved', 'cancelled', 'expired')", name="ck_pending_clarifications_status_valid"),
        schema="flame",
    )
    op.create_index("ix_pending_clarifications_session_status", "pending_clarifications",
                    ["session_id", "status"], schema="flame")


def downgrade():
    op.drop_index("ix_pending_clarifications_session_status", table_name="pending_clarifications", schema="flame")
    op.drop_table("pending_clarifications", schema="flame")

