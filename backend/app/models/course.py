import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Enum, Integer, Boolean, Text, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class DifficultyLevel(str, enum.Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CourseCategory(str, enum.Enum):
    WEB_SECURITY = "web_security"
    NETWORK_SECURITY = "network_security"
    MALWARE_ANALYSIS = "malware_analysis"
    CRYPTOGRAPHY = "cryptography"
    FORENSICS = "forensics"
    REVERSE_ENGINEERING = "reverse_engineering"
    CLOUD_SECURITY = "cloud_security"
    SOC_OPERATIONS = "soc_operations"
    PENETRATION_TESTING = "penetration_testing"
    INCIDENT_RESPONSE = "incident_response"


class LessonType(str, enum.Enum):
    TEXT = "text"
    VIDEO = "video"
    INTERACTIVE = "interactive"
    QUIZ = "quiz"
    LAB = "lab"


class ContentBlockType(str, enum.Enum):
    """Types of content blocks within a lesson."""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    VIDEO = "video"
    DIAGRAM = "diagram"
    QUIZ_INLINE = "quiz_inline"
    WIKIPEDIA = "wikipedia"
    CALLOUT = "callout"  # tips, warnings, notes
    COLLAPSIBLE = "collapsible"


class ResourceType(str, enum.Enum):
    """Types of external resources."""
    WIKIPEDIA = "wikipedia"
    YOUTUBE = "youtube"
    ARTICLE = "article"
    TOOL = "tool"
    DOCUMENTATION = "documentation"
    GITHUB = "github"


class GenerationStage(str, enum.Enum):
    """Stages in the course generation pipeline."""
    QUEUED = "QUEUED"
    STRUCTURE = "STRUCTURE"
    CONTENT = "CONTENT"
    CODE_EXAMPLES = "CODE_EXAMPLES"
    DIAGRAMS = "DIAGRAMS"
    IMAGES = "IMAGES"
    WIKIPEDIA = "WIKIPEDIA"
    QUIZZES = "QUIZZES"
    REVIEW = "REVIEW"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class GenerationStatus(str, enum.Enum):
    """Status of content generation."""
    PENDING = "PENDING"
    GENERATING = "GENERATING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ============================================================================
# MAIN MODELS
# ============================================================================

class Course(Base):
    """Main course model with enhanced fields for AI-generated content."""
    __tablename__ = "courses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    short_description = Column(String(500), nullable=True)

    # Classification
    category = Column(Enum(CourseCategory), nullable=False)
    difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.BEGINNER)
    estimated_hours = Column(Integer, default=1)
    points = Column(Integer, default=100)

    # Prerequisites and skills
    prerequisites = Column(JSON, default=list)  # List of course IDs
    skills_taught = Column(JSON, default=list)  # List of skill IDs

    # Media
    thumbnail_url = Column(String(500), nullable=True)
    cover_image_url = Column(String(500), nullable=True)  # NEW: Full cover image
    trailer_video_url = Column(String(500), nullable=True)  # NEW: Intro video

    # Enhanced content metadata - NEW
    learning_outcomes = Column(JSON, default=list)  # High-level outcomes
    what_youll_learn = Column(JSON, default=list)  # Bullet points
    target_audience = Column(Text, nullable=True)  # Who is this for

    # Generation tracking - NEW
    is_ai_generated = Column(Boolean, default=False)
    is_published = Column(Boolean, default=False)
    generation_status = Column(Enum(GenerationStatus), default=GenerationStatus.PENDING)
    generation_metadata = Column(JSON, default=dict)  # Track generation stages/options

    # Owner - each user owns their courses
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    modules = relationship("Module", back_populates="course", cascade="all, delete-orphan", order_by="Module.order")
    generation_jobs = relationship("CourseGenerationJob", back_populates="course", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[created_by])

    def __repr__(self):
        return f"<Course {self.title}>"


class Module(Base):
    """Course module with enhanced fields for learning objectives."""
    __tablename__ = "modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    order = Column(Integer, default=0)

    # Enhanced content - NEW
    learning_objectives = Column(JSON, default=list)  # What students will learn
    summary = Column(Text, nullable=True)  # Module summary
    estimated_duration = Column(Integer, default=30)  # Minutes

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    course = relationship("Course", back_populates="modules")
    lessons = relationship("Lesson", back_populates="module", cascade="all, delete-orphan", order_by="Lesson.order")

    def __repr__(self):
        return f"<Module {self.title}>"


