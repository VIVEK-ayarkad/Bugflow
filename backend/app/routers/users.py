from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user, require_roles
from app.database import get_db
from app.errors import ErrorResponse
from app.models import User, UserRole
from app.schemas import UserResponse, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users",
    description="Retrieve a list of all registered users in the platform, with optional filtering by role or search term.",
    responses={
        200: {"description": "List of user profiles", "model": list[UserResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_users(
    role: UserRole | None = Query(None, description="Filter users by assigned role"),
    search: str | None = Query(None, max_length=100, description="Search users by username or email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List system users with optional search and role filtering."""
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if search:
        s = f"%{search.strip()}%"
        query = query.filter((User.username.ilike(s)) | (User.email.ilike(s)))
    return query.order_by(User.username.asc()).all()


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user by ID",
    description="Retrieve public profile details of a specific user by their ID.",
    responses={
        200: {"description": "User profile found", "model": UserResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve specific user profile by user ID."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")
    return user


@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
    summary="Update user role (Admin only)",
    description="Assign a new role to a user. Restricted strictly to Administrator accounts.",
    responses={
        200: {"description": "User role updated successfully", "model": UserResponse},
        403: {"description": "Access forbidden - Admin role required", "model": ErrorResponse},
        404: {"description": "User not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def update_user_role(
    user_id: int,
    payload: UserRoleUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    """Update user role (Admin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with ID {user_id} not found")

    prev_role = user.role.value
    user.role = payload.role
    db.commit()
    db.refresh(user)

    log_activity(
        db,
        user_id=admin_user.id,
        action="Role Changed",
        details=f"User '{user.username}' role changed from '{prev_role}' to '{payload.role.value}' by admin",
    )
    return user
