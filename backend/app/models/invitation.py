"""Invitation models for organization member invitations."""
import uuid
import enum
import secrets
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, DateTime,
    ForeignKey, Enum, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.organization import OrgMemberRole

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.organization import Organization, Batch


class InvitationStatus(str, enum.Enum):
    """Status of an invitation."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    DECLINED = "declined"


class Invitation(Base):
    """Invitation to join an organization."""
    __tablename__ = "invitations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Invitation token (for URL)
    token = Column(String(64), unique=True, nullable=False, index=True)

    # Invitee information
    email = Column(String(255), nullable=False, index=True)
    full_name = Column(String(255), nullable=True)

    # Role to assign upon acceptance
    role = Column(Enum(OrgMemberRole), default=OrgMemberRole.MEMBER, nullable=False)

    # Optional batch assignment
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("batches.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status tracking
    status = Column(Enum(InvitationStatus), default=InvitationStatus.PENDING, nullable=False)

    # Expiration
    expires_at = Column(DateTime(timezone=True), nullable=False)

    # Personal message from inviter
    message = Column(Text, nullable=True)

    # Tracking
    invited_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    accepted_by = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    accepted_at = Column(DateTime(timezone=True), nullable=True)

    # Email tracking
    email_sent = Column(Boolean, default=False, nullable=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent = Column(Boolean, default=False, nullable=False)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization", back_populates="invitations")
    batch = relationship("Batch")
    inviter = relationship("User", foreign_keys=[invited_by])
    acceptor = relationship("User", foreign_keys=[accepted_by])

    __table_args__ = (
        Index('ix_invitations_org_status', 'organization_id', 'status'),
        Index('ix_invitations_email_status', 'email', 'status'),
    )

    def __repr__(self):
        return f"<Invitation {self.email} to org={self.organization_id} status={self.status.value}>"

    @classmethod
    def generate_token(cls) -> str:
        """Generate a secure invitation token."""
        return secrets.token_urlsafe(48)

    @classmethod
    def create_invitation(
        cls,
        organization_id: str,
        email: str,
        invited_by: str,
        role: OrgMemberRole = OrgMemberRole.MEMBER,
        batch_id: str = None,
        full_name: str = None,
        message: str = None,
        expires_days: int = 7,
    ) -> "Invitation":
        """Create a new invitation."""
        return cls(
            organization_id=organization_id,
            email=email.lower().strip(),
            full_name=full_name,
            role=role,
            batch_id=batch_id,
            message=message,
            invited_by=invited_by,
            token=cls.generate_token(),
            expires_at=datetime.utcnow() + timedelta(days=expires_days),
        )

    @property
    def is_valid(self) -> bool:
        """Check if invitation is valid (pending and not expired)."""
        if self.status != InvitationStatus.PENDING:
            return False
        if datetime.utcnow() > self.expires_at.replace(tzinfo=None):
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Check if invitation has expired."""
        return datetime.utcnow() > self.expires_at.replace(tzinfo=None)

    @property
    def days_until_expiry(self) -> int:
        """Get days until expiration."""
        if self.is_expired:
            return 0
        delta = self.expires_at.replace(tzinfo=None) - datetime.utcnow()
        return max(0, delta.days)

    def accept(self, user_id: str) -> None:
        """Mark invitation as accepted."""
        self.status = InvitationStatus.ACCEPTED
        self.accepted_by = user_id
        self.accepted_at = datetime.utcnow()

    def cancel(self) -> None:
        """Cancel the invitation."""
        self.status = InvitationStatus.CANCELLED

    def decline(self) -> None:
        """Decline the invitation."""
        self.status = InvitationStatus.DECLINED

    def mark_expired(self) -> None:
        """Mark invitation as expired."""
        self.status = InvitationStatus.EXPIRED

    def mark_email_sent(self) -> None:
        """Mark that invitation email was sent."""
        self.email_sent = True
        self.email_sent_at = datetime.utcnow()

    def mark_reminder_sent(self) -> None:
        """Mark that reminder email was sent."""
        self.reminder_sent = True
        self.reminder_sent_at = datetime.utcnow()

    @property
    def invite_url(self) -> str:
        """Generate the invitation URL."""
        # Base URL should come from settings
        return f"/invite/{self.token}"

    def to_public_dict(self) -> dict:
        """Convert to dict for public API response (no sensitive data)."""
        return {
            "id": str(self.id),
            "organization_name": self.organization.name if self.organization else None,
            "organization_logo": self.organization.logo_url if self.organization else None,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value,
            "message": self.message,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_valid": self.is_valid,
            "days_until_expiry": self.days_until_expiry,
        }


class BulkImportJob(Base):
    """Track bulk user import jobs."""
    __tablename__ = "bulk_import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Job status
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed

    # File info
    filename = Column(String(255), nullable=True)
    file_size = Column(Integer, nullable=True)

    # Progress
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    successful_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)

    # Results
    errors = Column(Text, nullable=True)  # JSON list of errors
    created_user_ids = Column(Text, nullable=True)  # JSON list of created user IDs

    # Options
    send_invitations = Column(Boolean, default=True, nullable=False)
    default_role = Column(Enum(OrgMemberRole), default=OrgMemberRole.MEMBER, nullable=False)
    default_batch_id = Column(UUID(as_uuid=True), ForeignKey("batches.id", ondelete="SET NULL"), nullable=True)

    # Tracking
    started_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    organization = relationship("Organization")
    user = relationship("User", foreign_keys=[started_by])
    batch = relationship("Batch")

    def __repr__(self):
        return f"<BulkImportJob org={self.organization_id} status={self.status}>"

    @property
    def progress_percent(self) -> int:
        """Calculate progress percentage."""
        if self.total_rows == 0:
            return 0
        return int((self.processed_rows / self.total_rows) * 100)

    def start_processing(self) -> None:
        """Mark job as processing."""
        self.status = "processing"
        self.started_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark job as completed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    def fail(self, error: str) -> None:
        """Mark job as failed."""
        self.status = "failed"
        self.errors = error
        self.completed_at = datetime.utcnow()

    def add_success(self, user_id: str) -> None:
        """Record a successful import."""
        self.processed_rows += 1
        self.successful_rows += 1
        # Add to created user IDs
        import json
        ids = json.loads(self.created_user_ids or "[]")
        ids.append(user_id)
        self.created_user_ids = json.dumps(ids)

    def add_failure(self, row_num: int, error: str) -> None:
        """Record a failed import row."""
        self.processed_rows += 1
        self.failed_rows += 1
        # Add to errors
        import json
        errors = json.loads(self.errors or "[]")
        errors.append({"row": row_num, "error": error})
        self.errors = json.dumps(errors)
