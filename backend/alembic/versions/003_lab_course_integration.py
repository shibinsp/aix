"""Add lab-course integration fields to LabSession

Revision ID: 003_lab_course
Revises: 002_organization_system
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_lab_course'
down_revision = '002_organization_system'
branch_labels = None
depends_on = None


def upgrade():
    # Add course integration fields to lab_sessions
    op.add_column('lab_sessions', sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('lab_sessions', sa.Column('lesson_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('lab_sessions', sa.Column('completed_objectives', sa.JSON(), nullable=True, server_default='[]'))
    op.add_column('lab_sessions', sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lab_sessions', sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('lab_sessions', sa.Column('duration_minutes', sa.Integer(), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key(
        'fk_lab_sessions_course_id',
        'lab_sessions', 'courses',
        ['course_id'], ['id'],
        ondelete='SET NULL'
    )
    op.create_foreign_key(
        'fk_lab_sessions_lesson_id',
        'lab_sessions', 'lessons',
        ['lesson_id'], ['id'],
        ondelete='SET NULL'
    )

    # Add index for course_id lookups
    op.create_index('ix_lab_sessions_course_id', 'lab_sessions', ['course_id'])


def downgrade():
    # Remove indexes
    op.drop_index('ix_lab_sessions_course_id', table_name='lab_sessions')

    # Remove foreign keys
    op.drop_constraint('fk_lab_sessions_lesson_id', 'lab_sessions', type_='foreignkey')
    op.drop_constraint('fk_lab_sessions_course_id', 'lab_sessions', type_='foreignkey')

    # Remove columns
    op.drop_column('lab_sessions', 'duration_minutes')
    op.drop_column('lab_sessions', 'ended_at')
    op.drop_column('lab_sessions', 'last_activity')
    op.drop_column('lab_sessions', 'completed_objectives')
    op.drop_column('lab_sessions', 'lesson_id')
    op.drop_column('lab_sessions', 'course_id')
