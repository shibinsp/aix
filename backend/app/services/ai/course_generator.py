"""
Advanced AI Course Generation Pipeline.

Multi-stage course generation with rich content including:
- Detailed lesson content (2000+ words)
- Code examples with syntax highlighting
- Mermaid diagrams
- Wikipedia integration
- Image suggestions
- YouTube video recommendations
- Inline quizzes
"""

import asyncio
import json
import re
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from uuid import UUID
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.course import (
    Course, Module, Lesson, ContentBlock, ExternalResource,
    CourseGenerationJob, GenerationStage, GenerationStatus,
    ContentBlockType, ResourceType, DifficultyLevel, CourseCategory
)
from app.services.ai.teaching_engine import teaching_engine
from app.services.ai.diagram_generator import diagram_generator
from app.services.ai.quiz_generator import quiz_generator

logger = structlog.get_logger()


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
        "project": "interactive",
        "workshop": "interactive",
        "activity": "interactive",
        "tutorial": "text",
        "lecture": "text",
        "reading": "text",
        "theory": "text",
        "overview": "text",
        "introduction": "text",
        "assessment": "quiz",
        "test": "quiz",
        "exam": "quiz",
        "challenge": "lab",
        "practice": "lab",
        "ctf": "lab",
        "simulation": "lab",
    }

    if lesson_type in valid_types:
        return lesson_type
    return type_mapping.get(lesson_type, "text")


