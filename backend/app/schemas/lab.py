from pydantic import BaseModel, Field
from typing import Optional, List, Any, Dict
from datetime import datetime
from uuid import UUID


class LabCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    lab_type: str = "tutorial"
    difficulty: str = "beginner"
    estimated_time: int = 30
    points: int = 50
    infrastructure_spec: Dict[str, Any] = Field(default_factory=dict)
    flags: List[Dict[str, Any]] = []
    objectives: List[str] = []
    instructions: Optional[str] = None
    hints: List[str] = []
    category: Optional[str] = None
    tags: List[str] = []


class LabResponse(BaseModel):
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    lab_type: str
    difficulty: str
    estimated_time: int = 30
    points: int = 50
    infrastructure_spec: Optional[Dict[str, Any]] = None
    flags: Optional[List[Dict[str, Any]]] = None
    objectives: Optional[List[Any]] = None
    instructions: Optional[str] = None
    hints: Optional[List[str]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_published: bool = False
    is_ai_generated: bool = False
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Handle NULL values from database."""
        if hasattr(obj, '__dict__'):
            # Convert None to empty lists/dicts for JSON fields
            if obj.infrastructure_spec is None:
                obj.infrastructure_spec = {}
            if obj.flags is None:
                obj.flags = []
            if obj.objectives is None:
                obj.objectives = []
            if obj.hints is None:
                obj.hints = []
            if obj.tags is None:
                obj.tags = []
            if obj.is_ai_generated is None:
                obj.is_ai_generated = False
            if obj.is_published is None:
                obj.is_published = False
        return super().model_validate(obj, **kwargs)


class LabSessionCreate(BaseModel):
    lab_id: UUID


class LabSessionResponse(BaseModel):
    id: UUID
    user_id: UUID
    lab_id: Optional[UUID] = None  # Optional for Alphha VM sessions
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    access_url: Optional[str] = None
    flags_captured: List[str] = []
    objectives_completed: List[str] = []
    score: int = 0
    attempts: int = 0
    created_at: datetime
    preset: Optional[str] = None  # For Alphha VM sessions
    vnc_url: Optional[str] = None  # VNC URL for desktop sessions
    vnc_password: Optional[str] = None  # VNC password
    novnc_port: Optional[int] = None  # noVNC port

    class Config:
        from_attributes = True

    @classmethod
    def model_validate(cls, obj, **kwargs):
        """Handle NULL values from database."""
        if hasattr(obj, '__dict__'):
            if obj.flags_captured is None:
                obj.flags_captured = []
            if obj.objectives_completed is None:
                obj.objectives_completed = []
            if obj.score is None:
                obj.score = 0
            if obj.attempts is None:
                obj.attempts = 0
        return super().model_validate(obj, **kwargs)


class FlagSubmission(BaseModel):
    flag: str


class LabSessionUpdate(BaseModel):
    status: Optional[str] = None
    flags_captured: Optional[List[str]] = None
    objectives_completed: Optional[List[str]] = None
