"""B5 request leases and fencing tokens."""
from alembic import op
import sqlalchemy as sa

revision = "20260926_12"
down_revision = "20260926_11"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("answer_requests", sa.Column("claim_token", sa.String(64)), schema="flame")
    op.add_column("answer_requests", sa.Column("lease_expires_at", sa.DateTime(timezone=True)), schema="flame")
    op.add_column("answer_requests", sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), schema="flame")
    op.create_check_constraint("ck_answer_requests_attempts_nonnegative", "answer_requests", "attempts >= 0", schema="flame")

def downgrade():
    op.drop_constraint("ck_answer_requests_attempts_nonnegative", "answer_requests", schema="flame", type_="check")
    op.drop_column("answer_requests", "attempts", schema="flame")
    op.drop_column("answer_requests", "lease_expires_at", schema="flame")
    op.drop_column("answer_requests", "claim_token", schema="flame")
