from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.models import IssuePriority, IssueSeverity, IssueStatus, SprintStatus, UserRole

# ── Generic Responses ────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str = Field(..., description="Status or confirmation message", examples=["Operation completed successfully."])


class HealthResponse(BaseModel):
    status: str = Field("ok", description="Application operational status", examples=["ok"])
    app: str = Field("BugFlow API", description="Application service name", examples=["BugFlow API"])
    version: str = Field("1.0.0", description="API version string", examples=["1.0.0"])
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        description="UTC server timestamp",
    )


# ── Auth & Users ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr = Field(..., description="Valid email address", examples=["tester@example.com"])
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\.\-]+$", description="Unique username (letters, numbers, dots, hyphens, underscores)", examples=["alex_qa"])
    password: str = Field(..., min_length=6, max_length=128, description="User password (min 6 characters)", examples=["SecretPass123!"])
    role: UserRole | None = Field(default=UserRole.REPORTER, description="Assigned user role in BugFlow", examples=["reporter"])


class UserLogin(BaseModel):
    email: EmailStr = Field(..., description="Registered email address", examples=["tester@example.com"])
    password: str = Field(..., min_length=1, description="Account password", examples=["SecretPass123!"])


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique user ID", examples=[1])
    email: str = Field(..., description="User email address", examples=["alex@bugflow.dev"])
    username: str = Field(..., description="Unique username", examples=["alex_lead"])
    role: UserRole = Field(..., description="Assigned role", examples=["admin"])
    created_at: datetime = Field(..., description="Account creation timestamp")


class UserRoleUpdate(BaseModel):
    role: UserRole = Field(..., description="Updated role for the user", examples=["developer"])


class UserProfileUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_\.\-]+$", description="New username", examples=["alex_prime"])
    email: EmailStr | None = Field(default=None, description="New email address", examples=["alex_prime@bugflow.dev"])
    current_password: str | None = Field(default=None, min_length=1, description="Current password required for password change")
    new_password: str | None = Field(default=None, min_length=6, max_length=128, description="New password", examples=["NewSuperPass999!"])


class Token(BaseModel):
    access_token: str = Field(..., description="JWT Bearer access token string")
    token_type: str = Field("bearer", description="Token scheme type", examples=["bearer"])
    user: UserResponse = Field(..., description="Authenticated user details")


class TokenData(BaseModel):
    user_id: int | None = None
    role: str | None = None


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Project title", examples=["Alpha E-Commerce"])
    description: str | None = Field(default=None, max_length=2000, description="Detailed project description", examples=["Core e-commerce platform defect tracking."])


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200, description="Updated project title", examples=["Alpha Platform 2.0"])
    description: str | None = Field(default=None, max_length=2000, description="Updated project description")


class ProjectMemberCreate(BaseModel):
    user_id: int = Field(..., ge=1, description="Target User ID to add to project", examples=[2])
    role_in_project: str | None = Field(default="Member", max_length=100, description="Project role or designation", examples=["Lead QA"])


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Membership record ID", examples=[1])
    project_id: int = Field(..., description="Project ID", examples=[10])
    user_id: int = Field(..., description="User ID", examples=[2])
    role_in_project: str | None = Field(None, description="Custom role title", examples=["Lead QA"])
    created_at: datetime = Field(..., description="Timestamp added to project")
    user: UserResponse = Field(..., description="Member user profile")


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Project ID", examples=[10])
    name: str = Field(..., description="Project name", examples=["BugFlow Core"])
    description: str | None = Field(None, description="Project description")
    owner_id: int = Field(..., description="Owner User ID", examples=[1])
    created_at: datetime = Field(..., description="Project creation timestamp")
    owner: UserResponse | None = Field(None, description="Project owner user profile")
    members: list[ProjectMemberResponse] = Field(default_factory=list, description="List of active project members")


# ── Sprints ───────────────────────────────────────────────────────────────────

class SprintCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200, description="Sprint name", examples=["Sprint 14 - Checkout Hardening"])
    goal: str | None = Field(default=None, max_length=1000, description="Sprint goal or milestone focus", examples=["Zero critical checkout bugs"])
    start_date: datetime | None = Field(default=None, description="Sprint starting datetime")
    end_date: datetime | None = Field(default=None, description="Sprint completion datetime")

    @model_validator(mode="after")
    def validate_dates(self) -> "SprintCreate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Sprint end_date cannot be earlier than start_date")
        return self


class SprintUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200, description="Updated sprint name")
    goal: str | None = Field(default=None, max_length=1000, description="Updated sprint goal")
    start_date: datetime | None = Field(default=None, description="Updated start datetime")
    end_date: datetime | None = Field(default=None, description="Updated end datetime")
    status: SprintStatus | None = Field(default=None, description="Updated sprint status", examples=["active"])

    @model_validator(mode="after")
    def validate_dates(self) -> "SprintUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Sprint end_date cannot be earlier than start_date")
        return self


class SprintResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Sprint ID", examples=[3])
    project_id: int = Field(..., description="Parent project ID", examples=[10])
    name: str = Field(..., description="Sprint name", examples=["Sprint 14"])
    goal: str | None = Field(None, description="Sprint goal")
    start_date: datetime | None = Field(None, description="Start date")
    end_date: datetime | None = Field(None, description="End date")
    status: SprintStatus = Field(..., description="Current sprint status", examples=["active"])
    created_at: datetime = Field(..., description="Creation timestamp")


class SprintCompleteRequest(BaseModel):
    action: str = Field(default="backlog", description="Action for remaining issues: 'backlog' or 'rollover'", examples=["backlog"])
    rollover_sprint_id: int | None = Field(default=None, description="Target sprint ID if action is 'rollover'")


class SprintBulkAssignRequest(BaseModel):
    issue_ids: list[int] = Field(..., min_length=1, description="List of issue IDs to assign or unassign")
    action: str = Field(default="add", description="Action: 'add' (to this sprint) or 'remove' (to backlog)", examples=["add"])


class SprintMetricsResponse(BaseModel):
    sprint_id: int = Field(..., description="Sprint ID")
    sprint_name: str = Field(..., description="Sprint Name")
    status: SprintStatus = Field(..., description="Sprint status")
    start_date: datetime | None = Field(None, description="Start date")
    end_date: datetime | None = Field(None, description="End date")
    goal: str | None = Field(None, description="Sprint goal")
    total_issues: int = Field(0, description="Total issues count in sprint")
    open_issues: int = Field(0, description="Open issues count")
    in_progress_issues: int = Field(0, description="In progress count")
    in_review_issues: int = Field(0, description="In review count")
    resolved_issues: int = Field(0, description="Resolved count")
    closed_issues: int = Field(0, description="Closed count")
    critical_issues: int = Field(0, description="Critical issues count")
    high_issues: int = Field(0, description="High severity count")
    medium_issues: int = Field(0, description="Medium severity count")
    low_issues: int = Field(0, description="Low severity count")
    completion_rate: float = Field(0.0, description="Ratio of resolved/closed issues")
    days_total: int | None = Field(None, description="Total days in sprint cycle")
    days_remaining: int | None = Field(None, description="Remaining days until end date")
    workload: list[dict[str, Any]] = Field(default_factory=list, description="Developer workload distribution")
    burndown: list[dict[str, Any]] = Field(default_factory=list, description="Burndown daily progression points")


# ── Comments & Attachments ────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Comment message content", examples=["Investigated logs; looks like an unhandled null in token refresh."])


class CommentUpdate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000, description="Updated comment text")


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Comment ID", examples=[12])
    issue_id: int = Field(..., description="Associated issue ID", examples=[45])
    user_id: int = Field(..., description="Author user ID", examples=[3])
    content: str = Field(..., description="Comment text")
    created_at: datetime = Field(..., description="Timestamp created")
    updated_at: datetime = Field(..., description="Timestamp last edited")
    user: UserResponse = Field(..., description="Author user details")


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Attachment ID", examples=[7])
    issue_id: int = Field(..., description="Target issue ID", examples=[45])
    user_id: int = Field(..., description="Uploader user ID", examples=[2])
    filename: str = Field(..., description="Original filename", examples=["screenshot_checkout_crash.png"])
    filepath: str = Field(..., description="Static URL / relative file path", examples=["/uploads/abc1234.png"])
    file_type: str = Field(..., description="MIME content type", examples=["image/png"])
    file_size: int = Field(..., description="File size in bytes", examples=[1048576])
    created_at: datetime = Field(..., description="Upload timestamp")
    user: UserResponse = Field(..., description="Uploader user profile")


