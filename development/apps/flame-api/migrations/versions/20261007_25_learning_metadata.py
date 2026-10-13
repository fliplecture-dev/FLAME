"""Optional teaching metadata on the three owning catalogues; preserve existing content."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "20261007_25"
down_revision = "20261003_24"
branch_labels = None
depends_on = None


def upgrade():
    for table in ("resources", "teachers", "activity_kits"):
        op.add_column(table, sa.Column("learning_metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")), schema="flame")
        op.create_check_constraint(op.f("ck_"+table+"_learning_metadata_object"), table,
            "jsonb_typeof(learning_metadata) = 'object'", schema="flame")


def downgrade():
    for table in ("activity_kits", "teachers", "resources"):
        op.drop_constraint(op.f("ck_"+table+"_learning_metadata_object"), table, schema="flame", type_="check")
        op.drop_column(table, "learning_metadata", schema="flame")
