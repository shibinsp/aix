"""AI services for course generation and teaching."""

from app.services.ai.teaching_engine import TeachingEngine, teaching_engine
from app.services.ai.prompts import SystemPrompts
from app.services.ai.course_generator import CourseGenerationPipeline, course_generator
from app.services.ai.diagram_generator import DiagramGenerator, diagram_generator
from app.services.ai.quiz_generator import QuizGenerator, quiz_generator

__all__ = [
    "TeachingEngine",
    "teaching_engine",
    "SystemPrompts",
    "CourseGenerationPipeline",
    "course_generator",
    "DiagramGenerator",
    "diagram_generator",
    "QuizGenerator",
    "quiz_generator",
]
