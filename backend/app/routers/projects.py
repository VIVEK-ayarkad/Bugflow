from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import ActivityLog, Issue, Project, ProjectMember, Sprint, User, UserRole
from app.pdf_service import generate_project_summary_pdf
from app.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
    SprintResponse,
)

router = APIRouter(prefix="/projects", tags=["projects"])


def _check_project_access(project: Project, user: User) -> bool:
    if user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
        return True
    if project.owner_id == user.id:
        return True
    member_user_ids = [m.user_id for m in project.members]
    return user.id in member_user_ids


@router.get(
    "",
    response_model=list[ProjectResponse],
    summary="List accessible projects",
    description="Retrieve projects accessible by the authenticated user. Admins and Project Managers see all projects.",
    responses={
        200: {"description": "List of projects", "model": list[ProjectResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_projects(
    search: str | None = Query(None, max_length=100, description="Filter projects by name or description"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List accessible projects."""
    if current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
        query = db.query(Project)
    else:
        member_project_ids = [m.project_id for m in current_user.project_memberships]
        if member_project_ids:
            query = db.query(Project).filter(
                (Project.owner_id == current_user.id) | (Project.id.in_(member_project_ids))
            )
        else:
            query = db.query(Project).filter(Project.owner_id == current_user.id)

    if search:
        s = f"%{search.strip()}%"
        query = query.filter((Project.name.ilike(s)) | (Project.description.ilike(s)))

    return query.order_by(Project.created_at.desc()).all()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
    description="Create a new project workspace. The authenticated creator is automatically registered as Project Lead.",
    responses={
        201: {"description": "Project created successfully", "model": ProjectResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error in payload", "model": ErrorResponse},
    },
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new project."""
    project = Project(
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add creator as Project Member with Project Lead role
    member = ProjectMember(project_id=project.id, user_id=current_user.id, role_in_project="Project Lead")
    db.add(member)
    db.commit()
    db.refresh(project)

    log_activity(
        db,
        user_id=current_user.id,
        action="Project Created",
        details=f"Project '{project.name}' created",
        project_id=project.id,
    )
    return project


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details",
    description="Retrieve comprehensive details for a specific project including members and owner info.",
    responses={
        200: {"description": "Project details retrieved", "model": ProjectResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
        403: {"description": "Access forbidden", "model": ErrorResponse},
    },
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get project by ID."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    if not _check_project_access(project, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied to this project")

    return project


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project details",
    description="Update project name or description. Requires Project Owner, Project Manager, or Admin role.",
    responses={
        200: {"description": "Project updated successfully", "model": ProjectResponse},
        403: {"description": "Not authorized to modify this project", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update project details."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.PROJECT_MANAGER] and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this project")

    update_data = payload.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "description" in update_data and update_data["description"]:
        update_data["description"] = update_data["description"].strip()

    for field, value in update_data.items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)

    log_activity(
        db,
        user_id=current_user.id,
        action="Project Updated",
        details=f"Project '{project.name}' updated",
        project_id=project.id,
    )
    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete project",
    description="Permanently delete a project and cascade clean associated sprints, issues, and logs.",
    responses={
        204: {"description": "Project deleted successfully"},
        403: {"description": "Not authorized to delete this project", "model": ErrorResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this project")

    # Clean up associated activity logs
    db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete()
    log_activity(db, user_id=current_user.id, action="Project Deleted", details=f"Project '{project.name}' deleted")
    db.delete(project)
    db.commit()


@router.get(
    "/{project_id}/members",
    response_model=list[ProjectMemberResponse],
    summary="List project members",
    description="Retrieve all assigned members and their roles within a specific project.",
    responses={
        200: {"description": "List of project members", "model": list[ProjectMemberResponse]},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def get_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List members of a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add or update project member",
    description="Add a registered user to a project team, or update their role designation.",
    responses={
        201: {"description": "Member added or updated", "model": ProjectMemberResponse},
        404: {"description": "Project or target User not found", "model": ErrorResponse},
        403: {"description": "Forbidden", "model": ErrorResponse},
    },
)
def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add or update a project member."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    # Check authority to add members (owner, manager, or admin)
    if current_user.role not in [UserRole.ADMIN, UserRole.PROJECT_MANAGER] and project.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to manage project members")

    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{payload.user_id} not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id
    ).first()

    if existing:
        existing.role_in_project = payload.role_in_project or "Member"
        db.commit()
        db.refresh(existing)
        return existing

    member = ProjectMember(
        project_id=project_id,
        user_id=payload.user_id,
        role_in_project=payload.role_in_project or "Member",
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    log_activity(
        db,
        user_id=current_user.id,
        action="Member Added",
        details=f"Added '{target_user.username}' as '{member.role_in_project}' to project '{project.name}'",
        project_id=project_id,
    )
    return member


@router.delete(
    "/{project_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove project member",
    description="Remove a user's membership from the project.",
    responses={
        204: {"description": "Member removed successfully"},
        403: {"description": "Forbidden", "model": ErrorResponse},
        404: {"description": "Project or member not found", "model": ErrorResponse},
    },
)
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a member from a project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    if current_user.role not in [UserRole.ADMIN, UserRole.PROJECT_MANAGER] and project.owner_id != current_user.id and current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to remove members from this project")

    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
    ).first()
    if member:
        db.delete(member)
        db.commit()


@router.get(
    "/{project_id}/sprints",
    response_model=list[SprintResponse],
    summary="List sprints for a project",
    description="Retrieve all planning, active, and completed sprints for a specific project.",
    responses={
        200: {"description": "List of sprints", "model": list[SprintResponse]},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def get_project_sprints(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sprints within a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    return db.query(Sprint).filter(Sprint.project_id == project_id).order_by(Sprint.created_at.desc()).all()


@router.get(
    "/{project_id}/pdf",
    summary="Export Project QA Summary PDF",
    description="Generate and stream an executive defect intelligence report PDF for the project.",
    responses={
        200: {"description": "PDF file stream", "content": {"application/pdf": {}}},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def download_project_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download project summary PDF report."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    issues = db.query(Issue).filter(Issue.project_id == project_id).order_by(Issue.created_at.desc()).all()
    pdf_bytes = generate_project_summary_pdf(project, issues)
    clean_name = "".join(c for c in project.name if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"defect_summary_{clean_name.replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/pdf"
        }
    )
