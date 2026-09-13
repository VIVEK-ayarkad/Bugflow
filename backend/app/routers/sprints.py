from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.activity import log_activity
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import Issue, IssuePriority, IssueSeverity, IssueStatus, Project, Sprint, SprintStatus, User, utc_now
from app.schemas import (
    SprintBulkAssignRequest,
    SprintCompleteRequest,
    SprintCreate,
    SprintMetricsResponse,
    SprintResponse,
    SprintUpdate,
)

router = APIRouter(prefix="/api/sprints", tags=["sprints"])


@router.get(
    "",
    response_model=list[SprintResponse],
    summary="List all sprints",
    description="Retrieve all sprints across the platform or filter by specific project ID.",
    responses={
        200: {"description": "List of sprints", "model": list[SprintResponse]},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def list_sprints(
    project_id: int | None = Query(None, description="Optional Project ID filter"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List sprints with optional project filtering."""
    query = db.query(Sprint)
    if project_id:
        query = query.filter(Sprint.project_id == project_id)
    return query.order_by(Sprint.created_at.desc()).all()


@router.post(
    "",
    response_model=SprintResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new sprint",
    description="Create a sprint milestone within a project. Status defaults to 'planning'.",
    responses={
        201: {"description": "Sprint created successfully", "model": SprintResponse},
        404: {"description": "Project not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def create_sprint(
    payload: SprintCreate,
    project_id: int = Query(..., description="Target project ID for the sprint"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new sprint milestone."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project #{project_id} not found")

    sprint = Sprint(
        project_id=project_id,
        name=payload.name.strip(),
        goal=payload.goal.strip() if payload.goal else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=SprintStatus.PLANNING,
    )
    db.add(sprint)
    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Created",
        details=f"Sprint '{sprint.name}' created for project '{project.name}'",
        project_id=project_id,
    )
    return sprint


@router.get(
    "/{sprint_id}",
    response_model=SprintResponse,
    summary="Get sprint by ID",
    description="Retrieve specific sprint details.",
    responses={
        200: {"description": "Sprint details", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def get_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get sprint details."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")
    return sprint


@router.get(
    "/{sprint_id}/metrics",
    response_model=SprintMetricsResponse,
    summary="Get sprint metrics and burndown data",
    description="Calculates comprehensive status breakdown, developer workload, and ideal vs actual burndown progression.",
    responses={
        200: {"description": "Sprint metrics", "model": SprintMetricsResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def get_sprint_metrics(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compute detailed sprint metrics, burndown curve, and team workload."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    issues = sprint.issues
    total = len(issues)
    open_cnt = sum(1 for i in issues if i.status == IssueStatus.OPEN)
    in_prog_cnt = sum(1 for i in issues if i.status == IssueStatus.IN_PROGRESS)
    in_rev_cnt = sum(1 for i in issues if i.status == IssueStatus.IN_REVIEW)
    resolved_cnt = sum(1 for i in issues if i.status == IssueStatus.RESOLVED)
    closed_cnt = sum(1 for i in issues if i.status == IssueStatus.CLOSED)

    crit_cnt = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL)
    high_cnt = sum(1 for i in issues if i.severity == IssueSeverity.HIGH and i.priority != IssuePriority.CRITICAL)
    med_cnt = sum(1 for i in issues if i.severity == IssueSeverity.MEDIUM)
    low_cnt = sum(1 for i in issues if i.severity == IssueSeverity.LOW)

    completed_total = resolved_cnt + closed_cnt
    completion_rate = round(completed_total / total, 2) if total > 0 else 0.0

    # Calculate days timeline
    now = utc_now()
    days_total = None
    days_remaining = None
    if sprint.start_date and sprint.end_date:
        total_delta = (sprint.end_date - sprint.start_date).days
        days_total = max(1, total_delta)
        remaining_delta = (sprint.end_date - now).days
        days_remaining = max(0, remaining_delta) if sprint.end_date > now else 0
    elif sprint.end_date:
        remaining_delta = (sprint.end_date - now).days
        days_remaining = max(0, remaining_delta) if sprint.end_date > now else 0

    # Developer workload
    dev_map: dict[str, dict[str, Any]] = {}
    for issue in issues:
        dev_id = issue.assigned_developer_id
        dev_name = issue.assigned_developer.username if issue.assigned_developer else "Unassigned"
        key = str(dev_id or "unassigned")
        if key not in dev_map:
            dev_map[key] = {
                "developer_id": dev_id,
                "username": dev_name,
                "total": 0,
                "open": 0,
                "resolved": 0,
            }
        dev_map[key]["total"] += 1
        if issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]:
            dev_map[key]["resolved"] += 1
        else:
            dev_map[key]["open"] += 1

    workload = list(dev_map.values())
    workload.sort(key=lambda x: x["total"], reverse=True)

    # ── High-Precision Intraday Burndown Progression Calculation ──
    num_days = days_total if days_total and 1 <= days_total <= 60 else 14
    start_dt = sprint.start_date or (sprint.created_at if sprint.created_at else now - timedelta(days=7))
    end_dt = sprint.end_date or (start_dt + timedelta(days=num_days))
    if end_dt <= start_dt:
        end_dt = start_dt + timedelta(days=14)

    total_seconds = max(1.0, (end_dt - start_dt).total_seconds())

    # Collect discrete resolution / status update events
    events: list[dict[str, Any]] = [
        {
            "timestamp": start_dt,
            "label": "Sprint Started",
            "type": "start",
            "issue_id": None,
        }
    ]

    for issue in issues:
        if issue.updated_at and issue.updated_at >= start_dt and issue.updated_at <= now:
            if issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]:
                events.append({
                    "timestamp": issue.updated_at,
                    "label": f"Resolved: #{issue.id} {issue.title[:32]}",
                    "type": "resolution",
                    "issue_id": issue.id,
                })
            else:
                events.append({
                    "timestamp": issue.updated_at,
                    "label": f"Updated: #{issue.id} ({issue.status.value})",
                    "type": "update",
                    "issue_id": issue.id,
                })

    # Current live state checkpoint
    if now >= start_dt:
        events.append({
            "timestamp": now,
            "label": "Current Live State",
            "type": "now",
            "issue_id": None,
        })

    # Sort events by timestamp
    events.sort(key=lambda x: x["timestamp"])

    intraday_points: list[dict[str, Any]] = []
    seen_times = set()
    for ev in events:
        ts = ev["timestamp"]
        ts_str = ts.strftime("%Y-%m-%d %H:%M:%S")
        if ts_str in seen_times:
            continue
        seen_times.add(ts_str)

        elapsed_sec = max(0.0, (ts - start_dt).total_seconds())
        day_prog = min(float(num_days), (elapsed_sec / total_seconds) * num_days)
        ideal = max(0.0, round(total - (total * (elapsed_sec / total_seconds)), 1))

        resolved_so_far = sum(
            1 for i in issues
            if i.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
            and (i.updated_at is None or i.updated_at <= ts)
        )
        actual = max(0, total - resolved_so_far)

        formatted_date = ts.strftime("%b %d, %I:%M %p")

        intraday_points.append({
            "day_index": round(day_prog, 2),
            "date": formatted_date,
            "timestamp": ts.isoformat(),
            "ideal_remaining": ideal,
            "actual_remaining": actual,
            "resolved_count": resolved_so_far,
            "open_count": actual,
            "event_label": ev["label"],
            "is_live": (ev["type"] == "now"),
        })

    # Append future days up to num_days so the ideal burn slope spans the full sprint
    current_max_day = intraday_points[-1]["day_index"] if intraday_points else 0
    next_day_start = max(1, int(current_max_day) + 1)
    for day_idx in range(next_day_start, num_days + 1):
        day_timestamp = start_dt + timedelta(days=day_idx)
        day_date = day_timestamp.strftime("%b %d")
        ideal = round(total - (total * (day_idx / num_days)), 1) if num_days > 0 else 0
        intraday_points.append({
            "day_index": day_idx,
            "date": day_date,
            "timestamp": day_timestamp.isoformat(),
            "ideal_remaining": max(0, ideal),
            "actual_remaining": None,
            "resolved_count": None,
            "open_count": None,
            "event_label": f"Day {day_idx} Target",
            "is_live": False,
        })

    burndown = intraday_points

    return SprintMetricsResponse(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        status=sprint.status,
        start_date=sprint.start_date,
        end_date=sprint.end_date,
        goal=sprint.goal,
        total_issues=total,
        open_issues=open_cnt,
        in_progress_issues=in_prog_cnt,
        in_review_issues=in_rev_cnt,
        resolved_issues=resolved_cnt,
        closed_issues=closed_cnt,
        critical_issues=crit_cnt,
        high_issues=high_cnt,
        medium_issues=med_cnt,
        low_issues=low_cnt,
        completion_rate=completion_rate,
        days_total=days_total,
        days_remaining=days_remaining,
        workload=workload,
        burndown=burndown,
    )


@router.put(
    "/{sprint_id}",
    response_model=SprintResponse,
    summary="Update sprint",
    description="Update sprint name, goal, date boundaries, or status.",
    responses={
        200: {"description": "Sprint updated successfully", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def update_sprint(
    sprint_id: int,
    payload: SprintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update sprint properties."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in ["name", "goal"] and isinstance(value, str):
            value = value.strip()
        setattr(sprint, field, value)

    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Updated",
        details=f"Sprint '{sprint.name}' updated",
        project_id=sprint.project_id,
    )
    return sprint


@router.post(
    "/{sprint_id}/start",
    response_model=SprintResponse,
    summary="Start sprint",
    description="Transition sprint status from 'planning' to 'active'.",
    responses={
        200: {"description": "Sprint activated", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def start_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start an active sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    sprint.status = SprintStatus.ACTIVE
    if not sprint.start_date:
        sprint.start_date = utc_now()
    if not sprint.end_date:
        sprint.end_date = utc_now() + timedelta(days=14)

    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Started",
        details=f"Sprint '{sprint.name}' marked active",
        project_id=sprint.project_id,
    )
    return sprint


@router.post(
    "/{sprint_id}/complete",
    response_model=SprintResponse,
    summary="Complete sprint",
    description="Transition sprint status to 'completed' with smart issue rollover options.",
    responses={
        200: {"description": "Sprint completed", "model": SprintResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def complete_sprint(
    sprint_id: int,
    payload: SprintCompleteRequest | None = Body(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a sprint and optionally rollover open issues."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    sprint.status = SprintStatus.COMPLETED

    # Rollover unresolved issues if requested
    if payload:
        open_issues = db.query(Issue).filter(
            Issue.sprint_id == sprint_id,
            Issue.status.notin_([IssueStatus.RESOLVED, IssueStatus.CLOSED]),
        ).all()

        if payload.action == "rollover" and payload.rollover_sprint_id:
            target_sprint = db.query(Sprint).filter(Sprint.id == payload.rollover_sprint_id).first()
            if target_sprint:
                for issue in open_issues:
                    issue.sprint_id = target_sprint.id
        elif payload.action == "backlog":
            for issue in open_issues:
                issue.sprint_id = None

    db.commit()
    db.refresh(sprint)

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Completed",
        details=f"Sprint '{sprint.name}' completed",
        project_id=sprint.project_id,
    )
    return sprint


@router.post(
    "/{sprint_id}/issues/bulk-assign",
    summary="Bulk assign or remove issues from sprint",
    description="Add or move multiple issues to/from the sprint in a single atomic transaction.",
    responses={
        200: {"description": "Bulk assignment successful"},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def bulk_assign_sprint_issues(
    sprint_id: int,
    payload: SprintBulkAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk assign or remove issues from a sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    target_sprint_id = sprint.id if payload.action == "add" else None
    updated = (
        db.query(Issue)
        .filter(Issue.id.in_(payload.issue_ids), Issue.project_id == sprint.project_id)
        .update({"sprint_id": target_sprint_id}, synchronize_session="fetch")
    )
    db.commit()

    log_activity(
        db,
        user_id=current_user.id,
        action="Sprint Issues Assigned",
        details=f"Moved {updated} issue(s) {'into' if payload.action == 'add' else 'out of'} sprint '{sprint.name}'",
        project_id=sprint.project_id,
    )
    return {"success": True, "count": updated, "action": payload.action, "sprint_id": sprint.id}


@router.delete(
    "/{sprint_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete sprint",
    description="Delete a sprint and unlink assigned issues to maintain referential consistency.",
    responses={
        204: {"description": "Sprint deleted successfully"},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def delete_sprint(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a sprint."""
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Sprint #{sprint_id} not found")

    # Unlink assigned issues
    db.query(Issue).filter(Issue.sprint_id == sprint_id).update({"sprint_id": None})
    db.delete(sprint)
    db.commit()
