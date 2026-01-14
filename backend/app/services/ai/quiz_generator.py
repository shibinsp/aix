"""
Quiz Generator for course assessments.

Generates various question types:
- Multiple choice
- True/False
- Fill in the blank
- Code completion
"""

import json
import re
from typing import Dict, Any, List, Optional
import structlog

from app.services.ai.teaching_engine import teaching_engine

logger = structlog.get_logger()


class QuizGenerator:
    """Service for generating quizzes from lesson content."""

    QUESTION_TYPES = [
        "multiple_choice",
        "true_false",
        "fill_blank",
        "code_completion",
    ]

    async def generate_lesson_quiz(
        self,
        content: str,
        learning_objectives: List[str],
        num_questions: int = 5,
        difficulty: str = "intermediate",
    ) -> List[Dict[str, Any]]:
        """
        Generate a quiz based on lesson content.

        Returns list of questions with format:
        {
            "question": "Question text",
            "type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "Why this is correct",
            "points": 10,
            "difficulty": "intermediate"
        }
        """
        # Truncate content if too long
        max_content_length = 3000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        objectives_text = "\n".join(f"- {obj}" for obj in learning_objectives) if learning_objectives else "General understanding"

        prompt = f"""Generate {num_questions} quiz questions based on this lesson content.

Learning Objectives:
{objectives_text}

Content:
{content}

Requirements:
1. Create a mix of question types (multiple choice, true/false)
2. Questions should test understanding, not just memorization
3. Include practical cybersecurity scenarios where relevant
4. Provide clear explanations for correct answers
5. Difficulty level: {difficulty}

Return ONLY a valid JSON array with this format:
[
    {{
        "question": "What is the primary purpose of...",
        "type": "multiple_choice",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "Option A",
        "explanation": "This is correct because...",
        "points": 10,
        "difficulty": "{difficulty}"
    }},
    {{
        "question": "True or False: SQL injection attacks...",
        "type": "true_false",
        "options": ["True", "False"],
        "correct_answer": "True",
        "explanation": "This is true because...",
        "points": 5,
        "difficulty": "{difficulty}"
    }}
]

Generate the quiz questions now:"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await teaching_engine.generate_response(
                messages,
                teaching_mode="challenge",
                skill_level=difficulty,
                temperature=0.6,
                max_tokens=3000,
            )

            # Parse JSON
            json_str = self._clean_json_response(response)
            questions = json.loads(json_str)

            # Validate and fix questions
            validated_questions = []
            for q in questions:
                validated = self._validate_question(q, difficulty)
                if validated:
                    validated_questions.append(validated)

            return validated_questions[:num_questions]

        except Exception as e:
            logger.error("Failed to generate quiz", error=str(e))
            return self._generate_fallback_questions(learning_objectives, num_questions, difficulty)

    async def generate_single_question(
        self,
        topic: str,
        question_type: str = "multiple_choice",
        difficulty: str = "intermediate",
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate a single quiz question on a specific topic."""
        type_instructions = {
            "multiple_choice": "Create a multiple choice question with 4 options (A, B, C, D).",
            "true_false": "Create a true/false question.",
            "fill_blank": "Create a fill-in-the-blank question with the blank indicated as ___.",
            "code_completion": "Create a code completion question where the user fills in missing code.",
        }

        instruction = type_instructions.get(question_type, type_instructions["multiple_choice"])

        prompt = f"""Generate a {difficulty} level quiz question about: {topic}

{f"Context: {context}" if context else ""}

{instruction}

Return ONLY valid JSON:
{{
    "question": "The question text",
    "type": "{question_type}",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer": "The correct option",
    "explanation": "Why this is correct",
    "points": 10,
    "difficulty": "{difficulty}"
}}"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await teaching_engine.generate_response(
                messages,
                teaching_mode="challenge",
                temperature=0.6,
                max_tokens=1000,
            )

            json_str = self._clean_json_response(response)
            question = json.loads(json_str)
            return self._validate_question(question, difficulty)

        except Exception as e:
            logger.error("Failed to generate question", error=str(e), topic=topic)
            return self._generate_fallback_question(topic, question_type, difficulty)

    async def generate_code_challenge(
        self,
        language: str,
        concept: str,
        difficulty: str = "intermediate",
    ) -> Dict[str, Any]:
        """Generate a code-based challenge question."""
        prompt = f"""Create a {difficulty} level coding challenge in {language} about: {concept}

