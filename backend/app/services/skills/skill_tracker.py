import math
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import UUID
import structlog

logger = structlog.get_logger()


class SkillTracker:
    """
    Skill tracking service using Item Response Theory (IRT) for accurate skill assessment.
    Uses a simplified 1-parameter Rasch model for skill estimation.
    """

    def __init__(self):
        # Default skill domains and subskills
        self.default_skill_tree = {
            "network_security": {
                "name": "Network Security",
                "skills": [
                    "tcp_ip_fundamentals",
                    "network_scanning",
                    "packet_analysis",
                    "firewall_configuration",
                    "ids_ips",
                    "vpn_tunneling",
                ],
            },
            "web_security": {
                "name": "Web Application Security",
                "skills": [
                    "sql_injection",
                    "xss",
                    "csrf",
                    "authentication_attacks",
                    "session_management",
                    "api_security",
                    "file_upload_vulnerabilities",
                ],
            },
            "system_security": {
                "name": "System Security",
                "skills": [
                    "linux_administration",
                    "windows_security",
                    "privilege_escalation",
                    "hardening",
                    "patch_management",
                ],
            },
            "cryptography": {
                "name": "Cryptography",
                "skills": [
                    "symmetric_encryption",
                    "asymmetric_encryption",
                    "hashing",
                    "pki",
                    "tls_ssl",
                ],
            },
            "forensics": {
                "name": "Digital Forensics",
                "skills": [
                    "disk_forensics",
                    "memory_forensics",
                    "network_forensics",
                    "log_analysis",
                    "incident_response",
                ],
            },
            "malware_analysis": {
                "name": "Malware Analysis",
                "skills": [
                    "static_analysis",
                    "dynamic_analysis",
                    "reverse_engineering",
                    "sandbox_analysis",
                ],
            },
            "cloud_security": {
                "name": "Cloud Security",
                "skills": [
                    "aws_security",
                    "azure_security",
                    "container_security",
                    "kubernetes_security",
                    "iam",
                ],
            },
            "soc_operations": {
                "name": "SOC Operations",
                "skills": [
                    "siem",
                    "threat_hunting",
                    "threat_intelligence",
                    "security_monitoring",
                    "alert_triage",
                ],
            },
        }

    def calculate_proficiency(
        self,
        current_level: float,
        question_difficulty: float,
        is_correct: bool,
        learning_rate: float = 0.1,
    ) -> float:
        """
        Calculate new proficiency level based on assessment response.
        Uses simplified IRT-based calculation.

        Args:
            current_level: Current proficiency (0.0 - 5.0)
            question_difficulty: Question difficulty (0.0 - 1.0)
            is_correct: Whether the answer was correct
            learning_rate: How much to adjust based on new data

        Returns:
            New proficiency level
        """
        # Scale difficulty to proficiency range (0-5)
        scaled_difficulty = question_difficulty * 5

        # Calculate expected probability of correct answer
        # Using logistic function (1PL IRT model)
        theta = current_level - scaled_difficulty
        expected_prob = 1 / (1 + math.exp(-theta))

        # Actual outcome (1 for correct, 0 for incorrect)
        actual = 1 if is_correct else 0

        # Update proficiency based on surprise
        # If correct on hard question -> increase more
        # If incorrect on easy question -> decrease more
        surprise = actual - expected_prob
        adjustment = learning_rate * surprise

        # Apply adjustment with bounds
        new_level = current_level + adjustment
        new_level = max(0.0, min(5.0, new_level))

        return round(new_level, 2)

    def calculate_confidence(
        self,
        assessment_history: List[Dict[str, Any]],
        min_assessments: int = 5,
    ) -> float:
        """
        Calculate confidence score based on assessment consistency.

        Args:
            assessment_history: List of past assessments
            min_assessments: Minimum assessments for high confidence

        Returns:
            Confidence score (0.0 - 1.0)
        """
        if not assessment_history:
            return 0.5  # Default confidence

        num_assessments = len(assessment_history)

        # Base confidence on number of assessments
        volume_confidence = min(num_assessments / min_assessments, 1.0)

        # Calculate consistency (variance in performance)
        if num_assessments < 2:
            consistency = 0.5
        else:
            # Calculate performance variance
            performances = []
            for item in assessment_history[-10:]:  # Last 10 assessments
                difficulty = item.get("difficulty", 0.5)
                correct = item.get("correct", False)
                # Performance relative to difficulty
                perf = 1 - difficulty if correct else difficulty - 1
                performances.append(perf)

            variance = sum((p - sum(performances) / len(performances)) ** 2 for p in performances) / len(performances)
            consistency = max(0, 1 - variance)

        # Combine factors
        confidence = (volume_confidence * 0.6 + consistency * 0.4)
        return round(confidence, 2)

    def get_recommended_difficulty(
        self,
        proficiency_level: float,
        target_success_rate: float = 0.7,
    ) -> float:
        """
        Get recommended question difficulty for optimal learning.

        The "zone of proximal development" - not too easy, not too hard.

        Args:
            proficiency_level: Current skill level (0-5)
            target_success_rate: Desired probability of correct answer

        Returns:
            Recommended difficulty (0.0 - 1.0)
        """
        # Inverse of success probability formula
        # If we want 70% success rate, question should be slightly below current level
        theta_offset = math.log(target_success_rate / (1 - target_success_rate))

        # Calculate difficulty in proficiency scale
        recommended_proficiency = proficiency_level - theta_offset

        # Convert to 0-1 difficulty scale
        difficulty = recommended_proficiency / 5.0
        difficulty = max(0.1, min(0.9, difficulty))

        return round(difficulty, 2)

    def generate_skill_assessment(
        self,
        skill_name: str,
        current_level: float,
        num_questions: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Generate a skill assessment with appropriate difficulty distribution.

        Args:
            skill_name: Name of the skill to assess
            current_level: Current proficiency level
            num_questions: Number of questions to generate

        Returns:
            List of question specifications
        """
        questions = []
        base_difficulty = self.get_recommended_difficulty(current_level)

        for i in range(num_questions):
            # Vary difficulty around the base
            # Start easier, progressively get harder
            difficulty_offset = (i - num_questions // 2) * 0.1
            difficulty = max(0.1, min(0.9, base_difficulty + difficulty_offset))

            questions.append({
                "index": i + 1,
                "skill": skill_name,
                "difficulty": difficulty,
                "question_type": self._get_question_type(difficulty),
            })

        return questions

    def _get_question_type(self, difficulty: float) -> str:
        """Get appropriate question type based on difficulty."""
        if difficulty < 0.3:
            return "multiple_choice"
        elif difficulty < 0.6:
            return "short_answer"
        elif difficulty < 0.8:
            return "practical"
        else:
            return "scenario"

    def calculate_overall_proficiency(
        self,
        skill_levels: Dict[str, float],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Calculate overall proficiency across multiple skills.

        Args:
            skill_levels: Dictionary of skill names to proficiency levels
            weights: Optional weights for each skill

        Returns:
            Weighted average proficiency
        """
        if not skill_levels:
            return 0.0

        if weights is None:
            weights = {skill: 1.0 for skill in skill_levels}

        total_weight = sum(weights.get(skill, 1.0) for skill in skill_levels)
        weighted_sum = sum(
            level * weights.get(skill, 1.0)
            for skill, level in skill_levels.items()
        )

        return round(weighted_sum / total_weight, 2) if total_weight > 0 else 0.0

    def get_skill_level_label(self, proficiency: float) -> str:
        """Get human-readable label for proficiency level."""
        if proficiency < 1.0:
            return "Novice"
        elif proficiency < 2.0:
            return "Beginner"
        elif proficiency < 3.0:
            return "Intermediate"
        elif proficiency < 4.0:
            return "Advanced"
        elif proficiency < 4.5:
            return "Expert"
        else:
            return "Master"

    def get_learning_recommendations(
        self,
        user_skills: Dict[str, Dict[str, Any]],
        career_goal: str,
    ) -> List[Dict[str, Any]]:
        """
        Get personalized learning recommendations based on skill gaps.

        Args:
            user_skills: Current user skill data
            career_goal: User's career objective

        Returns:
            List of recommended skills to focus on
        """
        # Define skill importance by career goal
        career_skill_priorities = {
            "soc_analyst": {
                "siem": 1.0,
                "log_analysis": 0.9,
                "threat_hunting": 0.8,
                "network_forensics": 0.7,
                "incident_response": 0.9,
            },
            "pentester": {
                "sql_injection": 1.0,
                "xss": 0.9,
                "privilege_escalation": 1.0,
                "network_scanning": 0.8,
                "web_security": 0.9,
            },
            "security_engineer": {
                "hardening": 1.0,
                "firewall_configuration": 0.9,
                "cloud_security": 0.8,
                "container_security": 0.7,
                "iam": 0.8,
            },
            "malware_analyst": {
                "static_analysis": 1.0,
                "dynamic_analysis": 0.9,
                "reverse_engineering": 1.0,
                "sandbox_analysis": 0.8,
            },
        }

        priorities = career_skill_priorities.get(career_goal, {})
        recommendations = []

        for skill_name, priority in priorities.items():
            current = user_skills.get(skill_name, {}).get("proficiency_level", 0)
            target = 3.0 + priority  # Target based on priority

            if current < target:
                gap = target - current
                recommendations.append({
                    "skill": skill_name,
                    "current_level": current,
                    "target_level": target,
                    "gap": round(gap, 2),
                    "priority": priority,
                    "recommended_focus": gap > 2.0,
                })

        # Sort by priority and gap size
        recommendations.sort(key=lambda x: (-x["priority"], -x["gap"]))

        return recommendations[:10]  # Top 10 recommendations


# Singleton instance
skill_tracker = SkillTracker()
