import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.infrastructure.database import Base, get_db
from app.main import app


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Setup the database schema once for the entire test session."""
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        await conn.execute(text("CREATE SCHEMA public;"))
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for a single test. Disposed after test."""
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    session_local = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_local() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def override_dependencies(db_session: AsyncSession):
    """Override get_db dependency in the app for testing."""

    async def _get_test_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(autouse=True)
async def clean_db():
    """Clean all tables in the database after each test."""
    yield
    # Create a fresh engine for clean up to avoid loop issues
    engine = create_async_engine(settings.DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE users, refresh_tokens, wallets, ledger_entries, "
                "organizations, organization_members, api_keys, worker_profiles, "
                "tasks, task_assignments, submissions, evidences, reputation_events, "
                "webhook_endpoints, webhook_deliveries, audit_events, idempotency_keys CASCADE;"
            )
        )
    await engine.dispose()


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTPX AsyncClient for testing the app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",  # type: ignore
    ) as ac:
        yield ac
