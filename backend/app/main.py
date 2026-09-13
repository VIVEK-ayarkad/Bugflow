from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine
from app.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    sqlalchemy_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from app.routers import (
    admin,
    ai,
    attachments,
    auth,
    comments,
    dashboard,
    issues,
    notifications,
    projects,
    sprints,
    users,
)
from app.schemas import HealthResponse

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _seed_demo_accounts():
    """Ensure standard enterprise demo accounts exist for evaluation."""
    from app.auth import hash_password
    from app.database import SessionLocal
    from app.models import User, UserRole

    db = SessionLocal()
    try:
        demo_users = [
            ("admin@bugflow.io", "admin_lead", "admin123", UserRole.ADMIN),
            ("dev@bugflow.io", "alex_developer", "dev123", UserRole.DEVELOPER),
            ("qa@bugflow.io", "sarah_qa", "qa123", UserRole.QA_TESTER),
            ("pm@bugflow.io", "marcus_pm", "pm123", UserRole.PROJECT_MANAGER),
        ]
        for email, username, pwd, role in demo_users:
            user = db.query(User).filter(User.email.ilike(email)).first()
            if not user:
                db.add(User(email=email, username=username, hashed_password=hash_password(pwd), role=role))
            else:
                user.hashed_password = hash_password(pwd)
                user.role = role
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Lifecycle startup and shutdown handler."""
    Base.metadata.create_all(bind=engine)
    _seed_demo_accounts()
    yield


TAGS_METADATA = [
    {
        "name": "auth",
        "description": "Authentication endpoints: User registration, JSON & OAuth2 login, JWT token issuance, authenticated profile, and session management.",
    },
    {
        "name": "users",
        "description": "User discovery, profile lookups, and administrator role assignment.",
    },
    {
        "name": "projects",
        "description": "Project workspace management, team memberships, and project summary PDF exports.",
    },
    {
        "name": "issues",
        "description": "Core defect tracking engine: Full CRUD, lifecycle transitions, assignment, audit trails, and defect report PDF streaming.",
    },
    {
        "name": "comments",
        "description": "Defect discussion threads, developer technical notes, and resolution commentary.",
    },
    {
        "name": "attachments",
        "description": "Secure file uploads, screenshots, and error log attachment storage.",
    },
    {
        "name": "sprints",
        "description": "Sprint planning, milestone tracking, and sprint lifecycle transitions.",
    },
    {
        "name": "dashboard",
        "description": "Executive dashboard metrics, velocity analytics, severity distributions, and global activity stream.",
    },
    {
        "name": "notifications",
        "description": "In-app notifications for bug assignments, status transitions, and comment mentions.",
    },
    {
        "name": "admin",
        "description": "Administrative governance: System reports, user management, and system-wide audit logging.",
    },
    {
        "name": "ai",
        "description": "AI Defect Intelligence: Dense vector semantic search, automated taxonomy classification, duplicate prevention, and Resolution Assistance Copilot.",
    },
    {
        "name": "health",
        "description": "Service health checks and API uptime verification.",
    },
]

API_DESCRIPTION = """
## 🚀 BugFlow Defect Intelligence & Bug Tracking REST API

BugFlow provides high-throughput, enterprise-grade defect tracking, sprint management, and dense vector AI intelligence.

### 🔑 Authentication
Most endpoints require a **Bearer JWT Token** in the `Authorization` header:
`Authorization: Bearer <your_access_token>`

You can obtain an access token via `POST /api/auth/login` or by clicking the **Authorize** button in Swagger UI.

### 🛡️ Role-Based Access Control (RBAC)
- **Admin**: Full administrative access across all projects, system metrics, and user management.
- **Project Manager**: Project configuration, sprint creation, and team assignment.
- **Developer**: Defect resolution, status transitions, and resolution assistance.
- **QA Tester**: Defect creation, classification assistance, verification, and PDF generation.
- **Reporter**: Bug ticket submission and issue tracking.
"""

app = FastAPI(
    title="BugFlow API",
    summary="AI-Powered Defect Intelligence & Bug Tracking Platform REST API",
    description=API_DESCRIPTION,
    version="1.0.0",
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/openapi.json",
    swagger_ui_parameters={
        "persistAuthorization": True,
        "displayRequestDuration": True,
        "defaultModelsExpandDepth": -1,
        "docExpansion": "none",
    },
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Compression & Performance Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directory for attachments
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

from fastapi.responses import RedirectResponse

# Register Routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(issues.router)
app.include_router(comments.router)
app.include_router(attachments.router)
app.include_router(sprints.router)
app.include_router(dashboard.router)
app.include_router(notifications.router)
app.include_router(admin.router)
app.include_router(ai.router, prefix="/api")


@app.get(
    "/api/health",
    response_model=HealthResponse,
    tags=["health"],
    summary="Health check",
    description="Check backend operational status and API version.",
)
def health():
    """Service health and uptime endpoint."""
    return HealthResponse(status="ok", app="BugFlow API", version="1.0.0")


@app.get("/api/docs", include_in_schema=False)
def redirect_api_docs():
    """Convenience redirect for /api/docs -> /docs."""
    return RedirectResponse(url="/docs")


@app.get("/api/redoc", include_in_schema=False)
def redirect_api_redoc():
    """Convenience redirect for /api/redoc -> /redoc."""
    return RedirectResponse(url="/redoc")


@app.get("/", include_in_schema=False)
def redirect_root():
    """Convenience redirect for root / -> /docs."""
    return RedirectResponse(url="/docs")

