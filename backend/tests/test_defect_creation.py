from app.models import ActivityLog


def test_create_defect_with_complete_fields(client, test_project, qa_user, qa_headers, developer_user, test_sprint, db_session):
    """Creating a defect with full attributes should succeed, persist to database, and link relationships."""
    payload = {
        "title": "Stripe 3DS verification modal freezes on iOS Safari",
        "description": "Summary:\n• Modal freezes after user submits SMS OTP.\n\nSteps to Reproduce:\n1. Open checkout on iOS Safari\n2. Enter card details\n3. Wait for 3DS SMS OTP modal\n4. Submit OTP\n\nExpected Result:\n• Modal dismisses and order confirmation renders.\n\nActual Result:\n• Spinner locks up indefinitely.",
        "steps_to_reproduce": "1. Open checkout\n2. Submit OTP",
        "expected_behavior": "Modal dismisses",
        "actual_behavior": "Spinner hangs",
        "severity": "critical",
        "priority": "high",
        "status": "open",
        "category": "Payment",
        "module": "Checkout / Gateway",
        "defect_type": "Functional Defect",
        "os": "iOS 17.5",
        "browser": "Mobile Safari",
        "assigned_developer_id": developer_user.id,
        "sprint_id": test_sprint.id,
    }

    response = client.post(f"/api/projects/{test_project.id}/issues", json=payload, headers=qa_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] is not None
    assert data["title"] == payload["title"]
    assert data["severity"] == "critical"
    assert data["priority"] == "high"
    assert data["status"] == "open"
    assert data["project_id"] == test_project.id
    assert data["reporter_id"] == qa_user.id
    assert data["assigned_developer_id"] == developer_user.id
    assert data["sprint_id"] == test_sprint.id

    # Verify ActivityLog created in DB
    log = db_session.query(ActivityLog).filter(ActivityLog.issue_id == data["id"]).first()
    assert log is not None
    assert log.action == "Bug Created"
    assert log.user_id == qa_user.id


def test_create_defect_minimal_fields_defaults_applied(client, test_project, reporter_headers):
    """Creating a defect with minimal required fields should apply appropriate defaults."""
    payload = {
        "title": "Minor typo in settings footer",
        "description": "The footer says 'Copright' instead of 'Copyright'.",
    }
    response = client.post(f"/api/projects/{test_project.id}/issues", json=payload, headers=reporter_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["severity"] == "medium"
    assert data["priority"] == "medium"
    assert data["status"] == "open"
    assert data["assigned_developer_id"] is None
    assert data["sprint_id"] is None


def test_create_defect_nonexistent_project_returns_404(client, qa_headers):
    """Attempting to file a defect under a non-existent project ID must return HTTP 404."""
    payload = {
        "title": "Bug in missing project",
        "description": "Some description",
    }
    response = client.post("/api/projects/99999/issues", json=payload, headers=qa_headers)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_create_defect_unauthenticated_rejected(client, test_project):
    """Attempting to file a defect without authentication must return HTTP 401."""
    payload = {
        "title": "Unauthenticated defect",
        "description": "Some description",
    }
    response = client.post(f"/api/projects/{test_project.id}/issues", json=payload)
    assert response.status_code == 401


def test_create_defect_validation_empty_title_rejected(client, test_project, qa_headers):
    """Creating a defect with an empty title string must return HTTP 422."""
    payload = {
        "title": "",
        "description": "Valid description content",
    }
    response = client.post(f"/api/projects/{test_project.id}/issues", json=payload, headers=qa_headers)
    assert response.status_code == 422


def test_create_defect_validation_invalid_severity_enum(client, test_project, qa_headers):
    """Providing an invalid severity string must return HTTP 422 validation error."""
    payload = {
        "title": "Valid defect title",
        "description": "Valid description",
        "severity": "ultra_mega_critical",
    }
    response = client.post(f"/api/projects/{test_project.id}/issues", json=payload, headers=qa_headers)
    assert response.status_code == 422


def test_ai_assist_expansion_workflow(client, qa_headers):
    """AI Copilot Assist endpoint must expand brief raw bug notes into standardized line-by-line format."""
    payload = {
        "raw_description": "payment failed with 500 error when clicking checkout button on mac chrome"
    }
    response = client.post("/api/ai/assist", json=payload, headers=qa_headers)
    assert response.status_code == 200
    data = response.json()
    assert "formatted_report" in data
    report = data["formatted_report"]
    assert "title" in report
    assert "description" in report
    assert "steps_to_reproduce" in report


def test_ai_classify_defect_taxonomy_workflow(client, qa_headers):
    """AI Defect Classification must accurately infer Category, Module, Defect Type, and Severity."""
    payload = {
        "description": "Unable to complete order because payment gateway returns 500 internal server error on stripe charge submit",
        "title": "Payment gateway failure"
    }
    response = client.post("/api/ai/classify-defect", json=payload, headers=qa_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] in ["Payment", "Finance", "Checkout"]
    assert "suggested_severity" in data
    assert "suggested_priority" in data
    assert data["confidence"] > 0


def test_ai_duplicate_prevention_workflow(client, test_project, test_issue, qa_headers):
    """Detecting duplicates against existing project tickets should flag high token similarity matches."""
    payload = {
        "project_id": test_project.id,
        "title": "Payment checkout 500 error on card submit",
        "description": "Checkout crashes with 500 error when clicking pay now with credit card",
    }
    response = client.post("/api/ai/detect-duplicates", json=payload, headers=qa_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["has_duplicates"] is True
    assert len(data["potential_duplicates"]) >= 1
    assert data["potential_duplicates"][0]["id"] == test_issue.id
