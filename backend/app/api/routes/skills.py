from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_user_id
from app.models.user import User
from app.models.skill import Skill, SkillDomain, UserSkill
from app.services.skills import skill_tracker as st

router = APIRouter()


@router.get("/domains")
async def list_skill_domains(db: AsyncSession = Depends(get_db)):
    """List all skill domains."""
    result = await db.execute(select(SkillDomain).order_by(SkillDomain.order))
    domains = result.scalars().all()

    if not domains:
        # Return default domains if none in DB
        return [
            {"id": k, "name": v["name"], "skills": v["skills"]}
            for k, v in st.skill_tracker.default_skill_tree.items()
        ]

    return [
        {
            "id": str(d.id),
            "name": d.name,
            "description": d.description,
            "icon": d.icon,
            "color": d.color,
        }
        for d in domains
    ]


@router.get("/tree")
async def get_skill_tree():
    """Get the complete skill tree structure."""
    return st.skill_tracker.default_skill_tree


@router.get("/my")
async def get_my_skills(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's skill levels."""
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id)
    )
    user_skills = result.scalars().all()

    skills_data = {}
    for us in user_skills:
        skill_result = await db.execute(select(Skill).where(Skill.id == us.skill_id))
        skill = skill_result.scalar_one_or_none()
        if skill:
            skills_data[skill.name] = {
                "proficiency_level": us.proficiency_level,
                "confidence_score": us.confidence_score,
                "level_label": st.skill_tracker.get_skill_level_label(us.proficiency_level),
                "total_practice_time": us.total_practice_time,
                "questions_attempted": us.questions_attempted,
                "questions_correct": us.questions_correct,
                "last_practiced": us.last_practiced.isoformat() if us.last_practiced else None,
            }

    # Calculate overall stats
    if skills_data:
        overall = st.skill_tracker.calculate_overall_proficiency(
            {k: v["proficiency_level"] for k, v in skills_data.items()}
        )
    else:
        overall = 0.0

    return {
        "skills": skills_data,
        "overall_proficiency": overall,
        "overall_level": st.skill_tracker.get_skill_level_label(overall),
    }


@router.get("/recommendations")
async def get_skill_recommendations(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get personalized skill learning recommendations."""
    # Get user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get user skills
    result = await db.execute(
        select(UserSkill).where(UserSkill.user_id == user_id)
    )
    user_skills_db = result.scalars().all()

    # Build skills dict
    user_skills = {}
    for us in user_skills_db:
        skill_result = await db.execute(select(Skill).where(Skill.id == us.skill_id))
        skill = skill_result.scalar_one_or_none()
        if skill:
            user_skills[skill.name] = {
                "proficiency_level": us.proficiency_level,
            }

    # Get recommendations based on career goal
    recommendations = st.skill_tracker.get_learning_recommendations(
        user_skills=user_skills,
        career_goal=user.career_goal.value if user.career_goal else "general",
    )

    return {
        "career_goal": user.career_goal.value if user.career_goal else "general",
        "recommendations": recommendations,
    }


@router.post("/assess")
async def assess_skill(
    skill_name: str,
    question: str,
    answer: str,
    difficulty: float = 0.5,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Submit a skill assessment answer."""
    from app.services.ai import teaching_engine

    # Use AI to evaluate the answer
    assessment = await teaching_engine.assess_skill(
        skill_name=skill_name,
        user_response=answer,
        question=question,
        difficulty=difficulty,
    )

    # Get or create user skill
    skill_result = await db.execute(select(Skill).where(Skill.name == skill_name))
    skill = skill_result.scalar_one_or_none()

    if skill:
        user_skill_result = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill.id,
            )
        )
        user_skill = user_skill_result.scalar_one_or_none()

        if user_skill:
            # Update proficiency
            new_level = st.skill_tracker.calculate_proficiency(
                current_level=user_skill.proficiency_level,
                question_difficulty=difficulty,
                is_correct=assessment.get("correct", False),
            )

            # Update assessment history
            history = user_skill.assessment_history or []
            history.append({
                "difficulty": difficulty,
                "correct": assessment.get("correct", False),
                "score": assessment.get("score", 0),
            })

            user_skill.proficiency_level = new_level
            user_skill.assessment_history = history[-50:]  # Keep last 50
            user_skill.questions_attempted += 1
            if assessment.get("correct", False):
                user_skill.questions_correct += 1

            # Update confidence
            user_skill.confidence_score = st.skill_tracker.calculate_confidence(
                user_skill.assessment_history
            )

            await db.commit()

            assessment["new_proficiency"] = new_level
            assessment["confidence"] = user_skill.confidence_score

    return assessment


@router.get("/assessment/{skill_name}")
async def generate_skill_assessment(
    skill_name: str,
    num_questions: int = 5,
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Generate a skill assessment quiz."""
    # Get user's current level for this skill
    skill_result = await db.execute(select(Skill).where(Skill.name == skill_name))
    skill = skill_result.scalar_one_or_none()

    current_level = 1.0  # Default

    if skill:
        user_skill_result = await db.execute(
            select(UserSkill).where(
                UserSkill.user_id == user_id,
                UserSkill.skill_id == skill.id,
            )
        )
        user_skill = user_skill_result.scalar_one_or_none()
        if user_skill:
            current_level = user_skill.proficiency_level

    # Generate assessment questions
    questions = st.skill_tracker.generate_skill_assessment(
        skill_name=skill_name,
        current_level=current_level,
        num_questions=num_questions,
    )

    return {
        "skill": skill_name,
        "current_level": current_level,
        "questions": questions,
    }


@router.get("/level-info")
async def get_skill_level_info():
    """Get information about skill levels."""
    return {
        "levels": [
            {"level": 0, "label": "Novice", "description": "Just starting out"},
            {"level": 1, "label": "Beginner", "description": "Basic understanding"},
            {"level": 2, "label": "Intermediate", "description": "Can apply concepts"},
            {"level": 3, "label": "Advanced", "description": "Deep understanding"},
            {"level": 4, "label": "Expert", "description": "Can teach others"},
            {"level": 5, "label": "Master", "description": "Industry-leading expertise"},
        ],
        "scale": {
            "min": 0,
            "max": 5,
            "units": "proficiency points",
        },
    }
