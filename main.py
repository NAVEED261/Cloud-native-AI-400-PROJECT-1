"""
Task Management API - Built with FastAPI and SQLModel
Complete CRUD operations with full documentation
"""

from typing import List, Optional
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException, status, Query, Path, Depends
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy.exc import SQLAlchemyError

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Create database tables on startup."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Get database session as dependency."""
    with Session(engine) as session:
        yield session


# ============================================================================
# MODELS & SCHEMAS
# ============================================================================

class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class TaskPriority(str, Enum):
    """Task priority enumeration."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskBase(SQLModel):
    """Base task model with common fields."""
    title: str = Field(min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(
        default=None,
        max_length=2000,
        description="Detailed task description"
    )
    status: TaskStatus = Field(
        default=TaskStatus.TODO,
        description="Current task status"
    )
    priority: TaskPriority = Field(
        default=TaskPriority.MEDIUM,
        description="Task priority level"
    )
    due_date: Optional[datetime] = Field(
        default=None,
        description="Task due date"
    )


class Task(TaskBase, table=True):
    """Task database model."""
    __tablename__ = "tasks"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When task was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When task was last updated"
    )
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When task was completed"
    )


class TaskCreate(TaskBase):
    """Schema for creating a new task."""
    pass


class TaskUpdate(SQLModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None, max_length=2000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None


class TaskRead(TaskBase):
    """Schema for reading task (response model)."""
    id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# FASTAPI APP SETUP
# ============================================================================

app = FastAPI(
    title="Task Management API",
    description="Complete CRUD API for managing tasks with priorities and status tracking",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


@app.on_event("startup")
def on_startup():
    """Create database tables on application startup."""
    create_db_and_tables()


# ============================================================================
# HEALTH CHECK ENDPOINT
# ============================================================================

@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    response_description="API health status"
)
async def health_check():
    """
    Health check endpoint to verify API is running.

    Returns:
        dict: Status of the API
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

@app.post(
    "/tasks",
    response_model=TaskRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
    summary="Create a new task",
    responses={
        201: {"description": "Task created successfully"},
        422: {"description": "Invalid input data"}
    }
)
async def create_task(
    task: TaskCreate,
    session: Session = Depends(get_session)
) -> Task:
    """
    Create a new task.

    Args:
        task: Task data to create
        session: Database session (injected)

    Returns:
        TaskRead: Created task with ID

    Raises:
        HTTPException: If database operation fails
    """
    try:
        db_task = Task.from_orm(task)
        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/tasks",
    response_model=List[TaskRead],
    tags=["Tasks"],
    summary="List all tasks",
    responses={
        200: {"description": "List of tasks"}
    }
)
async def list_tasks(
    skip: int = Query(0, ge=0, description="Number of tasks to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of tasks to return"),
    status_filter: Optional[TaskStatus] = Query(None, description="Filter by task status"),
    priority_filter: Optional[TaskPriority] = Query(None, description="Filter by priority"),
    session: Session = Depends(get_session)
) -> List[TaskRead]:
    """
    List all tasks with optional filtering and pagination.

    Args:
        skip: Number of tasks to skip (default: 0)
        limit: Maximum number of tasks to return (default: 50, max: 100)
        status_filter: Filter by status (optional)
        priority_filter: Filter by priority (optional)
        session: Database session (injected)

    Returns:
        List[TaskRead]: List of tasks matching criteria
    """
    try:
        query = select(Task)

        if status_filter:
            query = query.where(Task.status == status_filter)

        if priority_filter:
            query = query.where(Task.priority == priority_filter)

        query = query.offset(skip).limit(limit)
        tasks = session.exec(query).all()
        return tasks
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskRead,
    tags=["Tasks"],
    summary="Get a specific task",
    responses={
        200: {"description": "Task found"},
        404: {"description": "Task not found"}
    }
)
async def get_task(
    task_id: int = Path(..., gt=0, description="Task ID"),
    session: Session = Depends(get_session)
) -> Task:
    """
    Get a specific task by ID.

    Args:
        task_id: ID of the task to retrieve
        session: Database session (injected)

    Returns:
        TaskRead: Task details

    Raises:
        HTTPException: If task not found
    """
    try:
        task = session.get(Task, task_id)

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )

        return task
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.put(
    "/tasks/{task_id}",
    response_model=TaskRead,
    tags=["Tasks"],
    summary="Update a task",
    responses={
        200: {"description": "Task updated successfully"},
        404: {"description": "Task not found"},
        422: {"description": "Invalid input data"}
    }
)
async def update_task(
    task_id: int = Path(..., gt=0, description="Task ID"),
    task_update: TaskUpdate = None,
    session: Session = Depends(get_session)
) -> Task:
    """
    Update a specific task.

    Args:
        task_id: ID of the task to update
        task_update: Updated task data
        session: Database session (injected)

    Returns:
        TaskRead: Updated task

    Raises:
        HTTPException: If task not found or database error
    """
    try:
        db_task = session.get(Task, task_id)

        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )

        # Update only provided fields
        update_data = task_update.dict(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        # If status changed to DONE, set completed_at
        if update_data.get("status") == TaskStatus.DONE:
            update_data["completed_at"] = datetime.utcnow()
        elif update_data.get("status") and update_data["status"] != TaskStatus.DONE:
            update_data["completed_at"] = None

        for key, value in update_data.items():
            setattr(db_task, key, value)

        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"],
    summary="Delete a task",
    responses={
        204: {"description": "Task deleted successfully"},
        404: {"description": "Task not found"}
    }
)
async def delete_task(
    task_id: int = Path(..., gt=0, description="Task ID"),
    session: Session = Depends(get_session)
):
    """
    Delete a specific task.

    Args:
        task_id: ID of the task to delete
        session: Database session (injected)

    Raises:
        HTTPException: If task not found or database error
    """
    try:
        db_task = session.get(Task, task_id)

        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )

        session.delete(db_task)
        session.commit()
        return None
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


