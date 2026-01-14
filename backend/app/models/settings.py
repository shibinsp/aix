"""System settings and API key storage models."""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey, JSON, Enum, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.core.database import Base


def utcnow():
    return datetime.now(timezone.utc)


class SettingCategory(str, enum.Enum):
    """Categories for grouping system settings."""
    GENERAL = "general"
    AI_SERVICES = "ai_services"
    LABS = "labs"
    SECURITY = "security"
    RATE_LIMITS = "rate_limits"
    NOTIFICATIONS = "notifications"
    FEATURES = "features"


class SystemSetting(Base):
    """Stores system settings that can be changed at runtime."""
    __tablename__ = "system_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)  # JSON-encoded value
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    category = Column(Enum(SettingCategory), default=SettingCategory.GENERAL, index=True)

    # Metadata
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_sensitive = Column(Boolean, default=False)  # If true, mask in UI
    is_readonly = Column(Boolean, default=False)  # Some settings can only be set via env
    requires_restart = Column(Boolean, default=False)
    is_super_admin_only = Column(Boolean, default=False)  # Only super admin can modify

    # Validation
    validation_rules = Column(JSON, nullable=True)  # {"min": 1, "max": 100, "options": [...]}

    # Audit
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    updater = relationship("User", foreign_keys=[updated_by])

    def get_typed_value(self):
        """Return the value converted to its proper type."""
        if self.value is None:
            return None

        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            import json
            return json.loads(self.value)
        else:
            return self.value


class APIKeyStore(Base):
    """Securely stores API keys with encryption."""
    __tablename__ = "api_key_store"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service_name = Column(String(100), unique=True, nullable=False, index=True)

    # Encrypted key storage
    encrypted_key = Column(Text, nullable=True)  # AES-256 encrypted
    key_hint = Column(String(20), nullable=True)  # Last 4 chars for identification

    # Metadata
    label = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    documentation_url = Column(String(500), nullable=True)
    required = Column(Boolean, default=False)  # Is this key required for the service to work?

    # Status
    is_configured = Column(Boolean, default=False)
    is_valid = Column(Boolean, nullable=True)  # Result of last validation test
    last_validated_at = Column(DateTime(timezone=True), nullable=True)
    validation_error = Column(Text, nullable=True)

    # Audit
    updated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    created_at = Column(DateTime(timezone=True), default=utcnow)

    updater = relationship("User", foreign_keys=[updated_by])


