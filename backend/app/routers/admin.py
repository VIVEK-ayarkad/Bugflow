from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.models import (
    ActivityLog,
    Attachment,
    Comment,
    Issue,
    Notification,
    Project,
    ProjectMember,
    User,
    UserRole,
)
from app.schemas import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Clean up dependent relational references safely
    db.query(Issue).filter(Issue.assigned_developer_id == user_id).update({"assigned_developer_id": None})
    db.query(Issue).filter(Issue.reporter_id == user_id).update({"reporter_id": admin.id})
    db.query(Project).filter(Project.owner_id == user_id).update({"owner_id": admin.id})
    db.query(ProjectMember).filter(ProjectMember.user_id == user_id).delete()
    db.query(Comment).filter(Comment.user_id == user_id).delete()
    db.query(Attachment).filter(Attachment.user_id == user_id).delete()
    db.query(ActivityLog).filter(ActivityLog.user_id == user_id).delete()
    db.query(Notification).filter(Notification.user_id == user_id).delete()

    db.delete(user)
    db.commit()


@router.get("/reports")
def get_admin_reports(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    total_users = db.query(User).count()
    total_projects = db.query(Project).count()
    total_bugs = db.query(Issue).count()

    users_by_role = {}
    for r in UserRole:
        users_by_role[r.value] = db.query(User).filter(User.role == r).count()

    return {
        "system_metrics": {
            "total_users": total_users,
            "total_projects": total_projects,
            "total_bugs": total_bugs,
        },
        "users_by_role": users_by_role,
    }
