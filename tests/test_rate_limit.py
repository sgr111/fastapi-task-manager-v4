import pytest


# ===== RATE LIMIT TESTS (4 tests) =====

@pytest.mark.asyncio
async def test_rate_limit_auth_endpoint(client):
    """Test authentication endpoints are rate limited."""
    # Make 31 login requests (limit is 30/minute)
    responses = []
    for i in range(31):
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": "testuser",
                "password": "TestPass123",
            },
        )
        responses.append(response)
    
    # First 30 should succeed (with 401 for invalid creds)
    for i in range(30):
        assert responses[i].status_code in [401, 409]  # Invalid creds or user not found
    
    # 31st should be rate limited (429)
    assert responses[30].status_code == 429
    assert "Rate limit exceeded" in responses[30].json()["error"]


@pytest.mark.asyncio
async def test_rate_limit_read_tasks(client, auth_headers, created_task):
    """Test read endpoints are rate limited (100/minute)."""
    # Make 101 requests (limit is 100/minute)
    responses = []
    for i in range(101):
        response = await client.get(
            f"/api/v1/tasks/{created_task['id']}",
            headers=auth_headers,
        )
        responses.append(response)
    
    # First 100 should succeed (200 OK)
    for i in range(100):
        assert responses[i].status_code == 200
    
    # 101st should be rate limited (429)
    assert responses[100].status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_write_tasks(client, auth_headers):
    """Test write endpoints are rate limited (30/minute)."""
    # Make 31 task creation requests (limit is 30/minute)
    responses = []
    for i in range(31):
        response = await client.post(
            "/api/v1/tasks/",
            json={"title": f"Task {i}"},
            headers=auth_headers,
        )
        responses.append(response)
    
    # First 30 should succeed (201 Created)
    for i in range(30):
        assert responses[i].status_code == 201
    
    # 31st should be rate limited (429)
    assert responses[30].status_code == 429


@pytest.mark.asyncio
async def test_rate_limit_different_users(client, registered_user, registered_user_2):
    """Test rate limits are per-IP/per-user (not global)."""
    # Get tokens for both users
    response1 = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    token1 = response1.json()["access_token"]
    
    response2 = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user_2["username"],
            "password": registered_user_2["password"],
        },
    )
    token2 = response2.json()["access_token"]
    
    # Make requests from both users
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}
    
    # Create 30 tasks from user 1
    for i in range(30):
        response = await client.post(
            "/api/v1/tasks/",
            json={"title": f"User1 Task {i}"},
            headers=headers1,
        )
        assert response.status_code == 201
    
    # User 1 should be rate limited on 31st
    response = await client.post(
        "/api/v1/tasks/",
        json={"title": "User1 Task 31"},
        headers=headers1,
    )
    assert response.status_code == 429
    
    # User 2 should still be able to create tasks (separate limit)
    response = await client.post(
        "/api/v1/tasks/",
        json={"title": "User2 Task 1"},
        headers=headers2,
    )
    assert response.status_code == 201  # Should succeed


@pytest.mark.asyncio
async def test_rate_limit_returns_429_status(client):
    """Test rate limit returns correct 429 status code."""
    # Make many requests to trigger rate limit
    for _ in range(31):
        await client.post(
            "/api/v1/auth/login",
            json={"username": "test", "password": "test"},
        )
    
    # Next request should be rate limited
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test", "password": "test"},
    )
    
    assert response.status_code == 429
    data = response.json()
    assert "error" in data
    assert "Rate limit exceeded" in data["error"]
