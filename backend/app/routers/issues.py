from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.activity import create_notification, log_activity
from app.ai import generate_resolution_assistance
from app.auth import get_current_user
from app.database import get_db
from app.models import Issue, IssuePriority, IssueSeverity, IssueStatus, Project, Sprint, User, UserRole
from app.pdf_service import generate_issue_pdf
from app.schemas import (
    IssueAssignUpdate,
    IssueCreate,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
    ResolutionAssistanceRequest,
    ResolutionAssistanceResponse,
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

    issue_data = payload.model_dump()
    if issue_data.get("assigned_developer_id"):
        dev = db.query(User).filter(User.id == issue_data["assigned_developer_id"]).first()
        if not dev:
            issue_data["assigned_developer_id"] = None

    if issue_data.get("sprint_id"):
        sp = db.query(Sprint).filter(Sprint.id == issue_data["sprint_id"], Sprint.project_id == project_id).first()
        if not sp:
            issue_data["sprint_id"] = None

    issue = Issue(
        **issue_data,
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
        if field == "assigned_developer_id" and value:
            dev = db.query(User).filter(User.id == value).first()
            if not dev:
                value = None
        if field == "sprint_id" and value:
            sp = db.query(Sprint).filter(Sprint.id == value, Sprint.project_id == issue.project_id).first()
            if not sp:
                value = None
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


@router.get("/api/issues/{issue_id}/pdf")
def download_issue_pdf(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    pdf_bytes = generate_issue_pdf(issue)
    filename = f"defect_report_DEF-{issue.id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Content-Type": "application/pdf"
        }
    )


@router.get("/api/issues/{issue_id}/resolution-assistance", response_model=ResolutionAssistanceResponse)
async def get_issue_resolution_assistance(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Issue not found")

    req = ResolutionAssistanceRequest(
        issue_id=issue.id,
        title=issue.title,
        description=issue.description or "",
        category=issue.category,
        module=issue.module,
        project_id=issue.project_id
    )
    return await generate_resolution_assistance(req, db)
