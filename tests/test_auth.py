import pytest


# ===== REGISTRATION TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_register_success(client):
    """Test successful user registration."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "TestPass123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert "password" not in data  # Password never returned
    assert "id" in data
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_register_duplicate_email(client, registered_user):
    """Test registration fails with duplicate email."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": registered_user["email"],
            "username": "differentuser",
            "password": "TestPass123",
        },
    )
    assert response.status_code == 409
    assert "Email already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client, registered_user):
    """Test registration fails with duplicate username."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "different@example.com",
            "username": registered_user["username"],
            "password": "TestPass123",
        },
    )
    assert response.status_code == 409
    assert "Username already taken" in response.json()["detail"]


# ===== PASSWORD VALIDATION TESTS (2 tests) =====

@pytest.mark.asyncio
async def test_register_weak_password(client):
    """Test registration fails with weak password (no uppercase)."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpass123",  # No uppercase
        },
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_register_short_password(client):
    """Test registration fails with too short password."""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "Test12",  # Only 6 chars
        },
    )
    assert response.status_code == 422


# ===== LOGIN TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_login_success(client, registered_user):
    """Test successful login returns both tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": registered_user["password"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, registered_user):
    """Test login fails with wrong password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": registered_user["username"],
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):
    """Test login fails with nonexistent user."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "ghostuser",
            "password": "TestPass123",
        },
    )
    assert response.status_code == 401


# ===== REFRESH TOKEN TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_refresh_token_success(client, tokens):
    """Test refresh token endpoint returns new access token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["access_token"] != tokens["access_token"]  # Different token


@pytest.mark.asyncio
async def test_refresh_token_invalid(client):
    """Test refresh token endpoint fails with invalid token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_with_access_token_fails(client, tokens):
    """Test refresh endpoint fails when using access token instead."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["access_token"]},  # Wrong token type
    )
    assert response.status_code == 401
    assert "Invalid or expired refresh token" in response.json()["detail"]