# ── Activity & Notifications ──────────────────────────────────────────────────

class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Activity log record ID", examples=[101])
    issue_id: int | None = Field(None, description="Related issue ID if applicable", examples=[45])
    project_id: int | None = Field(None, description="Related project ID if applicable", examples=[10])
    user_id: int = Field(..., description="User ID who performed action", examples=[1])
    action: str = Field(..., description="Action title", examples=["Status Changed"])
    details: str | None = Field(None, description="Descriptive change details", examples=["Bug #45 status changed from 'open' to 'in_progress'"])
    created_at: datetime = Field(..., description="Activity timestamp")
    user: UserResponse = Field(..., description="User profile who triggered activity")


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Notification ID", examples=[55])
    user_id: int = Field(..., description="Target recipient User ID", examples=[2])
    title: str = Field(..., description="Notification title", examples=["Bug Assigned to You"])
    message: str = Field(..., description="Notification body message", examples=["You were assigned to Bug #45: Checkout timeout"])
    link: str | None = Field(None, description="Relative destination link", examples=["/issues/45"])
    is_read: bool = Field(..., description="Read status flag", examples=[False])
    created_at: datetime = Field(..., description="Timestamp received")


# ── Issues ────────────────────────────────────────────────────────────────────

class IssueCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=300, description="Defect title", examples=["Payment Gateway 500 on card verification"])
    description: str = Field(..., min_length=1, max_length=20000, description="Defect summary or structured expansion", examples=["When user clicks 'Pay Now', the verification API crashes."])
    steps_to_reproduce: str | None = Field(default=None, max_length=10000, description="Numbered reproduction steps", examples=["1. Add item to cart\n2. Proceed to checkout\n3. Click Pay Now"])
    expected_behavior: str | None = Field(default=None, max_length=5000, description="Expected software behavior", examples=["Payment is processed and order receipt shown."])
    actual_behavior: str | None = Field(default=None, max_length=5000, description="Actual observed defect behavior", examples=["500 Internal Server Error returned by payment endpoint."])
    severity: IssueSeverity = Field(default=IssueSeverity.MEDIUM, description="Defect severity classification", examples=["high"])
    priority: IssuePriority = Field(default=IssuePriority.MEDIUM, description="Triage priority level", examples=["high"])
    status: IssueStatus = Field(default=IssueStatus.OPEN, description="Initial workflow status", examples=["open"])
    os: str | None = Field(default=None, max_length=100, description="Operating system environment", examples=["macOS Sonoma 14.5"])
    browser: str | None = Field(default=None, max_length=100, description="Browser environment", examples=["Chrome 126.0"])
    category: str | None = Field(default=None, max_length=100, description="Defect domain category", examples=["Payment"])
    module: str | None = Field(default=None, max_length=150, description="Affected component or module", examples=["Checkout / Gateway"])
    defect_type: str | None = Field(default=None, max_length=100, description="Specific defect type", examples=["Functional Defect"])
    assigned_developer_id: int | None = Field(default=None, ge=1, description="Assigned developer User ID", examples=[3])
    sprint_id: int | None = Field(default=None, ge=1, description="Associated Sprint ID", examples=[2])


class IssueUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300, description="Updated defect title")
    description: str | None = Field(default=None, min_length=1, max_length=20000, description="Updated description")
    steps_to_reproduce: str | None = Field(default=None, max_length=10000, description="Updated reproduction steps")
    expected_behavior: str | None = Field(default=None, max_length=5000, description="Updated expected behavior")
    actual_behavior: str | None = Field(default=None, max_length=5000, description="Updated actual behavior")
    severity: IssueSeverity | None = Field(default=None, description="Updated severity")
    priority: IssuePriority | None = Field(default=None, description="Updated priority")
    status: IssueStatus | None = Field(default=None, description="Updated workflow status")
    os: str | None = Field(default=None, max_length=100, description="Updated OS environment")
    browser: str | None = Field(default=None, max_length=100, description="Updated browser")
    category: str | None = Field(default=None, max_length=100, description="Updated category")
    module: str | None = Field(default=None, max_length=150, description="Updated module")
    defect_type: str | None = Field(default=None, max_length=100, description="Updated defect type")
    assigned_developer_id: int | None = Field(default=None, description="Updated developer assignment")
    sprint_id: int | None = Field(default=None, description="Updated sprint assignment")


