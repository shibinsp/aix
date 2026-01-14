"""Common dependencies for authentication and authorization."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User
from app.models.admin import UserRole, Permission


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get the current authenticated user."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.permission_overrides))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="User account is banned")
    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin privileges (Admin or Super Admin)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def get_current_super_admin(user: User = Depends(get_current_user)) -> User:
    """Require super admin privileges."""
    if not user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return user


async def get_current_moderator(user: User = Depends(get_current_user)) -> User:
    """Require at least moderator privileges."""
    if not user.is_moderator:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Moderator privileges required",
        )
    return user


def require_permission(permission: Permission):
    """
    Create a dependency that requires a specific permission.

    Usage:
        @router.get("/users")
        async def list_users(
            current_user: User = Depends(require_permission(Permission.USER_VIEW))
        ):
            ...
    """
    async def permission_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required",
            )
        return user

    return permission_checker


def require_any_permission(*permissions: Permission):
    """
    Create a dependency that requires any of the specified permissions.

    Usage:
        @router.get("/content")
        async def list_content(
            current_user: User = Depends(require_any_permission(
                Permission.CONTENT_VIEW, Permission.CONTENT_CREATE
            ))
        ):
            ...
    """
    async def permission_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        for perm in permissions:
            if user.has_permission(perm):
                return user

        perm_names = [p.value for p in permissions]
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: one of {perm_names} required",
        )

    return permission_checker


def require_role(min_role: UserRole):
    """
    Create a dependency that requires a minimum role level.

    Usage:
        @router.get("/admin/settings")
        async def get_settings(
            current_user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
    """
    role_hierarchy = {
        UserRole.USER: 1,
        UserRole.MODERATOR: 2,
        UserRole.ADMIN: 3,
        UserRole.SUPER_ADMIN: 4,
    }

    async def role_checker(
        user: User = Depends(get_current_user),
    ) -> User:
        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(min_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {min_role.value} or higher required",
            )
        return user

    return role_checker
