from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List
from functools import lru_cache
import json


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "CyberAIx"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    SERVER_HOST: str = "localhost"  # External host for access URLs (set via SERVER_HOST env)

    # Security - SECRET_KEY is required, no default
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_AUTH_PER_MINUTE: int = 10

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://cyberx:cyberx@localhost:5432/cyberx"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # AI Services
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    MISTRAL_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    DEFAULT_AI_MODEL: str = "mistral-large-latest"  # Using Mistral API
    DEFAULT_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # External Services (Images, Videos)
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    PEXELS_API_KEY: Optional[str] = None
    YOUTUBE_API_KEY: Optional[str] = None

    # Course Generation Settings
    MAX_LESSON_LENGTH: int = 3000
    MIN_LESSON_LENGTH: int = 1500
    GENERATION_TIMEOUT: int = 300  # seconds per lesson

    # RAG Settings
    VECTOR_DB_PATH: str = "./data/vector_db"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 5

    # Lab Settings
    LAB_NETWORK_PREFIX: str = "cyberx_lab_"
    LAB_TIMEOUT_MINUTES: int = 120
    MAX_CONCURRENT_LABS: int = 50

    # Kubernetes Lab Settings
    K8S_LAB_NAMESPACE: str = "cyberaix-labs"
    K8S_IN_CLUSTER: bool = False  # Set to True when running in Kubernetes
    K8S_POD_TIMEOUT: int = 120  # Seconds to wait for pod to be ready
    K8S_POD_TTL: int = 7200  # Pod lifetime in seconds (2 hours)

    # VM Settings (QEMU/KVM)
    LAB_VM_PATH: str = "./data/vms"  # Configurable via LAB_VM_PATH env
    LAB_TEMPLATE_PATH: str = "./data/lab_templates/alphaLinux"  # Configurable via LAB_TEMPLATE_PATH env
    WORKSPACE_BASE: str = "/home/alphha/courses"  # Workspace base path in containers
    VM_DEFAULT_MEMORY: str = "512M"
    VM_DEFAULT_CPUS: int = 1
    VM_DEFAULT_DISK_SIZE: str = "4G"
    MAX_CONCURRENT_VMS: int = 10

    # CORS (add production URLs via CORS_ORIGINS env var)
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # HTTPS
    FORCE_HTTPS: bool = False

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
