"""Tests for task endpoints."""

import pytest
from httpx import AsyncClient


# ===== TASK CREATION TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_create_task_success(client, auth_headers):
    """Test successful task creation."""
    response = await client.post(
        "/api/v1/tasks/",
        json={
            "title": "New Task",
            "description": "Task description",
            "status": "todo",
            "priority": "medium",
            "metadata": {"priority": "high", "tags": ["urgent"]},
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Task"
    assert data["description"] == "Task description"
    assert data["status"] == "todo"
    assert data["priority"] == "medium"
    assert data["metadata"] == {"priority": "high", "tags": ["urgent"]}
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_task_minimal(client, auth_headers):
    """Test task creation with only required fields."""
    response = await client.post(
        "/api/v1/tasks/",
        json={"title": "Minimal Task"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Minimal Task"
    assert data["status"] == "todo"  # Default value
    assert data["priority"] == "medium"  # Default value
    assert "id" in data


@pytest.mark.asyncio
async def test_create_task_missing_title(client, auth_headers):
    """Test task creation fails without title."""
    response = await client.post(
        "/api/v1/tasks/",
        json={"description": "No title"},
        headers=auth_headers,
    )
    assert response.status_code == 422


# ===== TASK RETRIEVAL TESTS (4 tests) =====

@pytest.mark.asyncio
async def test_list_tasks_pagination_default(client, auth_headers, multiple_tasks):
    """Test listing tasks with default pagination."""
    response = await client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "skip" in data
    assert "limit" in data
    assert len(data["items"]) <= 10


@pytest.mark.asyncio
async def test_list_tasks_pagination_custom(client, auth_headers, multiple_tasks):
    """Test listing tasks with custom pagination."""
    response = await client.get(
        "/api/v1/tasks/?skip=5&limit=5",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["skip"] == 5
    assert data["limit"] == 5


@pytest.mark.asyncio
async def test_list_tasks_pagination_max_limit(client, auth_headers, multiple_tasks):
    """Test listing tasks respects max limit."""
    response = await client.get(
        "/api/v1/tasks/?limit=1000",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] <= 100  # Max limit


@pytest.mark.asyncio
async def test_get_task_success(client, auth_headers, created_task):
    """Test retrieving a specific task."""
    task_id = created_task["id"]
    response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == created_task["title"]


@pytest.mark.asyncio
async def test_get_task_not_found(client, auth_headers):
    """Test retrieving non-existent task."""
    response = await client.get("/api/v1/tasks/99999", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_other_user_task_forbidden(client, auth_headers, auth_headers_2, created_task):
    """Test user cannot access another user's task."""
    task_id = created_task["id"]
    response = await client.get(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers_2,
    )
    assert response.status_code == 403


# ===== TASK UPDATE TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_update_task_success(client, auth_headers, created_task):
    """Test updating a task."""
    task_id = created_task["id"]
    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "title": "Updated Task",
            "status": "in_progress",
            "priority": "high",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"


@pytest.mark.asyncio
async def test_update_task_metadata(client, auth_headers, created_task):
    """Test updating task metadata."""
    task_id = created_task["id"]
    response = await client.put(
        f"/api/v1/tasks/{task_id}",
        json={
            "metadata": {"tags": ["updated"], "assignee": "john"},
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"] == {"tags": ["updated"], "assignee": "john"}


@pytest.mark.asyncio
async def test_update_nonexistent_task(client, auth_headers):
    """Test updating non-existent task."""
    response = await client.put(
        "/api/v1/tasks/99999",
        json={"title": "Updated"},
        headers=auth_headers,
    )
    assert response.status_code == 404


# ===== TASK DELETION TESTS (2 tests) =====

@pytest.mark.asyncio
async def test_delete_task_soft_delete(client, auth_headers, created_task):
    """Test task soft delete."""
    task_id = created_task["id"]
    response = await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_deleted_task_excluded_from_list(client, auth_headers, created_task):
    """Test deleted tasks don't appear in list."""
    task_id = created_task["id"]
    
    # Delete the task
    await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    
    # Get list - deleted task should not appear
    response = await client.get("/api/v1/tasks/", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    task_ids = [task["id"] for task in data["items"]]
    assert task_id not in task_ids


@pytest.mark.asyncio
async def test_delete_nonexistent_task(client, auth_headers):
    """Test deleting non-existent task."""
    response = await client.delete(
        "/api/v1/tasks/99999",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ===== AUDIT LOG TESTS (3 tests) =====

@pytest.mark.asyncio
async def test_get_task_audit_log_after_creation(client, auth_headers, created_task):
    """Test audit log records task creation."""
    task_id = created_task["id"]
    response = await client.get(
        f"/api/v1/tasks/{task_id}/audit",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["action"] == "CREATE"
    assert data[0]["task_id"] == task_id


@pytest.mark.asyncio
async def test_audit_log_tracks_updates(client, auth_headers, created_task):
    """Test audit log records task updates."""
    task_id = created_task["id"]
    
    # Update the task
    await client.put(
        f"/api/v1/tasks/{task_id}",
        json={"status": "done"},
        headers=auth_headers,
    )
    
    # Check audit log
    response = await client.get(
        f"/api/v1/tasks/{task_id}/audit",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert data[-1]["action"] == "UPDATE"


@pytest.mark.asyncio
async def test_audit_log_tracks_deletions(client, auth_headers, created_task):
    """Test audit log records task deletions."""
    task_id = created_task["id"]
    
    # Delete the task
    await client.delete(
        f"/api/v1/tasks/{task_id}",
        headers=auth_headers,
    )
    
    # Check audit log
    response = await client.get(
        f"/api/v1/tasks/{task_id}/audit",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    assert data[-1]["action"] == "DELETE"