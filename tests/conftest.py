import pytest
import pytest_asyncio
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DATABASE_URL)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

if hasattr(app.state, "limiter"):
    app.state.limiter.enabled = False
    
@pytest_asyncio.fixture(scope="function", autouse=True)
async def setup_database():
    """Create and drop tables for each test."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    """Client with rate limiting DISABLED for tests."""
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    # Disable rate limiting by making limit() a no-op decorator
    def no_limit(*args, **kwargs):
        def decorator(func):
            return func
        return decorator

    with patch("app.core.limiter.limiter.limit", no_limit):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as c:
            yield c

    app.dependency_overrides.clear()


# ===== USER FIXTURES =====

@pytest_asyncio.fixture
async def registered_user(client):
    payload = {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPass123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


@pytest_asyncio.fixture
async def registered_user_2(client):
    payload = {
        "email": "test2@example.com",
        "username": "testuser2",
        "password": "TestPass456",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    return payload


# ===== TOKEN FIXTURES =====

@pytest_asyncio.fixture
async def tokens(client, registered_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
    }


@pytest_asyncio.fixture
async def auth_headers(tokens):
    return {"Authorization": f"Bearer {tokens['access_token']}"}


@pytest_asyncio.fixture
async def auth_headers_2(client, registered_user_2):
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user_2["username"],
            "password": registered_user_2["password"],
        },
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ===== TASK FIXTURES =====

@pytest_asyncio.fixture
async def created_task(client, auth_headers):
    response = await client.post(
        "/api/v1/tasks/",
        json={"title": "Test Task", "description": "Test Description"},
        headers=auth_headers,
    )
    assert response.status_code == 201, f"Expected 201 got {response.status_code}: {response.text}"
    return response.json()


@pytest_asyncio.fixture
async def created_completed_task(client, auth_headers):
    response = await client.post(
        "/api/v1/tasks/",
        json={"title": "Completed Task", "description": "Already done", "is_completed": True},
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def multiple_tasks(client, auth_headers):
    tasks = []
    for i in range(10):
        response = await client.post(
            "/api/v1/tasks/",
            json={
                "title": f"Task {i+1}",
                "description": f"Description for task {i+1}",
            },
            headers=auth_headers,
        )
        assert response.status_code == 201, f"Task {i+1}: Expected 201 got {response.status_code}: {response.text}"
        tasks.append(response.json())
    return tasks
