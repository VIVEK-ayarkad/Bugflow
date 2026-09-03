from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.activity import create_notification, log_activity
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import Comment, Issue, User, UserRole
from app.schemas import CommentCreate, CommentResponse, CommentUpdate

router = APIRouter(tags=["comments"])


@router.get(
    "/api/issues/{issue_id}/comments",
    response_model=list[CommentResponse],
    summary="List comments for an issue",
    description="Retrieve all discussion comments posted on a specific defect in chronological order.",
    responses={
        200: {"description": "List of issue comments", "model": list[CommentResponse]},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def list_issue_comments(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List comments for an issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")
    return db.query(Comment).filter(Comment.issue_id == issue_id).order_by(Comment.created_at.asc()).all()


@router.post(
    "/api/issues/{issue_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to an issue",
    description="Post a new discussion comment or technical note to a defect ticket.",
    responses={
        201: {"description": "Comment posted successfully", "model": CommentResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def add_comment(
    issue_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new comment to an issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment content cannot be empty")

    comment = Comment(
        issue_id=issue_id,
        user_id=current_user.id,
        content=content,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    log_activity(
        db,
        user_id=current_user.id,
        action="Comment Added",
        details=f"Added comment on Bug #{issue.id}",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    # Notify reporter and assigned developer
    recipients = {issue.reporter_id, issue.assigned_developer_id} - {None, current_user.id}
    for r_id in recipients:
        create_notification(
            db,
            user_id=r_id,
            title="New Comment",
            message=f"{current_user.username} commented on Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return comment


@router.put(
    "/api/comments/{comment_id}",
    response_model=CommentResponse,
    summary="Edit comment content",
    description="Edit an existing comment. Permitted only for the comment author or an Administrator.",
    responses={
        200: {"description": "Comment edited successfully", "model": CommentResponse},
        403: {"description": "Not authorized to edit this comment", "model": ErrorResponse},
        404: {"description": "Comment not found", "model": ErrorResponse},
    },
)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Edit comment text."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comment #{comment_id} not found")

    if comment.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this comment")

    content = payload.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Comment content cannot be empty")

    comment.content = content
    comment.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(comment)
    return comment


@router.delete(
    "/api/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete comment",
    description="Permanently delete a comment. Permitted only for the comment author or an Administrator.",
    responses={
        204: {"description": "Comment deleted successfully"},
        403: {"description": "Not authorized to delete this comment", "model": ErrorResponse},
        404: {"description": "Comment not found", "model": ErrorResponse},
    },
)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a comment."""
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comment #{comment_id} not found")

    if comment.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
