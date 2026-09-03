from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import Issue, Project, Sprint, SprintStatus, User
from app.schemas import SprintCreate, SprintResponse, SprintUpdate

router = APIRouter(prefix="/api/sprints", tags=["sprints"])


@router.get(
    "",
    response_model=list[SprintResponse],
    summary="List all sprints",
    description="Retrieve all sprints across the platform or filter by specific project ID.",
    responses={
        200: {"description": "List of sprints", "model": list[SprintResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_sprints(
    project_id: int | None = Query(None, description="Optional Project ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sprints with optional project filtering."""
    query = db.query(Sprint)
    if project_id:
        query = query.filter(Sprint.project_id == project_id)
    return query.order_by(Sprint.created_at.desc()).all()


@router.post(
    "",
    response_model=SprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sprint",
    description="Create a sprint milestone within a project. Status defaults to 'planning'.",
    responses={
        201: {"description": "Sprint created successfully", "model": SprintResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def create_sprint(
    payload: SprintCreate,
    project_id: int = Query(..., description="Target project ID for the sprint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new sprint milestone."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    sprint = Sprint(
        project_id=project_id,
        name=payload.name.strip(),
        goal=payload.goal.strip() if payload.goal else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=SprintStatus.PLANNING,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Created",
        details=f"Sprint '{sprint.name}' created for project '{project.name}'",
        project_id=project_id,
    )
    return sprint


@router.get(
    "/{sprint_id}",
    response_model=SprintResponse,
    summary="Get sprint by ID",
    description="Retrieve specific sprint details.",
    responses={
        200: {"description": "Sprint details", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def get_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sprint details."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")
    return sprint


@router.put(
    "/{sprint_id}",
    response_model=SprintResponse,
    summary="Update sprint",
    description="Update sprint name, goal, date boundaries, or status.",
    responses={
        200: {"description": "Sprint updated successfully", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def update_sprint(
    sprint_id: int,
    payload: SprintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update sprint properties."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ["name", "goal"] and isinstance(value, str):
            value = value.strip()
        setattr(sprint, field, value)

    db.commit()
    db.refresh(sprint)
    return sprint


@router.post(
    "/{sprint_id}/start",
    response_model=SprintResponse,
    summary="Start sprint",
    description="Transition sprint status from 'planning' to 'active'.",
    responses={
        200: {"description": "Sprint activated", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def start_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an active sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    sprint.status = SprintStatus.ACTIVE
    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Started",
        details=f"Sprint '{sprint.name}' marked active",
        project_id=sprint.project_id,
    )
    return sprint


@router.post(
    "/{sprint_id}/complete",
    response_model=SprintResponse,
    summary="Complete sprint",
    description="Transition sprint status to 'completed'.",
    responses={
        200: {"description": "Sprint completed", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def complete_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    sprint.status = SprintStatus.COMPLETED
    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Completed",
        details=f"Sprint '{sprint.name}' completed",
        project_id=sprint.project_id,
    )
    return sprint


@router.delete(
    "/{sprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete sprint",
    description="Delete a sprint and unlink assigned issues to maintain referential consistency.",
    responses={
        204: {"description": "Sprint deleted successfully"},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def delete_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    # Unlink assigned issues
    db.query(Issue).filter(Issue.sprint_id == sprint_id).update({"sprint_id": None})
    db.delete(sprint)
    db.commit()
