"""Allow metadata-only Interactive drafts; publication still requires media."""
from alembic import op
revision="20261011_29"
down_revision="20261009_28"
branch_labels=depends_on=None

def upgrade():
    op.drop_constraint(op.f("ck_resources_one_media_source"),"resources",schema="flame",type_="check")
    op.create_check_constraint("one_media_source","resources","(storage_key IS NULL) <> (external_url IS NULL) OR (type = 'interactive' AND NOT published AND storage_key IS NULL AND external_url IS NULL)",schema="flame")

def downgrade():
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM flame.resources WHERE storage_key IS NULL AND external_url IS NULL) THEN RAISE EXCEPTION 'Complete or remove metadata-only Interactive drafts before downgrade'; END IF; END $$")
    op.drop_constraint(op.f("ck_resources_one_media_source"),"resources",schema="flame",type_="check")
    op.create_check_constraint("one_media_source","resources","(storage_key IS NULL) <> (external_url IS NULL)",schema="flame")
