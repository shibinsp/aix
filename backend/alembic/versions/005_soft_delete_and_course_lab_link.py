"""Add soft delete support and course-lab linking

Revision ID: 005_soft_delete
Revises: 004_user_lesson_progress
Create Date: 2026-01-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_soft_delete'
down_revision = '004_user_lesson_progress'
branch_labels = None
depends_on = None


def upgrade():
    # Add soft delete fields to courses table
    op.add_column('courses', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('courses', sa.Column('deleted_at', sa.DateTime(), nullable=True))
    op.add_column('courses', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key for deleted_by in courses
    op.create_foreign_key('fk_courses_deleted_by', 'courses', 'users', ['deleted_by'], ['id'])

    # Add index on is_deleted for courses (for efficient filtering)
    op.create_index('ix_courses_is_deleted', 'courses', ['is_deleted'])

    # Add soft delete fields to labs table
    op.add_column('labs', sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('labs', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('labs', sa.Column('deleted_by', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key for deleted_by in labs
    op.create_foreign_key('fk_labs_deleted_by', 'labs', 'users', ['deleted_by'], ['id'])

    # Add index on is_deleted for labs
    op.create_index('ix_labs_is_deleted', 'labs', ['is_deleted'])

    # Add course_id to labs table for cascade delete relationship
    op.add_column('labs', sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key for course_id in labs
    op.create_foreign_key('fk_labs_course_id', 'labs', 'courses', ['course_id'], ['id'])

    # Add index on course_id for labs
    op.create_index('ix_labs_course_id', 'labs', ['course_id'])


def downgrade():
    # Remove course_id from labs
    op.drop_index('ix_labs_course_id', 'labs')
    op.drop_constraint('fk_labs_course_id', 'labs', type_='foreignkey')
    op.drop_column('labs', 'course_id')

    # Remove soft delete fields from labs
    op.drop_index('ix_labs_is_deleted', 'labs')
    op.drop_constraint('fk_labs_deleted_by', 'labs', type_='foreignkey')
    op.drop_column('labs', 'deleted_by')
    op.drop_column('labs', 'deleted_at')
    op.drop_column('labs', 'is_deleted')

    # Remove soft delete fields from courses
    op.drop_index('ix_courses_is_deleted', 'courses')
    op.drop_constraint('fk_courses_deleted_by', 'courses', type_='foreignkey')
    op.drop_column('courses', 'deleted_by')
    op.drop_column('courses', 'deleted_at')
    op.drop_column('courses', 'is_deleted')
