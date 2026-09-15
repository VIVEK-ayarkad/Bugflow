from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import ActivityLog, Issue, IssuePriority, IssueSeverity, IssueStatus, User
from app.schemas import ActivityLogResponse

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def format_duration(hours: float | None) -> str:
    """Format decimal hours into human-readable duration string displaying both days and hours."""
    if hours is None:
        return "N/A"
    days = hours / 24.0
    return f"{days:.1f} days ({hours:.1f} hrs)"


@router.get(
    "/stats",
    summary="Get aggregated dashboard statistics",
    description="Retrieve comprehensive defect metrics, resolution velocity, severity distributions, and monthly trends.",
    responses={
        200: {"description": "Dashboard analytics payload"},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def get_dashboard_stats(
    project_id: int | None = Query(None, description="Optional Project ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve full dashboard defect analytics."""
    query = db.query(Issue).options(joinedload(Issue.assigned_developer))
    if project_id:
        query = query.filter(Issue.project_id == project_id)

    issues = query.all()

    total_bugs = len(issues)
    open_bugs = sum(1 for i in issues if i.status == IssueStatus.OPEN)
    in_progress_bugs = sum(1 for i in issues if i.status == IssueStatus.IN_PROGRESS)
    in_review_bugs = sum(1 for i in issues if i.status == IssueStatus.IN_REVIEW)
    resolved_only_bugs = sum(1 for i in issues if i.status == IssueStatus.RESOLVED)
    closed_only_bugs = sum(1 for i in issues if i.status == IssueStatus.CLOSED)
    resolved_bugs = resolved_only_bugs + closed_only_bugs
    critical_bugs = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL)
    assigned_bugs = sum(1 for i in issues if i.assigned_developer_id == current_user.id)

    resolution_rate = round((resolved_bugs / total_bugs) * 100, 1) if total_bugs > 0 else 0.0

    # 1. Defects by Severity
    severity_counts = {
        "low": sum(1 for i in issues if i.severity == IssueSeverity.LOW),
        "medium": sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM),
        "high": sum(1 for i in issues if i.severity == IssueSeverity.HIGH),
        "critical": sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL),
    }

    # 2. Defects by Status
    status_counts = {
        "open": open_bugs,
        "in_progress": in_progress_bugs,
        "in_review": in_review_bugs,
        "resolved": resolved_only_bugs,
        "closed": closed_only_bugs,
    }

    # 3. Defects by Category
    category_counts_dict = defaultdict(int)
    for i in issues:
        cat_name = (i.category or "").strip() or "General"
        category_counts_dict[cat_name] += 1

    by_category = [
        {
            "category": cat,
            "count": cnt,
            "percentage": round((cnt / total_bugs) * 100, 1) if total_bugs > 0 else 0.0,
        }
        for cat, cnt in sorted(category_counts_dict.items(), key=lambda x: (-x[1], x[0]))
    ]

    # 4. Developer Workload Breakdown
    dev_workload_map = defaultdict(lambda: {
        "developer": "",
        "count": 0,
        "active_count": 0,
        "resolved_count": 0,
        "open_count": 0,
        "in_progress_count": 0,
        "in_review_count": 0,
        "critical_count": 0,
    })

    for i in issues:
        dev_name = i.assigned_developer.username if i.assigned_developer else "Unassigned"
        entry = dev_workload_map[dev_name]
        entry["developer"] = dev_name
        entry["count"] += 1

        is_active = i.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]
        if is_active:
            entry["active_count"] += 1
        else:
            entry["resolved_count"] += 1

        if i.status == IssueStatus.OPEN:
            entry["open_count"] += 1
        elif i.status == IssueStatus.IN_PROGRESS:
            entry["in_progress_count"] += 1
        elif i.status == IssueStatus.IN_REVIEW:
            entry["in_review_count"] += 1

        if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL:
            entry["critical_count"] += 1

    dev_workload = sorted(
        list(dev_workload_map.values()),
        key=lambda x: (-x["active_count"], -x["count"], x["developer"]),
    )

    # 5. Resolution Times & Activity Logs
    issue_ids = [i.id for i in issues]
    res_logs = {}
    if issue_ids:
        logs = (
            db.query(ActivityLog)
            .filter(
                ActivityLog.issue_id.in_(issue_ids),
                (ActivityLog.action == "Bug Closed")
                | (ActivityLog.action == "Status Changed")
                | (ActivityLog.details.ilike("%resolved%"))
                | (ActivityLog.details.ilike("%closed%")),
            )
            .order_by(ActivityLog.created_at.asc())
            .all()
        )
        for log in logs:
            if log.issue_id not in res_logs:
                details = (log.details or "").lower()
                if "resolved" in details or "closed" in details or log.action == "Bug Closed":
                    res_logs[log.issue_id] = log.created_at

    resolution_durations_hours = []
    sev_durations = {
        IssueSeverity.LOW: [],
        IssueSeverity.MEDIUM: [],
        IssueSeverity.HIGH: [],
        IssueSeverity.CRITICAL: [],
    }

    resolved_dates = []
    for i in issues:
        if i.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]:
            res_time = res_logs.get(i.id) or i.updated_at or i.created_at
            resolved_dates.append(res_time)
            if i.created_at and res_time:
                diff_hours = max(0.0, (res_time - i.created_at).total_seconds() / 3600.0)
                resolution_durations_hours.append(diff_hours)
                if i.severity in sev_durations:
                    sev_durations[i.severity].append(diff_hours)

    avg_resolution_hours = (
        sum(resolution_durations_hours) / len(resolution_durations_hours)
        if resolution_durations_hours
        else None
    )
    avg_resolution_days = (
        round(avg_resolution_hours / 24.0, 2)
        if avg_resolution_hours is not None
        else None
    )

    resolution_by_severity = {}
    for sev, durs in sev_durations.items():
        sev_key = sev.value
        avg_h = sum(durs) / len(durs) if durs else None
        avg_d = round(avg_h / 24.0, 2) if avg_h is not None else None
        resolution_by_severity[sev_key] = {
            "avg_hours": round(avg_h, 2) if avg_h is not None else None,
            "avg_days": avg_d,
            "formatted": format_duration(avg_h),
            "formatted_days": f"{avg_d:.1f} days" if avg_d is not None else "N/A",
            "formatted_hours": f"{avg_h:.1f} hrs" if avg_h is not None else "N/A",
            "count": len(durs),
        }

    # 6. Monthly Defect Trends
    now = datetime.now(timezone.utc)
    monthly_trend_map = {}
    for month_offset in range(5, -1, -1):
        month_date = now - timedelta(days=30 * month_offset)
        month_key = month_date.strftime("%b %Y")
        monthly_trend_map[month_key] = {
            "month": month_key,
            "count": 0,
            "created_count": 0,
            "resolved_count": 0,
        }

    for i in issues:
        if i.created_at:
            m_key = i.created_at.strftime("%b %Y")
            if m_key in monthly_trend_map:
                monthly_trend_map[m_key]["created_count"] += 1
                monthly_trend_map[m_key]["count"] += 1

    for res_date in resolved_dates:
        if res_date:
            m_key = res_date.strftime("%b %Y")
            if m_key in monthly_trend_map:
                monthly_trend_map[m_key]["resolved_count"] += 1

    monthly_reports = list(monthly_trend_map.values())

    # 7. Recent Activities
    act_query = db.query(ActivityLog).options(joinedload(ActivityLog.user))
    if project_id:
        act_query = act_query.filter(ActivityLog.project_id == project_id)
    recent_activities = act_query.order_by(ActivityLog.created_at.desc()).limit(10).all()

    return {
        "summary": {
            "total_bugs": total_bugs,
            "open_bugs": open_bugs,
            "in_progress_bugs": in_progress_bugs,
            "in_review_bugs": in_review_bugs,
            "resolved_bugs": resolved_only_bugs,
            "closed_bugs": closed_only_bugs,
            "total_resolved_and_closed": resolved_bugs,
            "critical_bugs": critical_bugs,
            "assigned_bugs": assigned_bugs,
            "resolution_rate": resolution_rate,
            "avg_resolution_time_hours": round(avg_resolution_hours, 2) if avg_resolution_hours is not None else None,
            "avg_resolution_time_days": avg_resolution_days,
            "avg_resolution_time_formatted": format_duration(avg_resolution_hours),
            "avg_resolution_time_days_formatted": f"{avg_resolution_days:.1f} days" if avg_resolution_days is not None else "N/A",
            "avg_resolution_time_hours_formatted": f"{avg_resolution_hours:.1f} hrs" if avg_resolution_hours is not None else "N/A",
        },
        "charts": {
            "by_severity": severity_counts,
            "by_status": status_counts,
            "by_category": by_category,
            "category_counts": dict(category_counts_dict),
            "monthly_reports": monthly_reports,
            "developer_workload": dev_workload,
            "resolution_by_severity": resolution_by_severity,
        },
        "recent_activities": [ActivityLogResponse.model_validate(a) for a in recent_activities],
    }


@router.get(
    "/activity",
    response_model=list[ActivityLogResponse],
    summary="Get global system activity feed",
    description="Retrieve paginated activity logs across projects.",
    responses={
        200: {"description": "Activity stream", "model": list[ActivityLogResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def get_dashboard_activity(
    project_id: int | None = Query(None, description="Filter by project ID"),
    limit: int = Query(50, ge=1, le=200, description="Max logs to return"),
    skip: int = Query(0, ge=0, description="Records to skip"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve paginated activity stream."""
    query = db.query(ActivityLog).options(joinedload(ActivityLog.user))
    if project_id:
        query = query.filter(ActivityLog.project_id == project_id)
    return query.order_by(ActivityLog.created_at.desc()).offset(skip).limit(limit).all()
