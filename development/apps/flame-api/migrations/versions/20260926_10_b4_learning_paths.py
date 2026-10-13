"""B4 exact My Learning paths through Subtopic."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "20260926_10"
down_revision = "20260926_09"
branch_labels = None
depends_on = None


def upgrade():
    for column, table in (("domain_id", "domains"), ("category_id", "categories"),
                          ("topic_id", "topics"), ("subtopic_id", "subtopics")):
        op.add_column("learning_memberships", sa.Column(column, UUID(as_uuid=True), nullable=True), schema="flame")
        op.create_foreign_key("fk_learning_memberships_" + column, "learning_memberships", table,
                              [column], ["id"], source_schema="flame", referent_schema="flame",
                              ondelete="RESTRICT")
    op.drop_index("uq_learning_subject_path", table_name="learning_memberships", schema="flame")
    op.create_index("uq_learning_subject_path", "learning_memberships",
        ["student_id", "curriculum_id", "level_id", "subject_id"], unique=True,
        schema="flame", postgresql_where=sa.text("subject_id IS NOT NULL AND domain_id IS NULL"))
    op.create_check_constraint("learning_path_depth", "learning_memberships",
        "(domain_id IS NULL OR subject_id IS NOT NULL) AND "
        "(topic_id IS NULL OR domain_id IS NOT NULL) AND "
        "(subtopic_id IS NULL OR topic_id IS NOT NULL)", schema="flame")
    op.create_index("uq_learning_domain_path", "learning_memberships",
        ["student_id", "domain_id"], unique=True, schema="flame",
        postgresql_where=sa.text("domain_id IS NOT NULL AND topic_id IS NULL"))
    op.create_index("uq_learning_topic_path", "learning_memberships",
        ["student_id", "topic_id"], unique=True, schema="flame",
        postgresql_where=sa.text("topic_id IS NOT NULL AND subtopic_id IS NULL"))
    op.create_index("uq_learning_subtopic_path", "learning_memberships",
        ["student_id", "subtopic_id"], unique=True, schema="flame",
        postgresql_where=sa.text("subtopic_id IS NOT NULL"))


def downgrade():
    op.drop_index("uq_learning_subject_path", table_name="learning_memberships", schema="flame")
    op.create_index("uq_learning_subject_path", "learning_memberships",
        ["student_id", "curriculum_id", "level_id", "subject_id"], unique=True,
        schema="flame", postgresql_where=sa.text("subject_id IS NOT NULL"))
    for name in ("uq_learning_subtopic_path", "uq_learning_topic_path", "uq_learning_domain_path"):
        op.drop_index(name, table_name="learning_memberships", schema="flame")
    op.drop_constraint("ck_learning_memberships_learning_path_depth", "learning_memberships",
                       schema="flame", type_="check")
    for column in ("subtopic_id", "topic_id", "category_id", "domain_id"):
        op.drop_constraint("fk_learning_memberships_" + column, "learning_memberships",
                           schema="flame", type_="foreignkey")
        op.drop_column("learning_memberships", column, schema="flame")

