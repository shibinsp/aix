from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from pydantic import BaseModel, Field
from typing import Optional

from app.core.database import get_db
from app.core.security import get_current_user_id, verify_password, get_password_hash
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter()

# Fields that users are allowed to update on their own profile
ALLOWED_SELF_UPDATE_FIELDS = {
    'full_name', 'skill_level', 'learning_style', 'career_goal', 
    'time_commitment', 'bio'
}


class PublicUserProfile(BaseModel):
    """Limited public profile for other users."""
    id: str
    username: str
    full_name: Optional[str] = None
    skill_level: str
    total_points: int
    total_labs_completed: int
    total_courses_completed: int
    current_streak: int

    class Config:
        from_attributes = True


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse.model_validate(user)


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    updates: UserUpdate,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Apply updates - only allow certain fields to be self-updated
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ALLOWED_SELF_UPDATE_FIELDS:
            setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/me/stats")
async def get_my_stats(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's statistics."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "total_points": user.total_points,
        "labs_completed": user.total_labs_completed,
        "courses_completed": user.total_courses_completed,
        "current_streak": user.current_streak,
        "member_since": user.created_at.isoformat(),
        "skill_level": user.skill_level.value,
    }


@router.get("/{user_id}", response_model=PublicUserProfile)
async def get_user_profile(
    user_id: UUID,
    current_user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a user's public profile (limited information)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return limited public profile only
    return PublicUserProfile(
        id=str(user.id),
        username=str(user.username),
        full_name=str(user.full_name) if user.full_name else None,
        skill_level=user.skill_level.value if hasattr(user.skill_level, 'value') else str(user.skill_level),
        total_points=int(user.total_points) if user.total_points else 0,
        total_labs_completed=int(user.total_labs_completed) if user.total_labs_completed else 0,
        total_courses_completed=int(user.total_courses_completed) if user.total_courses_completed else 0,
        current_streak=int(user.current_streak) if user.current_streak else 0,
    )


class PasswordChangeRequest(BaseModel):
    """Request to change password."""
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


@router.post("/me/password")
async def change_password(
    request: PasswordChangeRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Verify current password
    if not verify_password(request.current_password, str(user.hashed_password)):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    # Validate new password (same rules as registration)
    new_pass = request.new_password
    if len(new_pass) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if not any(c.isupper() for c in new_pass):
        raise HTTPException(status_code=400, detail="Password must contain at least one uppercase letter")
    if not any(c.islower() for c in new_pass):
        raise HTTPException(status_code=400, detail="Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in new_pass):
        raise HTTPException(status_code=400, detail="Password must contain at least one digit")

    # Update password
    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return {"message": "Password changed successfully"}
