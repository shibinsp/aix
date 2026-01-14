"""Add admin system tables and user role fields.

Revision ID: 001_admin_system
Revises:
Create Date: 2026-01-10

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_admin_system'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add terminated_by_admin to lab_sessions table
    op.add_column('lab_sessions', sa.Column('terminated_by_admin', sa.Boolean(), nullable=False, server_default='false'))

    # Create enum types
    op.execute("CREATE TYPE userrole AS ENUM ('super_admin', 'admin', 'moderator', 'user')")
    op.execute("""CREATE TYPE permission AS ENUM (
        'user:view', 'user:create', 'user:update', 'user:delete', 'user:role_assign', 'user:ban',
        'content:view', 'content:create', 'content:update', 'content:delete', 'content:approve', 'content:publish',
        'lab:view', 'lab:create', 'lab:delete', 'lab:manage_all',
        'vm:start', 'vm:stop_any',
        'settings:view', 'settings:update',
        'api_keys:view', 'api_keys:manage',
        'audit:view', 'audit:export',
        'monitor:view', 'monitor:manage',
        'admin:manage', 'super_admin:access'
    )""")
    op.execute("CREATE TYPE settingcategory AS ENUM ('general', 'ai_services', 'labs', 'security', 'rate_limits', 'notifications', 'features')")
    op.execute("""CREATE TYPE auditaction AS ENUM (
        'auth.login', 'auth.login_failed', 'auth.logout', 'auth.password_change', 'auth.password_reset',
        'user.create', 'user.update', 'user.delete', 'user.role_change', 'user.ban', 'user.unban', 'user.permission_override',
        'course.create', 'course.update', 'course.delete', 'course.publish', 'course.unpublish', 'course.approve', 'course.reject',
        'lab.create', 'lab.update', 'lab.delete', 'lab.publish', 'lab.approve', 'lab.reject',
        'setting.update', 'api_key.create', 'api_key.update', 'api_key.delete', 'api_key.view',
        'lab_session.start', 'lab_session.stop', 'lab_session.force_stop',
        'vm.start', 'vm.stop', 'vm.force_stop',
        'system.restart', 'backup.create', 'backup.restore', 'settings.export', 'settings.import', 'audit.export'
    )""")
    op.execute("CREATE TYPE auditseverity AS ENUM ('info', 'warning', 'critical')")

    # Add role column to users table
    op.add_column('users', sa.Column('role', postgresql.ENUM('super_admin', 'admin', 'moderator', 'user', name='userrole', create_type=False), nullable=True))
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    op.alter_column('users', 'role', nullable=False, server_default='user')
    op.create_index('ix_users_role', 'users', ['role'])

    # Add ban tracking columns to users
    op.add_column('users', sa.Column('is_banned', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('users', sa.Column('banned_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('banned_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True))
    op.add_column('users', sa.Column('ban_reason', sa.Text(), nullable=True))

    # Create role_permissions table
    op.create_table(
        'role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('role', postgresql.ENUM('super_admin', 'admin', 'moderator', 'user', name='userrole', create_type=False), nullable=False, index=True),
        sa.Column('permission', postgresql.ENUM(name='permission', create_type=False), nullable=False),
        sa.UniqueConstraint('role', 'permission', name='uix_role_permission'),
    )

    # Create user_permission_overrides table
    op.create_table(
        'user_permission_overrides',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('permission', postgresql.ENUM(name='permission', create_type=False), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.UniqueConstraint('user_id', 'permission', name='uix_user_permission'),
    )

    # Create system_settings table
    op.create_table(
        'system_settings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('value_type', sa.String(20), nullable=False, server_default='string'),
        sa.Column('category', postgresql.ENUM('general', 'ai_services', 'labs', 'security', 'rate_limits', 'notifications', 'features', name='settingcategory', create_type=False), nullable=False, index=True),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_sensitive', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_readonly', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('requires_restart', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_super_admin_only', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('validation_rules', postgresql.JSON(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create api_key_store table
    op.create_table(
        'api_key_store',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('service_name', sa.String(100), unique=True, nullable=False, index=True),
        sa.Column('encrypted_key', sa.Text(), nullable=True),
        sa.Column('key_hint', sa.String(20), nullable=True),
        sa.Column('label', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('documentation_url', sa.String(500), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_configured', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('is_valid', sa.Boolean(), nullable=True),
        sa.Column('last_validated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validation_error', sa.Text(), nullable=True),
        sa.Column('updated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('user_email', sa.String(255), nullable=True),
        sa.Column('user_role', sa.String(50), nullable=True),
        sa.Column('action', postgresql.ENUM(name='auditaction', create_type=False), nullable=False, index=True),
        sa.Column('severity', postgresql.ENUM('info', 'warning', 'critical', name='auditseverity', create_type=False), nullable=False, server_default='info'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('target_type', sa.String(50), nullable=True, index=True),
        sa.Column('target_id', sa.String(100), nullable=True),
        sa.Column('target_name', sa.String(255), nullable=True),
        sa.Column('old_value', postgresql.JSON(), nullable=True),
        sa.Column('new_value', postgresql.JSON(), nullable=True),
        sa.Column('extra_data', postgresql.JSON(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # Create indexes for audit_logs
    op.create_index('ix_audit_logs_user_timestamp', 'audit_logs', ['user_id', 'timestamp'])
    op.create_index('ix_audit_logs_action_timestamp', 'audit_logs', ['action', 'timestamp'])
    op.create_index('ix_audit_logs_target', 'audit_logs', ['target_type', 'target_id'])


def downgrade() -> None:
    # Remove terminated_by_admin from lab_sessions
    op.drop_column('lab_sessions', 'terminated_by_admin')

    # Drop tables
    op.drop_table('audit_logs')
    op.drop_table('api_key_store')
    op.drop_table('system_settings')
    op.drop_table('user_permission_overrides')
    op.drop_table('role_permissions')

    # Remove columns from users
    op.drop_column('users', 'ban_reason')
    op.drop_column('users', 'banned_by')
    op.drop_column('users', 'banned_at')
    op.drop_column('users', 'is_banned')
    op.drop_index('ix_users_role', 'users')
    op.drop_column('users', 'role')

    # Drop enum types
    op.execute("DROP TYPE auditseverity")
    op.execute("DROP TYPE auditaction")
    op.execute("DROP TYPE settingcategory")
    op.execute("DROP TYPE permission")
    op.execute("DROP TYPE userrole")
