"""Guest Curiosity access and optional member-owned contact details."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20261017_32"
down_revision = "20261017_31"
branch_labels = depends_on = None
FIELDS = [("phone_number",32),("contact_number",32),("address",1000),("city",100),("state",100),("country",100),("pincode",20)]


def upgrade():
    for name, length in FIELDS:
        op.add_column("student_profiles", sa.Column(name, sa.String(length), nullable=True), schema="flame")
    op.create_table("guest_access",
        sa.Column("id_hash", sa.String(64), primary_key=True),
        sa.Column("student_id", UUID(as_uuid=True), sa.ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), schema="flame")
    op.execute("ALTER TABLE flame.guest_access ENABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON flame.guest_access FROM PUBLIC")
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN REVOKE ALL ON flame.guest_access FROM anon; END IF; IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN REVOKE ALL ON flame.guest_access FROM authenticated; END IF; END $$")


def downgrade():
    connection = op.get_bind()
    if connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM flame.guest_access) OR EXISTS (SELECT 1 FROM flame.student_profiles WHERE phone_number IS NOT NULL OR contact_number IS NOT NULL OR address IS NOT NULL OR city IS NOT NULL OR state IS NOT NULL OR country IS NOT NULL OR pincode IS NOT NULL)")):
        raise RuntimeError("Export and explicitly resolve guest/profile data before downgrade.")
    op.drop_table("guest_access", schema="flame")
    for name, _ in reversed(FIELDS):
        op.drop_column("student_profiles", name, schema="flame")
