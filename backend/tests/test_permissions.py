import pytest

from app.models import (
    Comment,
    Issue,
)


def test_admin_endpoints_accessible_by_admin(client, admin_headers):
    """System administrators must have full access to all /api/admin/* endpoints."""
    users_res = client.get("/api/admin/users", headers=admin_headers)
    assert users_res.status_code == 200

    reports_res = client.get("/api/admin/reports", headers=admin_headers)
    assert reports_res.status_code == 200

    logs_res = client.get("/api/admin/logs", headers=admin_headers)
    assert logs_res.status_code == 200


@pytest.mark.parametrize("headers_fixture", ["developer_headers", "qa_headers", "reporter_headers", "pm_headers"])
def test_admin_endpoints_forbidden_for_non_admins(client, request, headers_fixture):
    """Non-admin users must be rejected with HTTP 403 Forbidden on /api/admin/* endpoints."""
    headers = request.getfixturevalue(headers_fixture)
    users_res = client.get("/api/admin/users", headers=headers)
    assert users_res.status_code == 403

    reports_res = client.get("/api/admin/reports", headers=headers)
    assert reports_res.status_code == 403

    logs_res = client.get("/api/admin/logs", headers=headers)
    assert logs_res.status_code == 403


def test_update_user_role_permission(client, admin_headers, developer_headers, developer_user):
    """Only Admins can update user roles via PUT /api/users/{id}/role."""
    # Admin succeeds
    adm_res = client.put(
        f"/api/users/{developer_user.id}/role",
        json={"role": "project_manager"},
        headers=admin_headers,
    )
    assert adm_res.status_code == 200
    assert adm_res.json()["role"] == "project_manager"

    # Non-admin rejected with 403
    non_adm_res = client.put(
        f"/api/users/{developer_user.id}/role",
        json={"role": "developer"},
        headers=developer_headers,
    )
    assert non_adm_res.status_code == 403


def test_project_update_permissions(client, test_project, admin_headers, developer_headers, reporter_headers):
    """Project updates require Project Owner, PM, or Admin role."""
    # Admin can update
    adm_res = client.put(f"/api/projects/{test_project.id}", json={"name": "Renamed by Admin"}, headers=admin_headers)
    assert adm_res.status_code == 200

    # Unrelated reporter cannot update
    rep_res = client.put(f"/api/projects/{test_project.id}", json={"name": "Renamed by Reporter"}, headers=reporter_headers)
    assert rep_res.status_code == 403


def test_project_delete_permissions(client, test_project, admin_headers, developer_headers):
    """Project deletion requires Admin or Project Owner."""
    # Developer cannot delete project
    dev_res = client.delete(f"/api/projects/{test_project.id}", headers=developer_headers)
    assert dev_res.status_code == 403

    # Admin can delete project
    adm_res = client.delete(f"/api/projects/{test_project.id}", headers=admin_headers)
    assert adm_res.status_code == 204


def test_comment_edit_and_delete_permissions(client, test_issue, developer_user, developer_headers, qa_headers, admin_headers, db_session):
    """Only comment author or Admin can edit and delete a comment."""
    comment = Comment(
        issue_id=test_issue.id,
        user_id=developer_user.id,
        content="Developer initial note",
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)

    # QA user attempts to edit developer's comment -> 403
    qa_edit = client.put(f"/api/comments/{comment.id}", json={"content": "Tampered content"}, headers=qa_headers)
    assert qa_edit.status_code == 403

    # Author can edit
    dev_edit = client.put(f"/api/comments/{comment.id}", json={"content": "Author edit"}, headers=developer_headers)
    assert dev_edit.status_code == 200
    assert dev_edit.json()["content"] == "Author edit"

    # QA user attempts to delete developer's comment -> 403
    qa_del = client.delete(f"/api/comments/{comment.id}", headers=qa_headers)
    assert qa_del.status_code == 403

    # Admin can delete any comment
    adm_del = client.delete(f"/api/comments/{comment.id}", headers=admin_headers)
    assert adm_del.status_code == 204


def test_issue_delete_permissions(client, test_project, qa_user, qa_headers, reporter_headers, admin_headers, db_session):
    """Defect deletion is restricted to Reporter, Assignee, Owner, or Admin."""
    issue = Issue(
        title="Issue for permission testing",
        description="Description",
        project_id=test_project.id,
        reporter_id=qa_user.id,
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)

    # Unrelated reporter cannot delete
    rep_del = client.delete(f"/api/issues/{issue.id}", headers=reporter_headers)
    assert rep_del.status_code == 403

    # Reporter who filed it can delete
    qa_del = client.delete(f"/api/issues/{issue.id}", headers=qa_headers)
    assert qa_del.status_code == 204
