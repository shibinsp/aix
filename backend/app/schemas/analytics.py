"""Pydantic schemas for analytics and progress tracking."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID


class UserProgressSummary(BaseModel):
    """Summary of a user's learning progress."""
    user_id: UUID
    username: str
    full_name: Optional[str]
    email: str
    # Progress
    courses_completed: int
    courses_in_progress: int
    labs_completed: int
    total_points: int
    current_streak: int
    # Time spent
    total_learning_hours: float
    terminal_hours: float
    desktop_hours: float
    # Activity
    last_activity: Optional[datetime]
    joined_at: datetime


class CourseProgress(BaseModel):
    """Progress for a single course."""
    course_id: UUID
    course_title: str
    progress_percent: int
    lessons_completed: int
    total_lessons: int
    labs_completed: int
    total_labs: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_activity: Optional[datetime]


class LeaderboardEntry(BaseModel):
    """Entry in a leaderboard."""
    rank: int
    user_id: UUID
    username: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    points: int
    courses_completed: int
    labs_completed: int
    streak: int


class BatchAnalytics(BaseModel):
    """Analytics for a batch."""
    batch_id: UUID
    batch_name: str
    # Members
    total_members: int
    active_members: int  # Active in last 7 days
    inactive_members: int
    # Progress
    avg_progress_percent: float
    completion_rate: float  # % who completed curriculum
    # Courses
    courses_in_curriculum: int
    avg_courses_completed: float
    # Labs
    total_labs_completed: int
    avg_labs_per_member: float
    # Time
    total_learning_hours: float
    avg_hours_per_member: float
    # Top performers
    top_performers: List[LeaderboardEntry]


class OrganizationAnalytics(BaseModel):
    """Analytics for an organization."""
    organization_id: UUID
    organization_name: str
    # Members
    total_members: int
    active_members: int
    new_members_this_month: int
    # Batches
    total_batches: int
    active_batches: int
    # Progress
    total_courses_completed: int
    total_labs_completed: int
    avg_progress_percent: float
    # Time
    total_learning_hours: float
    terminal_hours: float
    desktop_hours: float
    # Resource usage
    avg_storage_used_mb: float
    # Engagement
    daily_active_users: List[dict]  # [{date, count}]
    weekly_completions: List[dict]  # [{week, courses, labs}]


class UserAnalytics(BaseModel):
    """Detailed analytics for a single user."""
    user_id: UUID
    username: str
    full_name: Optional[str]
    # Overall progress
    courses_completed: int
    courses_in_progress: int
    total_courses_started: int
    labs_completed: int
    total_points: int
    current_streak: int
    longest_streak: int
    # Time
    total_learning_hours: float
    terminal_hours: float
    desktop_hours: float
    avg_session_duration_minutes: float
    # Course details
    course_progress: List[CourseProgress]
    # Activity
    activity_by_day: List[dict]  # [{date, minutes, labs}]
    skills_acquired: List[dict]  # [{skill, level}]
    # Engagement
    days_active_this_month: int
    last_activity: Optional[datetime]


class ProgressReport(BaseModel):
    """Progress report for a user or batch."""
    period_start: date
    period_end: date
    # Progress
    courses_started: int
    courses_completed: int
    labs_completed: int
    points_earned: int
    # Time
    total_hours: float
    terminal_hours: float
    desktop_hours: float
    # Skills
    skills_improved: List[dict]
    # Comparison
    vs_previous_period: Optional[dict]  # % change


class ActivityFeed(BaseModel):
    """Activity feed item."""
    id: UUID
    user_id: UUID
    username: str
    activity_type: str  # course_completed, lab_completed, skill_acquired, etc.
    title: str
    description: Optional[str]
    points_earned: Optional[int]
    timestamp: datetime


class ActivityFeedResponse(BaseModel):
    """Paginated activity feed."""
    items: List[ActivityFeed]
    total: int
    page: int
    page_size: int


# Comparison/benchmarking
class BenchmarkComparison(BaseModel):
    """Compare user's progress to others."""
    user_progress_percent: float
    batch_avg_percent: float
    org_avg_percent: float
    platform_avg_percent: float
    percentile_in_batch: int
    percentile_in_org: int


# Export
class ExportRequest(BaseModel):
    """Request to export analytics data."""
    format: str = "csv"  # csv, xlsx, json
    include_user_details: bool = True
    include_progress: bool = True
    include_activity: bool = True
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ExportResponse(BaseModel):
    """Response with export download URL."""
    download_url: str
    expires_at: datetime
    format: str
    rows: int
