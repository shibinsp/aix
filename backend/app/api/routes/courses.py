from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID
from pydantic import BaseModel
import re
import json
import structlog
import asyncio
from datetime import datetime

from app.core.database import get_db, async_session_maker
from app.core.security import get_current_user_id
from app.core.dependencies import get_current_admin
from app.core.sanitization import validate_pagination
from app.models.user import User
from app.models.course import (
    Course, Module, Lesson, ContentBlock, ExternalResource,
    CourseCategory, DifficultyLevel, CourseGenerationJob,
    GenerationStage, GenerationStatus
)
from app.models.lab import Lab, LabType
from app.schemas.course import (
    CourseCreate, CourseResponse, ModuleCreate, LessonCreate,
    AdvancedCourseGenerationRequest, CourseGenerationJobResponse,
    LessonFullResponse, ContentBlockResponse, ExternalResourceResponse
)
from app.services.ai import teaching_engine
from app.services.ai.course_generator import course_generator
from app.services.limits import limit_enforcer

logger = structlog.get_logger()


class NewsLearningRequest(BaseModel):
    """Request to generate learning content from a news article."""
    article_id: str
    title: str
    summary: str
    category: str
    severity: Optional[str] = None
    tags: List[str] = []


class NewsLearningResponse(BaseModel):
    """Response with generated learning resources."""
    course_id: str
    course_title: str
    course_slug: str
    lab_id: Optional[str] = None
    lab_title: Optional[str] = None
    lab_slug: Optional[str] = None
    message: str

router = APIRouter()


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def normalize_lesson_type(lesson_type: str) -> str:
    """Normalize AI-generated lesson types to valid enum values."""
    valid_types = {"text", "video", "interactive", "quiz", "lab"}
    lesson_type = lesson_type.lower().strip()

    # Map common AI variations to valid types
    type_mapping = {
        "hands-on": "interactive",
        "hands_on": "interactive",
        "practical": "interactive",
        "exercise": "interactive",
        "tutorial": "text",
        "lecture": "text",
        "reading": "text",
        "assessment": "quiz",
        "test": "quiz",
        "challenge": "lab",
        "practice": "lab",
    }

    if lesson_type in valid_types:
        return lesson_type
    return type_mapping.get(lesson_type, "text")


