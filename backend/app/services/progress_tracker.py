"""Progress tracker for long-running operations."""
import asyncio
from datetime import datetime
from typing import Dict, Optional
from enum import Enum
import uuid


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class JobProgress:
    """Progress tracking for a job."""
    def __init__(self, job_id: str, total_steps: int, description: str):
        self.job_id = job_id
        self.total_steps = total_steps
        self.current_step = 0
        self.description = description
        self.status = JobStatus.PENDING
        self.current_task = ""
        self.error_message: Optional[str] = None
        self.result: Optional[Dict] = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None

    @property
    def percentage(self) -> int:
        """Calculate completion percentage."""
        if self.total_steps == 0:
            return 0
        return min(100, int((self.current_step / self.total_steps) * 100))

    def update(self, step: int, task: str = ""):
        """Update progress."""
        self.current_step = step
        self.current_task = task
        self.status = JobStatus.IN_PROGRESS
        self.updated_at = datetime.utcnow()

    def complete(self, result: Optional[Dict] = None):
        """Mark job as completed."""
        self.status = JobStatus.COMPLETED
        self.current_step = self.total_steps
        self.result = result
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def fail(self, error: str):
        """Mark job as failed."""
        self.status = JobStatus.FAILED
        self.error_message = error
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "percentage": self.percentage,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_task": self.current_task,
            "description": self.description,
            "error_message": self.error_message,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class ProgressTracker:
    """Global progress tracker for managing job progress."""

    def __init__(self):
        self._jobs: Dict[str, JobProgress] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def create_job(self, total_steps: int, description: str) -> str:
        """Create a new job and return its ID."""
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobProgress(job_id, total_steps, description)
        return job_id

    def get_job(self, job_id: str) -> Optional[JobProgress]:
        """Get job by ID."""
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, step: int, task: str = ""):
        """Update job progress."""
        job = self._jobs.get(job_id)
        if job:
            job.update(step, task)

    def complete_job(self, job_id: str, result: Optional[Dict] = None):
        """Mark job as completed."""
        job = self._jobs.get(job_id)
        if job:
            job.complete(result)

    def fail_job(self, job_id: str, error: str):
        """Mark job as failed."""
        job = self._jobs.get(job_id)
        if job:
            job.fail(error)

    async def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Remove jobs older than max_age_hours."""
        while True:
            await asyncio.sleep(3600)  # Run every hour
            cutoff = datetime.utcnow().timestamp() - (max_age_hours * 3600)

            to_remove = [
                job_id for job_id, job in self._jobs.items()
                if job.updated_at.timestamp() < cutoff
            ]

            for job_id in to_remove:
                del self._jobs[job_id]

    def start_cleanup(self):
        """Start the cleanup background task."""
        if not self._cleanup_task:
            self._cleanup_task = asyncio.create_task(self.cleanup_old_jobs())


# Global instance
progress_tracker = ProgressTracker()
