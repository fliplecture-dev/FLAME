"""Persisted workbook previews and idempotent import receipts.

Revision ID: 20260925_06
Revises: 20260925_05
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260925_06"
down_revision = "20260925_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "curriculum_imports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("curriculum_id", sa.UUID(), sa.ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_bytes", sa.LargeBinary(), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("sheet_levels", postgresql.JSONB(), nullable=True),
        sa.Column("preview_revision", sa.UUID(), nullable=True),
        sa.Column("base_revision", sa.Integer(), nullable=True),
        sa.Column("preview_rows", postgresql.JSONB(), nullable=True),
        sa.Column("preview_result", postgresql.JSONB(), nullable=True),
        sa.Column("issue_count", sa.Integer(), nullable=False),
        sa.Column("committed_result", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('uploaded', 'previewed', 'committed')", name="ck_curriculum_imports_status_valid"),
        sa.CheckConstraint("issue_count >= 0", name="ck_curriculum_imports_issue_count_nonnegative"),
        schema="flame",
    )
    op.create_index("ix_curriculum_imports_curriculum_created", "curriculum_imports", ["curriculum_id", "created_at"], schema="flame")
    op.create_table(
        "curriculum_import_commits",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("import_id", sa.UUID(), sa.ForeignKey("flame.curriculum_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("owner_subject", sa.String(255), nullable=False),
        sa.Column("idempotency_key", sa.String(255), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("result", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("owner_subject", "idempotency_key", name="uq_import_commit_owner_key"),
        schema="flame",
    )
    op.create_table(
        "curriculum_import_sources",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("curriculum_id", sa.UUID(), sa.ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("topic_id", sa.UUID(), sa.ForeignKey("flame.topics.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("subtopic_id", sa.UUID(), sa.ForeignKey("flame.subtopics.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source_text", sa.String(2000), nullable=False),
        sa.Column("first_import_id", sa.UUID(), sa.ForeignKey("flame.curriculum_imports.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("topic_id", "subtopic_id", "source_text", name="uq_import_source_path_text"),
        schema="flame",
    )


def downgrade() -> None:
    op.drop_table("curriculum_import_sources", schema="flame")
    op.drop_table("curriculum_import_commits", schema="flame")
    op.drop_index("ix_curriculum_imports_curriculum_created", table_name="curriculum_imports", schema="flame")
    op.drop_table("curriculum_imports", schema="flame")
