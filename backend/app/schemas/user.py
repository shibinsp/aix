from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        # Check for special characters for stronger passwords
        if not any(c in '!@#$%^&*(),.?":{}|<>-_=+[]\\;\'`~' for c in v):
            raise ValueError('Password must contain at least one special character')
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    skill_level: Optional[str] = None
    learning_style: Optional[str] = None
    career_goal: Optional[str] = None
    time_commitment: Optional[int] = None
    bio: Optional[str] = None


class UserResponse(UserBase):
    id: UUID
    skill_level: str
    learning_style: str
    career_goal: str
    time_commitment: int
    is_active: bool
    is_verified: bool
    total_points: int
    total_labs_completed: int
    total_courses_completed: int
    current_streak: int
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserWithOrgResponse(UserResponse):
    """Extended user response with organization info."""
    role: Optional[str] = None
    org_role: Optional[str] = None
    organization_id: Optional[str] = None


class UserLogin(BaseModel):
    email: str  # Can be email or username
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