class IssueStatusUpdate(BaseModel):
    status: IssueStatus = Field(..., description="Target defect status", examples=["in_progress"])


class IssueAssignUpdate(BaseModel):
    assigned_developer_id: int | None = Field(default=None, description="Assigned developer User ID or null to unassign", examples=[3])


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Unique Defect ID", examples=[45])
    title: str = Field(..., description="Defect title", examples=["Payment Gateway 500"])
    description: str = Field(..., description="Defect description")
    steps_to_reproduce: str | None = Field(None, description="Reproduction steps")
    expected_behavior: str | None = Field(None, description="Expected outcome")
    actual_behavior: str | None = Field(None, description="Actual outcome")
    severity: IssueSeverity = Field(..., description="Severity level", examples=["high"])
    priority: IssuePriority = Field(..., description="Priority level", examples=["high"])
    status: IssueStatus = Field(..., description="Workflow status", examples=["open"])
    os: str | None = Field(None, description="Operating system")
    browser: str | None = Field(None, description="Browser")
    category: str | None = Field(None, description="Category taxonomy", examples=["Payment"])
    module: str | None = Field(None, description="Affected module", examples=["Checkout / Gateway"])
    defect_type: str | None = Field(None, description="Defect classification", examples=["Functional Defect"])
    project_id: int = Field(..., description="Parent project ID", examples=[10])
    reporter_id: int = Field(..., description="Reporter user ID", examples=[1])
    assigned_developer_id: int | None = Field(None, description="Assigned developer User ID", examples=[3])
    sprint_id: int | None = Field(None, description="Sprint ID", examples=[2])
    created_at: datetime = Field(..., description="Ticket creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")

    reporter: UserResponse | None = Field(None, description="Reporter user profile")
    assigned_developer: UserResponse | None = Field(None, description="Assigned developer user profile")
    sprint: SprintResponse | None = Field(None, description="Assigned sprint details")
    comments_count: int = Field(0, description="Total comments on defect", examples=[3])
    attachments_count: int = Field(0, description="Total files attached", examples=[1])


# ── AI Features ───────────────────────────────────────────────────────────────

class DefectClassifyRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=5000, description="Defect text or error trace", examples=["When clicking checkout, payment gateway crashes with 500 timeout."])
    title: str | None = Field(default=None, max_length=300, description="Optional defect title", examples=["Payment timeout error"])


class DefectClassifyResponse(BaseModel):
    category: str = Field(..., description="Recommended category", examples=["Payment"])
    module: str = Field(..., description="Recommended component/module", examples=["Checkout / Gateway"])
    defect_type: str = Field(..., description="Recommended defect type", examples=["Functional Defect"])
    suggested_severity: IssueSeverity = Field(..., description="Suggested severity", examples=["high"])
    suggested_priority: IssuePriority = Field(..., description="Suggested priority", examples=["high"])
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Classification confidence score", examples=[0.95])
    rationale: str = Field(..., description="AI classification reasoning", examples=["Payment issues block core transaction flows."])
    tags: list[str] = Field(default_factory=list, description="Suggested diagnostic tags", examples=[["payment", "checkout", "gateway"]])


class AIAssistRequest(BaseModel):
    raw_description: str = Field(..., min_length=1, max_length=5000, description="Raw, brief, or unstructured bug notes", examples=["cant login on mac safari getting error"])


class AIAssistResponse(BaseModel):
    needs_more_info: bool = Field(False, description="Flag indicating if more information is required from reporter")
    follow_up_questions: list[str] = Field(default_factory=list, description="Follow-up diagnostic questions if notes are insufficient")
    formatted_report: dict[str, Any] | None = Field(None, description="Structured line-by-line formatted defect report")
    message: str = Field(..., description="AI Copilot conversational status message")