class Lesson(Base):
    """Course lesson with enhanced fields for rich content."""
    __tablename__ = "lessons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=True)  # Markdown content (legacy, for backward compat)
    lesson_type = Column(Enum(LessonType), default=LessonType.TEXT)
    order = Column(Integer, default=0)

    # Enhanced content metadata - NEW
    learning_objectives = Column(JSON, default=list)  # Lesson-specific objectives
    key_takeaways = Column(JSON, default=list)  # Summary points
    estimated_reading_time = Column(Integer, default=10)  # Minutes
    word_count = Column(Integer, default=0)

    # Generation tracking - NEW
    generation_status = Column(Enum(GenerationStatus), default=GenerationStatus.PENDING)
    generation_progress = Column(JSON, default=dict)  # {"stage": "content", "percent": 50}

    # Lab integration
    lab_id = Column(UUID(as_uuid=True), ForeignKey("labs.id"), nullable=True)

    # Quiz/Assessment data
    quiz_data = Column(JSON, nullable=True)

    # Duration and points
    duration = Column(Integer, default=10)  # Minutes
    points = Column(Integer, default=10)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    module = relationship("Module", back_populates="lessons")
    lab = relationship("Lab", foreign_keys=[lab_id])
    content_blocks = relationship("ContentBlock", back_populates="lesson", cascade="all, delete-orphan", order_by="ContentBlock.order")
    external_resources = relationship("ExternalResource", back_populates="lesson", cascade="all, delete-orphan", order_by="ExternalResource.order")

    def __repr__(self):
        return f"<Lesson {self.title}>"


# ============================================================================
# NEW MODELS FOR RICH CONTENT
# ============================================================================

class ContentBlock(Base):
    """
    Modular content block within a lesson.
    Supports multiple content types: text, code, images, videos, diagrams, etc.
    """
    __tablename__ = "content_blocks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    block_type = Column(Enum(ContentBlockType), nullable=False)
    order = Column(Integer, default=0)

    # Main content (interpretation depends on block_type)
    content = Column(Text, nullable=True)

    # Type-specific metadata stored as JSON
    # Examples:
    # CODE: {"language": "python", "filename": "exploit.py", "executable": true, "output": "..."}
    # IMAGE: {"url": "...", "alt": "...", "source": "unsplash", "attribution": "Photo by..."}
    # VIDEO: {"youtube_id": "xxx", "start_time": 0, "end_time": null, "title": "..."}
    # DIAGRAM: {"diagram_type": "mermaid", "source_code": "graph TD..."}
    # WIKIPEDIA: {"article_title": "SQL injection", "section": "Overview", "url": "..."}
    # CALLOUT: {"callout_type": "tip|warning|note|danger", "title": "Pro Tip"}
    # COLLAPSIBLE: {"title": "Click to expand", "default_open": false}
    # QUIZ_INLINE: {"question": "...", "type": "multiple_choice", "options": [...], "answer": "..."}
    block_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lesson = relationship("Lesson", back_populates="content_blocks")

    def __repr__(self):
        return f"<ContentBlock {self.block_type.value} order={self.order}>"


class ExternalResource(Base):
    """
    External resource linked to a lesson.
    Supports Wikipedia, YouTube, documentation, tools, etc.
    """
    __tablename__ = "external_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lesson_id = Column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    resource_type = Column(Enum(ResourceType), nullable=False)
    order = Column(Integer, default=0)

    # Resource info
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)

    # Cached content (e.g., Wikipedia summary)
    cached_content = Column(Text, nullable=True)
    cached_at = Column(DateTime, nullable=True)

    # Additional metadata
    # YOUTUBE: {"video_id": "xxx", "channel": "...", "duration": "10:30"}
    # WIKIPEDIA: {"article_title": "...", "section": "..."}
    # TOOL: {"platform": "linux", "install_command": "..."}
    resource_metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    lesson = relationship("Lesson", back_populates="external_resources")

    def __repr__(self):
        return f"<ExternalResource {self.resource_type.value}: {self.title[:30]}>"


class CourseGenerationJob(Base):
    """
    Tracks the multi-stage course generation process.
    Enables progress monitoring, resumption, and error handling.
    """
    __tablename__ = "course_generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Generation options (what was requested)
    options = Column(JSON, default=dict)
    # {"topic": "...", "difficulty": "...", "include_code": true, "include_diagrams": true, ...}

    # Stage tracking
    current_stage = Column(Enum(GenerationStage), default=GenerationStage.QUEUED)
    stages_completed = Column(JSON, default=list)  # ["structure", "content", ...]
    stages_failed = Column(JSON, default=list)  # ["images", ...] with error info

    # Progress tracking
    total_lessons = Column(Integer, default=0)
    lessons_completed = Column(Integer, default=0)
    current_lesson_id = Column(UUID(as_uuid=True), nullable=True)
    current_lesson_title = Column(String(255), nullable=True)

    # Overall progress percentage
    progress_percent = Column(Integer, default=0)

    # Error handling
    error_message = Column(Text, nullable=True)
    error_stage = Column(String(50), nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    estimated_completion = Column(DateTime, nullable=True)

    # Relationships
    course = relationship("Course", back_populates="generation_jobs")
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<CourseGenerationJob {self.id} stage={self.current_stage.value}>"

    @property
    def is_complete(self) -> bool:
        return self.current_stage == GenerationStage.COMPLETED

    @property
    def is_failed(self) -> bool:
        return self.current_stage == GenerationStage.FAILED

    @property
    def is_in_progress(self) -> bool:
        return self.current_stage not in [GenerationStage.COMPLETED, GenerationStage.FAILED, GenerationStage.QUEUED]
