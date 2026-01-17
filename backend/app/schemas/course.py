from pydantic import BaseModel, Field
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID


# ============================================================================
# CONTENT BLOCK SCHEMAS
# ============================================================================

class ContentBlockCreate(BaseModel):
    """Schema for creating a content block."""
    block_type: str
    order: int = 0
    content: Optional[str] = None
    block_metadata: Optional[dict] = {}


class ContentBlockResponse(BaseModel):
    """Schema for content block response."""
    id: UUID
    lesson_id: UUID
    block_type: str
    order: int
    content: Optional[str] = None
    block_metadata: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# EXTERNAL RESOURCE SCHEMAS
# ============================================================================

class ExternalResourceCreate(BaseModel):
    """Schema for creating an external resource."""
    resource_type: str
    title: str
    url: str
    description: Optional[str] = None
    order: int = 0
    resource_metadata: Optional[dict] = {}


class ExternalResourceResponse(BaseModel):
    """Schema for external resource response."""
    id: UUID
    lesson_id: UUID
    resource_type: str
    title: str
    url: str
    description: Optional[str] = None
    cached_content: Optional[str] = None
    order: int
    resource_metadata: dict = {}
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# LESSON SCHEMAS
# ============================================================================

class LessonCreate(BaseModel):
    """Schema for creating a lesson."""
    title: str
    content: Optional[str] = None
    lesson_type: str = "text"
    order: int = 0
    lab_id: Optional[UUID] = None
    quiz_data: Optional[dict] = None
    duration: int = 10
    points: int = 10
    learning_objectives: List[str] = []
    key_takeaways: List[str] = []


class LessonResponse(BaseModel):
    """Basic lesson response (without content blocks)."""
    id: UUID
    module_id: UUID
    title: str
    content: Optional[str] = None
    lesson_type: str
    order: int
    lab_id: Optional[UUID] = None
    duration: int
    points: int
    learning_objectives: List[str] = []
    key_takeaways: List[str] = []
    estimated_reading_time: int = 10
    word_count: int = 0
    generation_status: str = "PENDING"
    created_at: datetime

    class Config:
        from_attributes = True


class LessonFullResponse(BaseModel):
    """Full lesson response with all content blocks and resources."""
    id: UUID
    module_id: UUID
    title: str
    content: Optional[str] = None
    lesson_type: str
    order: int
    lab_id: Optional[UUID] = None
    duration: int
    points: int
    learning_objectives: List[str] = []
    key_takeaways: List[str] = []
    estimated_reading_time: int = 10
    word_count: int = 0
    generation_status: str = "PENDING"
    generation_progress: dict = {}
    quiz_data: Optional[dict] = None
    content_blocks: List[ContentBlockResponse] = []
    external_resources: List[ExternalResourceResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# MODULE SCHEMAS
# ============================================================================

class ModuleCreate(BaseModel):
    """Schema for creating a module."""
    title: str
    description: Optional[str] = None
    order: int = 0
    learning_objectives: List[str] = []
    lessons: Optional[List[LessonCreate]] = []


class ModuleResponse(BaseModel):
    """Module response with lessons."""
    id: UUID
    course_id: UUID
    title: str
    description: Optional[str] = None
    order: int
    learning_objectives: List[str] = []
    summary: Optional[str] = None
    estimated_duration: int = 30
    lessons: List[LessonResponse] = []
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# COURSE SCHEMAS
# ============================================================================

class CourseCreate(BaseModel):
    """Schema for creating a course."""
    title: str = Field(..., min_length=3, max_length=255)
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: str
    difficulty: str = "beginner"
    estimated_hours: int = 1
    points: int = 100
    prerequisites: List[UUID] = []
    skills_taught: List[UUID] = []
    thumbnail_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    learning_outcomes: List[str] = []
    what_youll_learn: List[str] = []
    target_audience: Optional[str] = None
    modules: Optional[List[ModuleCreate]] = []


class CourseResponse(BaseModel):
    """Course response with modules."""
    id: UUID
    title: str
    slug: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    category: str
    difficulty: str
    estimated_hours: int
    points: int
    prerequisites: List[Any] = []
    skills_taught: List[Any] = []
    thumbnail_url: Optional[str] = None
    cover_image_url: Optional[str] = None
    trailer_video_url: Optional[str] = None
    learning_outcomes: List[str] = []
    what_youll_learn: List[str] = []
    target_audience: Optional[str] = None
    is_ai_generated: bool
    is_published: bool
    generation_status: str = "PENDING"
    created_by: Optional[UUID] = None
    modules: List[ModuleResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# COURSE GENERATION SCHEMAS
# ============================================================================

class AdvancedCourseGenerationRequest(BaseModel):
    """Request for advanced AI course generation."""
    topic: str = Field(..., min_length=3, max_length=500)
    difficulty: str = "beginner"
    num_modules: int = Field(default=5, ge=3, le=10)
    include_code_examples: bool = True
    include_diagrams: bool = True
    include_videos: bool = True
    include_wikipedia: bool = True
    include_quizzes: bool = True
    target_lesson_length: int = Field(default=2000, ge=200, le=2000)


class CourseGenerationJobResponse(BaseModel):
    """Response for course generation job status."""
    id: UUID
    course_id: UUID
    current_stage: str
    stages_completed: List[str] = []
    stages_failed: List[str] = []
    total_lessons: int = 0
    lessons_completed: int = 0
    current_lesson_title: Optional[str] = None
    progress_percent: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationProgressUpdate(BaseModel):
    """WebSocket message for generation progress updates."""
    job_id: UUID
    stage: str
    progress_percent: int
    current_lesson: Optional[str] = None
    message: str
    is_complete: bool = False
    is_error: bool = False
