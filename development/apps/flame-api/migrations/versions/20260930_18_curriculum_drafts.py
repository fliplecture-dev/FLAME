"""Private curriculum draft snapshots.

Revision ID: 20260930_18
Revises: 20260928_17
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260930_18"
down_revision = "20260928_17"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "curriculum_drafts",
        sa.Column("curriculum_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("revision", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("paths", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("source_import_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by_subject", sa.String(length=255), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("base_revision >= 0", name=op.f("ck_curriculum_drafts_base_revision_nonnegative")),
        sa.CheckConstraint("revision >= 1", name=op.f("ck_curriculum_drafts_revision_positive")),
        sa.ForeignKeyConstraint(["curriculum_id"], ["flame.curricula.id"], name=op.f("fk_curriculum_drafts_curriculum_id_curricula"), ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("curriculum_id", name=op.f("pk_curriculum_drafts")),
        schema="flame",
    )


def downgrade():
    op.drop_table("curriculum_drafts", schema="flame")
