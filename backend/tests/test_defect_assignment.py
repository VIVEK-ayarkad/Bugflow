from app.models import ActivityLog, Notification, User, UserRole


def test_assign_defect_to_developer(client, test_issue, developer_user, pm_headers, db_session):
    """Assigning a defect to a developer should update the record, log activity, and notify the assignee."""
    payload = {
        "assigned_developer_id": developer_user.id
    }
    response = client.put(f"/api/issues/{test_issue.id}/assign", json=payload, headers=pm_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_developer_id"] == developer_user.id
    assert data["assigned_developer"]["username"] == developer_user.username

    # Verify notification created for the assigned developer
    notif = db_session.query(Notification).filter(
        Notification.user_id == developer_user.id,
        Notification.title == "Bug Assigned to You"
    ).first()
    assert notif is not None
    assert str(test_issue.id) in notif.message

    # Verify ActivityLog audit entry
    log = db_session.query(ActivityLog).filter(
        ActivityLog.issue_id == test_issue.id,
        ActivityLog.action == "Bug Assigned"
    ).order_by(ActivityLog.created_at.desc()).first()
    assert log is not None
    assert developer_user.username in (log.details or "")


def test_unassign_defect(client, test_issue, pm_headers):
    """Setting assigned_developer_id to null should unassign the issue."""
    payload = {
        "assigned_developer_id": None
    }
    response = client.put(f"/api/issues/{test_issue.id}/assign", json=payload, headers=pm_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["assigned_developer_id"] is None
    assert data["assigned_developer"] is None


def test_assign_defect_nonexistent_developer_returns_404(client, test_issue, pm_headers):
    """Attempting to assign a defect to a non-existent user ID must return HTTP 404."""
    payload = {
        "assigned_developer_id": 99999
    }
    response = client.put(f"/api/issues/{test_issue.id}/assign", json=payload, headers=pm_headers)
    assert response.status_code == 404
    assert "Target developer not found" in response.json()["detail"]


def test_reassign_defect_notifies_new_developer(client, test_issue, developer_user, pm_headers, db_session):
    """Reassigning a defect to another developer should dispatch a notification to the new developer."""
    # Create another developer
    from app.auth import hash_password
    dev2 = User(
        email="dev2@bugflow.dev",
        username="dev_alex",
        hashed_password=hash_password("DevPass123!"),
        role=UserRole.DEVELOPER,
    )
    db_session.add(dev2)
    db_session.commit()
    db_session.refresh(dev2)

    payload = {"assigned_developer_id": dev2.id}
    response = client.put(f"/api/issues/{test_issue.id}/assign", json=payload, headers=pm_headers)
    assert response.status_code == 200

    notif = db_session.query(Notification).filter(
        Notification.user_id == dev2.id,
        Notification.title == "Bug Assigned to You"
    ).first()
    assert notif is not None


def test_filter_issues_by_assigned_developer(client, test_issue, developer_user, developer_headers):
    """Filtering issues by assigned_developer_id should only return issues assigned to that developer."""
    response = client.get(f"/api/issues?assigned_developer_id={developer_user.id}", headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for issue in data:
        assert issue["assigned_developer_id"] == developer_user.id


def test_filter_my_bugs_only(client, test_issue, developer_user, developer_headers):
    """Setting my_bugs_only=true should filter issues assigned to or reported by current user."""
    response = client.get("/api/issues?my_bugs_only=true", headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for issue in data:
        assert issue["assigned_developer_id"] == developer_user.id or issue["reporter_id"] == developer_user.id
