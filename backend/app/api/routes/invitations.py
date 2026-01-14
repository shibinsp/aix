"""API routes for organization invitations."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from uuid import UUID
import structlog

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_permission
from app.core.security import get_password_hash
from app.models.user import User
from app.models.admin import Permission
from app.models.organization import Organization, OrganizationMembership, OrgMemberRole, BatchMembership
from app.models.invitation import Invitation, InvitationStatus
from app.schemas.invitation import (
    InvitationCreate, BulkInvitationCreate, InvitationResponse, InvitationListResponse,
    PublicInvitationResponse, AcceptInvitationRequest, AcceptInvitationResponse,
    DeclineInvitationResponse, ResendInvitationRequest,
)

logger = structlog.get_logger()

router = APIRouter()


# ============================================================================
# INVITATION MANAGEMENT (ORG ADMIN)
# ============================================================================

@router.post("/organizations/{org_id}/invitations", response_model=InvitationResponse, status_code=status.HTTP_201_CREATED)
async def create_invitation(
    org_id: UUID,
    invite_data: InvitationCreate,
    current_user: User = Depends(require_permission(Permission.INVITE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """Create an invitation to join an organization."""
    # Verify organization exists and user has access
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not current_user.is_super_admin:
        membership = await db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == org_id,
                OrganizationMembership.user_id == current_user.id,
                OrganizationMembership.org_role.in_([OrgMemberRole.OWNER, OrgMemberRole.ADMIN])
            )
        )
        if not membership.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Only organization admins can create invitations")

    # Check if email already has a pending invitation
    existing = await db.execute(
        select(Invitation).where(
            Invitation.organization_id == org_id,
            Invitation.email == invite_data.email.lower(),
            Invitation.status == InvitationStatus.PENDING
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="An invitation is already pending for this email")

    # Check if user already exists and is in an organization
    existing_user = await db.execute(
        select(User).where(User.email == invite_data.email.lower())
    )
    user = existing_user.scalar_one_or_none()
    if user:
        existing_membership = await db.execute(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
        if existing_membership.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This user is already a member of an organization")

    # Create invitation
    invitation = Invitation.create_invitation(
        organization_id=str(org_id),
        email=invite_data.email,
        invited_by=str(current_user.id),
        role=OrgMemberRole(invite_data.role.value),
        batch_id=str(invite_data.batch_id) if invite_data.batch_id else None,
        full_name=invite_data.full_name,
        message=invite_data.message,
        expires_days=invite_data.expires_days,
    )

    db.add(invitation)
    await db.commit()
    await db.refresh(invitation)

    logger.info("Invitation created", invite_id=str(invitation.id), email=invite_data.email, org_id=str(org_id))

    return await _build_invitation_response(invitation, db)


@router.post("/organizations/{org_id}/invitations/bulk", response_model=List[InvitationResponse])
async def create_bulk_invitations(
    org_id: UUID,
    bulk_data: BulkInvitationCreate,
    current_user: User = Depends(require_permission(Permission.INVITE_CREATE)),
    db: AsyncSession = Depends(get_db),
):
    """Create multiple invitations at once."""
    org = await db.get(Organization, org_id)
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    created_invitations = []

    for invite_data in bulk_data.invitations:
        try:
            # Check for existing pending invitation
            existing = await db.execute(
                select(Invitation).where(
                    Invitation.organization_id == org_id,
                    Invitation.email == invite_data.email.lower(),
                    Invitation.status == InvitationStatus.PENDING
                )
            )
            if existing.scalar_one_or_none():
                continue  # Skip duplicates

            invitation = Invitation.create_invitation(
                organization_id=str(org_id),
                email=invite_data.email,
                invited_by=str(current_user.id),
                role=OrgMemberRole(invite_data.role.value),
                batch_id=str(invite_data.batch_id) if invite_data.batch_id else None,
                full_name=invite_data.full_name,
                message=invite_data.message,
                expires_days=invite_data.expires_days,
            )
            db.add(invitation)
            await db.flush()

            created_invitations.append(invitation)

        except Exception as e:
            logger.warning(f"Failed to create invitation for {invite_data.email}: {e}")
            continue

    await db.commit()

    logger.info("Bulk invitations created", count=len(created_invitations), org_id=str(org_id))

    return [await _build_invitation_response(inv, db) for inv in created_invitations]


@router.get("/organizations/{org_id}/invitations", response_model=InvitationListResponse)
async def list_organization_invitations(
    org_id: UUID,
    current_user: User = Depends(require_permission(Permission.INVITE_VIEW)),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = None,
):
    """List invitations for an organization."""
    query = select(Invitation).where(Invitation.organization_id == org_id)

    if status_filter:
        query = query.where(Invitation.status == InvitationStatus(status_filter))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Count pending
    pending_result = await db.execute(
        select(func.count(Invitation.id)).where(
            Invitation.organization_id == org_id,
            Invitation.status == InvitationStatus.PENDING
        )
    )
    pending_count = pending_result.scalar()

    # Paginate
    offset = (page - 1) * page_size
    query = query.order_by(Invitation.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    invitations = result.scalars().all()

    items = [await _build_invitation_response(inv, db) for inv in invitations]

    return InvitationListResponse(
        items=items,
        total=total,
        pending_count=pending_count,
        page=page,
        page_size=page_size,
    )


@router.delete("/invitations/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_invitation(
    invite_id: UUID,
    current_user: User = Depends(require_permission(Permission.INVITE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a pending invitation."""
    invitation = await db.get(Invitation, invite_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only cancel pending invitations")

    invitation.cancel()
    await db.commit()

    logger.info("Invitation cancelled", invite_id=str(invite_id))


@router.post("/invitations/{invite_id}/resend")
async def resend_invitation(
    invite_id: UUID,
    request: ResendInvitationRequest,
    current_user: User = Depends(require_permission(Permission.INVITE_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Resend an invitation email."""
    invitation = await db.get(Invitation, invite_id)
    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Can only resend pending invitations")

    # TODO: Actually send email
    if request.send_email:
        invitation.mark_reminder_sent()

    await db.commit()

    return {"message": "Invitation resent", "invite_id": str(invite_id)}


# ============================================================================
# PUBLIC INVITATION ENDPOINTS
# ============================================================================

@router.get("/invite/{token}", response_model=PublicInvitationResponse)
async def get_invitation_by_token(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Get invitation details by token (public endpoint for acceptance page)."""
    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.organization))
        .where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    return invitation.to_public_dict()


@router.post("/invite/{token}/accept", response_model=AcceptInvitationResponse)
async def accept_invitation(
    token: str,
    accept_data: AcceptInvitationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation and join the organization."""
    result = await db.execute(
        select(Invitation)
        .options(selectinload(Invitation.organization))
        .where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if not invitation.is_valid:
        if invitation.is_expired:
            invitation.mark_expired()
            await db.commit()
            raise HTTPException(status_code=400, detail="Invitation has expired")
        raise HTTPException(status_code=400, detail="Invitation is no longer valid")

    # Check if user already exists
    existing_user = await db.execute(
        select(User).where(User.email == invitation.email)
    )
    user = existing_user.scalar_one_or_none()

    if user:
        # Existing user - check if they're already in an org
        existing_membership = await db.execute(
            select(OrganizationMembership).where(OrganizationMembership.user_id == user.id)
        )
        if existing_membership.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="You are already a member of an organization")
    else:
        # New user - must provide username and password
        if not accept_data.username or not accept_data.password:
            raise HTTPException(
                status_code=400,
                detail="Username and password are required to create a new account"
            )

        # Check if username is taken
        username_check = await db.execute(
            select(User).where(User.username == accept_data.username)
        )
        if username_check.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Username is already taken")

        # Create new user
        user = User(
            email=invitation.email,
            username=accept_data.username,
            hashed_password=get_password_hash(accept_data.password),
            full_name=invitation.full_name,
            is_verified=True,  # Auto-verify invited users
        )
        db.add(user)
        await db.flush()

    # Create organization membership
    membership = OrganizationMembership(
        organization_id=invitation.organization_id,
        user_id=user.id,
        org_role=invitation.role,
        invited_by=invitation.invited_by,
    )
    db.add(membership)

    # Add to batch if specified
    if invitation.batch_id:
        batch_membership = BatchMembership(
            batch_id=invitation.batch_id,
            user_id=user.id,
        )
        db.add(batch_membership)

    # Mark invitation as accepted
    invitation.accept(str(user.id))

    await db.commit()

    logger.info("Invitation accepted", invite_id=str(invitation.id), user_id=str(user.id))

    return AcceptInvitationResponse(
        success=True,
        message="Welcome to the organization!",
        user_id=user.id,
        organization_id=invitation.organization_id,
        organization_name=invitation.organization.name if invitation.organization else "Unknown",
        redirect_url="/dashboard",
    )


@router.post("/invite/{token}/decline", response_model=DeclineInvitationResponse)
async def decline_invitation(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    """Decline an invitation."""
    result = await db.execute(
        select(Invitation).where(Invitation.token == token)
    )
    invitation = result.scalar_one_or_none()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != InvitationStatus.PENDING:
        raise HTTPException(status_code=400, detail="Invitation is no longer pending")

    invitation.decline()
    await db.commit()

    logger.info("Invitation declined", invite_id=str(invitation.id))

    return DeclineInvitationResponse(
        success=True,
        message="Invitation declined",
    )


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def _build_invitation_response(invitation: Invitation, db: AsyncSession) -> InvitationResponse:
    """Build invitation response with computed fields."""
    return InvitationResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        full_name=invitation.full_name,
        role=invitation.role,
        batch_id=invitation.batch_id,
        status=invitation.status,
        expires_at=invitation.expires_at,
        message=invitation.message,
        invited_by=invitation.invited_by,
        accepted_by=invitation.accepted_by,
        accepted_at=invitation.accepted_at,
        email_sent=invitation.email_sent,
        email_sent_at=invitation.email_sent_at,
        reminder_sent=invitation.reminder_sent,
        created_at=invitation.created_at,
        is_valid=invitation.is_valid,
        days_until_expiry=invitation.days_until_expiry,
        invite_url=invitation.invite_url,
    )