class CodeFixRequest(BaseModel):
    code: str = Field(..., min_length=1, max_length=20000, description="Faulty or buggy code snippet to diagnose and repair", examples=['function getPrice(item) { return item.price * 1.15; }'])
    error_log: str | None = Field(default=None, max_length=5000, description="Optional error trace or console log", examples=["TypeError: Cannot read properties of undefined (reading 'price')"])
    language: str | None = Field(default="javascript", max_length=50, description="Programming language identifier", examples=["javascript"])
    audit_profile: str = Field(default="comprehensive", description="Diagnostic lens: comprehensive, security, performance, concurrency, resource_safety, unit_tests")


class CodeFixResponse(BaseModel):
    is_correct: bool = Field(False, description="Whether original input code was already syntactically and semantically correct")
    user_mistake: str | None = Field(None, description="Summary of user syntax or logic mistake")
    root_cause: str = Field(..., description="Deep technical root cause analysis")
    explanation: str = Field(..., description="Explanation of proposed code fix")
    corrected_code: str = Field(..., description="Direct corrected code snippet ready for deployment")
    diff_lines: list[dict[str, Any]] = Field(default_factory=list, description="Unified line-by-line diff metadata")
    prevention_tip: str = Field(..., description="Best practice tip to prevent recurring bugs")
    security_findings: list[dict[str, Any]] = Field(default_factory=list, description="OWASP/CWE security and vulnerability audit")
    complexity_analysis: dict[str, Any] | None = Field(None, description="Big-O time and space complexity comparison")
    concurrency_risks: list[str] = Field(default_factory=list, description="Thread-safety, deadlock, and race condition warnings")
    generated_unit_tests: str | None = Field(None, description="Automated executable unit & regression test suite (PyTest / Jest / JUnit)")
    resilience_patterns: list[str] = Field(default_factory=list, description="Applied fault-tolerance patterns: Circuit Breaker, Exponential Backoff, Idempotency")
    ast_verified: bool = Field(default=True, description="True if corrected code was compiled and validated via language parser")


class SeverityPredictRequest(BaseModel):
    title: str | None = Field(default="", max_length=300, description="Defect title")
    description: str = Field(..., min_length=1, max_length=5000, description="Defect description or impact scope", examples=["All users unable to complete purchases across site."])


class SeverityPredictResponse(BaseModel):
    predicted_severity: IssueSeverity = Field(..., description="Predicted severity level", examples=["critical"])
    predicted_priority: IssuePriority = Field(IssuePriority.MEDIUM, description="Predicted priority level", examples=["critical"])
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Prediction confidence score")
    rationale: str = Field(..., description="Impact reasoning justifying severity assessment")


class DuplicateDetectRequest(BaseModel):
    project_id: int = Field(..., ge=1, description="Target Project ID to search within", examples=[10])
    title: str = Field(..., min_length=1, max_length=300, description="Title of new defect candidate")
    description: str = Field(..., min_length=1, max_length=5000, description="Description of new defect candidate")


class DuplicateDetectResponse(BaseModel):
    has_duplicates: bool = Field(..., description="True if potential duplicates exceeding confidence threshold were detected")
    potential_duplicates: list[dict[str, Any]] = Field(default_factory=list, description="Matching historical defect records with similarity scores")


class SprintHealthRequest(BaseModel):
    sprint_id: int = Field(..., ge=1, description="Sprint ID to analyze")


class SprintHealthResponse(BaseModel):
    sprint_id: int = Field(..., description="Analyzed Sprint ID", examples=[3])
    sprint_name: str = Field(..., description="Sprint name", examples=["Sprint 14"])
    risk_level: str = Field(..., description="Sprint risk classification: Low, Medium, High, Critical", examples=["Medium"])
    health_score: int = Field(..., ge=0, le=100, description="Overall health score (0-100)", examples=[78])
    open_issues_count: int = Field(..., description="Active open issues count in sprint", examples=[4])
    resolved_issues_count: int = Field(..., description="Completed issues count", examples=[8])
    critical_issues_count: int = Field(..., description="Critical defect count in sprint", examples=[1])
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations to ensure sprint success")


