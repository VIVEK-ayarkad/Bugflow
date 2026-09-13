import sys
from pathlib import Path

# Ensure backend root is on sys.path
BACKEND_ROOT = str(Path(__file__).resolve().parent)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

def test_api_suite():
    print("🚀 Starting BugFlow REST API Verification Test Suite...\n")
    passed = 0
    failed = 0

    def assert_test(condition, test_name, details=""):
        nonlocal passed, failed
        if condition:
            print(f"  ✅ PASS: {test_name}")
            passed += 1
        else:
            print(f"  ❌ FAIL: {test_name} - {details}")
            failed += 1

    # ── 1. Health & OpenAPI Spec ─────────────────────────────────────────────
    print("📋 [1/7] Testing Health & Swagger/OpenAPI Documentation...")
    res = client.get("/api/health")
    assert_test(res.status_code == 200 and res.json().get("status") == "ok", "GET /api/health")

    res = client.get("/api/openapi.json")
    assert_test(res.status_code == 200, "GET /api/openapi.json returns 200")
    openapi = res.json()
    assert_test("paths" in openapi and len(openapi["paths"]) >= 25, f"OpenAPI paths documented ({len(openapi.get('paths', {}))} endpoints found)")
    assert_test("tags" in openapi and len(openapi["tags"]) >= 10, f"OpenAPI tags documented ({len(openapi.get('tags', []))} tags found)")
    assert_test(openapi.get("info", {}).get("title") == "BugFlow API", "OpenAPI title matches BugFlow API")

    # ── 2. Auth: Register, Login (JSON + Form), Me, Profile, Logout ──────────
    print("\n🔐 [2/7] Testing Authentication & Route Security...")

    # Test validation error on short password
    bad_reg = client.post("/api/auth/register", json={"email": "bad@test.com", "username": "baduser", "password": "123"})
    assert_test(bad_reg.status_code == 422 and "Password" in bad_reg.text or "password" in bad_reg.text, "Validation: Reject short password (HTTP 422)")

    # Test validation error on invalid email
    bad_email = client.post("/api/auth/register", json={"email": "not-an-email", "username": "bademailuser", "password": "ValidPassword123!"})
    assert_test(bad_email.status_code == 422, "Validation: Reject invalid email format (HTTP 422)")

    import time
    ts = int(time.time())
    admin_email = f"admin_{ts}@bugflow.dev"
    admin_user = f"admin_{ts}"
    dev_email = f"dev_{ts}@bugflow.dev"
    dev_user = f"dev_{ts}"

    # Register admin (or first user)
    reg_admin = client.post("/api/auth/register", json={
        "email": admin_email,
        "username": admin_user,
        "password": "AdminPassword123!",
        "role": "admin"
    })
    assert_test(reg_admin.status_code == 201, "POST /api/auth/register creates user (HTTP 201)")
    admin_token = reg_admin.json().get("access_token")
    admin_id = reg_admin.json()["user"]["id"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Register developer
    reg_dev = client.post("/api/auth/register", json={
        "email": dev_email,
        "username": dev_user,
        "password": "DevPassword123!",
        "role": "developer"
    })
    assert_test(reg_dev.status_code == 201, "POST /api/auth/register creates developer")
    dev_token = reg_dev.json().get("access_token")
    dev_id = reg_dev.json()["user"]["id"]
    dev_headers = {"Authorization": f"Bearer {dev_token}"}

    # Test JSON login
    login_res = client.post("/api/auth/login", json={"email": admin_email, "password": "AdminPassword123!"})
    assert_test(login_res.status_code == 200 and "access_token" in login_res.json(), "POST /api/auth/login (JSON) returns JWT token")

    # Test OAuth2 form login for Swagger UI Authorize
    oauth_res = client.post("/api/auth/token", data={"username": admin_email, "password": "AdminPassword123!"})
    assert_test(oauth_res.status_code == 200 and "access_token" in oauth_res.json(), "POST /api/auth/token (OAuth2 Form) works for Swagger UI")

    # Test invalid login credentials
    bad_login = client.post("/api/auth/login", json={"email": admin_email, "password": "WrongPassword!"})
    assert_test(bad_login.status_code == 401 and "Invalid" in bad_login.json().get("detail", ""), "Error Handling: 401 on invalid login password")

    # Test GET /api/auth/me without token -> 401
    unauth_me = client.get("/api/auth/me")
    assert_test(unauth_me.status_code == 401, "Security: Protected route rejects missing token (HTTP 401)")

    # Test GET /api/auth/me with token
    auth_me = client.get("/api/auth/me", headers=admin_headers)
    assert_test(auth_me.status_code == 200 and auth_me.json()["email"] == admin_email, "GET /api/auth/me returns authenticated user")

    # Test PUT /api/auth/profile
    prof_res = client.put("/api/auth/profile", json={"username": f"admin_upd_{ts}"}, headers=admin_headers)
    assert_test(prof_res.status_code == 200 and prof_res.json()["username"] == f"admin_upd_{ts}", "PUT /api/auth/profile updates profile")

    # Test POST /api/auth/logout
    logout_res = client.post("/api/auth/logout", headers=admin_headers)
    assert_test(logout_res.status_code == 200, "POST /api/auth/logout returns 200")

    # ── 3. Users API & RBAC ──────────────────────────────────────────────────
    print("\n👥 [3/7] Testing Users API & Role-Based Access Control...")
    users_res = client.get("/api/users", headers=admin_headers)
    assert_test(users_res.status_code == 200 and isinstance(users_res.json(), list), "GET /api/users lists users")

    get_u = client.get(f"/api/users/{dev_id}", headers=admin_headers)
    assert_test(get_u.status_code == 200 and get_u.json()["id"] == dev_id, "GET /api/users/{id} retrieves user by ID")

    # Dev trying to access admin endpoint -> 403 Forbidden
    forbidden_res = client.get("/api/admin/users", headers=dev_headers)
    assert_test(forbidden_res.status_code == 403, "RBAC Security: Non-admin rejected from /api/admin/* (HTTP 403)")

    # ── 4. Projects & Sprints ────────────────────────────────────────────────
    print("\n📁 [4/7] Testing Projects & Sprints APIs...")
    proj_res = client.post("/api/projects", json={
        "name": f"Project Test {ts}",
        "description": "Integration test project"
    }, headers=admin_headers)
    assert_test(proj_res.status_code == 201, "POST /api/projects creates project")
    project_id = proj_res.json()["id"]

    # Get project
    p_get = client.get(f"/api/projects/{project_id}", headers=admin_headers)
    assert_test(p_get.status_code == 200 and p_get.json()["name"] == f"Project Test {ts}", "GET /api/projects/{id}")

    # Add member
    member_res = client.post(f"/api/projects/{project_id}/members", json={
        "user_id": dev_id,
        "role_in_project": "QA Lead"
    }, headers=admin_headers)
    assert_test(member_res.status_code == 201, "POST /api/projects/{id}/members adds member")

    # List members
    members_list = client.get(f"/api/projects/{project_id}/members", headers=admin_headers)
    assert_test(members_list.status_code == 200 and len(members_list.json()) >= 2, "GET /api/projects/{id}/members")

    # Sprint validation: end_date < start_date -> 422
    bad_sprint = client.post(f"/api/sprints?project_id={project_id}", json={
        "name": "Invalid Sprint",
        "start_date": "2026-09-10T10:00:00",
        "end_date": "2026-09-01T10:00:00"
    }, headers=admin_headers)
    assert_test(bad_sprint.status_code == 422, "Validation: Reject sprint with end_date < start_date (HTTP 422)")

    # Create valid sprint
    sprint_res = client.post(f"/api/sprints?project_id={project_id}", json={
        "name": f"Sprint 1 - {ts}",
        "goal": "Test sprint goal",
        "start_date": "2026-09-01T10:00:00",
        "end_date": "2026-09-15T10:00:00"
    }, headers=admin_headers)
    assert_test(sprint_res.status_code == 201, "POST /api/sprints creates sprint")
    sprint_id = sprint_res.json()["id"]

    # Project sprints sub-resource
    p_sprints = client.get(f"/api/projects/{project_id}/sprints", headers=admin_headers)
    assert_test(p_sprints.status_code == 200 and len(p_sprints.json()) >= 1, "GET /api/projects/{id}/sprints sub-resource")

    # Start sprint
    start_sp = client.post(f"/api/sprints/{sprint_id}/start", headers=admin_headers)
    assert_test(start_sp.status_code == 200 and start_sp.json()["status"] == "active", "POST /api/sprints/{id}/start")

    # Sprint Metrics & Burndown calculation
    sp_metrics = client.get(f"/api/sprints/{sprint_id}/metrics", headers=admin_headers)
    assert_test(sp_metrics.status_code == 200 and "burndown" in sp_metrics.json() and "workload" in sp_metrics.json(), "GET /api/sprints/{id}/metrics (burndown & workload)")

    # ── 5. Issues, Comments, Attachments, PDF ────────────────────────────────
    print("\n🐛 [5/7] Testing Issues, Comments, Attachments, and PDFs...")
    issue_payload = {
        "title": "Payment gateway timeout on checkout",
        "description": "Summary: Payment Gateway timeout error.\nSteps to Reproduce:\n1. Add item\n2. Pay\nExpected: Success\nActual: 500 error",
        "severity": "high",
        "priority": "high",
        "category": "Payment",
        "module": "Checkout",
        "defect_type": "Functional Defect",
        "assigned_developer_id": dev_id,
        "sprint_id": sprint_id
    }
    issue_res = client.post(f"/api/projects/{project_id}/issues", json=issue_payload, headers=admin_headers)
    assert_test(issue_res.status_code == 201, "POST /api/projects/{id}/issues creates defect")
    issue_id = issue_res.json()["id"]

    # List all issues with filters
    issues_list = client.get(f"/api/issues?project_id={project_id}&severity=high", headers=admin_headers)
    assert_test(issues_list.status_code == 200 and len(issues_list.json()) >= 1, "GET /api/issues with query filters")

    # Get single issue
    issue_detail = client.get(f"/api/issues/{issue_id}", headers=admin_headers)
    assert_test(issue_detail.status_code == 200 and issue_detail.json()["id"] == issue_id, "GET /api/issues/{id}")

    # Update issue status
    stat_upd = client.put(f"/api/issues/{issue_id}/status", json={"status": "in_progress"}, headers=admin_headers)
    assert_test(stat_upd.status_code == 200 and stat_upd.json()["status"] == "in_progress", "PUT /api/issues/{id}/status")

    # Issue Activity Audit Log
    act_log = client.get(f"/api/issues/{issue_id}/activity", headers=admin_headers)
    assert_test(act_log.status_code == 200 and len(act_log.json()) >= 1, "GET /api/issues/{id}/activity returns defect audit history")

    # Add Comment
    comment_res = client.post(f"/api/issues/{issue_id}/comments", json={"content": "Investigated error logs. Null pointer exception found."}, headers=admin_headers)
    assert_test(comment_res.status_code == 201, "POST /api/issues/{id}/comments creates comment")
    comment_id = comment_res.json()["id"]

    # List Comments
    comments_list = client.get(f"/api/issues/{issue_id}/comments", headers=admin_headers)
    assert_test(comments_list.status_code == 200 and len(comments_list.json()) >= 1, "GET /api/issues/{id}/comments")

    # Edit Comment
    comm_edit = client.put(f"/api/comments/{comment_id}", json={"content": "Updated comment: Fixed in next commit."}, headers=admin_headers)
    assert_test(comm_edit.status_code == 200, "PUT /api/comments/{id} edits comment")

    # Test PDF Downloads
    issue_pdf = client.get(f"/api/issues/{issue_id}/pdf", headers=admin_headers)
    assert_test(issue_pdf.status_code == 200 and issue_pdf.headers.get("content-type") == "application/pdf", "GET /api/issues/{id}/pdf streams PDF report")

    proj_pdf = client.get(f"/api/projects/{project_id}/pdf", headers=admin_headers)
    assert_test(proj_pdf.status_code == 200 and proj_pdf.headers.get("content-type") == "application/pdf", "GET /api/projects/{id}/pdf streams project summary PDF")

    # Resolution Assistance
    res_assist = client.get(f"/api/issues/{issue_id}/resolution-assistance", headers=admin_headers)
    assert_test(res_assist.status_code == 200 and "investigation_areas" in res_assist.json(), "GET /api/issues/{id}/resolution-assistance")

    # Blast Radius Intelligence Endpoints
    proj_blast = client.get(f"/api/projects/{project_id}/blast-radius", headers=admin_headers)
    assert_test(
        proj_blast.status_code == 200
        and len(proj_blast.json().get("nodes", [])) >= 8
        and "system_blast_score" in proj_blast.json()
        and "containment_strategies" in proj_blast.json(),
        "GET /api/projects/{id}/blast-radius (system dependency graph & cascade report)"
    )

    issue_blast = client.get(f"/api/issues/{issue_id}/blast-radius", headers=admin_headers)
    assert_test(
        issue_blast.status_code == 200
        and issue_blast.json().get("epicenter_module") is not None
        and "direct_impact_modules" in issue_blast.json()
        and "cascade_risk_modules" in issue_blast.json(),
        "GET /api/issues/{id}/blast-radius (issue-focused blast radius & cascade risks)"
    )

    # ── 6. Dashboard, Notifications & Admin ──────────────────────────────────
    print("\n📊 [6/7] Testing Dashboard, Notifications & Admin Reports...")
    dash_stats = client.get(f"/api/dashboard/stats?project_id={project_id}", headers=admin_headers)
    assert_test(dash_stats.status_code == 200 and "summary" in dash_stats.json(), "GET /api/dashboard/stats")

    dash_act = client.get("/api/dashboard/activity", headers=admin_headers)
    assert_test(dash_act.status_code == 200 and isinstance(dash_act.json(), list), "GET /api/dashboard/activity")

    notifs = client.get("/api/notifications", headers=dev_headers)
    assert_test(notifs.status_code == 200 and len(notifs.json()) >= 1, "GET /api/notifications (dev received notification on assignment)")

    notif_id = notifs.json()[0]["id"]
    read_notif = client.put(f"/api/notifications/{notif_id}/read", headers=dev_headers)
    assert_test(read_notif.status_code == 200 and read_notif.json()["is_read"] is True, "PUT /api/notifications/{id}/read")

    admin_rep = client.get("/api/admin/reports", headers=admin_headers)
    assert_test(admin_rep.status_code == 200 and "system_metrics" in admin_rep.json(), "GET /api/admin/reports")

    admin_logs = client.get("/api/admin/logs", headers=admin_headers)
    assert_test(admin_logs.status_code == 200 and len(admin_logs.json()) >= 1, "GET /api/admin/logs returns system audit trail")

    # ── 7. AI Defect Intelligence Endpoints ──────────────────────────────────
    print("\n🤖 [7/7] Testing AI Defect Intelligence Endpoints...")
    classify_res = client.post("/api/ai/classify-defect", json={
        "description": "User clicks checkout and gets 500 internal server error on stripe credit card validation"
    }, headers=admin_headers)
    assert_test(classify_res.status_code == 200 and "category" in classify_res.json(), "POST /api/ai/classify-defect")

    assist_res = client.post("/api/ai/assist", json={
        "raw_description": "payment failed with 500 error on checkout"
    }, headers=admin_headers)
    assert_test(assist_res.status_code == 200, "POST /api/ai/assist")

    severity_res = client.post("/api/ai/predict-severity", json={
        "description": "Complete database outage, all users unable to login or checkout"
    }, headers=admin_headers)
    assert_test(severity_res.status_code == 200 and severity_res.json().get("predicted_severity") == "critical", "POST /api/ai/predict-severity (detects critical outage)")

    dup_res = client.post("/api/ai/detect-duplicates", json={
        "project_id": project_id,
        "title": "Payment gateway timeout",
        "description": "Payment gateway times out during card verification"
    }, headers=admin_headers)
    assert_test(dup_res.status_code == 200 and "has_duplicates" in dup_res.json(), "POST /api/ai/detect-duplicates")

    sprint_h = client.post(f"/api/ai/sprint-health/{sprint_id}", headers=admin_headers)
    assert_test(sprint_h.status_code == 200 and "health_score" in sprint_h.json(), "POST /api/ai/sprint-health/{id}")

    sprint_retro = client.post(f"/api/ai/sprint-retrospective/{sprint_id}", headers=admin_headers)
    assert_test(sprint_retro.status_code == 200 and "velocity_score" in sprint_retro.json() and "action_items" in sprint_retro.json(), "POST /api/ai/sprint-retrospective/{id}")

    sprint_adv = client.post(f"/api/ai/sprint-advisor/{sprint_id}", headers=admin_headers)
    assert_test(sprint_adv.status_code == 200 and "capacity_status" in sprint_adv.json(), "POST /api/ai/sprint-advisor/{id}")

    # Test Sprint Bulk Assign
    bulk_res = client.post(f"/api/sprints/{sprint_id}/issues/bulk-assign", json={
        "issue_ids": [issue_id],
        "action": "add"
    }, headers=admin_headers)
    assert_test(bulk_res.status_code == 200 and bulk_res.json()["success"] is True, "POST /api/sprints/{id}/issues/bulk-assign")

    sem_res = client.post("/api/ai/semantic-search", json={
        "query": "card charge fails on submit",
        "project_id": project_id
    }, headers=admin_headers)
    assert_test(sem_res.status_code == 200 and "results" in sem_res.json(), "POST /api/ai/semantic-search (concept similarity)")

    # ── AI Chatbot & Mentor Tests ────────────────────────────────────────────
    chat_topics_res = client.get("/api/ai/chat/topics", headers=admin_headers)
    assert_test(chat_topics_res.status_code == 200 and len(chat_topics_res.json().get("categories", [])) >= 3, "GET /api/ai/chat/topics (beginner categories)")

    chat_res = client.post("/api/ai/chat", json={
        "messages": [
            {"role": "user", "content": "How do I write a good bug report?"}
        ],
        "mode": "general_mentor"
    }, headers=admin_headers)
    assert_test(chat_res.status_code == 200 and len(chat_res.json().get("reply", "")) > 50, "POST /api/ai/chat (general beginner mentoring)")

    chat_review_res = client.post("/api/ai/chat", json={
        "messages": [
            {"role": "user", "content": "Review my draft bug report: payment button crashes"}
        ],
        "mode": "draft_reviewer",
        "context": {
            "draft_title": "payment button crashes",
            "draft_description": "User clicks checkout submit and nothing happens."
        }
    }, headers=admin_headers)
    assert_test(chat_review_res.status_code == 200 and "Review" in chat_review_res.json().get("reply", ""), "POST /api/ai/chat (draft bug review mode)")

    chat_err_res = client.post("/api/ai/chat", json={
        "messages": [
            {"role": "user", "content": "Explain 500 internal server error"}
        ],
        "mode": "error_explainer"
    }, headers=admin_headers)
    assert_test(chat_err_res.status_code == 200 and "500" in chat_err_res.json().get("reply", ""), "POST /api/ai/chat (error explanation mode)")

    # ── Automated Test Teardown Cleanup ───────────────────────────────────────
    try:
        from app.database import SessionLocal
        from app.models import ActivityLog, Attachment, Comment, Issue, Notification, Project, ProjectMember, Sprint, User
        db = SessionLocal()
        if "project_id" in locals() and project_id:
            sub_issues = db.query(Issue.id).filter(Issue.project_id == project_id).all()
            sub_issue_ids = [i[0] for i in sub_issues]
            if sub_issue_ids:
                db.query(Comment).filter(Comment.issue_id.in_(sub_issue_ids)).delete(synchronize_session=False)
                db.query(Attachment).filter(Attachment.issue_id.in_(sub_issue_ids)).delete(synchronize_session=False)
                db.query(ActivityLog).filter(ActivityLog.issue_id.in_(sub_issue_ids)).delete(synchronize_session=False)
                db.query(Issue).filter(Issue.id.in_(sub_issue_ids)).delete(synchronize_session=False)
            db.query(Sprint).filter(Sprint.project_id == project_id).delete(synchronize_session=False)
            db.query(ProjectMember).filter(ProjectMember.project_id == project_id).delete(synchronize_session=False)
            db.query(ActivityLog).filter(ActivityLog.project_id == project_id).delete(synchronize_session=False)
            db.query(Project).filter(Project.id == project_id).delete(synchronize_session=False)

        # Find all test user IDs
        stray_users = db.query(User.id).filter(User.email.like("%@bugflow.dev")).all()
        all_test_uids = list(set([u[0] for u in stray_users] + ([admin_id] if "admin_id" in locals() and admin_id else []) + ([dev_id] if "dev_id" in locals() and dev_id else [])))
        if all_test_uids:
            # Delete any projects owned by test users
            user_projects = db.query(Project.id).filter(Project.owner_id.in_(all_test_uids)).all()
            user_proj_ids = [p[0] for p in user_projects]
            if user_proj_ids:
                p_issues = db.query(Issue.id).filter(Issue.project_id.in_(user_proj_ids)).all()
                p_issue_ids = [i[0] for i in p_issues]
                if p_issue_ids:
                    db.query(Comment).filter(Comment.issue_id.in_(p_issue_ids)).delete(synchronize_session=False)
                    db.query(Attachment).filter(Attachment.issue_id.in_(p_issue_ids)).delete(synchronize_session=False)
                    db.query(ActivityLog).filter(ActivityLog.issue_id.in_(p_issue_ids)).delete(synchronize_session=False)
                    db.query(Issue).filter(Issue.id.in_(p_issue_ids)).delete(synchronize_session=False)
                db.query(Sprint).filter(Sprint.project_id.in_(user_proj_ids)).delete(synchronize_session=False)
                db.query(ProjectMember).filter(ProjectMember.project_id.in_(user_proj_ids)).delete(synchronize_session=False)
                db.query(ActivityLog).filter(ActivityLog.project_id.in_(user_proj_ids)).delete(synchronize_session=False)
                db.query(Project).filter(Project.id.in_(user_proj_ids)).delete(synchronize_session=False)

            # Clean any remaining issues reported by test users
            rep_issues = db.query(Issue.id).filter(Issue.reporter_id.in_(all_test_uids)).all()
            rep_issue_ids = [i[0] for i in rep_issues]
            if rep_issue_ids:
                db.query(Comment).filter(Comment.issue_id.in_(rep_issue_ids)).delete(synchronize_session=False)
                db.query(Attachment).filter(Attachment.issue_id.in_(rep_issue_ids)).delete(synchronize_session=False)
                db.query(ActivityLog).filter(ActivityLog.issue_id.in_(rep_issue_ids)).delete(synchronize_session=False)
                db.query(Issue).filter(Issue.id.in_(rep_issue_ids)).delete(synchronize_session=False)

            db.query(Issue).filter(Issue.assigned_developer_id.in_(all_test_uids)).update({"assigned_developer_id": None}, synchronize_session=False)
            db.query(Notification).filter(Notification.user_id.in_(all_test_uids)).delete(synchronize_session=False)
            db.query(ActivityLog).filter(ActivityLog.user_id.in_(all_test_uids)).delete(synchronize_session=False)
            db.query(ProjectMember).filter(ProjectMember.user_id.in_(all_test_uids)).delete(synchronize_session=False)
            db.query(Comment).filter(Comment.user_id.in_(all_test_uids)).delete(synchronize_session=False)
            db.query(User).filter(User.id.in_(all_test_uids)).delete(synchronize_session=False)

        db.commit()
        db.close()
    except Exception as teardown_err:
        print(f"  ℹ️ Teardown note: {teardown_err}")

    print("\n=======================================================")
    print(f"📊 Verification Summary: {passed} PASSED, {failed} FAILED")
    print("=======================================================")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    test_api_suite()