# ============================================================================
# ADDITIONAL ENDPOINTS
# ============================================================================

@app.get(
    "/tasks/stats/overview",
    tags=["Tasks"],
    summary="Get task statistics",
    responses={
        200: {"description": "Task statistics"}
    }
)
async def get_task_statistics(session: Session = Depends(get_session)):
    """
    Get overall task statistics.

    Args:
        session: Database session (injected)

    Returns:
        dict: Statistics including totals by status and priority
    """
    try:
        # Total tasks
        total = len(session.exec(select(Task)).all())

        # By status
        by_status = {}
        for status_val in TaskStatus:
            count = len(session.exec(
                select(Task).where(Task.status == status_val)
            ).all())
            by_status[status_val.value] = count

        # By priority
        by_priority = {}
        for priority_val in TaskPriority:
            count = len(session.exec(
                select(Task).where(Task.priority == priority_val)
            ).all())
            by_priority[priority_val.value] = count

        # Completion rate
        done_count = by_status.get(TaskStatus.DONE.value, 0)
        completion_rate = (done_count / total * 100) if total > 0 else 0

        return {
            "total_tasks": total,
            "by_status": by_status,
            "by_priority": by_priority,
            "completion_rate": round(completion_rate, 2),
            "timestamp": datetime.utcnow().isoformat()
        }
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


@app.post(
    "/tasks/{task_id}/complete",
    response_model=TaskRead,
    tags=["Tasks"],
    summary="Mark task as complete",
    responses={
        200: {"description": "Task marked as complete"},
        404: {"description": "Task not found"}
    }
)
async def complete_task(
    task_id: int = Path(..., gt=0, description="Task ID"),
    session: Session = Depends(get_session)
) -> Task:
    """
    Mark a task as complete.

    Args:
        task_id: ID of the task to complete
        session: Database session (injected)

    Returns:
        TaskRead: Updated task

    Raises:
        HTTPException: If task not found
    """
    try:
        db_task = session.get(Task, task_id)

        if not db_task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task with id {task_id} not found"
            )

        db_task.status = TaskStatus.DONE
        db_task.completed_at = datetime.utcnow()
        db_task.updated_at = datetime.utcnow()

        session.add(db_task)
        session.commit()
        session.refresh(db_task)
        return db_task
    except SQLAlchemyError as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    print("Starting Task Management API...")
    print("Swagger UI: http://localhost:8000/docs")
    print("ReDoc: http://localhost:8000/redoc")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
