"""
Test Suite for Task Management API
Complete CRUD operation tests with pytest
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from main import app, get_session, Task, TaskCreate, TaskStatus, TaskPriority, TaskRead


# ============================================================================
# DATABASE SETUP FOR TESTING
# ============================================================================

@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with overridden database dependency."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns 200 with correct data."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data


# ============================================================================
# CREATE TASK TESTS
# ============================================================================

class TestCreateTask:
    """Test task creation endpoint."""

    def test_create_task_minimal(self, client: TestClient):
        """Test creating a task with only required fields."""
        response = client.post(
            "/tasks",
            json={"title": "Test Task"}
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Task"
        assert data["status"] == "todo"
        assert data["priority"] == "medium"
        assert data["id"] is not None
        assert data["description"] is None
        assert data["due_date"] is None

    def test_create_task_full(self, client: TestClient):
        """Test creating a task with all fields."""
        task_data = {
            "title": "Complete Project",
            "description": "Finish the FastAPI project",
            "status": "in_progress",
            "priority": "high",
            "due_date": "2026-02-01T00:00:00"
        }
        response = client.post("/tasks", json=task_data)
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Complete Project"
        assert data["description"] == "Finish the FastAPI project"
        assert data["status"] == "in_progress"
        assert data["priority"] == "high"

    def test_create_task_invalid_title_empty(self, client: TestClient):
        """Test creating a task with empty title fails."""
        response = client.post(
            "/tasks",
            json={"title": ""}
        )
        assert response.status_code == 422

    def test_create_task_invalid_status(self, client: TestClient):
        """Test creating a task with invalid status fails."""
        response = client.post(
            "/tasks",
            json={"title": "Test", "status": "invalid_status"}
        )
        assert response.status_code == 422

    def test_create_task_invalid_priority(self, client: TestClient):
        """Test creating a task with invalid priority fails."""
        response = client.post(
            "/tasks",
            json={"title": "Test", "priority": "invalid_priority"}
        )
        assert response.status_code == 422

    def test_create_multiple_tasks(self, client: TestClient):
        """Test creating multiple tasks."""
        tasks = [
            {"title": "Task 1", "priority": "low"},
            {"title": "Task 2", "priority": "medium"},
            {"title": "Task 3", "priority": "high"},
        ]
        responses = []
        for task in tasks:
            response = client.post("/tasks", json=task)
            assert response.status_code == 201
            responses.append(response.json())

        assert len(responses) == 3
        assert responses[0]["id"] != responses[1]["id"]
        assert responses[1]["id"] != responses[2]["id"]


# ============================================================================
# READ/LIST TASKS TESTS
# ============================================================================

class TestListTasks:
    """Test task listing endpoint."""

    def test_list_tasks_empty(self, client: TestClient):
        """Test listing tasks when none exist."""
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_tasks_with_data(self, client: TestClient):
        """Test listing tasks with data."""
        # Create tasks
        for i in range(3):
            client.post("/tasks", json={"title": f"Task {i+1}"})

        # List tasks
        response = client.get("/tasks")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(isinstance(task, dict) for task in data)

    def test_list_tasks_with_pagination(self, client: TestClient):
        """Test listing tasks with pagination."""
        # Create 10 tasks
        for i in range(10):
            client.post("/tasks", json={"title": f"Task {i+1}"})

        # List first 5
        response = client.get("/tasks?skip=0&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

        # List next 5
        response = client.get("/tasks?skip=5&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_list_tasks_filter_by_status(self, client: TestClient):
        """Test filtering tasks by status."""
        # Create tasks with different statuses
        client.post("/tasks", json={"title": "Todo Task", "status": "todo"})
        client.post("/tasks", json={"title": "In Progress Task", "status": "in_progress"})
        client.post("/tasks", json={"title": "Done Task", "status": "done"})

        # Filter by status
        response = client.get("/tasks?status_filter=todo")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "todo"

    def test_list_tasks_filter_by_priority(self, client: TestClient):
        """Test filtering tasks by priority."""
        # Create tasks with different priorities
        client.post("/tasks", json={"title": "Low Priority", "priority": "low"})
        client.post("/tasks", json={"title": "High Priority", "priority": "high"})

        # Filter by priority
        response = client.get("/tasks?priority_filter=high")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "high"

    def test_list_tasks_filter_by_both(self, client: TestClient):
        """Test filtering tasks by both status and priority."""
        # Create tasks
        client.post("/tasks", json={
            "title": "Task 1",
            "status": "todo",
            "priority": "low"
        })
        client.post("/tasks", json={
            "title": "Task 2",
            "status": "todo",
            "priority": "high"
        })

        # Filter
        response = client.get("/tasks?status_filter=todo&priority_filter=high")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "high"


# ============================================================================
# GET SPECIFIC TASK TESTS
# ============================================================================

class TestGetTask:
    """Test getting a specific task endpoint."""

    def test_get_task_exists(self, client: TestClient):
        """Test getting an existing task."""
        # Create task
        create_response = client.post("/tasks", json={"title": "Test Task"})
        task_id = create_response.json()["id"]

        # Get task
        response = client.get(f"/tasks/{task_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == "Test Task"

    def test_get_task_not_found(self, client: TestClient):
        """Test getting a non-existent task."""
        response = client.get("/tasks/999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_task_invalid_id(self, client: TestClient):
        """Test getting task with invalid ID format."""
        response = client.get("/tasks/invalid")
        assert response.status_code == 422

    def test_get_task_preserves_data(self, client: TestClient):
        """Test that getting task preserves all data."""
        task_data = {
            "title": "Important Task",
            "description": "This is important",
            "status": "in_progress",
            "priority": "urgent"
        }
        create_response = client.post("/tasks", json=task_data)
        task_id = create_response.json()["id"]

        response = client.get(f"/tasks/{task_id}")
        data = response.json()
        assert data["title"] == task_data["title"]
        assert data["description"] == task_data["description"]
        assert data["status"] == task_data["status"]
        assert data["priority"] == task_data["priority"]


# ============================================================================
# UPDATE TASK TESTS
# ============================================================================

class TestUpdateTask:
    """Test task update endpoint."""

    def test_update_task_title(self, client: TestClient):
        """Test updating only the task title."""
        create_response = client.post("/tasks", json={"title": "Original Title"})
        task_id = create_response.json()["id"]

        response = client.put(
            f"/tasks/{task_id}",
            json={"title": "Updated Title"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"

    def test_update_task_status(self, client: TestClient):
        """Test updating task status."""
        create_response = client.post("/tasks", json={"title": "Test"})
        task_id = create_response.json()["id"]

        response = client.put(
            f"/tasks/{task_id}",
            json={"status": "done"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["completed_at"] is not None

    def test_update_task_priority(self, client: TestClient):
        """Test updating task priority."""
        create_response = client.post("/tasks", json={"title": "Test"})
        task_id = create_response.json()["id"]

        response = client.put(
            f"/tasks/{task_id}",
            json={"priority": "urgent"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "urgent"

    def test_update_task_multiple_fields(self, client: TestClient):
        """Test updating multiple fields at once."""
        create_response = client.post("/tasks", json={"title": "Original"})
        task_id = create_response.json()["id"]

        update_data = {
            "title": "Updated",
            "description": "New description",
            "status": "in_progress",
            "priority": "high"
        }
        response = client.put(f"/tasks/{task_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]
        assert data["priority"] == update_data["priority"]

    def test_update_task_not_found(self, client: TestClient):
        """Test updating non-existent task."""
        response = client.put("/tasks/999", json={"title": "New"})
        assert response.status_code == 404

    def test_update_sets_updated_at(self, client: TestClient):
        """Test that updating sets updated_at timestamp."""
        create_response = client.post("/tasks", json={"title": "Test"})
        created_at = create_response.json()["created_at"]
        task_id = create_response.json()["id"]

        # Wait to ensure different timestamps
        import time
        time.sleep(0.1)

        response = client.put(f"/tasks/{task_id}", json={"title": "Updated"})
        updated_at = response.json()["updated_at"]
        assert updated_at > created_at

    def test_update_invalid_status(self, client: TestClient):
        """Test updating task with invalid status."""
        create_response = client.post("/tasks", json={"title": "Test"})
        task_id = create_response.json()["id"]

        response = client.put(f"/tasks/{task_id}", json={"status": "invalid"})
        assert response.status_code == 422


# ============================================================================
# DELETE TASK TESTS
# ============================================================================

class TestDeleteTask:
    """Test task deletion endpoint."""

    def test_delete_task_exists(self, client: TestClient):
        """Test deleting an existing task."""
        create_response = client.post("/tasks", json={"title": "Delete Me"})
        task_id = create_response.json()["id"]

        response = client.delete(f"/tasks/{task_id}")
        assert response.status_code == 204

        # Verify it's deleted
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 404

    def test_delete_task_not_found(self, client: TestClient):
        """Test deleting non-existent task."""
        response = client.delete("/tasks/999")
        assert response.status_code == 404

    def test_delete_task_removes_from_list(self, client: TestClient):
        """Test that deleting removes task from list."""
        # Create 3 tasks
        ids = []
        for i in range(3):
            response = client.post("/tasks", json={"title": f"Task {i+1}"})
            ids.append(response.json()["id"])

        # Delete first task
        client.delete(f"/tasks/{ids[0]}")

        # List and verify
        response = client.get("/tasks")
        data = response.json()
        assert len(data) == 2
        task_ids = [task["id"] for task in data]
        assert ids[0] not in task_ids
        assert ids[1] in task_ids
        assert ids[2] in task_ids


# ============================================================================
# COMPLETE TASK ENDPOINT TESTS
# ============================================================================

class TestCompleteTask:
    """Test task completion endpoint."""

    def test_complete_task(self, client: TestClient):
        """Test marking a task as complete."""
        create_response = client.post("/tasks", json={"title": "Finish Me"})
        task_id = create_response.json()["id"]

        response = client.post(f"/tasks/{task_id}/complete")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "done"
        assert data["completed_at"] is not None

    def test_complete_already_done_task(self, client: TestClient):
        """Test completing a task that's already done."""
        create_response = client.post("/tasks", json={"title": "Already Done", "status": "done"})
        task_id = create_response.json()["id"]
        original_completed_at = create_response.json()["completed_at"]

        response = client.post(f"/tasks/{task_id}/complete")
        assert response.status_code == 200

    def test_complete_task_not_found(self, client: TestClient):
        """Test completing non-existent task."""
        response = client.post("/tasks/999/complete")
        assert response.status_code == 404


