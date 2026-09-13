from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload, selectinload

from app.activity import create_notification, log_activity
from app.ai import generate_resolution_assistance
from app.auth import get_current_user
from app.blast_radius_service import compute_project_blast_radius
from app.database import get_db
from app.errors import ErrorResponse
from app.models import ActivityLog, Issue, IssuePriority, IssueSeverity, IssueStatus, Project, Sprint, User, UserRole
from app.pdf_service import generate_issue_pdf
from app.schemas import (
    ActivityLogResponse,
    BlastRadiusReport,
    IssueAssignUpdate,
    IssueCreate,
    IssueResponse,
    IssueStatusUpdate,
    IssueUpdate,
    ResolutionAssistanceRequest,
    ResolutionAssistanceResponse,
)

router = APIRouter(tags=["issues"])

ISSUE_EAGER_LOAD = (
    joinedload(Issue.reporter),
    joinedload(Issue.assigned_developer),
    joinedload(Issue.project),
    joinedload(Issue.sprint),
    selectinload(Issue.comments),
    selectinload(Issue.attachments),
)


def _build_issue_response(issue: Issue) -> IssueResponse:
    res = IssueResponse.model_validate(issue)
    res.comments_count = len(issue.comments)
    res.attachments_count = len(issue.attachments)
    return res


