"""Add Books and Classes without modifying existing catalogue records."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20261017_31"
down_revision = "20261012_30"
branch_labels = depends_on = None


def upgrade():
    op.create_table("catalogue_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.String(4000)),
        *[sa.Column(name, sa.String(length)) for name, length in [
            ("category", 80), ("subject", 120), ("level", 80), ("language", 80),
            ("format", 80), ("author", 255), ("location", 255), ("schedule", 255), ("availability", 255)]],
        sa.Column("price", sa.Numeric(12, 2)), sa.Column("currency", sa.String(3)),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("kind IN ('books', 'classes')", name="catalogue_kind"),
        sa.CheckConstraint("price IS NULL OR price >= 0", name="catalogue_price_nonnegative"),
        sa.CheckConstraint("(price IS NULL) = (currency IS NULL)", name="catalogue_price_currency"),
        sa.CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name="catalogue_currency"), schema="flame")
    op.create_index("ix_catalogue_entries_kind_published_title", "catalogue_entries", ["kind", "published", "title"], schema="flame")
    op.execute("ALTER TABLE flame.catalogue_entries ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON flame.catalogue_entries FROM PUBLIC")
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON flame.catalogue_entries FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON flame.catalogue_entries FROM authenticated; END IF; END $$")


def downgrade():
    # Refuse accidental removal of owner-authored inventory.
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM flame.catalogue_entries)")):
        raise RuntimeError("Export and explicitly resolve catalogue records before removing this table.")
    op.drop_index("ix_catalogue_entries_kind_published_title", table_name="catalogue_entries", schema="flame")
    op.drop_table("catalogue_entries", schema="flame")
