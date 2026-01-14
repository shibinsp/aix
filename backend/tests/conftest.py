"""Test configuration and fixtures."""
import pytest
import pytest_asyncio
import uuid as uuid_module
from typing import AsyncGenerator
from httpx import AsyncClient, ASGITransport
from sqlalchemy import event, TypeDecorator, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID, INET
from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.admin import UserRole


# Make SQLite understand PostgreSQL types by compiling to compatible types
def _compile_uuid(element, compiler, **kw):
    return "VARCHAR(36)"


def _compile_inet(element, compiler, **kw):
    return "VARCHAR(45)"  # IPv6 max length


SQLiteTypeCompiler.visit_UUID = _compile_uuid
SQLiteTypeCompiler.visit_INET = _compile_inet


# Monkey-patch the UUID type to handle string binding for SQLite
_original_uuid_bind_processor = PostgresUUID.bind_processor


def _patched_uuid_bind_processor(self, dialect):
    if dialect.name == 'sqlite':
        def process(value):
            if value is not None:
                if isinstance(value, uuid_module.UUID):
                    return str(value)
                return str(value)
            return value
        return process
    return _original_uuid_bind_processor(self, dialect)


PostgresUUID.bind_processor = _patched_uuid_bind_processor


# Also patch the result processor
_original_uuid_result_processor = PostgresUUID.result_processor


def _patched_uuid_result_processor(self, dialect, coltype):
    if dialect.name == 'sqlite':
        def process(value):
            if value is not None:
                if isinstance(value, uuid_module.UUID):
                    return value
                return uuid_module.UUID(value)
            return value
        return process
    return _original_uuid_result_processor(self, dialect, coltype)


PostgresUUID.result_processor = _patched_uuid_result_processor

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        username="testuser",
        hashed_password=get_password_hash("TestPass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    user = User(
        email="admin@example.com",
        username="adminuser",
        hashed_password=get_password_hash("AdminPass123"),
        is_active=True,
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {token}"}
