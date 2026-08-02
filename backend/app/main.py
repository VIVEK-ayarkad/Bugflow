from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
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

UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="BugFlow API",
    description="Centralized Enterprise Bug Tracking & Sprint Management Platform API with AI Copilot.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static file directory for attachments
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": "BugFlow API"}
