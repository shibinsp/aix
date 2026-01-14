"""Settings service for managing system settings and API keys."""
import json
from datetime import datetime, timezone
from typing import Optional, Any, Dict, List
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.settings import (
    SystemSetting,
    APIKeyStore,
    SettingCategory,
    DEFAULT_SETTINGS,
    DEFAULT_API_KEYS,
)
from app.models.user import User
from app.core.encryption import encrypt_api_key, decrypt_api_key, get_key_hint


def utcnow():
    return datetime.now(timezone.utc)


class SettingsService:
    """Service for managing system settings."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._cache: Dict[str, Any] = {}

    async def get_setting(self, key: str) -> Optional[SystemSetting]:
        """Get a setting by key."""
        result = await self.db.execute(
            select(SystemSetting).where(SystemSetting.key == key)
        )
        return result.scalar_one_or_none()

    async def get_value(self, key: str, default: Any = None) -> Any:
        """Get the typed value of a setting."""
        setting = await self.get_setting(key)
        if setting:
            return setting.get_typed_value()
        return default

    async def get_all_settings(self) -> List[SystemSetting]:
        """Get all settings."""
        result = await self.db.execute(
            select(SystemSetting).order_by(SystemSetting.category, SystemSetting.key)
        )
        return list(result.scalars().all())

    async def get_settings_by_category(
        self, category: SettingCategory
    ) -> List[SystemSetting]:
        """Get all settings in a category."""
        result = await self.db.execute(
            select(SystemSetting)
            .where(SystemSetting.category == category)
            .order_by(SystemSetting.key)
        )
        return list(result.scalars().all())

    async def update_setting(
        self,
        key: str,
        value: str,
        updater: User,
    ) -> Optional[SystemSetting]:
        """Update a setting value."""
        setting = await self.get_setting(key)
        if not setting:
            return None

        if setting.is_readonly:
            raise ValueError(f"Setting '{key}' is read-only")

        if setting.is_super_admin_only and not updater.is_super_admin:
            raise PermissionError(f"Setting '{key}' requires super admin privileges")

        # Validate value based on type
        self._validate_value(value, setting.value_type, setting.validation_rules)

        setting.value = value
        setting.updated_by = updater.id
        setting.updated_at = utcnow()

        await self.db.commit()
        await self.db.refresh(setting)

        # Clear cache
        self._cache.pop(key, None)

        return setting

    def _validate_value(
        self, value: str, value_type: str, validation_rules: Optional[Dict]
    ) -> None:
        """Validate a setting value."""
        if value_type == "int":
            try:
                int_val = int(value)
                if validation_rules:
                    if "min" in validation_rules and int_val < validation_rules["min"]:
                        raise ValueError(
                            f"Value must be at least {validation_rules['min']}"
                        )
                    if "max" in validation_rules and int_val > validation_rules["max"]:
                        raise ValueError(
                            f"Value must be at most {validation_rules['max']}"
                        )
            except ValueError as e:
                if "must be" in str(e):
                    raise
                raise ValueError(f"Invalid integer value: {value}")

        elif value_type == "float":
            try:
                float(value)
            except ValueError:
                raise ValueError(f"Invalid float value: {value}")

        elif value_type == "bool":
            if value.lower() not in ("true", "false", "1", "0", "yes", "no"):
                raise ValueError(f"Invalid boolean value: {value}")

        elif value_type == "json":
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise ValueError(f"Invalid JSON value: {value}")

        if validation_rules and "options" in validation_rules:
            if value not in validation_rules["options"]:
                raise ValueError(
                    f"Value must be one of: {validation_rules['options']}"
                )

    async def seed_defaults(self) -> int:
        """Seed default settings if they don't exist."""
        count = 0
        for setting_data in DEFAULT_SETTINGS:
            existing = await self.get_setting(setting_data["key"])
            if not existing:
                setting = SystemSetting(
                    key=setting_data["key"],
                    value=setting_data.get("value"),
                    value_type=setting_data.get("value_type", "string"),
                    category=setting_data.get("category", SettingCategory.GENERAL),
                    label=setting_data["label"],
                    description=setting_data.get("description"),
                    is_sensitive=setting_data.get("is_sensitive", False),
                    is_readonly=setting_data.get("is_readonly", False),
                    requires_restart=setting_data.get("requires_restart", False),
                    is_super_admin_only=setting_data.get("is_super_admin_only", False),
                    validation_rules=setting_data.get("validation_rules"),
                    created_at=utcnow(),
                )
                self.db.add(setting)
                count += 1

        if count > 0:
            await self.db.commit()

        return count


