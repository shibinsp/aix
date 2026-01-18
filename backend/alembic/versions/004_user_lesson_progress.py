"""Add user_lesson_progress table for tracking lesson completion

Revision ID: 004_user_lesson_progress
Revises: 003_lab_course
Create Date: 2026-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_user_lesson_progress'
down_revision = '003_lab_course'
branch_labels = None
depends_on = None


def upgrade():
    # Create user_lesson_progress table
    op.create_table(
        'user_lesson_progress',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('lesson_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('lessons.id'), nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('courses.id'), nullable=False),
        sa.Column('status', sa.String(50), default='in_progress', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_spent_minutes', sa.Integer(), default=0),
        sa.Column('points_awarded', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Create indexes for efficient lookups
    op.create_index('ix_user_lesson_progress_user_id', 'user_lesson_progress', ['user_id'])
    op.create_index('ix_user_lesson_progress_lesson_id', 'user_lesson_progress', ['lesson_id'])
    op.create_index('ix_user_lesson_progress_course_id', 'user_lesson_progress', ['course_id'])

    # Create unique constraint to prevent duplicate progress entries
    op.create_unique_constraint(
        'unique_user_lesson_progress',
        'user_lesson_progress',
        ['user_id', 'lesson_id']
    )


def downgrade():
    # Remove unique constraint
    op.drop_constraint('unique_user_lesson_progress', 'user_lesson_progress', type_='unique')

    # Remove indexes
    op.drop_index('ix_user_lesson_progress_course_id', table_name='user_lesson_progress')
    op.drop_index('ix_user_lesson_progress_lesson_id', table_name='user_lesson_progress')
    op.drop_index('ix_user_lesson_progress_user_id', table_name='user_lesson_progress')

    # Drop table
    op.drop_table('user_lesson_progress')
