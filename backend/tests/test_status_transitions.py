from app.models import ActivityLog, IssueStatus, Notification


def test_complete_status_transition_lifecycle(client, test_issue, developer_headers, db_session):
    """A defect should cleanly transition through all 5 workflow states: OPEN -> IN_PROGRESS -> IN_REVIEW -> RESOLVED -> CLOSED."""
    transitions = [
        IssueStatus.IN_PROGRESS,
        IssueStatus.IN_REVIEW,
        IssueStatus.RESOLVED,
        IssueStatus.CLOSED,
    ]

    for target_status in transitions:
        response = client.put(
            f"/api/issues/{test_issue.id}/status",
            json={"status": target_status.value},
            headers=developer_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == target_status.value


def test_status_transition_creates_activity_log(client, test_issue, developer_headers, db_session):
    """Transitioning status should write an audit log entry to the ActivityLog table."""
    response = client.put(
        f"/api/issues/{test_issue.id}/status",
        json={"status": "in_progress"},
        headers=developer_headers,
    )
    assert response.status_code == 200

    log = db_session.query(ActivityLog).filter(
        ActivityLog.issue_id == test_issue.id,
        ActivityLog.action == "Status Changed"
    ).order_by(ActivityLog.created_at.desc()).first()
    assert log is not None
    assert "in_progress" in (log.details or "")


def test_status_transition_to_closed_creates_bug_closed_log(client, test_issue, developer_headers, db_session):
    """Transitioning status to CLOSED should log 'Bug Closed' action."""
    response = client.put(
        f"/api/issues/{test_issue.id}/status",
        json={"status": "closed"},
        headers=developer_headers,
    )
    assert response.status_code == 200

    log = db_session.query(ActivityLog).filter(
        ActivityLog.issue_id == test_issue.id,
        ActivityLog.action == "Bug Closed"
    ).order_by(ActivityLog.created_at.desc()).first()
    assert log is not None


def test_status_transition_notifies_reporter(client, test_issue, qa_user, developer_headers, db_session):
    """Status update by developer should send a notification to the QA reporter."""
    response = client.put(
        f"/api/issues/{test_issue.id}/status",
        json={"status": "resolved"},
        headers=developer_headers,
    )
    assert response.status_code == 200

    notif = db_session.query(Notification).filter(
        Notification.user_id == qa_user.id,
    ).order_by(Notification.created_at.desc()).first()
    assert notif is not None
    assert "resolved" in notif.message.lower()


def test_status_transition_invalid_enum_rejected(client, test_issue, developer_headers):
    """Attempting to transition to an invalid status string must return HTTP 422."""
    response = client.put(
        f"/api/issues/{test_issue.id}/status",
        json={"status": "non_existent_status"},
        headers=developer_headers,
    )
    assert response.status_code == 422


def test_dashboard_stats_reflects_status_transitions(client, test_project, test_issue, developer_headers, admin_headers):
    """Dashboard statistics should dynamically update open, in_progress, resolved, and resolution rate counts."""
    # Move to resolved
    client.put(
        f"/api/issues/{test_issue.id}/status",
        json={"status": "resolved"},
        headers=developer_headers,
    )

    stats_res = client.get(f"/api/dashboard/stats?project_id={test_project.id}", headers=admin_headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["charts"]["by_status"]["resolved"] >= 1
    assert "avg_resolution_time_hours" in stats["summary"]
    assert "avg_resolution_time_days" in stats["summary"]
    assert "avg_resolution_time_formatted" in stats["summary"]
    assert "avg_resolution_time_days_formatted" in stats["summary"]
    assert "avg_resolution_time_hours_formatted" in stats["summary"]
    for sev_data in stats["charts"]["resolution_by_severity"].values():
        assert "avg_hours" in sev_data
        assert "avg_days" in sev_data
        assert "formatted" in sev_data