class APIKeyService:
    """Service for managing API keys."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_key_info(self, service_name: str) -> Optional[APIKeyStore]:
        """Get API key info (without decrypted key)."""
        result = await self.db.execute(
            select(APIKeyStore).where(APIKeyStore.service_name == service_name)
        )
        return result.scalar_one_or_none()

    async def get_all_keys(self) -> List[APIKeyStore]:
        """Get all API key entries."""
        result = await self.db.execute(
            select(APIKeyStore).order_by(APIKeyStore.service_name)
        )
        return list(result.scalars().all())

    async def get_decrypted_key(self, service_name: str) -> Optional[str]:
        """Get the decrypted API key for a service."""
        key_store = await self.get_key_info(service_name)
        if not key_store or not key_store.encrypted_key:
            return None
        return decrypt_api_key(key_store.encrypted_key)

    async def set_key(
        self,
        service_name: str,
        api_key: str,
        updater: User,
    ) -> APIKeyStore:
        """Set or update an API key."""
        key_store = await self.get_key_info(service_name)

        if not key_store:
            raise ValueError(f"Unknown service: {service_name}")

        key_store.encrypted_key = encrypt_api_key(api_key)
        key_store.key_hint = get_key_hint(api_key)
        key_store.is_configured = True
        key_store.is_valid = None  # Reset validation status
        key_store.validation_error = None
        key_store.updated_by = updater.id
        key_store.updated_at = utcnow()

        await self.db.commit()
        await self.db.refresh(key_store)

        return key_store

    async def delete_key(self, service_name: str, updater: User) -> bool:
        """Delete an API key."""
        key_store = await self.get_key_info(service_name)

        if not key_store:
            return False

        key_store.encrypted_key = None
        key_store.key_hint = None
        key_store.is_configured = False
        key_store.is_valid = None
        key_store.validation_error = None
        key_store.updated_by = updater.id
        key_store.updated_at = utcnow()

        await self.db.commit()
        return True

    async def validate_key(self, service_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate an API key by testing it against the service.

        Returns:
            Tuple of (is_valid, error_message)
        """
        key_store = await self.get_key_info(service_name)

        if not key_store or not key_store.encrypted_key:
            return False, "No key configured"

        api_key = decrypt_api_key(key_store.encrypted_key)
        if not api_key:
            return False, "Failed to decrypt key"

        # Test the key based on service
        is_valid, error = await self._test_api_key(service_name, api_key)

        # Update validation status
        key_store.is_valid = is_valid
        key_store.last_validated_at = utcnow()
        key_store.validation_error = error

        await self.db.commit()

        return is_valid, error

    async def _test_api_key(
        self, service_name: str, api_key: str
    ) -> tuple[bool, Optional[str]]:
        """Test an API key against its service."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                if service_name == "openai":
                    response = await client.get(
                        "https://api.openai.com/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"API returned {response.status_code}"

                elif service_name == "anthropic":
                    # Anthropic doesn't have a simple validation endpoint
                    # We just check format
                    if api_key.startswith("sk-ant-"):
                        return True, None
                    return False, "Invalid key format (should start with sk-ant-)"

                elif service_name == "mistral":
                    response = await client.get(
                        "https://api.mistral.ai/v1/models",
                        headers={"Authorization": f"Bearer {api_key}"},
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"API returned {response.status_code}"

                elif service_name == "gemini":
                    response = await client.get(
                        f"https://generativelanguage.googleapis.com/v1/models?key={api_key}",
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"API returned {response.status_code}"

                elif service_name == "unsplash":
                    response = await client.get(
                        "https://api.unsplash.com/photos/random",
                        headers={"Authorization": f"Client-ID {api_key}"},
                    )
                    if response.status_code in (200, 403):  # 403 = rate limited but valid
                        return True, None
                    return False, f"API returned {response.status_code}"

                elif service_name == "pexels":
                    response = await client.get(
                        "https://api.pexels.com/v1/curated?per_page=1",
                        headers={"Authorization": api_key},
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"API returned {response.status_code}"

                elif service_name == "youtube":
                    response = await client.get(
                        f"https://www.googleapis.com/youtube/v3/videos?part=id&id=dQw4w9WgXcQ&key={api_key}",
                    )
                    if response.status_code == 200:
                        return True, None
                    return False, f"API returned {response.status_code}"

                else:
                    return True, None  # Unknown service, assume valid

        except Exception as e:
            return False, str(e)

    async def seed_defaults(self) -> int:
        """Seed default API key entries if they don't exist."""
        count = 0
        for key_data in DEFAULT_API_KEYS:
            existing = await self.get_key_info(key_data["service_name"])
            if not existing:
                key_store = APIKeyStore(
                    service_name=key_data["service_name"],
                    label=key_data["label"],
                    description=key_data.get("description"),
                    documentation_url=key_data.get("documentation_url"),
                    required=key_data.get("required", False),
                    is_configured=False,
                    created_at=utcnow(),
                )
                self.db.add(key_store)
                count += 1

        if count > 0:
            await self.db.commit()

        return count