class SprintRetrospectiveResponse(BaseModel):
    sprint_id: int = Field(..., description="Sprint ID")
    sprint_name: str = Field(..., description="Sprint Name")
    velocity_score: int = Field(..., ge=0, le=100, description="Sprint velocity & delivery score (0-100)")
    completion_rate: float = Field(..., description="Issue completion percentage ratio")
    summary: str = Field(..., description="Executive sprint retrospective summary")
    highlights: list[str] = Field(default_factory=list, description="Sprint achievements and successes")
    blockers: list[str] = Field(default_factory=list, description="Encountered bottlenecks and unresolved issues")
    risk_drivers: list[str] = Field(default_factory=list, description="Root causes for delays or critical defects")
    action_items: list[str] = Field(default_factory=list, description="Recommended continuous improvement actions for next sprint")


class SprintAdvisorResponse(BaseModel):
    sprint_id: int = Field(..., description="Sprint ID")
    sprint_name: str = Field(..., description="Sprint Name")
    capacity_status: str = Field(..., description="Capacity evaluation: Balanced, Overloaded, Underutilized")
    risk_level: str = Field(..., description="Scope risk: Low, Medium, High")
    recommendations: list[str] = Field(default_factory=list, description="Actionable scope and workload advice")
    unassigned_critical_count: int = Field(0, description="Number of critical issues missing assignment")
    workload_skew_warning: str | None = Field(None, description="Warning if a single developer holds disproportionate tickets")


class SemanticSearchRequest(BaseModel):
    project_id: int | None = Field(default=None, ge=1, description="Optional Project ID filter")
    query: str = Field(..., min_length=1, max_length=500, description="Conceptual or keyword search phrase", examples=["transaction crashes during checkout"])
    threshold: float = Field(default=0.35, ge=0.0, le=1.0, description="Vector similarity cutoff threshold", examples=[0.35])
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of defect matches to return", examples=[20])


class SemanticSearchResponse(BaseModel):
    query: str = Field(..., description="Processed query term")
    results: list[dict[str, Any]] = Field(default_factory=list, description="Ranked defect matches with confidence scores")
    total_found: int = Field(..., description="Total matching defects found", examples=[2])


class ResolutionAssistanceRequest(BaseModel):
    issue_id: int | None = Field(default=None, ge=1, description="Existing Issue ID if generating for a saved ticket")
    title: str = Field(..., min_length=1, max_length=300, description="Defect title", examples=["Payment Gateway 500"])
    description: str = Field(default="", max_length=10000, description="Defect description")
    category: str | None = Field(default=None, max_length=100, description="Category classification", examples=["Payment"])
    module: str | None = Field(default=None, max_length=150, description="Affected module", examples=["Checkout / Gateway"])
    severity: IssueSeverity | str | None = Field(default=None, description="Defect severity classification", examples=["high"])
    comments: list[str] | str | None = Field(default=None, description="Discussion comments or developer diagnostic notes on this ticket")
    project_id: int | None = Field(default=None, ge=1, description="Project ID for historical defect context")


class HistoricalDeveloperComment(BaseModel):
    author: str = Field(..., description="Author username", examples=["alex_dev"])
    role: str | None = Field(default=None, description="Author role", examples=["developer"])
    content: str = Field(..., description="Comment body", examples=["Patched null check on payment payload."])
    created_at: str | None = Field(default=None, description="Comment timestamp")


class HistoricalResolutionDetail(BaseModel):
    defect_id: int = Field(..., description="Related Defect ID", examples=[102])
    defect_key: str = Field(..., description="Defect ticket key", examples=["DEF-102"])
    title: str = Field(..., description="Related Defect title", examples=["Stripe checkout timeout on submission"])
    severity: str = Field(..., description="Severity level", examples=["high"])
    status: str = Field(..., description="Defect status (Resolved / Closed)", examples=["resolved"])
    similarity_score: float = Field(..., description="Similarity match percentage (0-100)", examples=[94.5])
    previous_root_cause: str = Field(..., description="Identified root cause of the historical defect", examples=["Unhandled null response from payment gateway SDK."])
    previous_resolution: str = Field(..., description="Concrete code or configuration fix applied", examples=["Added null safety check and retry policy with exponential backoff."])
    relevant_developer_comments: list[HistoricalDeveloperComment] = Field(default_factory=list, description="Relevant developer comments explaining the fix")


