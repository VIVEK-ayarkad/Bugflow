from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import Notification, User
from app.schemas import MessageResponse, NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get(
    "",
    response_model=list[NotificationResponse],
    summary="List current user notifications",
    description="Retrieve recent notifications for the authenticated user.",
    responses={
        200: {"description": "List of notifications", "model": list[NotificationResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_notifications(
    limit: int = Query(50, ge=1, le=100, description="Max notifications to retrieve"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List notifications for current user."""
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .all()
    )


@router.put(
    "/{notification_id}/read",
    response_model=NotificationResponse,
    summary="Mark notification as read",
    description="Mark a specific notification as read.",
    responses={
        200: {"description": "Notification marked as read", "model": NotificationResponse},
        404: {"description": "Notification not found", "model": ErrorResponse},
    },
)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a notification as read."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification #{notification_id} not found")

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.put(
    "/read-all",
    response_model=MessageResponse,
    summary="Mark all notifications as read",
    description="Mark all unread notifications for the current user as read.",
    responses={
        200: {"description": "All notifications marked read", "model": MessageResponse},
    },
)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read."""
    db.query(Notification).filter(Notification.user_id == current_user.id).update({"is_read": True})
    db.commit()
    return MessageResponse(message="All notifications marked as read")


@router.delete(
    "/{notification_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete notification",
    description="Permanently remove a notification.",
    responses={
        204: {"description": "Notification deleted"},
        404: {"description": "Notification not found", "model": ErrorResponse},
    },
)
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Notification #{notification_id} not found")

    db.delete(notif)
    db.commit()


@router.delete(
    "",
    response_model=MessageResponse,
    summary="Clear read notifications",
    description="Delete all notifications that have already been read for the current user.",
    responses={
        200: {"description": "Read notifications cleared", "model": MessageResponse},
    },
)
def clear_read_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete all read notifications for current user."""
    deleted_count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(True),
    ).delete()
    db.commit()
    return MessageResponse(message=f"Cleared {deleted_count} read notifications")
