import enum
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utc_now() -> datetime:
    """Return naive UTC datetime without Python 3.12 deprecation warnings."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PROJECT_MANAGER = "project_manager"
    DEVELOPER = "developer"
    QA_TESTER = "qa_tester"
    REPORTER = "reporter"


class IssueStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IssueSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssuePriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SprintStatus(str, enum.Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    COMPLETED = "completed"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.REPORTER, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    owned_projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    project_memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reported_issues: Mapped[list["Issue"]] = relationship(
        back_populates="reporter",
        foreign_keys="Issue.reporter_id",
    )
    assigned_issues: Mapped[list["Issue"]] = relationship(
        back_populates="assigned_developer",
        foreign_keys="Issue.assigned_developer_id",
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="user")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    owner: Mapped["User"] = relationship(back_populates="owned_projects")
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    issues: Mapped[list["Issue"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    sprints: Mapped[list["Sprint"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMember(Base):
    __tablename__ = "project_members"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    role_in_project: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="project_memberships")


class Sprint(Base):
    __tablename__ = "sprints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[SprintStatus] = mapped_column(
        Enum(SprintStatus), default=SprintStatus.PLANNING, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    project: Mapped["Project"] = relationship(back_populates="sprints")
    issues: Mapped[list["Issue"]] = relationship(back_populates="sprint")


class Issue(Base):
    __tablename__ = "issues"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    steps_to_reproduce: Mapped[str | None] = mapped_column(Text, nullable=True)
    expected_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[IssueSeverity] = mapped_column(
        Enum(IssueSeverity), default=IssueSeverity.MEDIUM, nullable=False
    )
    priority: Mapped[IssuePriority] = mapped_column(
        Enum(IssuePriority), default=IssuePriority.MEDIUM, nullable=False
    )
    status: Mapped[IssueStatus] = mapped_column(
        Enum(IssueStatus), default=IssueStatus.OPEN, nullable=False
    )
    os: Mapped[str | None] = mapped_column(String(100), nullable=True)
    browser: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    module: Mapped[str | None] = mapped_column(String(150), nullable=True)
    defect_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    reporter_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_developer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    sprint_id: Mapped[int | None] = mapped_column(ForeignKey("sprints.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    project: Mapped["Project"] = relationship(back_populates="issues")
    reporter: Mapped["User"] = relationship(
        back_populates="reported_issues",
        foreign_keys=[reporter_id],
    )
    assigned_developer: Mapped["User | None"] = relationship(
        back_populates="assigned_issues",
        foreign_keys=[assigned_developer_id],
    )
    sprint: Mapped["Sprint | None"] = relationship(back_populates="issues")
    comments: Mapped[list["Comment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    attachments: Mapped[list["Attachment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")
    activity_logs: Mapped[list["ActivityLog"]] = relationship(back_populates="issue", cascade="all, delete-orphan")


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utc_now, onupdate=utc_now
    )

    issue: Mapped["Issue"] = relationship(back_populates="comments")
    user: Mapped["User"] = relationship(back_populates="comments")


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    issue_id: Mapped[int] = mapped_column(ForeignKey("issues.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    filepath: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    issue: Mapped["Issue"] = relationship(back_populates="attachments")
    user: Mapped["User"] = relationship(back_populates="attachments")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    issue_id: Mapped[int | None] = mapped_column(ForeignKey("issues.id"), nullable=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    issue: Mapped["Issue | None"] = relationship(back_populates="activity_logs")
    project: Mapped["Project | None"] = relationship()
    user: Mapped["User"] = relationship()


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped["User"] = relationship(back_populates="notifications")
