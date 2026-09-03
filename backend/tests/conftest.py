import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Ensure backend root is always on sys.path
BACKEND_ROOT = str(Path(__file__).resolve().parent.parent)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app.auth import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app
from app.models import (
    Issue,
    IssuePriority,
    IssueSeverity,
    IssueStatus,
    Project,
    ProjectMember,
    Sprint,
    SprintStatus,
    User,
    UserRole,
)

# In-memory SQLite database for test isolation
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create a fresh database schema before each test and drop it afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    """Provide an isolated database session for direct model queries in tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client():
    """FastAPI TestClient configured with test database override."""
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ── User & Auth Fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin@bugflow.dev",
        username="admin_lead",
        hashed_password=hash_password("AdminPass123!"),
        role=UserRole.ADMIN,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user):
    return create_access_token(user_id=admin_user.id, role=admin_user.role.value)


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def pm_user(db_session):
    user = User(
        email="pm@bugflow.dev",
        username="pm_sarah",
        hashed_password=hash_password("PmPass123!"),
        role=UserRole.PROJECT_MANAGER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def pm_token(pm_user):
    return create_access_token(user_id=pm_user.id, role=pm_user.role.value)


@pytest.fixture
def pm_headers(pm_token):
    return {"Authorization": f"Bearer {pm_token}"}


@pytest.fixture
def developer_user(db_session):
    user = User(
        email="dev@bugflow.dev",
        username="dev_john",
        hashed_password=hash_password("DevPass123!"),
        role=UserRole.DEVELOPER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def developer_token(developer_user):
    return create_access_token(user_id=developer_user.id, role=developer_user.role.value)


@pytest.fixture
def developer_headers(developer_token):
    return {"Authorization": f"Bearer {developer_token}"}


@pytest.fixture
def qa_user(db_session):
    user = User(
        email="qa@bugflow.dev",
        username="qa_alice",
        hashed_password=hash_password("QaPass123!"),
        role=UserRole.QA_TESTER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def qa_token(qa_user):
    return create_access_token(user_id=qa_user.id, role=qa_user.role.value)


@pytest.fixture
def qa_headers(qa_token):
    return {"Authorization": f"Bearer {qa_token}"}


@pytest.fixture
def reporter_user(db_session):
    user = User(
        email="reporter@bugflow.dev",
        username="reporter_bob",
        hashed_password=hash_password("ReporterPass123!"),
        role=UserRole.REPORTER,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def reporter_token(reporter_user):
    return create_access_token(user_id=reporter_user.id, role=reporter_user.role.value)


@pytest.fixture
def reporter_headers(reporter_token):
    return {"Authorization": f"Bearer {reporter_token}"}


# ── Project & Issue Fixtures ─────────────────────────────────────────────────

@pytest.fixture
def test_project(db_session, admin_user, developer_user):
    project = Project(
        name="BugFlow Core Platform",
        description="Core defect tracking and sprint intelligence engine.",
        owner_id=admin_user.id,
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # Add admin and dev as members
    db_session.add(ProjectMember(project_id=project.id, user_id=admin_user.id, role_in_project="Project Lead"))
    db_session.add(ProjectMember(project_id=project.id, user_id=developer_user.id, role_in_project="Backend Lead"))
    db_session.commit()
    return project


@pytest.fixture
def test_sprint(db_session, test_project):
    sprint = Sprint(
        project_id=test_project.id,
        name="Sprint 10 - Hardening",
        goal="Resolve high severity payment and auth defects",
        status=SprintStatus.ACTIVE,
    )
    db_session.add(sprint)
    db_session.commit()
    db_session.refresh(sprint)
    return sprint


@pytest.fixture
def test_issue(db_session, test_project, qa_user, developer_user, test_sprint):
    issue = Issue(
        title="Payment checkout 500 error on credit card submit",
        description="Summary:\n• Payment crashes when user clicks 'Pay Now'.\n\nSteps to Reproduce:\n1. Add item to cart\n2. Fill card details\n3. Click Pay Now\n\nExpected Result:\n• Order receipt shown.\n\nActual Result:\n• 500 Internal Server Error.",
        steps_to_reproduce="1. Add item\n2. Fill card\n3. Click Pay Now",
        expected_behavior="Order processed",
        actual_behavior="500 Internal Server Error",
        severity=IssueSeverity.HIGH,
        priority=IssuePriority.HIGH,
        status=IssueStatus.OPEN,
        category="Payment",
        module="Checkout / Gateway",
        defect_type="Functional Defect",
        project_id=test_project.id,
        reporter_id=qa_user.id,
        assigned_developer_id=developer_user.id,
        sprint_id=test_sprint.id,
    )
    db_session.add(issue)
    db_session.commit()
    db_session.refresh(issue)
    return issue
