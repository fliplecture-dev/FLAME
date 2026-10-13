"""Keep teacher topic expertise within its selected subject.

Revision ID: 20260925_04
Revises: 902e0b18bb4f
"""
from alembic import op

revision = "20260925_04"
down_revision = "902e0b18bb4f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE FUNCTION flame.validate_teacher_expertise_path()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.topic_id IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM flame.topics AS topic
                JOIN flame.domains AS domain ON domain.id = topic.domain_id
                WHERE topic.id = NEW.topic_id
                  AND domain.subject_id = NEW.subject_id
            ) THEN
                RAISE EXCEPTION USING
                    ERRCODE = '23514',
                    MESSAGE = 'teacher expertise topic must belong to subject';
            END IF;
            RETURN NEW;
        END;
        $$;
    """)
    op.execute("""
        CREATE TRIGGER teacher_expertise_path_valid
        BEFORE INSERT OR UPDATE OF subject_id, topic_id
        ON flame.teacher_expertise
        FOR EACH ROW EXECUTE FUNCTION flame.validate_teacher_expertise_path();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER teacher_expertise_path_valid ON flame.teacher_expertise")
    op.execute("DROP FUNCTION flame.validate_teacher_expertise_path()")
