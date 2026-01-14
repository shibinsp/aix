"""Role-Based Access Control (RBAC) utilities."""
from functools import wraps
from typing import List, Callable, Any
from fastapi import HTTPException, status

from app.models.admin import UserRole, Permission, ROLE_PERMISSIONS
from app.models.user import User


def check_role_hierarchy(actor_role: UserRole, target_role: UserRole) -> bool:
    """
    Check if actor's role is higher in hierarchy than target's role.

    Role hierarchy: SUPER_ADMIN > ADMIN > MODERATOR > USER

    Args:
        actor_role: The role of the user performing the action
        target_role: The role of the user being acted upon

    Returns:
        True if actor has higher or equal role
    """
    hierarchy = {
        UserRole.SUPER_ADMIN: 4,
        UserRole.ADMIN: 3,
        UserRole.MODERATOR: 2,
        UserRole.USER: 1,
    }
    return hierarchy.get(actor_role, 0) > hierarchy.get(target_role, 0)


def can_manage_role(actor_role: UserRole, target_role: UserRole) -> bool:
    """
    Check if actor can manage users with target role.

    - Super Admin can manage all roles
    - Admin can manage Moderator and User
    - Moderator can only manage User
    - User cannot manage anyone

    Args:
        actor_role: The role of the user performing the action
        target_role: The role being assigned or managed

    Returns:
        True if actor can manage the target role
    """
    if actor_role == UserRole.SUPER_ADMIN:
        return True
    if actor_role == UserRole.ADMIN:
        return target_role in (UserRole.MODERATOR, UserRole.USER)
    if actor_role == UserRole.MODERATOR:
        return target_role == UserRole.USER
    return False


def get_role_permissions(role: UserRole) -> List[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, [])


def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.

    Checks permission overrides first, then falls back to role-based permissions.

    Args:
        user: The user to check
        permission: The permission to check for

    Returns:
        True if user has the permission
    """
    # Use the user model's has_permission method
    return user.has_permission(permission)


def has_any_permission(user: User, permissions: List[Permission]) -> bool:
    """Check if user has any of the specified permissions."""
    return any(has_permission(user, p) for p in permissions)


def has_all_permissions(user: User, permissions: List[Permission]) -> bool:
    """Check if user has all of the specified permissions."""
    return all(has_permission(user, p) for p in permissions)


def require_permission(permission: Permission):
    """
    Decorator to require a specific permission for an endpoint.

    Usage:
        @require_permission(Permission.USER_CREATE)
        async def create_user(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Find the user in kwargs (usually 'current_user' or 'user')
            user = kwargs.get('current_user') or kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            if not has_permission(user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(*permissions: Permission):
    """Decorator to require any of the specified permissions."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user') or kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            if not has_any_permission(user, list(permissions)):
                perm_names = [p.value for p in permissions]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: one of {perm_names} required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(min_role: UserRole):
    """
    Decorator to require a minimum role level.

    Usage:
        @require_role(UserRole.MODERATOR)
        async def moderate_content(user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user = kwargs.get('current_user') or kwargs.get('user')
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated"
                )

            hierarchy = {
                UserRole.USER: 1,
                UserRole.MODERATOR: 2,
                UserRole.ADMIN: 3,
                UserRole.SUPER_ADMIN: 4,
            }

            user_level = hierarchy.get(user.role, 0)
            required_level = hierarchy.get(min_role, 0)

            if user_level < required_level:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role {min_role.value} or higher required"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


class PermissionChecker:
    """
    Dependency class for checking permissions in FastAPI routes.

    Usage:
        @router.get("/users")
        async def list_users(
            current_user: User = Depends(get_current_user),
            _: None = Depends(PermissionChecker(Permission.USER_VIEW))
        ):
            ...
    """

    def __init__(self, *permissions: Permission, require_all: bool = False):
        self.permissions = permissions
        self.require_all = require_all

    async def __call__(self, current_user: Any = None):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        if self.require_all:
            if not has_all_permissions(current_user, list(self.permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
        else:
            if not has_any_permission(current_user, list(self.permissions)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )


class RoleChecker:
    """
    Dependency class for checking roles in FastAPI routes.

    Usage:
        @router.get("/admin/settings")
        async def get_settings(
            current_user: User = Depends(get_current_user),
            _: None = Depends(RoleChecker(UserRole.ADMIN))
        ):
            ...
    """

    def __init__(self, min_role: UserRole):
        self.min_role = min_role
        self.hierarchy = {
            UserRole.USER: 1,
            UserRole.MODERATOR: 2,
            UserRole.ADMIN: 3,
            UserRole.SUPER_ADMIN: 4,
        }

    async def __call__(self, current_user: Any = None):
        if not current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated"
            )

        user_level = self.hierarchy.get(current_user.role, 0)
        required_level = self.hierarchy.get(self.min_role, 0)

        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {self.min_role.value} or higher required"
            )
