"""CLI commands for administrative tasks."""
import asyncio
import sys
import secrets
import string
from typing import Optional

import click
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.admin import UserRole
from app.models.settings import DEFAULT_SETTINGS, DEFAULT_API_KEYS
from app.services.settings.settings_service import SettingsService, APIKeyService


def get_db_session():
    """Create a database session for CLI commands."""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return async_session


def generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@click.group()
def cli():
    """AI CyberX Administration CLI."""
    pass


@cli.command()
@click.option("--email", prompt="Email address", help="Super admin email")
@click.option("--username", prompt="Username", help="Super admin username")
@click.option("--password", default=None, help="Password (leave empty to generate)")
@click.option("--full-name", default="Super Admin", help="Full name")
def create_superadmin(
    email: str, username: str, password: Optional[str], full_name: str
):
    """Create a super admin user."""

    async def _create():
        async_session = get_db_session()
        async with async_session() as db:
            # Check if user exists
            result = await db.execute(
                select(User).where((User.email == email) | (User.username == username))
            )
            existing = result.scalar_one_or_none()

            if existing:
                if existing.email == email:
                    click.echo(f"Error: User with email {email} already exists.")
                else:
                    click.echo(f"Error: User with username {username} already exists.")
                return False

            # Check if any super admin exists
            result = await db.execute(
                select(User).where(User.role == UserRole.SUPER_ADMIN)
            )
            existing_super = result.scalar_one_or_none()

            if existing_super:
                click.echo(
                    f"Warning: Super admin already exists ({existing_super.email})"
                )
                if not click.confirm("Create another super admin?"):
                    return False

            # Generate password if not provided
            actual_password = password or generate_password()

            # Create user
            from datetime import datetime, timezone

            user = User(
                email=email,
                username=username,
                hashed_password=get_password_hash(actual_password),
                full_name=full_name,
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_verified=True,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            db.add(user)
            await db.commit()
            await db.refresh(user)

            click.echo("\n" + "=" * 50)
            click.echo("Super Admin Created Successfully!")
            click.echo("=" * 50)
            click.echo(f"Email:    {email}")
            click.echo(f"Username: {username}")
            click.echo(f"Password: {actual_password}")
            click.echo(f"Role:     {user.role.value}")
            click.echo("=" * 50)
            click.echo("\nPlease save these credentials securely!")
            if not password:
                click.echo("(Password was auto-generated)")

            return True

    asyncio.run(_create())


@cli.command()
@click.option("--email", prompt="Email address", help="User email to promote")
def promote_to_admin(email: str):
    """Promote an existing user to admin role."""

    async def _promote():
        async_session = get_db_session()
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                click.echo(f"Error: User with email {email} not found.")
                return False

            if user.role in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
                click.echo(f"User {email} is already an {user.role.value}.")
                return False

            old_role = user.role
            user.role = UserRole.ADMIN
            await db.commit()

            click.echo(f"User {email} promoted from {old_role.value} to admin.")
            return True

    asyncio.run(_promote())


@cli.command()
@click.option("--email", prompt="Email address", help="User email to demote")
def demote_to_user(email: str):
    """Demote a user to regular user role."""

    async def _demote():
        async_session = get_db_session()
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                click.echo(f"Error: User with email {email} not found.")
                return False

            if user.role == UserRole.USER:
                click.echo(f"User {email} is already a regular user.")
                return False

            if user.role == UserRole.SUPER_ADMIN:
                if not click.confirm(
                    "This will demote a super admin. Are you sure?"
                ):
                    return False

            old_role = user.role
            user.role = UserRole.USER
            await db.commit()

            click.echo(f"User {email} demoted from {old_role.value} to user.")
            return True

    asyncio.run(_demote())


@cli.command()
def list_admins():
    """List all admin and super admin users."""

    async def _list():
        async_session = get_db_session()
        async with async_session() as db:
            result = await db.execute(
                select(User).where(
                    User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.MODERATOR])
                )
            )
            admins = result.scalars().all()

            if not admins:
                click.echo("No admins found.")
                return

            click.echo("\nAdmin Users:")
            click.echo("-" * 60)
            for admin in admins:
                status = "Active" if admin.is_active else "Inactive"
                banned = " (BANNED)" if admin.is_banned else ""
                click.echo(f"{admin.role.value:12} | {admin.email:30} | {status}{banned}")

    asyncio.run(_list())


@cli.command()
def seed_settings():
    """Seed default system settings and API key entries."""

    async def _seed():
        async_session = get_db_session()
        async with async_session() as db:
            settings_service = SettingsService(db)
            api_key_service = APIKeyService(db)

            settings_count = await settings_service.seed_defaults()
            api_keys_count = await api_key_service.seed_defaults()

            click.echo(f"Seeded {settings_count} settings and {api_keys_count} API key entries.")

    asyncio.run(_seed())


@cli.command()
@click.option("--email", prompt="Email address", help="User email to reset")
@click.option("--password", default=None, help="New password (leave empty to generate)")
def reset_password(email: str, password: Optional[str]):
    """Reset a user's password."""

    async def _reset():
        async_session = get_db_session()
        async with async_session() as db:
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()

            if not user:
                click.echo(f"Error: User with email {email} not found.")
                return False

            actual_password = password or generate_password()
            user.hashed_password = get_password_hash(actual_password)
            await db.commit()

            click.echo(f"\nPassword reset for {email}")
            click.echo(f"New password: {actual_password}")
            if not password:
                click.echo("(Password was auto-generated)")

            return True

    asyncio.run(_reset())


@cli.command()
def check_db():
    """Check database connection and tables."""

    async def _check():
        try:
            async_session = get_db_session()
            async with async_session() as db:
                # Try a simple query
                result = await db.execute(select(User).limit(1))
                click.echo("Database connection: OK")

                # Count users
                from sqlalchemy import func
                result = await db.execute(select(func.count(User.id)))
                count = result.scalar()
                click.echo(f"Total users: {count}")

                # Count by role
                for role in UserRole:
                    result = await db.execute(
                        select(func.count(User.id)).where(User.role == role)
                    )
                    role_count = result.scalar()
                    click.echo(f"  {role.value}: {role_count}")

        except Exception as e:
            click.echo(f"Database error: {e}")
            return False

    asyncio.run(_check())


if __name__ == "__main__":
    cli()