class ResolutionAssistanceResponse(BaseModel):
    investigation_areas: list[str] = Field(default_factory=list, description="Checklist of diagnostic inspection areas")
    investigation_disclaimer: str = Field(
        default="These diagnostic suggestions guide developer triage and investigation, but are not guaranteed root causes.",
        description="Explicit advisory disclaimer that suggestions are investigative starting points"
    )
    similar_defects: list[dict[str, Any]] = Field(default_factory=list, description="Historical related defects with resolution notes")
    historical_resolutions: list[HistoricalResolutionDetail] = Field(default_factory=list, description="Detailed historical resolution records acting as developer knowledge base")
    previous_resolution: str | None = Field(None, description="Summary of how similar historical bugs were resolved")
    possible_resolution: str = Field(..., description="Recommended technical code fix and diagnostic instructions")
    severity_mitigation: str | None = Field(None, description="Severity-specific mitigation advice and triage urgency")
    context_signals_used: list[str] = Field(default_factory=list, description="Context sources incorporated into resolution guidance: description, category, severity, comments, similar_defects, historical_resolutions")
    confidence: float = Field(0.95, ge=0.0, le=1.0, description="Assistance confidence level")


# ── Admin & Dashboard ─────────────────────────────────────────────────────────

class AdminMetrics(BaseModel):
    total_users: int = Field(..., description="Total registered users")
    total_projects: int = Field(..., description="Total active projects")
    total_bugs: int = Field(..., description="Total defects logged across system")


class AdminReportsResponse(BaseModel):
    system_metrics: AdminMetrics
    users_by_role: dict[str, int] = Field(..., description="Distribution of users across system roles")


# ── AI Chatbot & Beginner Mentor ─────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str = Field(..., description="Message author role: 'user', 'assistant', or 'system'", examples=["user"])
    content: str = Field(..., description="Message text content", examples=["How do I write a good bug report?"])
    timestamp: str | None = Field(default=None, description="Optional ISO timestamp string")


class AIChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(..., min_length=1, description="Chronological conversation message history")
    context: dict[str, Any] | None = Field(
        default=None,
        description="Optional active context such as issue_id, issue_title, issue_description, project_name, current_code, error_log",
    )
    mode: str | None = Field(
        default="general_mentor",
        description="Operational mode: 'general_mentor', 'bug_reporting', 'bug_solving', 'error_explainer', 'draft_reviewer', 'glossary'",
    )


class AIChatResponse(BaseModel):
    reply: str = Field(..., description="Educational, helpful response formatted in markdown")
    suggested_followups: list[str] = Field(
        default_factory=list,
        description="Quick follow-up questions the beginner can click to continue learning",
    )
    category: str | None = Field(default=None, description="Topic category (e.g., 'Bug Reporting', 'Debugging', 'Error Diagnostics')")
    helpful_tips: list[str] = Field(default_factory=list, description="Actionable best practice bullet points")


class AIChatTopicItem(BaseModel):
    id: str
    title: str
    prompt: str
    badge: str | None = None
    icon: str | None = None


class AIChatTopicCategory(BaseModel):
    category_id: str
    category_title: str
    description: str
    topics: list[AIChatTopicItem]


class AIChatTopicsResponse(BaseModel):
    categories: list[AIChatTopicCategory]


# ── Bug Blast-Radius & Architecture Dependency Visualizer ─────────────────────

class ModuleNode(BaseModel):
    id: str = Field(..., description="Unique module slug", examples=["payment_gateway"])
    name: str = Field(..., description="Module display name", examples=["Payment Gateway"])
    category: str = Field(default="Core", description="Functional category")
    open_defects_count: int = Field(default=0, description="Total active defects in module")
    critical_defects_count: int = Field(default=0, description="Critical defects in module")
    health_score: int = Field(default=100, ge=0, le=100, description="Module health score (0-100)")
    risk_tier: str = Field(default="Low", description="Risk classification: Low, Medium, High, Critical")
    assigned_developers: list[str] = Field(default_factory=list, description="Developers working on this module")
    is_epicenter: bool = Field(default=False, description="True if focused defect originated here")
    blast_zone: str = Field(default="safe", description="Zone: epicenter, direct_impact, cascade_risk, safe")
    defect_ids: list[int] = Field(default_factory=list, description="Defect IDs belonging to this module")


