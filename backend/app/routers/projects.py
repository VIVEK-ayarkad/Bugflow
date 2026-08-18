from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.models import ActivityLog, Issue, Project, ProjectMember, User, UserRole
from app.pdf_service import generate_project_summary_pdf
from app.schemas import (
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectResponse])
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]:
        projects = db.query(Project).order_by(Project.created_at.desc()).all()
    else:
        # User sees projects they own or are member of
        member_project_ids = [m.project_id for m in current_user.project_memberships]
        if member_project_ids:
            projects = (
                db.query(Project)
                .filter((Project.owner_id == current_user.id) | (Project.id.in_(member_project_ids)))
                .order_by(Project.created_at.desc())
                .all()
            )
        else:
            projects = (
                db.query(Project)
                .filter(Project.owner_id == current_user.id)
                .order_by(Project.created_at.desc())
                .all()
            )
    return projects


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        name=payload.name,
        description=payload.description,
        owner_id=current_user.id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Add creator as Project Member with Owner/Lead role
    member = ProjectMember(project_id=project.id, user_id=current_user.id, role_in_project="Project Lead")
    db.add(member)
    db.commit()
    db.refresh(project)

    log_activity(db, user_id=current_user.id, action="Project Created", details=f"Project '{project.name}' created", project_id=project.id)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this project")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    log_activity(db, user_id=current_user.id, action="Project Updated", details=f"Project '{project.name}' updated", project_id=project.id)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != UserRole.ADMIN and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this project")

    # Clean up associated activity logs to maintain referential integrity
    db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete()
    log_activity(db, user_id=current_user.id, action="Project Deleted", details=f"Project '{project.name}' deleted")
    db.delete(project)
    db.commit()


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def get_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(ProjectMember).filter(ProjectMember.project_id == project_id).all()


@router.post("/{project_id}/members", response_model=ProjectMemberResponse, status_code=status.HTTP_201_CREATED)
def add_project_member(
    project_id: int,
    payload: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    existing = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == payload.user_id
    ).first()

    if existing:
        existing.role_in_project = payload.role_in_project
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

    user = db.query(User).filter(User.id == payload.user_id).first()
    log_activity(db, user_id=current_user.id, action="Member Added", details=f"Added '{user.username if user else payload.user_id}' to project '{project.name}'", project_id=project_id)
    return member


@router.delete("/{project_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    member = db.query(ProjectMember).filter(
        ProjectMember.project_id == project_id, ProjectMember.user_id == user_id
    ).first()
    if member:
        db.delete(member)
        db.commit()


@router.get("/{project_id}/pdf")
def download_project_pdf(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

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
