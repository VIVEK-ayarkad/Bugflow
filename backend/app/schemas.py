from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import IssuePriority, IssueSeverity, IssueStatus, SprintStatus, UserRole


# ── Auth & Users ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    role: UserRole | None = UserRole.REPORTER


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    role: UserRole
    created_at: datetime


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=100)
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class ProjectMemberCreate(BaseModel):
    user_id: int
    role_in_project: str | None = "Member"


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    role_in_project: str | None
    created_at: datetime
    user: UserResponse


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    owner_id: int
    created_at: datetime
    owner: UserResponse | None = None
    members: list[ProjectMemberResponse] = []


# ── Sprints ───────────────────────────────────────────────────────────────────

class SprintCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    goal: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    goal: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    status: SprintStatus | None = None


class SprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    goal: str | None
    start_date: datetime | None
    end_date: datetime | None
    status: SprintStatus
    created_at: datetime


# ── Comments & Attachments ────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str = Field(min_length=1)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    user_id: int
    content: str
    created_at: datetime
    updated_at: datetime
    user: UserResponse


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int
    user_id: int
    filename: str
    filepath: str
    file_type: str
    file_size: int
    created_at: datetime
    user: UserResponse


# ── Activity & Notifications ──────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    issue_id: int | None
    project_id: int | None
    user_id: int
    action: str
    details: str | None
    created_at: datetime
    user: UserResponse


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    link: str | None
    is_read: bool
    created_at: datetime


# ── Issues ──────────────────────────────────────────────────────────────────

class IssueCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    steps_to_reproduce: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    severity: IssueSeverity = IssueSeverity.MEDIUM
    priority: IssuePriority = IssuePriority.MEDIUM
    status: IssueStatus = IssueStatus.OPEN
    os: str | None = None
    browser: str | None = None
    category: str | None = None
    module: str | None = None
    defect_type: str | None = None
    assigned_developer_id: int | None = None
    sprint_id: int | None = None


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    steps_to_reproduce: str | None = None
    expected_behavior: str | None = None
    actual_behavior: str | None = None
    severity: IssueSeverity | None = None
    priority: IssuePriority | None = None
    status: IssueStatus | None = None
    os: str | None = None
    browser: str | None = None
    category: str | None = None
    module: str | None = None
    defect_type: str | None = None
    assigned_developer_id: int | None = None
    sprint_id: int | None = None


class IssueStatusUpdate(BaseModel):
    status: IssueStatus


class IssueAssignUpdate(BaseModel):
    assigned_developer_id: int | None = None


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    steps_to_reproduce: str | None
    expected_behavior: str | None
    actual_behavior: str | None
    severity: IssueSeverity
    priority: IssuePriority
    status: IssueStatus
    os: str | None
    browser: str | None
    category: str | None = None
    module: str | None = None
    defect_type: str | None = None
    project_id: int
    reporter_id: int
    assigned_developer_id: int | None
    sprint_id: int | None
    created_at: datetime
    updated_at: datetime

    reporter: UserResponse | None = None
    assigned_developer: UserResponse | None = None
    sprint: SprintResponse | None = None
    comments_count: int = 0
    attachments_count: int = 0


# ── AI Features ─────────────────────────────────────────────────────────────

class DefectClassifyRequest(BaseModel):
    description: str = Field(min_length=1, max_length=5000)
    title: str | None = None


class DefectClassifyResponse(BaseModel):
    category: str
    module: str
    defect_type: str
    suggested_severity: IssueSeverity
    suggested_priority: IssuePriority
    confidence: float = 0.95
    rationale: str
    tags: list[str] = []


class AIAssistRequest(BaseModel):
    raw_description: str = Field(min_length=1, max_length=5000)


class AIAssistResponse(BaseModel):
    needs_more_info: bool
    follow_up_questions: list[str] = []
    formatted_report: dict | None = None
    message: str


class CodeFixRequest(BaseModel):
    code: str = Field(min_length=1, max_length=10000)
    error_log: str | None = None
    language: str | None = "javascript"


class CodeFixResponse(BaseModel):
    is_correct: bool = False
    user_mistake: str | None = None
    root_cause: str
    explanation: str
    corrected_code: str
    diff_lines: list[dict] = []
    prevention_tip: str


class SeverityPredictRequest(BaseModel):
    title: str | None = ""
    description: str = Field(min_length=1, max_length=5000)


class SeverityPredictResponse(BaseModel):
    predicted_severity: IssueSeverity
    predicted_priority: IssuePriority = IssuePriority.MEDIUM
    confidence: float = 0.95
    rationale: str


class DuplicateDetectRequest(BaseModel):
    project_id: int
    title: str
    description: str


class DuplicateDetectResponse(BaseModel):
    has_duplicates: bool
    potential_duplicates: list[dict] = []


class SprintHealthRequest(BaseModel):
    sprint_id: int


class SprintHealthResponse(BaseModel):
    sprint_id: int
    sprint_name: str
    risk_level: str  # "Low", "Medium", "High", "Critical"
    health_score: int  # 0 to 100
    open_issues_count: int
    resolved_issues_count: int
    critical_issues_count: int
    recommendations: list[str]


class SemanticSearchRequest(BaseModel):
    project_id: int | None = None
    query: str = Field(min_length=1, max_length=500)
    threshold: float = 0.35
    limit: int = 20


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[dict] = []
    total_found: int = 0


class ResolutionAssistanceRequest(BaseModel):
    issue_id: int | None = None
    title: str
    description: str = ""
    category: str | None = None
    module: str | None = None
    project_id: int | None = None


class ResolutionAssistanceResponse(BaseModel):
    investigation_areas: list[str]
    similar_defects: list[dict] = []
    previous_resolution: str | None = None
    possible_resolution: str
    confidence: float = 0.95