class DependencyEdge(BaseModel):
    source: str = Field(..., description="Upstream caller module ID")
    target: str = Field(..., description="Downstream provider module ID")
    relation_type: str = Field(default="depends_on", description="Relation type: calls, authenticates, processes, depends_on")
    severity_flow: str = Field(default="medium", description="Risk flow severity: critical, high, medium, low")
    is_active_impact_path: bool = Field(default=False, description="True if active blast wave travels along this edge")


class CausedIssueDetail(BaseModel):
    target_module_id: str = Field(..., description="Affected target module ID")
    target_module_name: str = Field(..., description="Affected target module name")
    impact_level: str = Field(..., description="direct_impact (1st degree) or cascade_risk (2nd degree)")
    failure_description: str = Field(..., description="Operational problem this defect triggers in the target module")
    affected_defect_ids: list[int] = Field(default_factory=list, description="Other open defect IDs in target module compounded or blocked")


class DefectAllocation(BaseModel):
    defect_id: int = Field(..., description="Defect ID")
    title: str = Field(..., description="Defect title")
    severity: str = Field(..., description="Defect severity: critical, high, medium, low")
    status: str = Field(..., description="Defect status: open, in_progress, in_review, resolved, closed")
    allocated_module_id: str = Field(..., description="Auto-allocated origin module ID")
    allocated_module_name: str = Field(..., description="Auto-allocated origin module display name")
    allocation_confidence: int = Field(default=95, description="Allocation confidence percentage")
    direct_impact_count: int = Field(default=0, description="Number of direct 1st-degree modules impacted")
    cascade_risk_count: int = Field(default=0, description="Number of cascading 2nd-degree modules threatened")
    direct_impact_module_names: list[str] = Field(default_factory=list, description="Names of directly impacted modules")
    cascade_risk_module_names: list[str] = Field(default_factory=list, description="Names of cascading risk modules")
    caused_issues: list[CausedIssueDetail] = Field(default_factory=list, description="Specific operational issues caused in other modules")
    containment_advice: str = Field(default="", description="Specific mitigation/containment action for this defect")


class BlastRadiusReport(BaseModel):
    project_id: int = Field(..., description="Project ID")
    project_name: str = Field(..., description="Project Name")
    focused_issue_id: int | None = Field(default=None, description="Focused defect ID if scoped to single bug")
    focused_issue_title: str | None = Field(default=None, description="Focused defect title")
    focused_module_id: str | None = Field(default=None, description="Epicenter module ID")
    system_blast_score: int = Field(..., ge=0, le=100, description="Overall system blast radius percentage (0-100%)")
    overall_status: str = Field(..., description="System status: Operational, Elevated Risk, Degraded Flow, Critical Cascade")
    epicenter_module: str | None = Field(default=None, description="Primary failure epicenter module name")
    direct_impact_count: int = Field(default=0, description="Count of directly impacted dependent modules")
    cascade_risk_count: int = Field(default=0, description="Count of secondary cascade risk modules")
    direct_impact_modules: list[str] = Field(default_factory=list, description="Names of directly impacted modules")
    cascade_risk_modules: list[str] = Field(default_factory=list, description="Names of secondary cascade risk modules")
    domain_archetype: str = Field(default="SaaS & Workflow Platform", description="Architectural domain blueprint of the project")
    available_archetypes: list[dict[str, str]] = Field(default_factory=list, description="List of available architecture domain blueprints")
    estimated_user_impact: str = Field(..., description="Executive narrative of business/user impact")
    containment_strategies: list[str] = Field(default_factory=list, description="Immediate AI containment recommendations")
    nodes: list[ModuleNode] = Field(default_factory=list, description="Architectural module nodes in the graph")
    edges: list[DependencyEdge] = Field(default_factory=list, description="Directional dependency links between modules")
    defect_allocations: list[DefectAllocation] = Field(default_factory=list, description="Autonomous allocation and downstream failure mapping for all defects in project")
    auto_allocated_summary: str = Field(default="", description="Autonomous allocation summary narrative")
    total_defects_analyzed: int = Field(default=0, description="Total defects evaluated in this project")



