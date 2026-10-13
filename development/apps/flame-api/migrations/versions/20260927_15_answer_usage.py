"""Persist bounded B7 usage metadata without retaining prompts or provider responses twice."""
from alembic import op
import sqlalchemy as sa

revision = "20260927_15"
down_revision = "20260926_14"
branch_labels = None
depends_on = None


def upgrade():
    for name, kind in (
        ("prompt_version", sa.String(64)),
        ("profile_version", sa.String(64)),
        ("model", sa.String(128)),
        ("input_tokens", sa.Integer()),
        ("output_tokens", sa.Integer()),
        ("latency_ms", sa.Integer()),
    ):
        op.add_column("answer_requests", sa.Column(name, kind), schema="flame")


def downgrade():
    for name in ("latency_ms", "output_tokens", "input_tokens", "model", "profile_version", "prompt_version"):
        op.drop_column("answer_requests", name, schema="flame")
