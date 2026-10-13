"""catalogues_foundation

Revision ID: 902e0b18bb4f
Revises: cacbe880bb5f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '902e0b18bb4f'
down_revision: Union[str, Sequence[str], None] = 'cacbe880bb5f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_subtopics_id_topic', 'subtopics', ['id', 'topic_id'], schema='flame')
    op.create_table('activity_kits',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=4000), nullable=True),
    sa.Column('image_keys', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('materials', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('instructions', sa.String(length=10000), nullable=True),
    sa.Column('supervision', sa.String(length=4000), nullable=True),
    sa.Column('cost', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('availability', sa.String(length=255), nullable=True),
    sa.Column('supplier_url', sa.String(length=2048), nullable=True),
    sa.Column('published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name=op.f('ck_activity_kits_currency_format')),
    sa.CheckConstraint('(cost IS NULL) = (currency IS NULL)', name=op.f('ck_activity_kits_cost_currency_together')),
    sa.CheckConstraint('cost IS NULL OR cost >= 0', name=op.f('ck_activity_kits_cost_nonnegative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_activity_kits')),
    schema='flame'
    )
    op.create_table('resources',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=True),
    sa.Column('storage_key', sa.String(length=1024), nullable=True),
    sa.Column('external_url', sa.String(length=2048), nullable=True),
    sa.Column('alt_text', sa.String(length=1000), nullable=True),
    sa.Column('caption_or_transcript', sa.String(length=10000), nullable=True),
    sa.Column('published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('(storage_key IS NULL) <> (external_url IS NULL)', name=op.f('ck_resources_one_media_source')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_resources_version_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resources')),
    schema='flame'
    )
    op.create_table('teachers',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('bio', sa.String(length=4000), nullable=True),
    sa.Column('qualifications', sa.String(length=4000), nullable=True),
    sa.Column('experience', sa.String(length=4000), nullable=True),
    sa.Column('languages', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
    sa.Column('availability', sa.String(length=255), nullable=True),
    sa.Column('published', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_teachers')),
    schema='flame'
    )
    op.create_table('teacher_expertise',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('teacher_id', sa.UUID(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('topic_id', sa.UUID(), nullable=True),
    sa.Column('claim_status', sa.String(length=24), server_default=sa.text("'declared'"), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['subject_id'], ['flame.subjects.id'], name=op.f('fk_teacher_expertise_subject_id_subjects'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['teacher_id'], ['flame.teachers.id'], name=op.f('fk_teacher_expertise_teacher_id_teachers'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_id'], ['flame.topics.id'], name=op.f('fk_teacher_expertise_topic_id_topics'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_teacher_expertise')),
    schema='flame'
    )
    op.create_index('uq_teacher_subject_expertise', 'teacher_expertise', ['teacher_id', 'subject_id'], unique=True, schema='flame', postgresql_where=sa.text('topic_id IS NULL'))
    op.create_index('uq_teacher_topic_expertise', 'teacher_expertise', ['teacher_id', 'subject_id', 'topic_id'], unique=True, schema='flame', postgresql_where=sa.text('topic_id IS NOT NULL'))
    op.create_table('kit_topics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('kit_id', sa.UUID(), nullable=False),
    sa.Column('topic_id', sa.UUID(), nullable=False),
    sa.Column('subtopic_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['kit_id'], ['flame.activity_kits.id'], name=op.f('fk_kit_topics_kit_id_activity_kits'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subtopic_id', 'topic_id'], ['flame.subtopics.id', 'flame.subtopics.topic_id'], name=op.f('fk_kit_topics_subtopic_id_subtopics'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_id'], ['flame.topics.id'], name=op.f('fk_kit_topics_topic_id_topics'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_kit_topics')),
    schema='flame'
    )
    op.create_index('uq_kit_subtopic', 'kit_topics', ['kit_id', 'topic_id', 'subtopic_id'], unique=True, schema='flame', postgresql_where=sa.text('subtopic_id IS NOT NULL'))
    op.create_index('uq_kit_topic_only', 'kit_topics', ['kit_id', 'topic_id'], unique=True, schema='flame', postgresql_where=sa.text('subtopic_id IS NULL'))
    op.create_table('resource_topics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('resource_id', sa.UUID(), nullable=False),
    sa.Column('topic_id', sa.UUID(), nullable=False),
    sa.Column('subtopic_id', sa.UUID(), nullable=True),
    sa.ForeignKeyConstraint(['resource_id'], ['flame.resources.id'], name=op.f('fk_resource_topics_resource_id_resources'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subtopic_id', 'topic_id'], ['flame.subtopics.id', 'flame.subtopics.topic_id'], name=op.f('fk_resource_topics_subtopic_id_subtopics'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['topic_id'], ['flame.topics.id'], name=op.f('fk_resource_topics_topic_id_topics'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_resource_topics')),
    schema='flame'
    )
    op.create_index('uq_resource_subtopic', 'resource_topics', ['resource_id', 'topic_id', 'subtopic_id'], unique=True, schema='flame', postgresql_where=sa.text('subtopic_id IS NOT NULL'))
    op.create_index('uq_resource_topic_only', 'resource_topics', ['resource_id', 'topic_id'], unique=True, schema='flame', postgresql_where=sa.text('subtopic_id IS NULL'))


def downgrade() -> None:
    op.drop_index('uq_resource_topic_only', table_name='resource_topics', schema='flame', postgresql_where=sa.text('subtopic_id IS NULL'))
    op.drop_index('uq_resource_subtopic', table_name='resource_topics', schema='flame', postgresql_where=sa.text('subtopic_id IS NOT NULL'))
    op.drop_table('resource_topics', schema='flame')
    op.drop_index('uq_kit_topic_only', table_name='kit_topics', schema='flame', postgresql_where=sa.text('subtopic_id IS NULL'))
    op.drop_index('uq_kit_subtopic', table_name='kit_topics', schema='flame', postgresql_where=sa.text('subtopic_id IS NOT NULL'))
    op.drop_table('kit_topics', schema='flame')
    op.drop_index('uq_teacher_topic_expertise', table_name='teacher_expertise', schema='flame', postgresql_where=sa.text('topic_id IS NOT NULL'))
    op.drop_index('uq_teacher_subject_expertise', table_name='teacher_expertise', schema='flame', postgresql_where=sa.text('topic_id IS NULL'))
    op.drop_table('teacher_expertise', schema='flame')
    op.drop_table('teachers', schema='flame')
    op.drop_table('resources', schema='flame')
    op.drop_table('activity_kits', schema='flame')
    op.drop_constraint('uq_subtopics_id_topic', 'subtopics', schema='flame', type_='unique')