@router.get(
    "/api/issues",
    response_model=list[IssueResponse],
    summary="List all issues with rich filtering",
    description="Query defects across all projects with filters for status, severity, priority, sprint, developer assignment, search query, and pagination.",
    responses={
        200: {"description": "List of matching defects", "model": list[IssueResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_all_issues(
    project_id: int | None = Query(None, description="Filter by parent Project ID"),
    search: str | None = Query(None, max_length=200, description="Search by Bug ID (#12), title, or description"),
    status: IssueStatus | None = Query(None, description="Filter by defect status"),
    severity: IssueSeverity | None = Query(None, description="Filter by severity level"),
    priority: IssuePriority | None = Query(None, description="Filter by priority level"),
    category: str | None = Query(None, max_length=100, description="Filter by category taxonomy"),
    module: str | None = Query(None, max_length=150, description="Filter by component module"),
    defect_type: str | None = Query(None, max_length=100, description="Filter by defect type"),
    sprint_id: int | None = Query(None, description="Filter by Sprint ID"),
    assigned_developer_id: int | None = Query(None, description="Filter by assigned developer User ID"),
    reporter_id: int | None = Query(None, description="Filter by reporter User ID"),
    my_bugs_only: bool = Query(False, description="Filter to show only defects reported by or assigned to current user"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=500, description="Maximum records to return"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List issues with multi-dimensional filtering."""
    query = db.query(Issue).options(*ISSUE_EAGER_LOAD)

    if project_id:
        query = query.filter(Issue.project_id == project_id)
    if status:
        query = query.filter(Issue.status == status)
    if severity:
        query = query.filter(Issue.severity == severity)
    if priority:
        query = query.filter(Issue.priority == priority)
    if category:
        query = query.filter(Issue.category.ilike(f"%{category.strip()}%"))
    if module:
        query = query.filter(Issue.module.ilike(f"%{module.strip()}%"))
    if defect_type:
        query = query.filter(Issue.defect_type.ilike(f"%{defect_type.strip()}%"))
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
        if search.strip().replace("#", "").isdigit():
            bug_id = int(search.strip().replace("#", ""))
            query = query.filter((Issue.id == bug_id) | (Issue.title.ilike(s)) | (Issue.description.ilike(s)))
        else:
            query = query.filter((Issue.title.ilike(s)) | (Issue.description.ilike(s)))

    issues = query.order_by(Issue.created_at.desc()).offset(skip).limit(limit).all()
    return [_build_issue_response(i) for i in issues]


@router.get(
    "/api/projects/{project_id}/issues",
    response_model=list[IssueResponse],
    summary="List issues for a specific project",
    description="Retrieve all defect tickets filed within a specific project.",
    responses={
        200: {"description": "List of project defects", "model": list[IssueResponse]},
        404: {"description": "Project not found", "model": ErrorResponse},
    },
)
def list_project_issues(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List issues belonging to a specific project."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    issues = db.query(Issue).options(*ISSUE_EAGER_LOAD).filter(Issue.project_id == project_id).order_by(Issue.created_at.desc()).all()
    return [_build_issue_response(i) for i in issues]



@router.post(
    "/api/projects/{project_id}/issues",
    response_model=IssueResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new defect ticket",
    description="File a new bug report under a project. Triggers activity logging and developer notification if assigned.",
    responses={
        201: {"description": "Bug ticket created", "model": IssueResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
        422: {"description": "Validation error in bug payload", "model": ErrorResponse},
    },
)
def create_issue(
    project_id: int,
    payload: IssueCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new defect ticket."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    issue_data = payload.model_dump()

    # Validate assigned developer existence
    if issue_data.get("assigned_developer_id"):
        dev = db.query(User).filter(User.id == issue_data["assigned_developer_id"]).first()
        if not dev:
            issue_data["assigned_developer_id"] = None

    # Validate sprint belongs to this project
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
        details=f"Bug #{issue.id} '{issue.title}' logged with severity '{issue.severity.value}'",
        issue_id=issue.id,
        project_id=project_id,
    )

    if issue.assigned_developer_id and issue.assigned_developer_id != current_user.id:
        create_notification(
            db,
            user_id=issue.assigned_developer_id,
            title="Bug Assigned",
            message=f"You were assigned to Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.get(
    "/api/issues/{issue_id}",
    response_model=IssueResponse,
    summary="Get defect ticket details",
    description="Retrieve comprehensive details for a defect ticket by its ID.",
    responses={
        200: {"description": "Issue details", "model": IssueResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def get_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve an issue by ID."""
    issue = db.query(Issue).options(*ISSUE_EAGER_LOAD).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")
    return _build_issue_response(issue)


@router.put(
    "/api/issues/{issue_id}",
    response_model=IssueResponse,
    summary="Update defect details",
    description="Modify defect title, description, reproduction steps, severity, priority, or assigned sprint.",
    responses={
        200: {"description": "Issue updated successfully", "model": IssueResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def update_issue(
    issue_id: int,
    payload: IssueUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update issue details."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

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

    issue.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(issue)

    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Updated",
        details=f"Bug #{issue.id} '{issue.title}' updated",
        issue_id=issue.id,
        project_id=issue.project_id,
    )

    if prev_status != issue.status and issue.reporter_id and issue.reporter_id != current_user.id:
        create_notification(
            db,
            user_id=issue.reporter_id,
            title="Status Changed",
            message=f"Bug #{issue.id} status changed to '{issue.status.value}'",
            link=f"/issues/{issue.id}",
        )

    if prev_assignee != issue.assigned_developer_id and issue.assigned_developer_id and issue.assigned_developer_id != current_user.id:
        create_notification(
            db,
            user_id=issue.assigned_developer_id,
            title="Bug Assigned",
            message=f"You were assigned to Bug #{issue.id}: {issue.title}",
            link=f"/issues/{issue.id}",
        )

    return _build_issue_response(issue)


@router.put(
    "/api/issues/{issue_id}/status",
    response_model=IssueResponse,
    summary="Update defect workflow status",
    description="Transition defect status (open -> in_progress -> in_review -> resolved -> closed).",
    responses={
        200: {"description": "Status updated", "model": IssueResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def update_issue_status(
    issue_id: int,
    payload: IssueStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Transition defect status."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    old_status = issue.status.value
    issue.status = payload.status
    issue.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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


@router.put(
    "/api/issues/{issue_id}/assign",
    response_model=IssueResponse,
    summary="Assign defect to developer",
    description="Assign a developer to the ticket, or set to null to unassign.",
    responses={
        200: {"description": "Assignment updated", "model": IssueResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def assign_issue(
    issue_id: int,
    payload: IssueAssignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign or unassign an issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    if payload.assigned_developer_id:
        target_dev = db.query(User).filter(User.id == payload.assigned_developer_id).first()
        if not target_dev:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target developer not found")

    issue.assigned_developer_id = payload.assigned_developer_id
    issue.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
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


@router.delete(
    "/api/issues/{issue_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete defect ticket",
    description="Permanently delete a defect ticket and its associated comments and attachments.",
    responses={
        204: {"description": "Issue deleted successfully"},
        403: {"description": "Not authorized to delete this issue", "model": ErrorResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def delete_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a defect ticket."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    # Check permission: Admin, Project Owner, Reporter, or Assigned Developer
    is_admin = current_user.role in [UserRole.ADMIN, UserRole.PROJECT_MANAGER]
    is_owner = issue.project.owner_id == current_user.id
    is_reporter = issue.reporter_id == current_user.id
    is_assignee = issue.assigned_developer_id == current_user.id

    if not (is_admin or is_owner or is_reporter or is_assignee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this defect")

    log_activity(
        db,
        user_id=current_user.id,
        action="Bug Deleted",
        details=f"Bug #{issue.id} '{issue.title}' deleted",
        project_id=issue.project_id,
    )
    db.delete(issue)
    db.commit()


@router.get(
    "/api/issues/{issue_id}/activity",
    response_model=list[ActivityLogResponse],
    summary="Get issue activity audit logs",
    description="Retrieve the chronological activity history and audit trail for a specific defect.",
    responses={
        200: {"description": "List of activity logs for the defect", "model": list[ActivityLogResponse]},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def get_issue_activity(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve activity history for a specific issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    return (
        db.query(ActivityLog)
        .filter(ActivityLog.issue_id == issue_id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )


@router.get(
    "/api/issues/{issue_id}/pdf",
    summary="Export Defect Investigation Report PDF",
    description="Generate and stream an investigation report PDF containing bug metadata, reproduction steps, resolution assistance, and full comment thread.",
    responses={
        200: {"description": "Defect report PDF", "content": {"application/pdf": {}}},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def download_issue_pdf(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Download individual defect investigation PDF."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

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


@router.get(
    "/api/issues/{issue_id}/resolution-assistance",
    response_model=ResolutionAssistanceResponse,
    summary="Get Resolution Assistance Copilot report",
    description="Generate diagnostic checklist, historical similar defects, previous resolution patterns, and technical fix snippet.",
    responses={
        200: {"description": "Resolution assistance report", "model": ResolutionAssistanceResponse},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
async def get_issue_resolution_assistance(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate resolution assistance for an existing issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    # Extract all existing comment notes on this issue
    issue_comments = [c.content for c in issue.comments if c.content] if issue.comments else []

    req = ResolutionAssistanceRequest(
        issue_id=issue.id,
        title=issue.title,
        description=issue.description or "",
        category=issue.category,
        module=issue.module,
        severity=issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
        comments=issue_comments,
        project_id=issue.project_id,
    )
    return await generate_resolution_assistance(req, db)


@router.get(
    "/api/issues/{issue_id}/blast-radius",
    response_model=BlastRadiusReport,
    summary="Get Failure Blast Radius for a Defect",
    description="Analyze the architectural blast radius, downstream dependency failures, and containment strategies for a specific bug.",
    responses={
        200: {"description": "Blast radius report for defect", "model": BlastRadiusReport},
        404: {"description": "Issue not found", "model": ErrorResponse},
    },
)
def get_issue_blast_radius(
    issue_id: int,
    domain: str | None = Query(default=None, description="Optional domain archetype override"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute specific failure blast radius for an existing issue."""
    issue = db.query(Issue).filter(Issue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Issue #{issue_id} not found")

    return compute_project_blast_radius(issue.project_id, db, focused_issue_id=issue.id, domain_override=domain)

