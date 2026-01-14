"""Add organization system tables.

Revision ID: 002_organization_system
Revises: 001_admin_system
Create Date: 2026-01-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002_organization_system'
down_revision: Union[str, None] = '001_admin_system'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create new enum types (with IF NOT EXISTS for idempotency)
    op.execute("DO $$ BEGIN CREATE TYPE organizationtype AS ENUM ('enterprise', 'educational', 'government', 'non_profit'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE orgmemberrole AS ENUM ('owner', 'admin', 'instructor', 'member'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE batchstatus AS ENUM ('active', 'inactive', 'completed', 'archived'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE environmenttype AS ENUM ('terminal', 'desktop'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE environmentstatus AS ENUM ('stopped', 'starting', 'running', 'stopping', 'error'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE invitationstatus AS ENUM ('pending', 'accepted', 'expired', 'cancelled', 'declined'); EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Update permission enum to add new permissions (idempotent)
    # PostgreSQL requires ALTER TYPE ADD VALUE - wrap in DO block to ignore if exists
    permission_values = [
        'org:create', 'org:view', 'org:update', 'org:delete', 'org:manage_members',
        'batch:create', 'batch:view', 'batch:update', 'batch:delete', 'batch:manage_members',
        'limits:view', 'limits:update', 'limits:override',
        'env:view_all', 'env:manage',
        'analytics:view', 'analytics:export',
        'invite:create', 'invite:view', 'invite:manage',
        'import:users'
    ]
    for perm in permission_values:
        op.execute(f"DO $$ BEGIN ALTER TYPE permission ADD VALUE '{perm}'; EXCEPTION WHEN duplicate_object THEN null; END $$;")

    # Create organizations table
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(255), unique=True, nullable=False, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('org_type', postgresql.ENUM('enterprise', 'educational', 'government', 'non_profit', name='organizationtype', create_type=False), nullable=False, server_default='educational'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('website', sa.String(500), nullable=True),
        sa.Column('contact_email', sa.String(255), nullable=True),
        sa.Column('max_members', sa.Integer(), nullable=True),
        sa.Column('subscription_tier', sa.String(50), nullable=True),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_organizations_name', 'organizations', ['name'])
    op.create_index('ix_organizations_type', 'organizations', ['org_type'])

    # Create batches table
    op.create_table(
        'batches',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', postgresql.ENUM('active', 'inactive', 'completed', 'archived', name='batchstatus', create_type=False), nullable=False, server_default='active'),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('max_users', sa.Integer(), nullable=True),
        sa.Column('curriculum_courses', postgresql.JSON(), nullable=True),
        sa.Column('settings', postgresql.JSON(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_batches_status', 'batches', ['status'])
    op.create_index('ix_batches_org_name', 'batches', ['organization_id', 'name'])

    # Create organization_memberships table
    op.create_table(
        'organization_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),  # Single org per user
        sa.Column('org_role', postgresql.ENUM('owner', 'admin', 'instructor', 'member', name='orgmemberrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_org_memberships_org_role', 'organization_memberships', ['organization_id', 'org_role'])

    # Create batch_memberships table
    op.create_table(
        'batch_memberships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('progress_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('courses_completed', postgresql.JSON(), nullable=True),
        sa.Column('labs_completed', postgresql.JSON(), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('batch_id', 'user_id', name='uix_batch_user'),
    )

    # Create organization_resource_limits table
    op.create_table(
        'organization_resource_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('max_courses_per_user', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('max_ai_generated_courses', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('max_concurrent_labs', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('max_lab_duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('max_terminal_hours_monthly', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('max_desktop_hours_monthly', sa.Integer(), nullable=False, server_default='10'),
        sa.Column('max_storage_gb', sa.Integer(), nullable=False, server_default='2'),
        sa.Column('enable_persistent_vm', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('custom_limits', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create batch_resource_limits table
    op.create_table(
        'batch_resource_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('batches.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('max_courses_per_user', sa.Integer(), nullable=True),
        sa.Column('max_ai_generated_courses', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_labs', sa.Integer(), nullable=True),
        sa.Column('max_lab_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('max_terminal_hours_monthly', sa.Integer(), nullable=True),
        sa.Column('max_desktop_hours_monthly', sa.Integer(), nullable=True),
        sa.Column('max_storage_gb', sa.Integer(), nullable=True),
        sa.Column('enable_persistent_vm', sa.Boolean(), nullable=True),
        sa.Column('custom_limits', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create user_resource_limits table
    op.create_table(
        'user_resource_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('max_courses_per_user', sa.Integer(), nullable=True),
        sa.Column('max_ai_generated_courses', sa.Integer(), nullable=True),
        sa.Column('max_concurrent_labs', sa.Integer(), nullable=True),
        sa.Column('max_lab_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('max_terminal_hours_monthly', sa.Integer(), nullable=True),
        sa.Column('max_desktop_hours_monthly', sa.Integer(), nullable=True),
        sa.Column('max_storage_gb', sa.Integer(), nullable=True),
        sa.Column('enable_persistent_vm', sa.Boolean(), nullable=True),
        sa.Column('unlimited_access', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('set_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('custom_limits', postgresql.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create user_usage_tracking table
    op.create_table(
        'user_usage_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('courses_created_total', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_courses_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('ai_courses_reset_date', sa.Date(), nullable=True),
        sa.Column('active_lab_sessions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('terminal_minutes_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('desktop_minutes_this_month', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_reset_date', sa.Date(), nullable=True),
        sa.Column('storage_used_mb', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # Create persistent_environments table
    op.create_table(
        'persistent_environments',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('env_type', postgresql.ENUM('terminal', 'desktop', name='environmenttype', create_type=False), nullable=False),
        sa.Column('container_id', sa.String(100), nullable=True),
        sa.Column('vm_id', sa.String(100), nullable=True),
        sa.Column('volume_name', sa.String(100), nullable=False),
        sa.Column('ssh_port', sa.Integer(), nullable=True),
        sa.Column('vnc_port', sa.Integer(), nullable=True),
        sa.Column('novnc_port', sa.Integer(), nullable=True),
        sa.Column('access_url', sa.String(500), nullable=True),
        sa.Column('vnc_password', sa.String(100), nullable=True),
        sa.Column('status', postgresql.ENUM('stopped', 'starting', 'running', 'stopping', 'error', name='environmentstatus', create_type=False), nullable=False, server_default='stopped'),
        sa.Column('last_started', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_stopped', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('total_usage_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('monthly_usage_minutes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('usage_reset_date', sa.Date(), nullable=True),
        sa.Column('memory_mb', sa.Integer(), nullable=False, server_default='512'),
        sa.Column('cpu_cores', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.UniqueConstraint('user_id', 'env_type', name='uix_user_env_type'),
    )
    op.create_index('ix_persistent_env_status', 'persistent_environments', ['status'])

    # Create environment_sessions table
    op.create_table(
        'environment_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('environment_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('persistent_environments.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('lab_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('peak_memory_mb', sa.Integer(), nullable=True),
        sa.Column('peak_cpu_percent', sa.Integer(), nullable=True),
        sa.Column('termination_reason', sa.String(100), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_env_sessions_user_dates', 'environment_sessions', ['user_id', 'started_at'])

    # Create invitations table
    op.create_table(
        'invitations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('token', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('email', sa.String(255), nullable=False, index=True),
        sa.Column('full_name', sa.String(255), nullable=True),
        sa.Column('role', postgresql.ENUM('owner', 'admin', 'instructor', 'member', name='orgmemberrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('status', postgresql.ENUM('pending', 'accepted', 'expired', 'cancelled', 'declined', name='invitationstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('invited_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accepted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('email_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('email_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reminder_sent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reminder_sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index('ix_invitations_org_status', 'invitations', ['organization_id', 'status'])
    op.create_index('ix_invitations_email_status', 'invitations', ['email', 'status'])

    # Create bulk_import_jobs table
    op.create_table(
        'bulk_import_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('filename', sa.String(255), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('total_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('processed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('successful_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_rows', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', sa.Text(), nullable=True),
        sa.Column('created_user_ids', sa.Text(), nullable=True),
        sa.Column('send_invitations', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('default_role', postgresql.ENUM('owner', 'admin', 'instructor', 'member', name='orgmemberrole', create_type=False), nullable=False, server_default='member'),
        sa.Column('default_batch_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('batches.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table('bulk_import_jobs')
    op.drop_table('invitations')
    op.drop_index('ix_env_sessions_user_dates', 'environment_sessions')
    op.drop_table('environment_sessions')
    op.drop_index('ix_persistent_env_status', 'persistent_environments')
    op.drop_table('persistent_environments')
    op.drop_table('user_usage_tracking')
    op.drop_table('user_resource_limits')
    op.drop_table('batch_resource_limits')
    op.drop_table('organization_resource_limits')
    op.drop_table('batch_memberships')
    op.drop_index('ix_org_memberships_org_role', 'organization_memberships')
    op.drop_table('organization_memberships')
    op.drop_index('ix_batches_org_name', 'batches')
    op.drop_index('ix_batches_status', 'batches')
    op.drop_table('batches')
    op.drop_index('ix_organizations_type', 'organizations')
    op.drop_index('ix_organizations_name', 'organizations')
    op.drop_table('organizations')

    # Drop enum types
    op.execute("DROP TYPE invitationstatus")
    op.execute("DROP TYPE environmentstatus")
    op.execute("DROP TYPE environmenttype")
    op.execute("DROP TYPE batchstatus")
    op.execute("DROP TYPE orgmemberrole")
    op.execute("DROP TYPE organizationtype")

    # Note: Cannot easily remove values from permission enum in PostgreSQL
    # The added permission values will remain in the enum
