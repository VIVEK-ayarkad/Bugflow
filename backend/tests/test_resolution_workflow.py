from app.models import Comment, Issue, IssuePriority, IssueSeverity, IssueStatus


def test_issue_resolution_assistance_endpoint(client, test_issue, developer_headers):
    """GET /api/issues/{id}/resolution-assistance should return actionable diagnostic areas and suggested fixes."""
    response = client.get(f"/api/issues/{test_issue.id}/resolution-assistance", headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "investigation_areas" in data
    assert len(data["investigation_areas"]) >= 1
    assert "possible_resolution" in data
    assert data["possible_resolution"] is not None
    assert "confidence" in data
    assert data["confidence"] > 0


def test_standalone_ai_resolution_assistance(client, developer_headers):
    """POST /api/ai/resolution-assistance should generate resolution guidance from an arbitrary bug description."""
    payload = {
        "title": "Payment gateway 500 error on checkout",
        "description": "API returned 500 internal server error due to unhandled null response from stripe card verification token",
        "category": "Payment",
        "module": "Checkout / Gateway",
        "severity": "high",
    }
    response = client.post("/api/ai/resolution-assistance", json=payload, headers=developer_headers)
    assert response.status_code == 200
    data = response.json()
    assert "investigation_areas" in data
    assert "possible_resolution" in data
    assert "severity_mitigation" in data
    assert "context_signals_used" in data


def test_root_cause_investigation_suggestions_and_disclaimer(client, developer_headers):
    """The system suggests areas developers should investigate with an explicit non-guaranteed suggestion disclaimer."""
    # Test 1: API / Timeout
    api_payload = {
        "title": "API request timeout on checkout",
        "description": "Payment endpoint returns gateway timeout after 30 seconds",
        "category": "Payment",
    }
    resp = client.post("/api/ai/resolution-assistance", json=api_payload, headers=developer_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "investigation_disclaimer" in data
    assert "suggestions" in data["investigation_disclaimer"].lower() or "not guaranteed" in data["investigation_disclaimer"].lower()
    areas = " ".join(data["investigation_areas"]).lower()
    assert "timeout" in areas or "api" in areas or "gateway" in areas

    # Test 2: Database / Connection
    db_payload = {
        "title": "Database connection pool timeout",
        "description": "Queries failing with connection errors during high traffic",
        "category": "Database",
    }
    resp_db = client.post("/api/ai/resolution-assistance", json=db_payload, headers=developer_headers)
    assert resp_db.status_code == 200
    db_areas = " ".join(resp_db.json()["investigation_areas"]).lower()
    assert "database" in db_areas or "connection" in db_areas or "query" in db_areas

    # Test 3: Auth / Middleware
    auth_payload = {
        "title": "JWT verification failure on protected routes",
        "description": "Users receiving 401 Unauthorized after token refresh",
        "category": "Authentication",
    }
    resp_auth = client.post("/api/ai/resolution-assistance", json=auth_payload, headers=developer_headers)
    assert resp_auth.status_code == 200
    auth_areas = " ".join(resp_auth.json()["investigation_areas"]).lower()
    assert "authentication" in auth_areas or "token" in auth_areas or "middleware" in auth_areas or "cors" in auth_areas


def test_historical_resolution_retrieval_knowledge_base(client, test_project, developer_user, developer_headers, db_session):
    """When a similar defect has already been resolved, the system returns Related Defect, Root Cause, Resolution, and Developer Comments."""
    # 1. Seed a historical resolved defect with developer fix comments
    past_defect = Issue(
        project_id=test_project.id,
        reporter_id=developer_user.id,
        assigned_developer_id=developer_user.id,
        title="Payment gateway crashes on checkout card submission",
        description="Checkout endpoint crashes with 500 error when clicking submit with card",
        category="Payment",
        module="Checkout",
        severity=IssueSeverity.HIGH,
        priority=IssuePriority.HIGH,
        status=IssueStatus.RESOLVED,
    )
    db_session.add(past_defect)
    db_session.commit()
    db_session.refresh(past_defect)

    # 2. Add developer comments explaining root cause and resolution
    past_comment = Comment(
        issue_id=past_defect.id,
        user_id=developer_user.id,
        content="Root cause: Unhandled null in card.status payload. Resolution: Added null check and retry policy.",
    )
    db_session.add(past_comment)
    db_session.commit()

    # 3. Query resolution assistance for a new similar defect
    payload = {
        "project_id": test_project.id,
        "title": "Payment gateway 500 error on checkout submit",
        "description": "Checkout crashes with 500 error when clicking submit payment",
        "category": "Payment",
        "module": "Checkout",
        "severity": "high",
    }
    response = client.post("/api/ai/resolution-assistance", json=payload, headers=developer_headers)
    assert response.status_code == 200
    data = response.json()

    assert "historical_resolutions" in data
    assert len(data["historical_resolutions"]) >= 1

    hist = data["historical_resolutions"][0]
    # Verify Related Defect Metadata
    assert hist["defect_id"] == past_defect.id
    assert hist["defect_key"] == f"DEF-{past_defect.id}"
    assert hist["title"] == past_defect.title
    assert hist["status"] == "resolved"
    assert hist["similarity_score"] >= 35.0

    # Verify Previous Root Cause
    assert "previous_root_cause" in hist
    assert len(hist["previous_root_cause"]) > 0

    # Verify Previous Resolution
    assert "previous_resolution" in hist
    assert len(hist["previous_resolution"]) > 0

    # Verify Relevant Developer Comments
    assert "relevant_developer_comments" in hist
    assert len(hist["relevant_developer_comments"]) >= 1
    assert hist["relevant_developer_comments"][0]["author"] == developer_user.username
    assert "Root cause" in hist["relevant_developer_comments"][0]["content"]


def test_complete_resolution_cycle_with_comments_and_pdf(client, test_issue, developer_headers, developer_user, db_session):
    """A developer fetches resolution assistance, comments the technical fix, resolves the bug, and exports the PDF."""
    # 1. Fetch Resolution Assistance
    res_assist = client.get(f"/api/issues/{test_issue.id}/resolution-assistance", headers=developer_headers)
    assert res_assist.status_code == 200
    fix_advice = res_assist.json()["possible_resolution"]

    # 2. Post Fix to Comments
    comment_payload = {
        "content": f"Resolved: {fix_advice}\nApplied fix in PR #42."
    }
    comment_res = client.post(f"/api/issues/{test_issue.id}/comments", json=comment_payload, headers=developer_headers)
    assert comment_res.status_code == 201

    # 3. Transition to RESOLVED
    stat_res = client.put(f"/api/issues/{test_issue.id}/status", json={"status": "resolved"}, headers=developer_headers)
    assert stat_res.status_code == 200
    assert stat_res.json()["status"] == "resolved"

    # 4. Transition to CLOSED
    close_res = client.put(f"/api/issues/{test_issue.id}/status", json={"status": "closed"}, headers=developer_headers)
    assert close_res.status_code == 200
    assert close_res.json()["status"] == "closed"

    # 5. Export Defect Investigation PDF Report
    pdf_res = client.get(f"/api/issues/{test_issue.id}/pdf", headers=developer_headers)
    assert pdf_res.status_code == 200
    assert pdf_res.headers.get("content-type") == "application/pdf"
    assert len(pdf_res.content) > 1000  # Non-empty binary PDF stream