# Default settings to seed into the database
DEFAULT_SETTINGS = [
    # AI Services
    {
        "key": "default_ai_model",
        "value": "mistral-large-latest",
        "value_type": "string",
        "category": SettingCategory.AI_SERVICES,
        "label": "Default AI Model",
        "description": "The default AI model to use for content generation",
        "validation_rules": {"options": ["gpt-4-turbo", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet", "mistral-large-latest", "gemini-pro"]},
    },
    {
        "key": "default_embedding_model",
        "value": "text-embedding-3-small",
        "value_type": "string",
        "category": SettingCategory.AI_SERVICES,
        "label": "Default Embedding Model",
        "description": "The default model for text embeddings",
    },

    # Rate Limits
    {
        "key": "rate_limit_per_minute",
        "value": "60",
        "value_type": "int",
        "category": SettingCategory.RATE_LIMITS,
        "label": "API Rate Limit (per minute)",
        "description": "Maximum API requests per minute per user",
        "validation_rules": {"min": 10, "max": 1000},
    },
    {
        "key": "rate_limit_auth_per_minute",
        "value": "10",
        "value_type": "int",
        "category": SettingCategory.RATE_LIMITS,
        "label": "Auth Rate Limit (per minute)",
        "description": "Maximum authentication attempts per minute",
        "validation_rules": {"min": 3, "max": 30},
    },

    # Labs
    {
        "key": "lab_timeout_minutes",
        "value": "120",
        "value_type": "int",
        "category": SettingCategory.LABS,
        "label": "Lab Session Timeout (minutes)",
        "description": "How long before an idle lab session is terminated",
        "validation_rules": {"min": 15, "max": 480},
    },
    {
        "key": "max_concurrent_labs",
        "value": "50",
        "value_type": "int",
        "category": SettingCategory.LABS,
        "label": "Max Concurrent Labs (total)",
        "description": "Maximum number of lab sessions running at once",
        "validation_rules": {"min": 10, "max": 500},
    },
    {
        "key": "max_concurrent_vms",
        "value": "10",
        "value_type": "int",
        "category": SettingCategory.LABS,
        "label": "Max Concurrent VMs (total)",
        "description": "Maximum number of VMs running at once",
        "validation_rules": {"min": 5, "max": 100},
    },
    {
        "key": "max_labs_per_user",
        "value": "3",
        "value_type": "int",
        "category": SettingCategory.LABS,
        "label": "Max Labs per User",
        "description": "Maximum concurrent labs per user",
        "validation_rules": {"min": 1, "max": 10},
    },
    {
        "key": "vm_default_memory",
        "value": "512M",
        "value_type": "string",
        "category": SettingCategory.LABS,
        "label": "Default VM Memory",
        "description": "Default memory allocation for VMs",
        "validation_rules": {"options": ["256M", "512M", "1G", "2G"]},
    },

    # Security
    {
        "key": "password_min_length",
        "value": "8",
        "value_type": "int",
        "category": SettingCategory.SECURITY,
        "label": "Minimum Password Length",
        "description": "Minimum required password length",
        "validation_rules": {"min": 8, "max": 32},
        "is_super_admin_only": True,
    },
    {
        "key": "session_timeout_hours",
        "value": "24",
        "value_type": "int",
        "category": SettingCategory.SECURITY,
        "label": "Session Timeout (hours)",
        "description": "How long before a user session expires",
        "validation_rules": {"min": 1, "max": 168},
        "is_super_admin_only": True,
    },
    {
        "key": "max_login_attempts",
        "value": "5",
        "value_type": "int",
        "category": SettingCategory.SECURITY,
        "label": "Max Login Attempts",
        "description": "Maximum failed login attempts before lockout",
        "validation_rules": {"min": 3, "max": 20},
        "is_super_admin_only": True,
    },

    # Features
    {
        "key": "enable_registration",
        "value": "true",
        "value_type": "bool",
        "category": SettingCategory.FEATURES,
        "label": "Enable User Registration",
        "description": "Allow new users to register",
    },
    {
        "key": "enable_ai_generation",
        "value": "true",
        "value_type": "bool",
        "category": SettingCategory.FEATURES,
        "label": "Enable AI Generation",
        "description": "Allow AI-powered course and lab generation",
    },
    {
        "key": "enable_vm_labs",
        "value": "true",
        "value_type": "bool",
        "category": SettingCategory.FEATURES,
        "label": "Enable VM Labs",
        "description": "Allow QEMU/KVM-based virtual machine labs",
    },
    {
        "key": "require_email_verification",
        "value": "false",
        "value_type": "bool",
        "category": SettingCategory.FEATURES,
        "label": "Require Email Verification",
        "description": "New users must verify their email before accessing the platform",
    },
]

# Default API key services to seed
DEFAULT_API_KEYS = [
    {
        "service_name": "openai",
        "label": "OpenAI API Key",
        "description": "API key for OpenAI GPT models (GPT-4, GPT-3.5)",
        "documentation_url": "https://platform.openai.com/api-keys",
        "required": False,
    },
    {
        "service_name": "anthropic",
        "label": "Anthropic API Key",
        "description": "API key for Anthropic Claude models",
        "documentation_url": "https://console.anthropic.com/settings/keys",
        "required": False,
    },
    {
        "service_name": "mistral",
        "label": "Mistral AI API Key",
        "description": "API key for Mistral AI models",
        "documentation_url": "https://console.mistral.ai/api-keys",
        "required": False,
    },
    {
        "service_name": "gemini",
        "label": "Google Gemini API Key",
        "description": "API key for Google Gemini models",
        "documentation_url": "https://aistudio.google.com/app/apikey",
        "required": False,
    },
    {
        "service_name": "unsplash",
        "label": "Unsplash Access Key",
        "description": "API key for Unsplash image search",
        "documentation_url": "https://unsplash.com/developers",
        "required": False,
    },
    {
        "service_name": "pexels",
        "label": "Pexels API Key",
        "description": "API key for Pexels image search",
        "documentation_url": "https://www.pexels.com/api/",
        "required": False,
    },
    {
        "service_name": "youtube",
        "label": "YouTube Data API Key",
        "description": "API key for YouTube video search",
        "documentation_url": "https://console.cloud.google.com/apis/credentials",
        "required": False,
    },
]
