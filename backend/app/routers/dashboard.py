from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ActivityLog, Issue, IssuePriority, IssueSeverity, IssueStatus, User
from app.schemas import ActivityLogResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
def get_dashboard_stats(
    project_id: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Issue)
    if project_id:
        query = query.filter(Issue.project_id == project_id)

    issues = query.all()

    total_bugs = len(issues)
    open_bugs = sum(1 for i in issues if i.status == IssueStatus.OPEN)
    in_progress_bugs = sum(1 for i in issues if i.status == IssueStatus.IN_PROGRESS)
    in_review_bugs = sum(1 for i in issues if i.status == IssueStatus.IN_REVIEW)
    resolved_bugs = sum(1 for i in issues if i.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED])
    critical_bugs = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL)
    assigned_bugs = sum(1 for i in issues if i.assigned_developer_id == current_user.id)

    # Bugs by Severity
    severity_counts = {
        "low": sum(1 for i in issues if i.severity == IssueSeverity.LOW),
        "medium": sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM),
        "high": sum(1 for i in issues if i.severity == IssueSeverity.HIGH),
        "critical": sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
    }

    # Bugs by Status
    status_counts = {
        "open": open_bugs,
        "in_progress": in_progress_bugs,
        "in_review": in_review_bugs,
        "resolved": sum(1 for i in issues if i.status == IssueStatus.RESOLVED),
        "closed": sum(1 for i in issues if i.status == IssueStatus.CLOSED),
    }

    # Developer Workload
    dev_workload_dict = defaultdict(int)
    for i in issues:
        if i.assigned_developer:
            dev_workload_dict[i.assigned_developer.username] += 1
        else:
            dev_workload_dict["Unassigned"] += 1

    dev_workload = [{"developer": k, "count": v} for k, v in dev_workload_dict.items()]

    # Monthly Bug Reports (past 6 months)
    monthly_dict = defaultdict(int)
    now = datetime.utcnow()
    for month_offset in range(5, -1, -1):
        month_date = now - timedelta(days=30 * month_offset)
        month_key = month_date.strftime("%b %Y")
        monthly_dict[month_key] = 0

    for i in issues:
        if i.created_at:
            m_key = i.created_at.strftime("%b %Y")
            if m_key in monthly_dict:
                monthly_dict[m_key] += 1

    monthly_reports = [{"month": k, "count": v} for k, v in monthly_dict.items()]

    # Recent Activities
    act_query = db.query(ActivityLog)
    if project_id:
        act_query = act_query.filter(ActivityLog.project_id == project_id)
    recent_activities = act_query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return {
        "summary": {
            "total_bugs": total_bugs,
            "open_bugs": open_bugs,
            "in_progress_bugs": in_progress_bugs,
            "in_review_bugs": in_review_bugs,
            "resolved_bugs": resolved_bugs,
            "critical_bugs": critical_bugs,
            "assigned_bugs": assigned_bugs,
        },
        "charts": {
            "by_severity": severity_counts,
            "by_status": status_counts,
            "monthly_reports": monthly_reports,
            "developer_workload": dev_workload,
        },
        "recent_activities": [ActivityLogResponse.model_validate(a) for a in recent_activities],
    }
