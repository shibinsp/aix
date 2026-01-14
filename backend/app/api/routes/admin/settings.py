"""Admin settings management routes."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_super_admin
from app.models.user import User
from app.models.settings import SettingCategory
from app.schemas.admin import SettingResponse, SettingUpdate, SettingsGroup
from app.services.settings.settings_service import SettingsService
from app.services.audit.audit_service import AuditService

router = APIRouter(prefix="/settings")


@router.get("", response_model=list[SettingResponse])
async def get_all_settings(
    category: Optional[SettingCategory] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all settings, optionally filtered by category."""
    settings_service = SettingsService(db)

    if category:
        settings = await settings_service.get_settings_by_category(category)
    else:
        settings = await settings_service.get_all_settings()

    # Filter out super admin only settings for non-super admins
    if not current_user.is_super_admin:
        settings = [s for s in settings if not s.is_super_admin_only]

    # Mask sensitive values
    result = []
    for setting in settings:
        resp = SettingResponse.model_validate(setting)
        if setting.is_sensitive and setting.value:
            resp.value = "***hidden***"
        result.append(resp)

    return result


@router.get("/grouped", response_model=list[SettingsGroup])
async def get_settings_grouped(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all settings grouped by category."""
    settings_service = SettingsService(db)
    all_settings = await settings_service.get_all_settings()

    # Filter out super admin only settings for non-super admins
    if not current_user.is_super_admin:
        all_settings = [s for s in all_settings if not s.is_super_admin_only]

    # Group by category
    groups = {}
    for setting in all_settings:
        cat = setting.category
        if cat not in groups:
            groups[cat] = []

        resp = SettingResponse.model_validate(setting)
        if setting.is_sensitive and setting.value:
            resp.value = "***hidden***"
        groups[cat].append(resp)

    return [
        SettingsGroup(category=cat, settings=settings)
        for cat, settings in groups.items()
    ]


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific setting."""
    settings_service = SettingsService(db)
    setting = await settings_service.get_setting(key)

    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    if setting.is_super_admin_only and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")

    resp = SettingResponse.model_validate(setting)
    if setting.is_sensitive and setting.value:
        resp.value = "***hidden***"

    return resp


@router.patch("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    update: SettingUpdate,
    request: Request,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a setting value."""
    settings_service = SettingsService(db)
    audit_service = AuditService(db)

    setting = await settings_service.get_setting(key)
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")

    if setting.is_super_admin_only and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Super admin access required")

    old_value = setting.value

    try:
        updated = await settings_service.update_setting(
            key=key,
            value=update.value,
            updater=current_user,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

    # Audit log
    await audit_service.log_setting_change(
        actor=current_user,
        setting_key=key,
        old_value=old_value,
        new_value=update.value,
        is_sensitive=setting.is_sensitive,
        request=request,
    )

    resp = SettingResponse.model_validate(updated)
    if updated.is_sensitive:
        resp.value = "***hidden***"

    return resp


@router.post("/seed")
async def seed_settings(
    current_user: User = Depends(get_current_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Seed default settings (super admin only)."""
    settings_service = SettingsService(db)
    count = await settings_service.seed_defaults()
    return {"message": f"Seeded {count} settings"}
