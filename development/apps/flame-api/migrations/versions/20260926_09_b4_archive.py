"""B4 soft archive flags for curriculum descendants."""
from alembic import op
import sqlalchemy as sa

revision = "20260926_09"
down_revision = "20260926_08"
branch_labels = None
depends_on = None

TABLES = ("levels", "subjects", "domains", "categories", "topics", "subtopics")

def upgrade():
    for table in TABLES:
        op.add_column(table, sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")), schema="flame")

def downgrade():
    for table in reversed(TABLES):
        op.drop_column(table, "archived", schema="flame")

