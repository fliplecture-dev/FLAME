"""B9.2 resource metadata and owned upload staging.

Revision ID: 20260928_16
Revises: 20260927_15
"""
from alembic import op
import sqlalchemy as sa

revision = "20260928_16"
down_revision = "20260927_15"
branch_labels = None
depends_on = None


def upgrade():
    for name, column in (
        ("mime_type", sa.String(100)),
        ("byte_size", sa.Integer()),
        ("rights_basis", sa.String(24)),
        ("rights_holder", sa.String(255)),
        ("rights_reference", sa.String(2048)),
        ("attribution", sa.String(2000)),
        ("distribution_scope", sa.String(255)),
    ):
        op.add_column("resources", sa.Column(name, column, nullable=True), schema="flame")
    op.create_check_constraint("ck_resources_byte_size_positive", "resources", "byte_size IS NULL OR byte_size > 0", schema="flame")
    op.create_check_constraint("ck_resources_rights_basis_valid", "resources", "rights_basis IS NULL OR rights_basis IN ('owned', 'licensed', 'permission')", schema="flame")
    op.create_table(
        "resource_uploads",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("storage_key", sa.String(1024), nullable=False, unique=True),
        sa.Column("owner_auth_subject", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(32), nullable=False),
        sa.Column("resource_id", sa.UUID(), sa.ForeignKey("flame.resources.id", ondelete="RESTRICT")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("byte_size > 0", name="ck_resource_uploads_byte_size_positive"),
        schema="flame",
    )


def downgrade():
    op.drop_table("resource_uploads", schema="flame")
    op.drop_constraint("ck_resources_rights_basis_valid", "resources", schema="flame", type_="check")
    op.drop_constraint("ck_resources_byte_size_positive", "resources", schema="flame", type_="check")
    for name in ("distribution_scope", "attribution", "rights_reference", "rights_holder", "rights_basis", "byte_size", "mime_type"):
        op.drop_column("resources", name, schema="flame")
