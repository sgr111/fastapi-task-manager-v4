"""
Rate Limiting Tests
====================
These tests run against the LIVE server (not test client) because:
- pytest client disables rate limiting for isolation
- Rate limiting requires a persistent session to accumulate request counts
- Uses httpx directly like verify_rate_limiting.py which is proven to work

Requirements:
    - FastAPI server must be running: uvicorn app.main:app --reload
    - Run separately: pytest tests/test_rate_limiting.py -v
"""

import pytest
import httpx
from datetime import datetime
import asyncio

BASE_URL = "http://localhost:8000"


def make_username():
    return f"ratetest_{int(datetime.now().timestamp())}"


@pytest.mark.asyncio
async def test_rate_limit_write_tasks_hit_at_31():
    """Test write endpoint rate limit hits at request #31 (30/minute limit)."""
    username = make_username()
    password = "RateTestPass123!"

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Register
        r = await client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password
        })
        assert r.status_code == 201, f"Registration failed: {r.json()}"

        # Login
        r = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        assert r.status_code == 200, f"Login failed: {r.json()}"
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Make 35 requests and track results
        results = []
        for i in range(1, 36):
            r = await client.post(
                "/api/v1/tasks/",
                json={"title": f"Rate Limit Task {i}"},
                headers=headers
            )
            results.append(r.status_code)
            if r.status_code == 429 and results.count(429) >= 3:
                break

        successful = results.count(201)
        rate_limited = results.count(429)
        rate_limit_hit_at = next((i + 1 for i, s in enumerate(results) if s == 429), None)

        assert successful >= 30, f"Expected 30 successful, got {successful}"
        assert rate_limited >= 1, f"Expected rate limiting, got none"
        assert rate_limit_hit_at == 31, f"Expected limit at #31, hit at #{rate_limit_hit_at}"


@pytest.mark.asyncio
async def test_rate_limit_returns_429_and_error_message():
    """Test that rate limit response has correct status and error message."""
    username = make_username()
    password = "RateTestPass123!"

    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Register and login
        await client.post("/api/v1/auth/register", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password
        })
        r = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Hit rate limit
        last_response = None
        for i in range(35):
            last_response = await client.post(
                "/api/v1/tasks/",
                json={"title": f"Task {i}"},
                headers=headers
            )
            if last_response.status_code == 429:
                break

        assert last_response.status_code == 429
        data = last_response.json()
        assert "error" in data
        assert "Rate limit exceeded" in data["error"]


@pytest.mark.asyncio
async def test_rate_limit_auth_endpoint():
    """Test auth endpoint rate limit (30/minute)."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        results = []
        for i in range(35):
            r = await client.post("/api/v1/auth/login", json={
                "username": "nonexistent",
                "password": "TestPass123"
            })
            results.append(r.status_code)
            if r.status_code == 429:
                break

        assert 429 in results, "Auth endpoint should be rate limited"
        rate_limit_hit_at = next((i + 1 for i, s in enumerate(results) if s == 429), None)
        assert rate_limit_hit_at <= 31, f"Should hit limit by request 31, hit at #{rate_limit_hit_at}"


@pytest.mark.asyncio
async def test_rate_limit_different_users_separate_limits():
    """Test that different users have separate rate limit quotas."""
    user1 = make_username()
    user2 = make_username() + "_b"
    password = "RateTestPass123!"

    
    await asyncio.sleep(61)      # Wait for previous test's rate limit to reset  
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Register both users
        for username in [user1, user2]:
            r = await client.post("/api/v1/auth/register", json={
                "username": username,
                "email": f"{username}@example.com",
                "password": password
            })
            assert r.status_code == 201

        # Login both users
        r1 = await client.post("/api/v1/auth/login", json={"username": user1, "password": password})
        r2 = await client.post("/api/v1/auth/login", json={"username": user2, "password": password})
        headers1 = {"Authorization": f"Bearer {r1.json()['access_token']}"}
        headers2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        # User 1 makes 30 requests (should all succeed)
        for i in range(30):
            r = await client.post(
                "/api/v1/tasks/",
                json={"title": f"User1 Task {i}"},
                headers=headers1
            )
            assert r.status_code == 201, f"User1 request {i+1} failed with {r.status_code}"

        # User 1 hits limit at 31st
        r = await client.post(
            "/api/v1/tasks/",
            json={"title": "User1 Task 31"},
            headers=headers1
        )
        assert r.status_code == 429, "User1 should be rate limited"

        # User 2 should still be free (separate limit)
        r = await client.post(
            "/api/v1/tasks/",
            json={"title": "User2 Task 1"},
            headers=headers2
        )
        assert r.status_code == 201, "User2 should not be affected by User1 rate limit"
