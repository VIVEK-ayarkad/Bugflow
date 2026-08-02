from sqlalchemy.orm import Session

from app.models import ActivityLog, Notification


def log_activity(
    db: Session,
    user_id: int,
    action: str,
    details: str | None = None,
    issue_id: int | None = None,
    project_id: int | None = None,
):
    activity = ActivityLog(
        user_id=user_id,
        action=action,
        details=details,
        issue_id=issue_id,
        project_id=project_id,
    )
    db.add(activity)
    db.commit()


def create_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    link: str | None = None,
):
    notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        link=link,
    )
    db.add(notif)
    db.commit()
