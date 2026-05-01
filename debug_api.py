"""Debug script to check API validation errors."""

import asyncio
import json
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.db.session import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


async def debug_api():
    """Test API and print full response."""
    # Setup database
    test_engine = create_async_engine(TEST_DATABASE_URL)
    TestingSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession)

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        # Override database dependency
        async def override_get_db():
            yield session

        app.dependency_overrides[get_db] = override_get_db

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # 1. Register user
            print("\n1️⃣  REGISTERING USER...")
            reg_response = await client.post(
                "/api/v1/auth/register",
                json={
                    "username": "testuser",
                    "email": "test@example.com",
                    "password": "TestPass123",
                },
            )
            print(f"Status: {reg_response.status_code}")
            print(f"Response: {reg_response.json()}")

            # 2. Login
            print("\n2️⃣  LOGGING IN...")
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "username": "testuser",
                    "password": "TestPass123",
                },
            )
            print(f"Status: {login_response.status_code}")
            login_data = login_response.json()
            print(f"Response: {login_data}")

            if login_response.status_code != 200:
                print("❌ Login failed!")
                return

            token = login_data.get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            # 3. Create task
            print("\n3️⃣  CREATING TASK...")
            task_payload = {
                "title": "Test Task",
                "description": "Test Description",
                "status": "todo",
                "priority": "medium",
            }
            print(f"Payload: {json.dumps(task_payload, indent=2)}")

            task_response = await client.post(
                "/api/v1/tasks/",
                json=task_payload,
                headers=headers,
            )
            print(f"Status: {task_response.status_code}")
            print(f"Response: {json.dumps(task_response.json(), indent=2)}")

            if task_response.status_code == 422:
                print("\n❌ VALIDATION ERROR DETAILS:")
                print(json.dumps(task_response.json(), indent=2))

        app.dependency_overrides.clear()

    # Cleanup
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


if __name__ == "__main__":
    asyncio.run(debug_api())