Requirements:
1. Provide a code snippet with a missing part (marked with # TODO or ___)
2. The user should complete the code
3. Include test cases to verify the solution
4. Explain what the completed code should do

Return JSON:
{{
    "question": "Complete the following code to...",
    "type": "code_completion",
    "language": "{language}",
    "starter_code": "def example():\\n    # TODO: implement\\n    pass",
    "solution": "def example():\\n    return 'solution'",
    "test_cases": [
        {{"input": "test_input", "expected": "expected_output"}}
    ],
    "hints": ["Hint 1", "Hint 2"],
    "explanation": "The solution works by...",
    "points": 20,
    "difficulty": "{difficulty}"
}}"""

        messages = [{"role": "user", "content": prompt}]

        try:
            response = await teaching_engine.generate_response(
                messages,
                teaching_mode="challenge",
                temperature=0.6,
                max_tokens=1500,
            )

            json_str = self._clean_json_response(response)
            return json.loads(json_str)

        except Exception as e:
            logger.error("Failed to generate code challenge", error=str(e))
            return {
                "question": f"Complete the code to demonstrate {concept}",
                "type": "code_completion",
                "language": language,
                "starter_code": f"# Complete the following\n# TODO: Implement {concept}\n",
                "solution": "# Solution would be here",
                "test_cases": [],
                "hints": [f"Review {concept} concepts"],
                "explanation": f"This tests understanding of {concept}",
                "points": 20,
                "difficulty": difficulty,
            }

    def _clean_json_response(self, response: str) -> str:
        """Clean and extract JSON from AI response."""
        response = response.strip()

        # Remove markdown code blocks
        if response.startswith("```"):
            lines = response.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response = "\n".join(lines)

        # Find JSON array or object
        if "[" in response:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start != -1 and end > start:
                response = response[start:end]
        elif "{" in response:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start != -1 and end > start:
                response = response[start:end]

        # Fix common JSON issues
        response = re.sub(r',\s*([}\]])', r'\1', response)  # Remove trailing commas

        return response

    def _validate_question(
        self,
        question: Dict[str, Any],
        difficulty: str,
    ) -> Optional[Dict[str, Any]]:
        """Validate and normalize a question object."""
        required_fields = ["question", "type", "correct_answer"]

        for field in required_fields:
            if field not in question:
                return None

        # Normalize type
        q_type = question.get("type", "multiple_choice").lower().replace(" ", "_")
        if q_type not in self.QUESTION_TYPES:
            q_type = "multiple_choice"

        # Ensure options exist for multiple choice
        if q_type == "multiple_choice" and not question.get("options"):
            return None

        # Ensure correct answer is in options
        if q_type in ["multiple_choice", "true_false"]:
            options = question.get("options", [])
            correct = question.get("correct_answer")
            if correct not in options:
                # Try to find a match
                for opt in options:
                    if correct.lower() in opt.lower() or opt.lower() in correct.lower():
                        question["correct_answer"] = opt
                        break
                else:
                    # Default to first option if no match
                    if options:
                        question["correct_answer"] = options[0]

        return {
            "question": question["question"],
            "type": q_type,
            "options": question.get("options", []),
            "correct_answer": question["correct_answer"],
            "explanation": question.get("explanation", ""),
            "points": question.get("points", 10),
            "difficulty": difficulty,
            "hints": question.get("hints", []),
        }

    def _generate_fallback_questions(
        self,
        learning_objectives: List[str],
        num_questions: int,
        difficulty: str,
    ) -> List[Dict[str, Any]]:
        """Generate simple fallback questions from objectives."""
        questions = []

        for i, objective in enumerate(learning_objectives[:num_questions]):
            questions.append({
                "question": f"Which of the following best describes: {objective}?",
                "type": "multiple_choice",
                "options": [
                    f"Understanding {objective}",
                    "An unrelated concept",
                    "A different security topic",
                    "None of the above",
                ],
                "correct_answer": f"Understanding {objective}",
                "explanation": f"This question tests your understanding of {objective}.",
                "points": 10,
                "difficulty": difficulty,
            })

        # Fill remaining with generic questions
        while len(questions) < num_questions:
            questions.append({
                "question": "What is a key principle of cybersecurity?",
                "type": "multiple_choice",
                "options": [
                    "Defense in depth",
                    "Single point of failure",
                    "Ignoring logs",
                    "Sharing passwords",
                ],
                "correct_answer": "Defense in depth",
                "explanation": "Defense in depth is a fundamental cybersecurity principle.",
                "points": 10,
                "difficulty": difficulty,
            })

        return questions[:num_questions]

    def _generate_fallback_question(
        self,
        topic: str,
        question_type: str,
        difficulty: str,
    ) -> Dict[str, Any]:
        """Generate a simple fallback question."""
        if question_type == "true_false":
            return {
                "question": f"True or False: Understanding {topic} is important for cybersecurity.",
                "type": "true_false",
                "options": ["True", "False"],
                "correct_answer": "True",
                "explanation": f"{topic} is an important cybersecurity concept.",
                "points": 5,
                "difficulty": difficulty,
            }
        else:
            return {
                "question": f"What is the purpose of {topic}?",
                "type": "multiple_choice",
                "options": [
                    f"To improve security through {topic}",
                    "To decrease system performance",
                    "To add complexity without benefit",
                    "None of the above",
                ],
                "correct_answer": f"To improve security through {topic}",
                "explanation": f"{topic} is used to enhance security.",
                "points": 10,
                "difficulty": difficulty,
            }

    async def evaluate_answer(
        self,
        question: Dict[str, Any],
        user_answer: str,
    ) -> Dict[str, Any]:
        """Evaluate a user's answer to a question."""
        correct_answer = question.get("correct_answer", "")
        is_correct = False

        q_type = question.get("type", "multiple_choice")

        if q_type in ["multiple_choice", "true_false"]:
            # Exact or close match
            is_correct = (
                user_answer.lower().strip() == correct_answer.lower().strip() or
                user_answer.lower() in correct_answer.lower()
            )
        elif q_type == "fill_blank":
            # More flexible matching for fill in blank
            is_correct = (
                correct_answer.lower() in user_answer.lower() or
                user_answer.lower() in correct_answer.lower()
            )
        elif q_type == "code_completion":
            # For code, we'd need to execute and test - simplified check here
            is_correct = correct_answer.strip() == user_answer.strip()

        points_earned = question.get("points", 10) if is_correct else 0

        return {
            "is_correct": is_correct,
            "correct_answer": correct_answer,
            "user_answer": user_answer,
            "points_earned": points_earned,
            "max_points": question.get("points", 10),
            "explanation": question.get("explanation", ""),
        }


# Singleton instance
quiz_generator = QuizGenerator()