# ============================================================================
# STATISTICS ENDPOINT TESTS
# ============================================================================

class TestTaskStatistics:
    """Test task statistics endpoint."""

    def test_statistics_empty(self, client: TestClient):
        """Test statistics with no tasks."""
        response = client.get("/tasks/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 0
        assert data["completion_rate"] == 0

    def test_statistics_with_tasks(self, client: TestClient):
        """Test statistics with multiple tasks."""
        # Create tasks with different statuses
        client.post("/tasks", json={"title": "Todo", "status": "todo"})
        client.post("/tasks", json={"title": "In Progress", "status": "in_progress"})
        complete_response = client.post("/tasks", json={"title": "Done", "status": "done"})

        response = client.get("/tasks/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 3
        assert data["by_status"]["todo"] == 1
        assert data["by_status"]["in_progress"] == 1
        assert data["by_status"]["done"] == 1
        assert data["completion_rate"] == pytest.approx(33.33, 0.1)

    def test_statistics_by_priority(self, client: TestClient):
        """Test statistics breakdown by priority."""
        for priority in ["low", "medium", "high", "urgent"]:
            client.post("/tasks", json={"title": f"{priority.title()} Task", "priority": priority})

        response = client.get("/tasks/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_tasks"] == 4
        assert all(count == 1 for count in data["by_priority"].values())

    def test_statistics_has_timestamp(self, client: TestClient):
        """Test that statistics includes timestamp."""
        response = client.get("/tasks/stats/overview")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "T" in data["timestamp"]  # ISO format check


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_workflow(self, client: TestClient):
        """Test a complete task workflow."""
        # 1. Create task
        create_response = client.post("/tasks", json={
            "title": "Build API",
            "description": "Create a task management API",
            "priority": "high"
        })
        assert create_response.status_code == 201
        task_id = create_response.json()["id"]

        # 2. Read task
        get_response = client.get(f"/tasks/{task_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "Build API"

        # 3. Update task
        update_response = client.put(f"/tasks/{task_id}", json={
            "status": "in_progress",
            "description": "Building the API implementation"
        })
        assert update_response.status_code == 200

        # 4. Complete task
        complete_response = client.post(f"/tasks/{task_id}/complete")
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "done"

        # 5. Verify in list
        list_response = client.get("/tasks?status_filter=done")
        assert list_response.status_code == 200
        assert any(t["id"] == task_id for t in list_response.json())

        # 6. Delete task
        delete_response = client.delete(f"/tasks/{task_id}")
        assert delete_response.status_code == 204

        # 7. Verify deleted
        final_response = client.get(f"/tasks/{task_id}")
        assert final_response.status_code == 404

    def test_concurrent_task_operations(self, client: TestClient):
        """Test multiple tasks being created and updated."""
        task_ids = []

        # Create 5 tasks
        for i in range(5):
            response = client.post("/tasks", json={
                "title": f"Task {i+1}",
                "priority": ["low", "medium", "high", "urgent", "low"][i]
            })
            task_ids.append(response.json()["id"])

        # Update some tasks
        for task_id in task_ids[:3]:
            response = client.put(f"/tasks/{task_id}", json={"status": "done"})
            assert response.status_code == 200

        # Verify statistics
        stats_response = client.get("/tasks/stats/overview")
        data = stats_response.json()
        assert data["total_tasks"] == 5
        assert data["by_status"]["done"] == 3
        assert data["completion_rate"] == 60.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
