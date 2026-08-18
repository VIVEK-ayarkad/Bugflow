from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.models import Issue, Project, Sprint, SprintStatus, User
from app.schemas import SprintCreate, SprintResponse, SprintUpdate

router = APIRouter(prefix="/api/sprints", tags=["sprints"])


@router.get("", response_model=list[SprintResponse])
def list_sprints(
    project_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Sprint)
    if project_id:
        query = query.filter(Sprint.project_id == project_id)
    return query.order_by(Sprint.created_at.desc()).all()


@router.post("", response_model=SprintResponse, status_code=status.HTTP_201_CREATED)
def create_sprint(
    payload: SprintCreate,
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sprint = Sprint(
        project_id=project_id,
        name=payload.name,
        goal=payload.goal,
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


@router.get("/{sprint_id}", response_model=SprintResponse)
def get_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return sprint


@router.put("/{sprint_id}", response_model=SprintResponse)
def update_sprint(
    sprint_id: int,
    payload: SprintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(sprint, field, value)
    db.commit()
    db.refresh(sprint)
    return sprint


@router.post("/{sprint_id}/start", response_model=SprintResponse)
def start_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    sprint.status = SprintStatus.ACTIVE
    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Started",
        details=f"Sprint '{sprint.name}' started",
        project_id=sprint.project_id,
    )
    return sprint


@router.post("/{sprint_id}/complete", response_model=SprintResponse)
def complete_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

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


@router.delete("/{sprint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")

    # Unlink issues assigned to this sprint to prevent foreign key errors
    db.query(Issue).filter(Issue.sprint_id == sprint_id).update({"sprint_id": None})
    db.delete(sprint)
    db.commit()