class CourseGenerationPipeline:
    """
    Multi-stage course generation with progress tracking.

    Stages:
    1. STRUCTURE - Generate course outline with modules and lessons
    2. CONTENT - Generate detailed content for each lesson
    3. CODE_EXAMPLES - Add code examples to relevant lessons
    4. DIAGRAMS - Generate Mermaid diagrams
    5. IMAGES - Find and attach images
    6. WIKIPEDIA - Integrate Wikipedia content
    7. QUIZZES - Generate lesson quizzes
    8. REVIEW - Final review and optimization
    """

    def __init__(self):
        self.stage_weights = {
            GenerationStage.STRUCTURE: 5,
            GenerationStage.CONTENT: 60,
            GenerationStage.CODE_EXAMPLES: 10,
            GenerationStage.DIAGRAMS: 5,
            GenerationStage.IMAGES: 5,
            GenerationStage.WIKIPEDIA: 5,
            GenerationStage.QUIZZES: 8,
            GenerationStage.REVIEW: 2,
        }

    async def generate_full_course(
        self,
        topic: str,
        difficulty: str,
        num_modules: int,
        options: Dict[str, Any],
        job_id: UUID,
        course_id: UUID,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ) -> Course:
        """
        Generate a complete course with all content.

        Args:
            topic: Course topic
            difficulty: Difficulty level
            num_modules: Number of modules to generate
            options: Generation options (include_code, include_diagrams, etc.)
            job_id: Generation job ID for tracking
            course_id: Course ID to populate
            db: Database session
            progress_callback: Async callback for progress updates
        """
        try:
            # Get the course and job
            course = await db.get(Course, course_id)
            job = await db.get(CourseGenerationJob, job_id)

            if not course or not job:
                raise ValueError("Course or job not found")

            # Stage 1: Generate Structure
            await self._update_job_stage(job, GenerationStage.STRUCTURE, db)
            if progress_callback:
                await progress_callback(job_id, "structure", 0, "Generating course structure...")

            structure = await self._generate_structure(topic, difficulty, num_modules, options)
            await self._create_course_structure(course, structure, db)
            await db.commit()

            # Count total lessons
            job.total_lessons = sum(len(m.get("lessons", [])) for m in structure.get("modules", []))
            await db.commit()

            if progress_callback:
                await progress_callback(job_id, "structure", 100, "Course structure created")

            # Stage 2: Generate Content
            await self._update_job_stage(job, GenerationStage.CONTENT, db)
            await self._generate_all_lesson_content(course, job, options, db, progress_callback)

            # Stage 3: Code Examples
            if options.get("include_code_examples", True):
                await self._update_job_stage(job, GenerationStage.CODE_EXAMPLES, db)
                await self._add_code_examples(course, job, db, progress_callback)

            # Stage 4: Diagrams
            if options.get("include_diagrams", True):
                await self._update_job_stage(job, GenerationStage.DIAGRAMS, db)
                await self._add_diagrams(course, job, db, progress_callback)

            # Stage 5: Images (placeholder - external service)
            if options.get("include_images", True):
                await self._update_job_stage(job, GenerationStage.IMAGES, db)
                await self._add_images(course, job, db, progress_callback)

            # Stage 6: Wikipedia
            if options.get("include_wikipedia", True):
                await self._update_job_stage(job, GenerationStage.WIKIPEDIA, db)
                await self._add_wikipedia_content(course, job, db, progress_callback)

            # Stage 7: Quizzes
            if options.get("include_quizzes", True):
                await self._update_job_stage(job, GenerationStage.QUIZZES, db)
                await self._add_quizzes(course, job, db, progress_callback)

            # Stage 8: Final Review
            await self._update_job_stage(job, GenerationStage.REVIEW, db)
            await self._final_review(course, db, progress_callback)

            # Mark as completed
            job.current_stage = GenerationStage.COMPLETED
            job.completed_at = datetime.utcnow()
            job.progress_percent = 100
            course.generation_status = GenerationStatus.COMPLETED
            course.is_published = True
            await db.commit()

            if progress_callback:
                await progress_callback(job_id, "completed", 100, "Course generation complete!")

            # Refresh and return
            await db.refresh(course)
            return course

        except Exception as e:
            logger.error("Course generation failed", error=str(e), job_id=str(job_id))
            if job:
                job.current_stage = GenerationStage.FAILED
                job.error_message = str(e)
                await db.commit()
            raise

    async def _update_job_stage(
        self,
        job: CourseGenerationJob,
        stage: GenerationStage,
        db: AsyncSession,
    ):
        """Update job to a new stage."""
        if job.current_stage != GenerationStage.QUEUED:
            job.stages_completed = job.stages_completed or []
            job.stages_completed.append(job.current_stage.value)

        job.current_stage = stage
        await db.commit()

    async def _generate_structure(
        self,
        topic: str,
        difficulty: str,
        num_modules: int,
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate course structure with modules and lesson titles."""
        prompt = f"""Create a comprehensive cybersecurity course structure on "{topic}" for {difficulty} level students.

Requirements:
- Generate exactly {num_modules} modules
- Each module should have 3-5 lessons
- Focus on practical, hands-on learning
- Include progressive difficulty within each module
- Lessons should build upon each other

IMPORTANT: Return ONLY valid JSON, no markdown, no extra text.

Format:
{{
    "title": "Course Title",
    "description": "Detailed course description (2-3 sentences)",
    "short_description": "Brief one-line description",
    "learning_outcomes": ["outcome1", "outcome2", "outcome3"],
    "what_youll_learn": ["point1", "point2", "point3", "point4"],
    "target_audience": "Description of who this course is for",
    "modules": [
        {{
            "title": "Module Title",
            "description": "Module description",
            "learning_objectives": ["objective1", "objective2"],
            "estimated_duration": 45,
            "lessons": [
                {{
                    "title": "Lesson Title",
                    "description": "Brief lesson description",
                    "type": "text",
                    "learning_objectives": ["objective1"],
                    "duration": 15,
                    "points": 10
                }}
            ]
        }}
    ]
}}"""

        messages = [{"role": "user", "content": prompt}]
        response = await teaching_engine.generate_response(
            messages,
            teaching_mode="lecture",
            skill_level=difficulty,
            temperature=0.6,
            max_tokens=4000,
        )

        # Parse JSON
        try:
            json_str = teaching_engine._clean_json_response(response)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse structure", error=str(e))
            raise ValueError(f"Failed to parse course structure: {e}")

    async def _create_course_structure(
        self,
        course: Course,
        structure: Dict[str, Any],
        db: AsyncSession,
    ):
        """Create database entities from structure."""
        # Update course fields
        course.title = structure.get("title", course.title)
        course.description = structure.get("description")
        course.short_description = structure.get("short_description")
        course.learning_outcomes = structure.get("learning_outcomes", [])
        course.what_youll_learn = structure.get("what_youll_learn", [])
        course.target_audience = structure.get("target_audience")
        course.generation_status = GenerationStatus.GENERATING

        # Create modules and lessons
        for module_order, module_data in enumerate(structure.get("modules", [])):
            module = Module(
                course_id=course.id,
                title=module_data["title"],
                description=module_data.get("description"),
                order=module_order,
                learning_objectives=module_data.get("learning_objectives", []),
                estimated_duration=module_data.get("estimated_duration", 30),
            )
            db.add(module)
            await db.flush()

            for lesson_order, lesson_data in enumerate(module_data.get("lessons", [])):
                # Normalize the lesson type from AI response
                raw_type = lesson_data.get("type", "text")
                normalized_type = normalize_lesson_type(raw_type)

                lesson = Lesson(
                    module_id=module.id,
                    title=lesson_data["title"],
                    lesson_type=normalized_type,
                    order=lesson_order,
                    learning_objectives=lesson_data.get("learning_objectives", []),
                    duration=lesson_data.get("duration", 15),
                    points=lesson_data.get("points", 10),
                    generation_status=GenerationStatus.PENDING,
                )
                db.add(lesson)

    async def _generate_all_lesson_content(
        self,
        course: Course,
        job: CourseGenerationJob,
        options: Dict[str, Any],
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Generate detailed content for all lessons."""
        # Reload course with modules and lessons
        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        target_length = options.get("target_lesson_length", 2000)
        total_lessons = job.total_lessons
        completed = 0

        for module in course.modules:
            for lesson in module.lessons:
                job.current_lesson_id = lesson.id
                job.current_lesson_title = lesson.title

                if progress_callback:
                    progress = int((completed / total_lessons) * 100)
                    await progress_callback(
                        job.id,
                        "content",
                        progress,
                        f"Generating: {lesson.title}"
                    )

                # Generate lesson content
                content = await self._generate_lesson_content(
                    lesson,
                    module,
                    course,
                    target_length,
                )

                # Update lesson
                lesson.content = content
                lesson.word_count = len(content.split())
                lesson.estimated_reading_time = max(1, lesson.word_count // 200)
                lesson.generation_status = GenerationStatus.COMPLETED

                # Create text content block
                text_block = ContentBlock(
                    lesson_id=lesson.id,
                    block_type=ContentBlockType.TEXT,
                    order=0,
                    content=content,
                    block_metadata={"source": "ai_generated"},
                )
                db.add(text_block)

                completed += 1
                job.lessons_completed = completed
                job.progress_percent = self._calculate_progress(
                    GenerationStage.CONTENT,
                    completed,
                    total_lessons
                )

                await db.commit()

    async def _generate_lesson_content(
        self,
        lesson: Lesson,
        module: Module,
        course: Course,
        target_length: int,
    ) -> str:
        """Generate detailed content for a single lesson."""
        prompt = f"""Write a detailed, comprehensive lesson on "{lesson.title}" as part of the module "{module.title}" in the course "{course.title}".

Target Length: {target_length} words (this is important!)

Learning Objectives:
{chr(10).join(f"- {obj}" for obj in (lesson.learning_objectives or ["Understand key concepts"]))}

Requirements:
1. Start with an engaging introduction
2. Use clear headings and subheadings (##, ###)
3. Include practical examples where relevant
4. Use bullet points and numbered lists for clarity
5. Add callouts for tips, warnings, or important notes using markdown blockquotes
6. Include a brief summary at the end
7. Write in an educational but engaging tone
8. Focus on cybersecurity practical applications

Format the content in Markdown. Focus on depth and practical understanding.

Write the complete lesson content now:"""

        messages = [{"role": "user", "content": prompt}]

        # For long content, we may need multiple chunks
        content = await teaching_engine.generate_response(
            messages,
            teaching_mode="lecture",
            skill_level=course.difficulty.value if course.difficulty else "beginner",
            temperature=0.7,
            max_tokens=4000,
        )

        # If content is too short, request more
        if len(content.split()) < target_length * 0.7:
            extension_prompt = f"""Continue and expand the following lesson content. Add more detail, examples, and explanations to reach approximately {target_length} words total.

Current content:
{content}

Continue with more detailed content:"""

            messages = [{"role": "user", "content": extension_prompt}]
            extension = await teaching_engine.generate_response(
                messages,
                teaching_mode="lecture",
                skill_level=course.difficulty.value if course.difficulty else "beginner",
                temperature=0.7,
                max_tokens=2000,
            )
            content = content + "\n\n" + extension

        return content

    async def _add_code_examples(
        self,
        course: Course,
        job: CourseGenerationJob,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Add code examples to relevant lessons."""
        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons).selectinload(Lesson.content_blocks)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        if progress_callback:
            await progress_callback(job.id, "code_examples", 0, "Adding code examples...")

        for module in course.modules:
            for lesson in module.lessons:
                # Check if lesson content mentions code/programming concepts
                if lesson.content and any(kw in lesson.content.lower() for kw in [
                    "code", "script", "command", "python", "bash", "terminal",
                    "exploit", "payload", "injection", "query", "function"
                ]):
                    code_examples = await self._generate_code_for_lesson(lesson)

                    for i, example in enumerate(code_examples):
                        # Get current max order
                        max_order = max((b.order for b in lesson.content_blocks), default=0)

                        code_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.CODE,
                            order=max_order + 1 + i,
                            content=example["code"],
                            block_metadata={
                                "language": example.get("language", "python"),
                                "filename": example.get("filename"),
                                "description": example.get("description"),
                                "executable": example.get("executable", False),
                            },
                        )
                        db.add(code_block)

        await db.commit()

        if progress_callback:
            await progress_callback(job.id, "code_examples", 100, "Code examples added")

    async def _generate_code_for_lesson(
        self,
        lesson: Lesson,
    ) -> List[Dict[str, Any]]:
        """Generate code examples for a lesson."""
        prompt = f"""Based on this lesson content, generate 1-2 practical code examples.

Lesson: {lesson.title}
Content Summary: {(lesson.content or "")[:500]}...

For each example, provide:
1. The code
2. Programming language
3. Brief description
4. Whether it's safe to execute (no destructive operations)

Return JSON array:
[
    {{
        "code": "actual code here",
        "language": "python",
        "filename": "example.py",
        "description": "What this code does",
        "executable": true
    }}
]

Only include practical, educational examples. Focus on cybersecurity tools and techniques."""

        messages = [{"role": "user", "content": prompt}]
        response = await teaching_engine.generate_response(
            messages,
            teaching_mode="challenge",
            temperature=0.5,
            max_tokens=2000,
        )

        try:
            json_str = teaching_engine._clean_json_response(response)
            # Handle array response
            if json_str.startswith("["):
                return json.loads(json_str)
            return []
        except json.JSONDecodeError:
            return []

    async def _add_diagrams(
        self,
        course: Course,
        job: CourseGenerationJob,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Add Mermaid diagrams to lessons."""
        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons).selectinload(Lesson.content_blocks)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        if progress_callback:
            await progress_callback(job.id, "diagrams", 0, "Generating diagrams...")

        for module in course.modules:
            for lesson in module.lessons:
                if lesson.content:
                    diagrams = await diagram_generator.suggest_diagrams_for_lesson(
                        lesson.content,
                        lesson.title
                    )

                    for i, diagram in enumerate(diagrams):
                        max_order = max((b.order for b in lesson.content_blocks), default=0)

                        diagram_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.DIAGRAM,
                            order=max_order + 1 + i,
                            content=diagram.get("code", ""),
                            block_metadata={
                                "diagram_type": "mermaid",
                                "title": diagram.get("title", ""),
                                "description": diagram.get("description", ""),
                            },
                        )
                        db.add(diagram_block)

        await db.commit()

        if progress_callback:
            await progress_callback(job.id, "diagrams", 100, "Diagrams created")

    async def _add_images(
        self,
        course: Course,
        job: CourseGenerationJob,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Add images to lessons (placeholder for image service integration)."""
        if progress_callback:
            await progress_callback(job.id, "images", 0, "Finding relevant images...")

        # Note: This will be fully implemented when image service is available
        # For now, we'll add placeholder image blocks

        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        try:
            from app.services.external.image_service import image_service

            for module in course.modules:
                for lesson in module.lessons:
                    # Get image for lesson topic
                    image = await image_service.find_cybersecurity_image(lesson.title)

                    if image:
                        # Find max order for content blocks
                        max_order_query = select(ContentBlock.order).where(
                            ContentBlock.lesson_id == lesson.id
                        ).order_by(ContentBlock.order.desc()).limit(1)
                        result = await db.execute(max_order_query)
                        max_order = result.scalar() or 0

                        image_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.IMAGE,
                            order=1,  # Put image near the top
                            content=image.get("alt", ""),
                            block_metadata={
                                "url": image.get("url"),
                                "thumbnail": image.get("thumbnail"),
                                "source": image.get("source"),
                                "attribution": image.get("attribution"),
                                "source_url": image.get("source_url"),
                            },
                        )
                        db.add(image_block)

            await db.commit()

        except ImportError:
            logger.warning("Image service not available")

        if progress_callback:
            await progress_callback(job.id, "images", 100, "Images added")

    async def _add_wikipedia_content(
        self,
        course: Course,
        job: CourseGenerationJob,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Add Wikipedia references and content to lessons."""
        if progress_callback:
            await progress_callback(job.id, "wikipedia", 0, "Fetching Wikipedia content...")

        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        try:
            from app.services.external.wikipedia_service import wikipedia_service

            for module in course.modules:
                for lesson in module.lessons:
                    # Get Wikipedia content for lesson topic
                    wiki_result = await wikipedia_service.summarize_for_lesson(lesson.title)

                    if wiki_result.get("url"):
                        # Add as external resource
                        resource = ExternalResource(
                            lesson_id=lesson.id,
                            resource_type=ResourceType.WIKIPEDIA,
                            order=0,
                            title=wiki_result.get("title", lesson.title),
                            url=wiki_result.get("url"),
                            description=wiki_result.get("summary", ""),
                            cached_content=wiki_result.get("summary"),
                            resource_metadata={
                                "sections_used": wiki_result.get("sections_used", []),
                                "thumbnail": wiki_result.get("thumbnail"),
                            },
                        )
                        db.add(resource)

                        # Also add as content block
                        max_order_query = select(ContentBlock.order).where(
                            ContentBlock.lesson_id == lesson.id
                        ).order_by(ContentBlock.order.desc()).limit(1)
                        result = await db.execute(max_order_query)
                        max_order = result.scalar() or 0

                        wiki_block = ContentBlock(
                            lesson_id=lesson.id,
                            block_type=ContentBlockType.WIKIPEDIA,
                            order=max_order + 1,
                            content=wiki_result.get("summary", ""),
                            block_metadata={
                                "title": wiki_result.get("title"),
                                "url": wiki_result.get("url"),
                                "thumbnail": wiki_result.get("thumbnail"),
                            },
                        )
                        db.add(wiki_block)

            await db.commit()

        except ImportError:
            logger.warning("Wikipedia service not available")

        if progress_callback:
            await progress_callback(job.id, "wikipedia", 100, "Wikipedia content added")

    async def _add_quizzes(
        self,
        course: Course,
        job: CourseGenerationJob,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Add quizzes to lessons."""
        if progress_callback:
            await progress_callback(job.id, "quizzes", 0, "Generating quizzes...")

        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        for module in course.modules:
            for lesson in module.lessons:
                if lesson.content:
                    quiz_questions = await quiz_generator.generate_lesson_quiz(
                        lesson.content,
                        lesson.learning_objectives or [],
                        num_questions=3,
                    )

                    if quiz_questions:
                        lesson.quiz_data = {
                            "questions": quiz_questions,
                            "passing_score": 70,
                            "time_limit": 300,  # 5 minutes
                        }

        await db.commit()

        if progress_callback:
            await progress_callback(job.id, "quizzes", 100, "Quizzes generated")

    async def _final_review(
        self,
        course: Course,
        db: AsyncSession,
        progress_callback: Optional[callable] = None,
    ):
        """Perform final review and optimization."""
        if progress_callback:
            await progress_callback(course.id, "review", 0, "Performing final review...")

        # Calculate course statistics
        stmt = (
            select(Course)
            .options(
                selectinload(Course.modules).selectinload(Module.lessons)
            )
            .where(Course.id == course.id)
        )
        result = await db.execute(stmt)
        course = result.scalar_one()

        total_duration = 0
        total_points = 0

        for module in course.modules:
            module_duration = 0
            for lesson in module.lessons:
                module_duration += lesson.duration or 0
                total_points += lesson.points or 0

            module.estimated_duration = module_duration
            total_duration += module_duration

        course.estimated_hours = max(1, total_duration // 60)
        course.points = total_points

        await db.commit()

        if progress_callback:
            await progress_callback(course.id, "review", 100, "Review complete")

    def _calculate_progress(
        self,
        current_stage: GenerationStage,
        items_completed: int,
        total_items: int,
    ) -> int:
        """Calculate overall progress percentage."""
        # Calculate completed stage weights
        completed_weight = 0
        current_weight = 0

        stage_order = [
            GenerationStage.STRUCTURE,
            GenerationStage.CONTENT,
            GenerationStage.CODE_EXAMPLES,
            GenerationStage.DIAGRAMS,
            GenerationStage.IMAGES,
            GenerationStage.WIKIPEDIA,
            GenerationStage.QUIZZES,
            GenerationStage.REVIEW,
        ]

        for stage in stage_order:
            if stage == current_stage:
                current_weight = self.stage_weights.get(stage, 0)
                break
            completed_weight += self.stage_weights.get(stage, 0)

        total_weight = sum(self.stage_weights.values())

        # Progress within current stage
        if total_items > 0:
            stage_progress = (items_completed / total_items) * current_weight
        else:
            stage_progress = 0

        return int(((completed_weight + stage_progress) / total_weight) * 100)


# Singleton instance
course_generator = CourseGenerationPipeline()
