"""curriculum_foundation

Revision ID: 4ade4490344f
Revises: 
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4ade4490344f'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('curricula',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=80), nullable=False),
    sa.Column('normalized_code', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('description', sa.String(length=2000), nullable=True),
    sa.Column('state', sa.String(length=16), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('revision', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("state IN ('draft', 'published', 'archived')", name=op.f('ck_curricula_state_valid')),
    sa.CheckConstraint('revision >= 0', name=op.f('ck_curricula_revision_nonnegative')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_curricula_version_positive')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_curricula')),
    sa.UniqueConstraint('normalized_code', name=op.f('uq_curricula_normalized_code')),
    schema='flame'
    )
    op.create_table('curriculum_revisions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('curriculum_id', sa.UUID(), nullable=False),
    sa.Column('number', sa.Integer(), nullable=False),
    sa.Column('change_kind', sa.String(length=40), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('number >= 1', name=op.f('ck_curriculum_revisions_number_positive')),
    sa.ForeignKeyConstraint(['curriculum_id'], ['flame.curricula.id'], name=op.f('fk_curriculum_revisions_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_curriculum_revisions')),
    sa.UniqueConstraint('curriculum_id', 'number', name=op.f('uq_curriculum_revisions_curriculum_id')),
    schema='flame'
    )
    op.create_table('levels',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('curriculum_id', sa.UUID(), nullable=False),
    sa.Column('code', sa.String(length=80), nullable=False),
    sa.Column('normalized_code', sa.String(length=80), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_levels_display_order_nonnegative')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_levels_version_positive')),
    sa.ForeignKeyConstraint(['curriculum_id'], ['flame.curricula.id'], name=op.f('fk_levels_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_levels')),
    sa.UniqueConstraint('curriculum_id', 'normalized_code', name='uq_levels_curriculum_code'),
    sa.UniqueConstraint('curriculum_id', 'normalized_name', name='uq_levels_curriculum_name'),
    schema='flame'
    )
    op.create_table('subjects',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('level_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_subjects_display_order_nonnegative')),
    sa.ForeignKeyConstraint(['level_id'], ['flame.levels.id'], name=op.f('fk_subjects_level_id_levels'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subjects')),
    sa.UniqueConstraint('level_id', 'normalized_name', name=op.f('uq_subjects_level_id')),
    schema='flame'
    )
    op.create_table('domains',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('subject_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_domains_display_order_nonnegative')),
    sa.ForeignKeyConstraint(['subject_id'], ['flame.subjects.id'], name=op.f('fk_domains_subject_id_subjects'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_domains')),
    sa.UniqueConstraint('subject_id', 'normalized_name', name=op.f('uq_domains_subject_id')),
    schema='flame'
    )
    op.create_table('categories',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('domain_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_categories_display_order_nonnegative')),
    sa.ForeignKeyConstraint(['domain_id'], ['flame.domains.id'], name=op.f('fk_categories_domain_id_domains'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_categories')),
    sa.UniqueConstraint('domain_id', 'normalized_name', name=op.f('uq_categories_domain_id')),
    sa.UniqueConstraint('id', 'domain_id', name=op.f('uq_categories_id')),
    schema='flame'
    )
    op.create_table('topics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('domain_id', sa.UUID(), nullable=False),
    sa.Column('category_id', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_topics_display_order_nonnegative')),
    sa.ForeignKeyConstraint(['category_id', 'domain_id'], ['flame.categories.id', 'flame.categories.domain_id'], name=op.f('fk_topics_category_id_categories'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['domain_id'], ['flame.domains.id'], name=op.f('fk_topics_domain_id_domains'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_topics')),
    schema='flame'
    )
    op.create_index('uq_topics_categorized_path', 'topics', ['domain_id', 'category_id', 'normalized_name'], unique=True, schema='flame', postgresql_where=sa.text('category_id IS NOT NULL'))
    op.create_index('uq_topics_uncategorized_path', 'topics', ['domain_id', 'normalized_name'], unique=True, schema='flame', postgresql_where=sa.text('category_id IS NULL'))
    op.create_table('subtopics',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('topic_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('normalized_name', sa.String(length=255), nullable=False),
    sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('display_order >= 0', name=op.f('ck_subtopics_display_order_nonnegative')),
    sa.ForeignKeyConstraint(['topic_id'], ['flame.topics.id'], name=op.f('fk_subtopics_topic_id_topics'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_subtopics')),
    sa.UniqueConstraint('topic_id', 'normalized_name', name=op.f('uq_subtopics_topic_id')),
    schema='flame'
    )


def downgrade() -> None:
    op.drop_table('subtopics', schema='flame')
    op.drop_index('uq_topics_uncategorized_path', table_name='topics', schema='flame', postgresql_where=sa.text('category_id IS NULL'))
    op.drop_index('uq_topics_categorized_path', table_name='topics', schema='flame', postgresql_where=sa.text('category_id IS NOT NULL'))
    op.drop_table('topics', schema='flame')
    op.drop_table('categories', schema='flame')
    op.drop_table('domains', schema='flame')
    op.drop_table('subjects', schema='flame')
    op.drop_table('levels', schema='flame')
    op.drop_table('curriculum_revisions', schema='flame')
    op.drop_table('curricula', schema='flame')
