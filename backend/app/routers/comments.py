from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.activity import create_notification, log_activity
from app.auth import get_current_user
from app.database import get_db
from app.models import Comment, Issue, User
from app.schemas import CommentCreate, CommentResponse, CommentUpdate

router = APIRouter(tags=["comments"])


@router.get("/api/issues/{issue_id}/comments", response_model=list[CommentResponse])
def list_issue_comments(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return db.query(Comment).filter(Comment.issue_id == issue_id).order_by(Comment.created_at.asc()).all()


@router.post("/api/issues/{issue_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    issue_id: int,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    comment = Comment(
        issue_id=issue_id,
        user_id=current_user.id,
        content=payload.content,
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

    # Notify reporter and assignee
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


@router.put("/api/comments/{comment_id}", response_model=CommentResponse)
def edit_comment(
    comment_id: int,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")

    comment.content = payload.content
    comment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(comment)
    return comment


@router.delete("/api/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.query(Comment).filter(Comment.id == comment_id).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    db.delete(comment)
    db.commit()
