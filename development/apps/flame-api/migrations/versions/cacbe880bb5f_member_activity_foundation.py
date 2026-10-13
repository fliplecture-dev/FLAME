"""member_activity_foundation

Revision ID: cacbe880bb5f
Revises: 4ade4490344f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'cacbe880bb5f'
down_revision: Union[str, Sequence[str], None] = '4ade4490344f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint('uq_levels_id_curriculum', 'levels', ['id', 'curriculum_id'], schema='flame')
    op.create_unique_constraint('uq_subjects_id_level', 'subjects', ['id', 'level_id'], schema='flame')
    op.create_table('admin_roles',
    sa.Column('auth_subject', sa.String(length=255), nullable=False),
    sa.Column('granted_by_subject', sa.String(length=255), nullable=True),
    sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('auth_subject', name=op.f('pk_admin_roles')),
    schema='flame'
    )
    op.create_table('student_profiles',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('auth_subject', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=True),
    sa.Column('email', sa.String(length=320), nullable=True),
    sa.Column('status', sa.String(length=24), server_default='active', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_student_profiles')),
    sa.UniqueConstraint('auth_subject', name=op.f('uq_student_profiles_auth_subject')),
    schema='flame'
    )
    op.create_table('deletion_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['student_id'], ['flame.student_profiles.id'], name=op.f('fk_deletion_requests_student_id_student_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_deletion_requests')),
    schema='flame'
    )
    op.create_table('sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('mode', sa.String(length=16), nullable=False),
    sa.Column('curriculum_id', sa.UUID(), nullable=True),
    sa.Column('revision', sa.Integer(), nullable=True),
    sa.Column('context_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(mode = 'study' AND curriculum_id IS NOT NULL AND revision IS NOT NULL AND context_snapshot IS NOT NULL) OR (mode = 'curiosity' AND curriculum_id IS NULL)", name=op.f('ck_sessions_mode_context_valid')),
    sa.CheckConstraint("mode IN ('study', 'curiosity')", name=op.f('ck_sessions_mode_valid')),
    sa.CheckConstraint('revision IS NULL OR revision >= 1', name=op.f('ck_sessions_revision_positive')),
    sa.ForeignKeyConstraint(['curriculum_id'], ['flame.curricula.id'], name=op.f('fk_sessions_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['flame.student_profiles.id'], name=op.f('fk_sessions_student_id_student_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_sessions')),
    sa.UniqueConstraint('id', 'student_id', name=op.f('uq_sessions_id')),
    schema='flame'
    )
    op.create_table('activity_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=True),
    sa.Column('event_type', sa.String(length=64), nullable=False),
    sa.Column('path_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('deduplication_key', sa.String(length=255), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['session_id', 'student_id'], ['flame.sessions.id', 'flame.sessions.student_id'], name=op.f('fk_activity_events_session_id_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['flame.student_profiles.id'], name=op.f('fk_activity_events_student_id_student_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_activity_events')),
    sa.UniqueConstraint('student_id', 'deduplication_key', name=op.f('uq_activity_events_student_id')),
    schema='flame'
    )
    op.create_table('answer_requests',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('idempotency_key', sa.String(length=255), nullable=False),
    sa.Column('payload_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), server_default=sa.text("'pending'"), nullable=False),
    sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('pending', 'completed', 'failed')", name=op.f('ck_answer_requests_status_valid')),
    sa.ForeignKeyConstraint(['session_id', 'student_id'], ['flame.sessions.id', 'flame.sessions.student_id'], name=op.f('fk_answer_requests_session_id_sessions'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['flame.student_profiles.id'], name=op.f('fk_answer_requests_student_id_student_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_answer_requests')),
    sa.UniqueConstraint('student_id', 'session_id', 'idempotency_key', name=op.f('uq_answer_requests_student_id')),
    schema='flame'
    )
    op.create_table('learning_memberships',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('student_id', sa.UUID(), nullable=False),
    sa.Column('curriculum_id', sa.UUID(), nullable=False),
    sa.Column('level_id', sa.UUID(), nullable=True),
    sa.Column('subject_id', sa.UUID(), nullable=True),
    sa.Column('visible', sa.Boolean(), server_default=sa.text('true'), nullable=False),
    sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('subject_id IS NULL OR level_id IS NOT NULL', name=op.f('ck_learning_memberships_subject_requires_level')),
    sa.CheckConstraint('version >= 1', name=op.f('ck_learning_memberships_version_positive')),
    sa.ForeignKeyConstraint(['curriculum_id'], ['flame.curricula.id'], name=op.f('fk_learning_memberships_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['level_id', 'curriculum_id'], ['flame.levels.id', 'flame.levels.curriculum_id'], name=op.f('fk_learning_memberships_level_id_levels'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['student_id'], ['flame.student_profiles.id'], name=op.f('fk_learning_memberships_student_id_student_profiles'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['subject_id', 'level_id'], ['flame.subjects.id', 'flame.subjects.level_id'], name=op.f('fk_learning_memberships_subject_id_subjects'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_learning_memberships')),
    schema='flame'
    )
    op.create_index('uq_learning_curriculum_path', 'learning_memberships', ['student_id', 'curriculum_id'], unique=True, schema='flame', postgresql_where=sa.text('level_id IS NULL'))
    op.create_index('uq_learning_level_path', 'learning_memberships', ['student_id', 'curriculum_id', 'level_id'], unique=True, schema='flame', postgresql_where=sa.text('level_id IS NOT NULL AND subject_id IS NULL'))
    op.create_index('uq_learning_subject_path', 'learning_memberships', ['student_id', 'curriculum_id', 'level_id', 'subject_id'], unique=True, schema='flame', postgresql_where=sa.text('subject_id IS NOT NULL'))
    op.create_table('messages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('session_id', sa.UUID(), nullable=False),
    sa.Column('turn_number', sa.Integer(), nullable=False),
    sa.Column('role', sa.String(length=16), nullable=False),
    sa.Column('blocks', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('resolved_curriculum_id', sa.UUID(), nullable=True),
    sa.Column('resolved_subject_id', sa.UUID(), nullable=True),
    sa.Column('resolved_topic_id', sa.UUID(), nullable=True),
    sa.Column('resolved_revision', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('user', 'assistant')", name=op.f('ck_messages_role_valid')),
    sa.CheckConstraint('turn_number >= 1', name=op.f('ck_messages_turn_positive')),
    sa.ForeignKeyConstraint(['resolved_curriculum_id'], ['flame.curricula.id'], name=op.f('fk_messages_resolved_curriculum_id_curricula'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resolved_subject_id'], ['flame.subjects.id'], name=op.f('fk_messages_resolved_subject_id_subjects'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['resolved_topic_id'], ['flame.topics.id'], name=op.f('fk_messages_resolved_topic_id_topics'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['session_id'], ['flame.sessions.id'], name=op.f('fk_messages_session_id_sessions'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_messages')),
    sa.UniqueConstraint('session_id', 'turn_number', 'role', name=op.f('uq_messages_session_id')),
    schema='flame'
    )


def downgrade() -> None:
    op.drop_table('messages', schema='flame')
    op.drop_index('uq_learning_subject_path', table_name='learning_memberships', schema='flame', postgresql_where=sa.text('subject_id IS NOT NULL'))
    op.drop_index('uq_learning_level_path', table_name='learning_memberships', schema='flame', postgresql_where=sa.text('level_id IS NOT NULL AND subject_id IS NULL'))
    op.drop_index('uq_learning_curriculum_path', table_name='learning_memberships', schema='flame', postgresql_where=sa.text('level_id IS NULL'))
    op.drop_table('learning_memberships', schema='flame')
    op.drop_table('answer_requests', schema='flame')
    op.drop_table('activity_events', schema='flame')
    op.drop_table('sessions', schema='flame')
    op.drop_table('deletion_requests', schema='flame')
    op.drop_table('student_profiles', schema='flame')
    op.drop_table('admin_roles', schema='flame')
    op.drop_constraint('uq_subjects_id_level', 'subjects', schema='flame', type_='unique')
    op.drop_constraint('uq_levels_id_curriculum', 'levels', schema='flame', type_='unique')
