from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import require_roles
from app.database import get_db
from app.errors import ErrorResponse
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
from app.schemas import ActivityLogResponse, AdminReportsResponse, UserResponse, UserRoleUpdate

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List all users (Admin only)",
    description="Retrieve full list of all system users. Requires Administrator role.",
    responses={
        200: {"description": "List of all user accounts", "model": list[UserResponse]},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
    },
)
def get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """List all registered users (Admin only)."""
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    summary="Change user role (Admin only)",
    description="Update role for any user in the platform. Requires Administrator role.",
    responses={
        200: {"description": "User role updated", "model": UserResponse},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
    },
)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update user role (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{user_id} not found")
    user.role = payload.role
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete user account (Admin only)",
    description="Permanently delete a user account and safely reassign or clean associated foreign key references. Admins cannot delete their own account.",
    responses={
        204: {"description": "User deleted successfully"},
        400: {"description": "Cannot delete own admin account", "model": ErrorResponse},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
    },
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Delete a user account safely (Admin only)."""
    if user_id == admin.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete your own admin account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User #{user_id} not found")

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


@router.get(
    "/reports",
    response_model=AdminReportsResponse,
    summary="System governance reports & metrics (Admin only)",
    description="Retrieve high-level system usage statistics, active bug counts, and user distribution by role.",
    responses={
        200: {"description": "System metrics report", "model": AdminReportsResponse},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
    },
)
def get_admin_reports(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Retrieve system-wide metrics and role breakdown (Admin only)."""
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


@router.get(
    "/logs",
    response_model=list[ActivityLogResponse],
    summary="System audit activity logs (Admin only)",
    description="Retrieve comprehensive audit log of all system actions for governance and compliance.",
    responses={
        200: {"description": "List of system activity logs", "model": list[ActivityLogResponse]},
        403: {"description": "Admin privileges required", "model": ErrorResponse},
    },
)
def get_admin_logs(
    limit: int = Query(100, ge=1, le=500, description="Max logs to return"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Retrieve system audit logs (Admin only)."""
    return db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()