@router.get("", response_model=List[CourseResponse])
async def list_courses(
    db: AsyncSession = Depends(get_db),
    user_id: str = Depends(get_current_user_id),
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
):
    """List courses created by the current user."""
    query = select(Course).options(
        selectinload(Course.modules).selectinload(Module.lessons)
    ).where(Course.created_by == user_id)

    if category:
        query = query.where(Course.category == category)
    if difficulty:
        query = query.where(Course.difficulty == difficulty)
    if search:
        query = query.where(Course.title.ilike(f"%{search}%"))

    skip, limit = validate_pagination(skip, limit, max_limit=50)
    query = query.order_by(Course.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    courses = result.scalars().all()

    return [CourseResponse.model_validate(c) for c in courses]


@router.get("/categories")
async def list_categories():
    """List available course categories."""
    return [
        {"value": cat.value, "label": cat.value.replace("_", " ").title()}
        for cat in CourseCategory
    ]


@router.get("/{course_id}", response_model=CourseResponse)
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get course details."""
    result = await db.execute(
        select(Course).options(
            selectinload(Course.modules).selectinload(Module.lessons)
        ).where(Course.id == course_id)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseResponse.model_validate(course)


@router.get("/slug/{slug}", response_model=CourseResponse)
async def get_course_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Get course by slug."""
    result = await db.execute(
        select(Course).options(
            selectinload(Course.modules).selectinload(Module.lessons)
        ).where(Course.slug == slug)
    )
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return CourseResponse.model_validate(course)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
async def create_course(
    course_data: CourseCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new course (admin only)."""
    # Generate unique slug
    base_slug = slugify(course_data.title)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Course).where(Course.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Create course
    course = Course(
        title=course_data.title,
        slug=slug,
        description=course_data.description,
        short_description=course_data.short_description,
        category=course_data.category,
        difficulty=course_data.difficulty,
        estimated_hours=course_data.estimated_hours,
        points=course_data.points,
        prerequisites=course_data.prerequisites,
        skills_taught=course_data.skills_taught,
        thumbnail_url=course_data.thumbnail_url,
        created_by=admin.id,  # Set owner
    )

    db.add(course)
    await db.commit()
    await db.refresh(course)

    # Create modules if provided
    for i, module_data in enumerate(course_data.modules or []):
        module = Module(
            course_id=course.id,
            title=module_data.title,
            description=module_data.description,
            order=i,
        )
        db.add(module)
        await db.commit()
        await db.refresh(module)

        # Create lessons for module
        for j, lesson_data in enumerate(module_data.lessons or []):
            lesson = Lesson(
                module_id=module.id,
                title=lesson_data.title,
                content=lesson_data.content,
                lesson_type=lesson_data.lesson_type,
                order=j,
                duration=lesson_data.duration,
                points=lesson_data.points,
            )
            db.add(lesson)

    await db.commit()
    await db.refresh(course)

    return CourseResponse.model_validate(course)


@router.post("/generate", response_model=CourseResponse)
async def generate_course(
    topic: str = Query(..., description="Topic for the course"),
    difficulty: str = Query("beginner", description="Course difficulty"),
    num_modules: int = Query(5, ge=3, le=10, description="Number of modules"),
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a course using AI."""
    # Check if user can create a course
    can_create, reason = await limit_enforcer.check_can_create_course(UUID(user_id), db)
    if not can_create:
        raise HTTPException(status_code=403, detail=reason)

    # Check if user can generate an AI course
    can_generate_ai, ai_reason = await limit_enforcer.check_can_generate_ai_course(UUID(user_id), db)
    if not can_generate_ai:
        raise HTTPException(status_code=403, detail=ai_reason)

    # Generate course content with AI
    course_content = await teaching_engine.generate_course_content(
        topic=topic,
        difficulty=difficulty,
        num_modules=num_modules,
    )

    if "error" in course_content:
        raise HTTPException(status_code=500, detail=course_content["error"])

    # Generate slug
    base_slug = slugify(course_content.get("title", topic))
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Course).where(Course.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Determine category based on topic
    category = CourseCategory.WEB_SECURITY  # Default
    topic_lower = topic.lower()
    if "network" in topic_lower:
        category = CourseCategory.NETWORK_SECURITY
    elif "malware" in topic_lower:
        category = CourseCategory.MALWARE_ANALYSIS
    elif "forensic" in topic_lower:
        category = CourseCategory.FORENSICS
    elif "crypto" in topic_lower:
        category = CourseCategory.CRYPTOGRAPHY
    elif "cloud" in topic_lower:
        category = CourseCategory.CLOUD_SECURITY
    elif "pentest" in topic_lower or "penetration" in topic_lower:
        category = CourseCategory.PENETRATION_TESTING

    # Create course
    course = Course(
        title=course_content.get("title", topic),
        slug=slug,
        description=course_content.get("description", ""),
        category=category,
        difficulty=difficulty,
        estimated_hours=num_modules * 2,
        is_ai_generated=True,
        is_published=True,  # Auto-publish for users
        created_by=user_id,  # Set owner
    )

    db.add(course)
    await db.commit()
    await db.refresh(course)

    # Create modules and lessons
    for i, module_data in enumerate(course_content.get("modules", [])):
        module = Module(
            course_id=course.id,
            title=module_data.get("title", f"Module {i+1}"),
            description=module_data.get("description", ""),
            order=i,
        )
        db.add(module)
        await db.commit()
        await db.refresh(module)

        for j, lesson_data in enumerate(module_data.get("lessons", [])):
            raw_type = lesson_data.get("type", "text")
            lesson = Lesson(
                module_id=module.id,
                title=lesson_data.get("title", f"Lesson {j+1}"),
                content=lesson_data.get("description", ""),
                lesson_type=normalize_lesson_type(raw_type),
                order=j,
            )
            db.add(lesson)

    await db.commit()

    # Record course creation for limit tracking
    await limit_enforcer.record_course_created(UUID(user_id), is_ai_generated=True, db=db)

    # Reload course with all relationships
    result = await db.execute(
        select(Course).options(
            selectinload(Course.modules).selectinload(Module.lessons)
        ).where(Course.id == course.id)
    )
    course = result.scalar_one()

    return CourseResponse.model_validate(course)


@router.post("/generate/advanced", response_model=CourseGenerationJobResponse)
async def generate_advanced_course(
    request: AdvancedCourseGenerationRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate an advanced AI course with rich content.

    This starts a background job that:
    - Generates course structure
    - Creates detailed lesson content (2000+ words)
    - Adds code examples
    - Generates Mermaid diagrams
    - Fetches relevant images
    - Integrates Wikipedia content
    - Creates quizzes

    Returns a job ID to track progress.
    """
    # Check if user can create a course
    can_create, reason = await limit_enforcer.check_can_create_course(UUID(user_id), db)
    if not can_create:
        raise HTTPException(status_code=403, detail=reason)

    # Check if user can generate an AI course
    can_generate_ai, ai_reason = await limit_enforcer.check_can_generate_ai_course(UUID(user_id), db)
    if not can_generate_ai:
        raise HTTPException(status_code=403, detail=ai_reason)

    # Record course creation upfront since job runs in background
    await limit_enforcer.record_course_created(UUID(user_id), is_ai_generated=True, db=db)

    # Generate unique slug
    base_slug = slugify(request.topic)
    slug = base_slug
    counter = 1

    while True:
        result = await db.execute(select(Course).where(Course.slug == slug))
        if not result.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # Determine category
    category = CourseCategory.WEB_SECURITY
    topic_lower = request.topic.lower()
    if "network" in topic_lower:
        category = CourseCategory.NETWORK_SECURITY
    elif "malware" in topic_lower:
        category = CourseCategory.MALWARE_ANALYSIS
    elif "forensic" in topic_lower:
        category = CourseCategory.FORENSICS
    elif "crypto" in topic_lower:
        category = CourseCategory.CRYPTOGRAPHY
    elif "cloud" in topic_lower:
        category = CourseCategory.CLOUD_SECURITY
    elif "pentest" in topic_lower or "penetration" in topic_lower:
        category = CourseCategory.PENETRATION_TESTING
    elif "reverse" in topic_lower:
        category = CourseCategory.REVERSE_ENGINEERING
    elif "soc" in topic_lower or "operations" in topic_lower:
        category = CourseCategory.SOC_OPERATIONS
    elif "incident" in topic_lower:
        category = CourseCategory.INCIDENT_RESPONSE

    # Create course placeholder
    course = Course(
        title=request.topic,
        slug=slug,
        description=f"Comprehensive course on {request.topic}",
        category=category,
        difficulty=request.difficulty,
        estimated_hours=request.num_modules * 3,
        is_ai_generated=True,
        is_published=False,
        generation_status=GenerationStatus.GENERATING,
        created_by=user_id,  # Set owner
    )

    db.add(course)
    await db.commit()
    await db.refresh(course)

    # Create generation job
    job = CourseGenerationJob(
        course_id=course.id,
        user_id=UUID(user_id),
        options={
            "topic": request.topic,
            "difficulty": request.difficulty,
            "num_modules": request.num_modules,
            "include_code_examples": request.include_code_examples,
            "include_diagrams": request.include_diagrams,
            "include_videos": request.include_videos,
            "include_wikipedia": request.include_wikipedia,
            "include_quizzes": request.include_quizzes,
            "target_lesson_length": request.target_lesson_length,
        },
        current_stage=GenerationStage.QUEUED,
        started_at=datetime.utcnow(),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Start background generation using asyncio.create_task for proper async handling
    asyncio.create_task(
        run_course_generation(
            job_id=job.id,
            course_id=course.id,
            topic=request.topic,
            difficulty=request.difficulty,
            num_modules=request.num_modules,
            options=job.options,
        )
    )

    logger.info("Started course generation task", job_id=str(job.id), topic=request.topic)
    return CourseGenerationJobResponse.model_validate(job)


async def run_course_generation(
    job_id: UUID,
    course_id: UUID,
    topic: str,
    difficulty: str,
    num_modules: int,
    options: dict,
):
    """Background task for course generation."""
    logger.info("Course generation started", job_id=str(job_id), topic=topic)

    async with async_session_maker() as db:
        try:
            await course_generator.generate_full_course(
                topic=topic,
                difficulty=difficulty,
                num_modules=num_modules,
                options=options,
                job_id=job_id,
                course_id=course_id,
                db=db,
            )
            logger.info("Course generation completed", job_id=str(job_id))
        except Exception as e:
            import traceback
            logger.error("Background course generation failed",
                        error=str(e),
                        job_id=str(job_id),
                        traceback=traceback.format_exc())
            # Update job status
            try:
                job = await db.get(CourseGenerationJob, job_id)
                if job:
                    job.current_stage = GenerationStage.FAILED
                    job.error_message = str(e)
                    await db.commit()
            except Exception as db_error:
                logger.error("Failed to update job status", error=str(db_error))


@router.get("/generate/{job_id}/status", response_model=CourseGenerationJobResponse)
async def get_generation_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get the status of a course generation job."""
    job = await db.get(CourseGenerationJob, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")

    return CourseGenerationJobResponse.model_validate(job)


@router.get("/{course_id}/lessons/{lesson_id}/full", response_model=LessonFullResponse)
async def get_full_lesson(
    course_id: UUID,
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a lesson with all content blocks and external resources."""
    # Verify course exists
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Get lesson with relationships
    stmt = (
        select(Lesson)
        .options(
            selectinload(Lesson.content_blocks),
            selectinload(Lesson.external_resources),
        )
        .where(Lesson.id == lesson_id)
    )
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    return LessonFullResponse.model_validate(lesson)


@router.post("/generate/{job_id}/regenerate-lesson/{lesson_id}")
async def regenerate_lesson(
    job_id: UUID,
    lesson_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate content for a specific lesson."""
    # Verify job and lesson
    job = await db.get(CourseGenerationJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Generation job not found")

    stmt = (
        select(Lesson)
        .options(selectinload(Lesson.module))
        .where(Lesson.id == lesson_id)
    )
    result = await db.execute(stmt)
    lesson = result.scalar_one_or_none()

    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")

    # Mark lesson as regenerating
    lesson.generation_status = GenerationStatus.GENERATING
    await db.commit()

    # Start regeneration in background using asyncio.create_task
    asyncio.create_task(
        regenerate_lesson_content(
            lesson_id=lesson_id,
            options=job.options,
        )
    )

    return {"message": "Lesson regeneration started", "lesson_id": str(lesson_id)}


async def regenerate_lesson_content(lesson_id: UUID, options: dict):
    """Background task to regenerate lesson content."""
    async with async_session_maker() as db:
        try:
            stmt = (
                select(Lesson)
                .options(
                    selectinload(Lesson.module).selectinload(Module.course),
                    selectinload(Lesson.content_blocks),
                )
                .where(Lesson.id == lesson_id)
            )
            result = await db.execute(stmt)
            lesson = result.scalar_one_or_none()

            if not lesson:
                return

            # Delete existing content blocks
            for block in lesson.content_blocks:
                await db.delete(block)

            # Generate new content
            from app.services.ai.course_generator import course_generator as cg

            content = await cg._generate_lesson_content(
                lesson,
                lesson.module,
                lesson.module.course,
                options.get("target_lesson_length", 2000),
            )

            lesson.content = content
            lesson.word_count = len(content.split())
            lesson.generation_status = GenerationStatus.COMPLETED

            # Create text content block
            text_block = ContentBlock(
                lesson_id=lesson.id,
                block_type="text",
                order=0,
                content=content,
                block_metadata={"source": "ai_regenerated"},
            )
            db.add(text_block)

            await db.commit()

        except Exception as e:
            logger.error("Lesson regeneration failed", error=str(e), lesson_id=str(lesson_id))


@router.patch("/{course_id}/publish")
async def publish_course(
    course_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Publish a course."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    course.is_published = True
    await db.commit()

    return {"message": "Course published successfully"}


@router.delete("/{course_id}")
async def delete_course(
    course_id: UUID,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a course."""
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()

    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    await db.delete(course)
    await db.commit()

    return {"message": "Course deleted successfully"}


def map_news_category_to_course(news_category: str) -> CourseCategory:
    """Map news category to course category."""
    mapping = {
        "vulnerabilities": CourseCategory.WEB_SECURITY,
        "ransomware": CourseCategory.MALWARE_ANALYSIS,
        "data breach": CourseCategory.INCIDENT_RESPONSE,
        "malware": CourseCategory.MALWARE_ANALYSIS,
        "apt": CourseCategory.PENETRATION_TESTING,
        "patches": CourseCategory.NETWORK_SECURITY,
        "policy": CourseCategory.SOC_OPERATIONS,
        "threats": CourseCategory.NETWORK_SECURITY,
    }
    return mapping.get(news_category.lower(), CourseCategory.WEB_SECURITY)


async def _generate_full_lesson_content(
    lesson_title: str,
    lesson_description: str,
    module_title: str,
    course_title: str,
    news_context: str,
    difficulty: str,
) -> str:
    """Generate comprehensive lesson content using AI."""
    prompt = f"""Write a detailed, comprehensive cybersecurity lesson on "{lesson_title}".

CONTEXT:
- This is part of the module "{module_title}" in the course "{course_title}"
- Based on recent news: {news_context[:500]}
- Target difficulty: {difficulty}

LESSON OVERVIEW: {lesson_description}

REQUIREMENTS:
1. Write 1500-2000 words of educational content
2. Start with an engaging introduction explaining the relevance
3. Use clear headings (##) and subheadings (###)
4. Include practical examples and real-world scenarios
5. Add bullet points and numbered lists for clarity
6. Include code snippets where relevant (use ```language blocks)
7. Add tips and warnings using blockquotes (> Note: or > Warning:)
8. End with a summary and key takeaways
9. Focus on actionable cybersecurity knowledge
10. Explain technical concepts clearly for {difficulty} level students

Write the complete lesson content in Markdown format:"""

    messages = [{"role": "user", "content": prompt}]

    content = await teaching_engine.generate_response(
        messages,
        teaching_mode="lecture",
        skill_level=difficulty,
        temperature=0.7,
        max_tokens=4000,
    )

    # If content is too short, expand it
    if len(content.split()) < 800:
        extension_prompt = f"""The lesson content is too short. Please expand on the following content with more detail, examples, and explanations. Target: 1500+ words.

Current content:
{content}

Continue with more detailed content, practical examples, and in-depth explanations:"""

        messages = [{"role": "user", "content": extension_prompt}]
        extension = await teaching_engine.generate_response(
            messages,
            teaching_mode="lecture",
            skill_level=difficulty,
            temperature=0.7,
            max_tokens=2500,
        )
        content = content + "\n\n" + extension

    return content


def map_severity_to_difficulty(severity: Optional[str]) -> str:
    """Map news severity to course difficulty."""
    if not severity:
        return "beginner"
    mapping = {
        "critical": "advanced",
        "high": "intermediate",
        "medium": "intermediate",
        "low": "beginner",
        "info": "beginner",
    }
    return mapping.get(severity.lower(), "beginner")


@router.post("/generate-from-news", response_model=NewsLearningResponse)
async def generate_learning_from_news(
    request: NewsLearningRequest,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a course and lab from a cybersecurity news article."""
    # Check if user can create a course
    can_create, reason = await limit_enforcer.check_can_create_course(UUID(user_id), db)
    if not can_create:
        raise HTTPException(status_code=403, detail=reason)

    # Check if user can generate an AI course
    can_generate_ai, ai_reason = await limit_enforcer.check_can_generate_ai_course(UUID(user_id), db)
    if not can_generate_ai:
        raise HTTPException(status_code=403, detail=ai_reason)

    logger.info("Generating learning content from news", article_id=request.article_id, title=request.title)

    # Determine difficulty based on severity
    difficulty = map_severity_to_difficulty(request.severity)
    category = map_news_category_to_course(request.category)

    # Generate a focused topic from the article
    topic = f"{request.title} - Understanding and Defense"
    tags_str = ", ".join(request.tags[:5]) if request.tags else request.category

    # Generate course content using AI
    course_prompt = f"""Based on this cybersecurity news, create an educational course:

NEWS TITLE: {request.title}
SUMMARY: {request.summary}
CATEGORY: {request.category}
SEVERITY: {request.severity or 'Medium'}
TAGS: {tags_str}

Create a practical cybersecurity course that teaches students:
1. What happened in this security incident/vulnerability
2. The technical details and attack vectors involved
3. How to detect such threats
4. How to defend against similar attacks
5. Hands-on skills to apply this knowledge

Generate {4 if difficulty == "beginner" else 5} modules with 3-4 lessons each.

Return JSON format:
{{
    "title": "Course title based on the news topic",
    "description": "Comprehensive course description",
    "modules": [
        {{
            "title": "Module Title",
            "description": "Module description",
            "lessons": [
                {{"title": "Lesson Title", "description": "Lesson content overview", "type": "text"}}
            ]
        }}
    ]
}}"""

    try:
        messages = [{"role": "user", "content": course_prompt}]
        course_response = await teaching_engine.generate_response(
            messages,
            teaching_mode="lecture",
            skill_level=difficulty,
            temperature=0.7,
            max_tokens=3000,
        )

        # Parse course JSON
        course_response = course_response.strip()
        if course_response.startswith("```"):
            lines = course_response.split("\n")
            course_response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        start = course_response.find("{")
        end = course_response.rfind("}") + 1
        if start == -1 or end == 0:
            raise ValueError("No JSON found in course response")

        course_data = json.loads(course_response[start:end])

        # Generate unique slug
        base_slug = slugify(course_data.get("title", request.title))
        slug = base_slug
        counter = 1
        while True:
            result = await db.execute(select(Course).where(Course.slug == slug))
            if not result.scalar_one_or_none():
                break
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create the course
        course = Course(
            title=course_data.get("title", request.title),
            slug=slug,
            description=course_data.get("description", request.summary),
            short_description=request.summary[:400] if len(request.summary) > 400 else request.summary,
            category=category,
            difficulty=difficulty,
            estimated_hours=len(course_data.get("modules", [])) * 2,
            points=150 if difficulty == "advanced" else 100 if difficulty == "intermediate" else 75,
            is_ai_generated=True,
            is_published=True,  # Auto-publish for user
            created_by=user_id,  # Set owner
        )

        db.add(course)
        await db.commit()
        await db.refresh(course)

        # Create modules and lessons with FULL content generation
        for i, module_data in enumerate(course_data.get("modules", [])):
            module = Module(
                course_id=course.id,
                title=module_data.get("title", f"Module {i+1}"),
                description=module_data.get("description", ""),
                order=i,
            )
            db.add(module)
            await db.commit()
            await db.refresh(module)

            for j, lesson_data in enumerate(module_data.get("lessons", [])):
                lesson_title = lesson_data.get("title", f"Lesson {j+1}")
                lesson_description = lesson_data.get("description", "")

                # Generate FULL lesson content using AI
                lesson_content = await _generate_full_lesson_content(
                    lesson_title=lesson_title,
                    lesson_description=lesson_description,
                    module_title=module_data.get("title", ""),
                    course_title=course_data.get("title", request.title),
                    news_context=f"{request.title}\n{request.summary}",
                    difficulty=difficulty,
                )

                lesson = Lesson(
                    module_id=module.id,
                    title=lesson_title,
                    content=lesson_content,
                    lesson_type="text",
                    order=j,
                    duration=15,
                    points=10,
                    word_count=len(lesson_content.split()),
                    estimated_reading_time=max(1, len(lesson_content.split()) // 200),
                    generation_status=GenerationStatus.COMPLETED,
                )
                db.add(lesson)
                await db.flush()

                # Create text content block
                text_block = ContentBlock(
                    lesson_id=lesson.id,
                    block_type=ContentBlockType.TEXT,
                    order=0,
                    content=lesson_content,
                    block_metadata={"source": "ai_generated"},
                )
                db.add(text_block)

                # Generate and add Wikipedia content for each lesson
                try:
                    from app.services.external.wikipedia_service import wikipedia_service
                    wiki_result = await wikipedia_service.summarize_for_lesson(lesson_title)
                    if wiki_result.get("url"):
                        wiki_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.WIKIPEDIA,
                            order=1,
                            content=wiki_result.get("summary", ""),
                            block_metadata={
                                "title": wiki_result.get("title"),
                                "url": wiki_result.get("url"),
                                "thumbnail": wiki_result.get("thumbnail"),
                            },
                        )
                        db.add(wiki_block)
                except Exception as wiki_error:
                    logger.warning(f"Wikipedia integration failed for lesson: {wiki_error}")

                # Generate diagram for the lesson
                try:
                    from app.services.ai.diagram_generator import diagram_generator
                    diagrams = await diagram_generator.suggest_diagrams_for_lesson(lesson_content, lesson_title)
                    for k, diagram in enumerate(diagrams[:1]):  # Limit to 1 diagram per lesson
                        diagram_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.DIAGRAM,
                            order=2 + k,
                            content=diagram.get("code", ""),
                            block_metadata={
                                "diagram_type": "mermaid",
                                "title": diagram.get("title", ""),
                                "description": diagram.get("description", ""),
                            },
                        )
                        db.add(diagram_block)
                except Exception as diagram_error:
                    logger.warning(f"Diagram generation failed for lesson: {diagram_error}")

        await db.commit()

        # Record course creation for limit tracking
        await limit_enforcer.record_course_created(UUID(user_id), is_ai_generated=True, db=db)

        # Now generate a lab
        lab_prompt = f"""Create a hands-on cybersecurity lab based on this news:

NEWS TITLE: {request.title}
SUMMARY: {request.summary}
CATEGORY: {request.category}

Create a practical lab that lets students:
1. Understand the vulnerability/attack in a safe environment
2. Practice detection techniques
3. Implement defensive measures

Return JSON format:
{{
    "title": "Lab Title",
    "description": "Lab description",
    "objectives": ["Objective 1", "Objective 2", "Objective 3"],
    "instructions": "Step-by-step markdown instructions for the lab",
    "flags": [
        {{"name": "flag1", "value": "FLAG{{example}}", "points": 50, "hint": "Hint for flag 1"}},
        {{"name": "flag2", "value": "FLAG{{example2}}", "points": 50, "hint": "Hint for flag 2"}}
    ],
    "estimated_time": 45
}}"""

        messages = [{"role": "user", "content": lab_prompt}]
        lab_response = await teaching_engine.generate_response(
            messages,
            teaching_mode="challenge",
            skill_level=difficulty,
            temperature=0.7,
            max_tokens=2000,
        )

        lab_id = None
        lab_title = None
        lab_slug_result = None

        try:
            lab_response = lab_response.strip()
            if lab_response.startswith("```"):
                lines = lab_response.split("\n")
                lab_response = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            start = lab_response.find("{")
            end = lab_response.rfind("}") + 1
            if start != -1 and end > 0:
                lab_data = json.loads(lab_response[start:end])

                # Generate lab slug
                lab_base_slug = slugify(lab_data.get("title", f"lab-{request.title}"))
                lab_slug_result = lab_base_slug
                counter = 1
                while True:
                    result = await db.execute(select(Lab).where(Lab.slug == lab_slug_result))
                    if not result.scalar_one_or_none():
                        break
                    lab_slug_result = f"{lab_base_slug}-{counter}"
                    counter += 1

                # Determine lab type based on difficulty
                lab_type = LabType.TUTORIAL if difficulty == "beginner" else LabType.CHALLENGE

                # Create the lab
                lab = Lab(
                    title=lab_data.get("title", f"Lab: {request.title}"),
                    slug=lab_slug_result,
                    description=lab_data.get("description", request.summary),
                    lab_type=lab_type,
                    difficulty=difficulty,
                    estimated_time=lab_data.get("estimated_time", 45),
                    points=100 if difficulty == "advanced" else 75 if difficulty == "intermediate" else 50,
                    infrastructure_spec={
                        "containers": [
                            {"name": "target", "image": "cyberx/vulnerable-app", "ports": ["80:80"]}
                        ],
                        "networks": ["lab_network"]
                    },
                    flags=lab_data.get("flags", []),
                    objectives=lab_data.get("objectives", []),
                    instructions=lab_data.get("instructions", "Complete the lab objectives."),
                    category=request.category.lower().replace(" ", "_"),
                    tags=request.tags[:5] if request.tags else [request.category.lower()],
                    is_published=True,
                    is_ai_generated=True,
                )

                db.add(lab)
                await db.commit()
                await db.refresh(lab)

                lab_id = str(lab.id)
                lab_title = lab.title

        except Exception as e:
            logger.warning("Failed to create lab, continuing with course only", error=str(e))

        await db.refresh(course)

        return NewsLearningResponse(
            course_id=str(course.id),
            course_title=course.title,
            course_slug=course.slug,
            lab_id=lab_id,
            lab_title=lab_title,
            lab_slug=lab_slug_result,
            message=f"Successfully created course '{course.title}'" + (f" and lab '{lab_title}'" if lab_title else "")
        )

    except json.JSONDecodeError as e:
        logger.error("Failed to parse AI response", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to generate learning content. Please try again.")
    except Exception as e:
        logger.error("Failed to generate learning content", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to generate content: {str(e)}")


# ============================================================================
# EXTERNAL CONTENT SEARCH ENDPOINTS
# ============================================================================

@router.get("/external/wikipedia/search")
async def search_wikipedia(
    query: str = Query(..., description="Search query"),
    limit: int = Query(5, ge=1, le=10),
):
    """Search Wikipedia for articles."""
    try:
        from app.services.external.wikipedia_service import wikipedia_service

        results = await wikipedia_service.search_articles(query, limit=limit)
        return {"results": results, "query": query}

    except ImportError:
        raise HTTPException(status_code=503, detail="Wikipedia service not available")
    except Exception as e:
        logger.error("Wikipedia search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Wikipedia search failed")


@router.get("/external/wikipedia/summary")
async def get_wikipedia_summary(
    topic: str = Query(..., description="Topic to summarize"),
):
    """Get a lesson-ready Wikipedia summary."""
    try:
        from app.services.external.wikipedia_service import wikipedia_service

        result = await wikipedia_service.summarize_for_lesson(topic)
        return result

    except ImportError:
        raise HTTPException(status_code=503, detail="Wikipedia service not available")
    except Exception as e:
        logger.error("Wikipedia summary failed", error=str(e))
        raise HTTPException(status_code=500, detail="Wikipedia summary failed")


@router.get("/external/images/search")
async def search_images(
    query: str = Query(..., description="Search query"),
    source: str = Query("auto", description="Image source: auto, unsplash, pexels, wikimedia"),
    limit: int = Query(5, ge=1, le=20),
):
    """Search for images from various sources."""
    try:
        from app.services.external.image_service import image_service, ImageSource

        source_enum = ImageSource(source.lower())
        results = await image_service.search_images(query, source=source_enum, limit=limit)
        return {"results": results, "query": query, "source": source}

    except ImportError:
        raise HTTPException(status_code=503, detail="Image service not available")
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid source: {source}")
    except Exception as e:
        logger.error("Image search failed", error=str(e))
        raise HTTPException(status_code=500, detail="Image search failed")


@router.get("/external/youtube/search")
async def search_youtube(
    query: str = Query(..., description="Search query"),
    difficulty: str = Query("beginner", description="Content difficulty level"),
    limit: int = Query(5, ge=1, le=10),
):
    """Search for educational YouTube videos."""
    try:
        from app.services.external.youtube_service import youtube_service

        results = await youtube_service.search_educational_videos(
            query,
            difficulty=difficulty,
            max_results=limit,
        )
        return {"results": results, "query": query, "difficulty": difficulty}

    except ImportError:
        raise HTTPException(status_code=503, detail="YouTube service not available")
    except Exception as e:
        logger.error("YouTube search failed", error=str(e))
        raise HTTPException(status_code=500, detail="YouTube search failed")
