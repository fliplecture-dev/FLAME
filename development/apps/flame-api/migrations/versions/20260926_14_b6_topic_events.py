"""Persist idempotent B6 school-topic checks and resolved context."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260926_14"
down_revision = "20260926_13"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "topic_check_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("student_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("question", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("clarification_id", postgresql.UUID(as_uuid=True)),
        sa.Column("choice_hash", sa.String(64)),
        sa.Column("context_snapshot", postgresql.JSONB()),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["student_id"], ["flame.student_profiles.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["session_id", "student_id"],
                                ["flame.sessions.id", "flame.sessions.student_id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["clarification_id"], ["flame.pending_clarifications.id"],
                                ondelete="RESTRICT"),
        sa.UniqueConstraint("student_id", "session_id", "idempotency_key"),
        sa.UniqueConstraint("clarification_id"),
        sa.CheckConstraint("status IN ('ready', 'clarification', 'out_of_scope', 'cancelled')",
                           name="ck_topic_check_events_status_valid"),
        schema="flame",
    )
    op.create_index("ix_topic_check_events_session_created", "topic_check_events",
                    ["session_id", "created_at", "id"], schema="flame")


def downgrade():
    op.drop_index("ix_topic_check_events_session_created",
                  table_name="topic_check_events", schema="flame")
    op.drop_table("topic_check_events", schema="flame")
