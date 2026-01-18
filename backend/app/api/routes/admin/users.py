"""Admin user management routes."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.core.security import get_password_hash
from app.core.permissions import can_manage_role
from app.core.sanitization import sanitize_like_pattern
from app.models.user import User
from app.models.admin import UserRole, UserPermissionOverride
from app.models.audit import AuditAction
from app.schemas.admin import (
    UserListItem,
    UserDetail,
    UserCreate,
    UserUpdate,
    RoleChange,
    BanUser,
    PermissionOverride,
)
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/users")


def utcnow():
    return datetime.now(timezone.utc)


@router.get("", response_model=list[UserListItem])
async def list_users(
    search: Optional[str] = Query(None, description="Search by email or username"),
    role: Optional[UserRole] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_banned: Optional[bool] = Query(None, description="Filter by ban status"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users with optional filters."""
    query = select(User)

    if search:
        search_pattern = sanitize_like_pattern(search)
        query = query.where(
            or_(
                User.email.ilike(f"%{search_pattern}%"),
                User.username.ilike(f"%{search_pattern}%"),
            )
        )

    if role:
        query = query.where(User.role == role)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if is_banned is not None:
        query = query.where(User.is_banned == is_banned)

    query = query.order_by(User.created_at.desc())
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    users = result.scalars().all()

    return [UserListItem.model_validate(u) for u in users]


@router.get("/count")
async def count_users(
    role: Optional[UserRole] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_banned: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user count with optional filters."""
    query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if is_banned is not None:
        query = query.where(User.is_banned == is_banned)

    count = await db.scalar(query)
    return {"count": count or 0}


@router.get("/{user_id}", response_model=UserDetail)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed user information."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.permission_overrides))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserDetail(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        is_banned=user.is_banned,
        created_at=user.created_at,
        last_login=user.last_login,
        total_points=user.total_points,
        is_verified=user.is_verified,
        skill_level=user.skill_level.value if user.skill_level else "beginner",
        learning_style=user.learning_style.value if user.learning_style else "kinesthetic",
        career_goal=user.career_goal.value if user.career_goal else "general",
        total_labs_completed=user.total_labs_completed,
        total_courses_completed=user.total_courses_completed,
        current_streak=user.current_streak,
        ban_reason=user.ban_reason,
        banned_at=user.banned_at,
    )


@router.post("", response_model=UserListItem)
async def create_user(
    user_data: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user (admin only)."""
    # Check if email exists
    existing = await db.execute(
        select(User).where(
            or_(User.email == user_data.email, User.username == user_data.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email or username already exists")

    # Check role assignment permission
    if user_data.role != UserRole.USER and not can_manage_role(
        current_user.role, user_data.role
    ):
        raise HTTPException(
            status_code=403, detail="Cannot assign this role"
        )

    new_user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True,
        created_at=utcnow(),
        updated_at=utcnow(),
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_CREATE,
        actor=current_user,
        target_user=new_user,
        new_data={"email": new_user.email, "role": new_user.role.value},
        request=request,
    )

    return UserListItem.model_validate(new_user)


@router.patch("/{user_id}", response_model=UserListItem)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user fields."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Can't edit users with higher role
    if not can_manage_role(current_user.role, user.role) and user.id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot edit this user")

    old_data = {
        "email": user.email,
        "username": user.username,
        "full_name": user.full_name,
        "is_active": user.is_active,
    }

    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = utcnow()
    await db.commit()
    await db.refresh(user)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_UPDATE,
        actor=current_user,
        target_user=user,
        old_data=old_data,
        new_data=update_data,
        request=request,
    )

    return UserListItem.model_validate(user)


@router.post("/{user_id}/role", response_model=UserListItem)
async def change_user_role(
    user_id: UUID,
    role_data: RoleChange,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Change a user's role."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot change your own role")

    # Check permissions
    if not can_manage_role(current_user.role, user.role):
        raise HTTPException(status_code=403, detail="Cannot manage this user's role")

    if not can_manage_role(current_user.role, role_data.role):
        raise HTTPException(status_code=403, detail="Cannot assign this role")

    old_role = user.role
    user.role = role_data.role
    user.updated_at = utcnow()

    await db.commit()
    await db.refresh(user)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_ROLE_CHANGE,
        actor=current_user,
        target_user=user,
        old_data={"role": old_role.value},
        new_data={"role": role_data.role.value},
        description=role_data.reason,
        request=request,
    )

    return UserListItem.model_validate(user)


@router.post("/{user_id}/ban", response_model=UserListItem)
async def ban_user(
    user_id: UUID,
    ban_data: BanUser,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ban a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot ban yourself")

    if not can_manage_role(current_user.role, user.role):
        raise HTTPException(status_code=403, detail="Cannot ban this user")

    if user.is_banned:
        raise HTTPException(status_code=400, detail="User is already banned")

    user.is_banned = True
    user.banned_at = utcnow()
    user.banned_by = current_user.id
    user.ban_reason = ban_data.reason
    user.updated_at = utcnow()

    await db.commit()
    await db.refresh(user)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_BAN,
        actor=current_user,
        target_user=user,
        new_data={"banned": True, "reason": ban_data.reason},
        description=ban_data.reason,
        request=request,
    )

    return UserListItem.model_validate(user)


@router.post("/{user_id}/unban", response_model=UserListItem)
async def unban_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unban a user."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_banned:
        raise HTTPException(status_code=400, detail="User is not banned")

    old_reason = user.ban_reason

    user.is_banned = False
    user.banned_at = None
    user.banned_by = None
    user.ban_reason = None
    user.updated_at = utcnow()

    await db.commit()
    await db.refresh(user)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_UNBAN,
        actor=current_user,
        target_user=user,
        old_data={"banned": True, "reason": old_reason},
        new_data={"banned": False},
        request=request,
    )

    return UserListItem.model_validate(user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (super admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")

    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Cannot delete a super admin")

    user_email = user.email

    # Audit log before deletion
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_DELETE,
        actor=current_user,
        target_user=user,
        old_data={"email": user.email, "role": user.role.value},
        request=request,
    )

    await db.delete(user)
    await db.commit()

    return {"message": f"User {user_email} deleted"}


@router.post("/{user_id}/permissions", response_model=dict)
async def set_permission_override(
    user_id: UUID,
    override: PermissionOverride,
    request: Request,
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Set a permission override for a user (super admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if override exists
    existing = await db.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission == override.permission,
        )
    )
    existing_override = existing.scalar_one_or_none()

    if existing_override:
        existing_override.granted = override.granted
        existing_override.reason = override.reason
        existing_override.granted_by = current_user.id
        existing_override.granted_at = utcnow()
    else:
        new_override = UserPermissionOverride(
            user_id=user_id,
            permission=override.permission,
            granted=override.granted,
            granted_by=current_user.id,
            granted_at=utcnow(),
            reason=override.reason,
        )
        db.add(new_override)

    await db.commit()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log_user_change(
        action=AuditAction.USER_PERMISSION_OVERRIDE,
        actor=current_user,
        target_user=user,
        new_data={
            "permission": override.permission.value,
            "granted": override.granted,
        },
        description=override.reason,
        request=request,
    )

    return {
        "message": f"Permission {override.permission.value} {'granted' if override.granted else 'revoked'}"
    }
