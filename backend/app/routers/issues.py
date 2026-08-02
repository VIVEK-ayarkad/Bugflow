from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import create_notification, log_activity
from app.auth import get_current_user
from app.database import get_db
from app.models import Issue, IssuePriority, IssueSeverity, IssueStatus, Project, User, UserRole
from app.schemas import (
    IssueAssignUpdate,
    IssueCreate,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
)

router = APIRouter(tags=["issues"])


def _build_issue_response(issue: Issue) -> IssueResponse:
    res = IssueResponse.model_validate(issue)
    res.comments_count = len(issue.comments)
    res.attachments_count = len(issue.attachments)
    return res


@router.get("/api/issues", response_model=list[IssueResponse])
def list_all_issues(
    project_id: int | None = Query(None),
    search: str | None = Query(None),
    status: IssueStatus | None = Query(None),
    severity: IssueSeverity | None = Query(None),
    priority: IssuePriority | None = Query(None),
    sprint_id: int | None = Query(None),
    assigned_developer_id: int | None = Query(None),
    reporter_id: int | None = Query(None),
    my_bugs_only: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Issue)

    if project_id:
        query = query.filter(Issue.project_id == project_id)
    if status:
        query = query.filter(Issue.status == status)
    if severity:
        query = query.filter(Issue.severity == severity)
    if priority:
        query = query.filter(Issue.priority == priority)
    if sprint_id:
        query = query.filter(Issue.sprint_id == sprint_id)
    if assigned_developer_id:
        query = query.filter(Issue.assigned_developer_id == assigned_developer_id)
    if reporter_id:
        query = query.filter(Issue.reporter_id == reporter_id)

    if my_bugs_only:
        query = query.filter((Issue.assigned_developer_id == current_user.id) | (Issue.reporter_id == current_user.id))

    if search:
        s = f"%{search.strip()}%"
        # Can search by ID (e.g. #5 or 5), title, or description
        if search.strip().replace("#", "").isdigit():
            bug_id = int(search.strip().replace("#", ""))
            query = query.filter((Issue.id == bug_id) | (Issue.title.ilike(s)) | (Issue.description.ilike(s)))
        else:
            query = query.filter((Issue.title.ilike(s)) | (Issue.description.ilike(s)))

    issues = query.order_by(Issue.created_at.desc()).all()
    return [_build_issue_response(i) for i in issues]


@router.get("/api/projects/{project_id}/issues", response_model=list[IssueResponse])
def list_project_issues(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issues = db.query(Issue).filter(Issue.project_id == project_id).order_by(Issue.created_at.desc()).all()
    return [_build_issue_response(i) for i in issues]


@router.post("/api/projects/{project_id}/issues", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_issue(
    project_id: int,
    payload: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    issue = Issue(
        **payload.model_dump(),
        project_id=project_id,
        reporter_id=current_user.id,
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)

    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Created",
        details=f"Bug #{issue.id} '{issue.title}' created with severity '{issue.severity.value}'",
        issue_id=issue.id,
        project_id=project_id,
    )

    if issue.assigned_developer_id:
        create_notification(
            db,
            user_id=issue.assigned_developer_id,
            title="Bug Assigned",
            message=f"You were assigned to Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.get("/api/issues/{issue_id}", response_model=IssueResponse)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")
    return _build_issue_response(issue)


@router.put("/api/issues/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    prev_status = issue.status
    prev_assignee = issue.assigned_developer_id

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, field, value)
    issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)

    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Updated",
        details=f"Bug #{issue.id} updated",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    if prev_status != issue.status:
        if issue.reporter_id and issue.reporter_id != current_user.id:
            create_notification(
                db,
                user_id=issue.reporter_id,
                title="Status Changed",
                message=f"Bug #{issue.id} status changed to '{issue.status.value}'",
                link=f"/issues/{issue.id}",
            )

    if prev_assignee != issue.assigned_developer_id and issue.assigned_developer_id:
        create_notification(
            db,
            user_id=issue.assigned_developer_id,
            title="Bug Assigned",
            message=f"You were assigned to Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.put("/api/issues/{issue_id}/status", response_model=IssueResponse)
def update_issue_status(
    issue_id: int,
    payload: IssueStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    old_status = issue.status.value
    issue.status = payload.status
    issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)

    action_label = "Bug Closed" if payload.status == IssueStatus.CLOSED else "Status Changed"
    log_activity(
        db,
        user_id=current_user.id,
        action=action_label,
        details=f"Bug #{issue.id} status changed from '{old_status}' to '{payload.status.value}'",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    # Notify reporter and assignee
    recipients = {issue.reporter_id, issue.assigned_developer_id} - {None, current_user.id}
    for r_id in recipients:
        create_notification(
            db,
            user_id=r_id,
            title=f"Bug #{issue.id} {payload.status.value.replace('_', ' ').capitalize()}",
            message=f"Bug #{issue.id} '{issue.title}' status updated to {payload.status.value}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.put("/api/issues/{issue_id}/assign", response_model=IssueResponse)
def assign_issue(
    issue_id: int,
    payload: IssueAssignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    issue.assigned_developer_id = payload.assigned_developer_id
    issue.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(issue)

    assignee_name = issue.assigned_developer.username if issue.assigned_developer else "Unassigned"
    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Assigned",
        details=f"Bug #{issue.id} assigned to '{assignee_name}'",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    if issue.assigned_developer_id and issue.assigned_developer_id != current_user.id:
        create_notification(
            db,
            user_id=issue.assigned_developer_id,
            title="Bug Assigned to You",
            message=f"You were assigned Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.delete("/api/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Deleted",
        details=f"Bug #{issue.id} '{issue.title}' deleted",
        project_id=issue.project_id,
    )
    db.delete(issue)
    db.commit()
