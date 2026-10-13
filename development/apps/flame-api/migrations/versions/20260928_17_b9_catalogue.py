"""B9 resource publication, kit uploads and recommendation snapshots.

Revision ID: 20260928_17
Revises: 20260928_16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20260928_17"
down_revision = "20260928_16"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("resources", sa.Column("accessibility_note", sa.String(1000)), schema="flame")
    op.add_column("resources", sa.Column("availability", sa.String(16), nullable=False, server_default=sa.text("'available'")), schema="flame")
    op.create_check_constraint("ck_resources_availability_valid", "resources", "availability IN ('available', 'unavailable')", schema="flame")
    op.add_column("resource_uploads", sa.Column("kit_id", sa.UUID(), sa.ForeignKey("flame.activity_kits.id", ondelete="RESTRICT")), schema="flame")
    op.create_check_constraint("ck_resource_uploads_one_upload_owner", "resource_uploads",
                               "NOT (resource_id IS NOT NULL AND kit_id IS NOT NULL)", schema="flame")
    op.create_table(
        "recommendation_sets",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("student_id", sa.UUID(), sa.ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("flame.sessions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("message_id", sa.UUID(), sa.ForeignKey("flame.messages.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("resource_ids", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("teacher_ids", JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("message_id", name="uq_recommendation_sets_message"),
        schema="flame",
    )


def downgrade():
    op.drop_table("recommendation_sets", schema="flame")
    op.drop_constraint("ck_resource_uploads_one_upload_owner", "resource_uploads", schema="flame", type_="check")
    op.drop_column("resource_uploads", "kit_id", schema="flame")
    op.drop_constraint("ck_resources_availability_valid", "resources", schema="flame", type_="check")
    op.drop_column("resources", "availability", schema="flame")
    op.drop_column("resources", "accessibility_note", schema="flame")
