from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import (
    assist_bug_report,
    classify_defect,
    detect_duplicates,
    fix_code_snippet,
    generate_chat_response,
    generate_resolution_assistance,
    get_chat_starter_topics,
    predict_severity,
    predict_sprint_health,
    semantic_search_defects,
)
from app.auth import get_current_user
from app.database import get_db
from app.errors import ErrorResponse
from app.models import User
from app.schemas import (
    AIAssistRequest,
    AIAssistResponse,
    AIChatRequest,
    AIChatResponse,
    AIChatTopicsResponse,
    CodeFixRequest,
    CodeFixResponse,
    DefectClassifyRequest,
    DefectClassifyResponse,
    DuplicateDetectRequest,
    DuplicateDetectResponse,
    ResolutionAssistanceRequest,
    ResolutionAssistanceResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SeverityPredictRequest,
    SeverityPredictResponse,
    SprintHealthResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/classify-defect",
    response_model=DefectClassifyResponse,
    summary="AI Defect Classification",
    description="Analyze raw defect text to recommend Category, Module, Defect Type, Severity, and Priority.",
    responses={
        200: {"description": "Taxonomy recommendations returned", "model": DefectClassifyResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_classify_defect(
    request: DefectClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    """Classify defect domain taxonomy using AI."""
    return await classify_defect(request)


@router.post(
    "/assist",
    response_model=AIAssistResponse,
    summary="Line-by-Line Structured Expansion Copilot",
    description="Expand brief or unstructured bug notes into a comprehensive, professional, line-by-line defect report.",
    responses={
        200: {"description": "Expanded bug report payload", "model": AIAssistResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_assist_bug_report(
    request: AIAssistRequest,
    current_user: User = Depends(get_current_user),
):
    """Expand raw bug notes into a standardized format."""
    return await assist_bug_report(request)


@router.post(
    "/predict-severity",
    response_model=SeverityPredictResponse,
    summary="Predict defect severity & business risk",
    description="Evaluate business impact and outage risk to suggest appropriate Severity and Priority levels.",
    responses={
        200: {"description": "Predicted severity level", "model": SeverityPredictResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_predict_severity(
    request: SeverityPredictRequest,
    current_user: User = Depends(get_current_user),
):
    """Predict defect severity and business risk score."""
    return await predict_severity(request)


@router.post(
    "/detect-duplicates",
    response_model=DuplicateDetectResponse,
    summary="Detect potential duplicate defects",
    description="Compare a new defect candidate against existing project issues using QA-domain token overlap and stemming.",
    responses={
        200: {"description": "Duplicate detection results", "model": DuplicateDetectResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
def ai_detect_duplicates(
    request: DuplicateDetectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check for duplicate defects in the project."""
    return detect_duplicates(request, db)


@router.post(
    "/fix-code",
    response_model=CodeFixResponse,
    summary="Code Doctor (Pure Direct Syntax & Semantic Repair)",
    description="Diagnose code errors and generate clean, corrected code with root cause explanation and diffs.",
    responses={
        200: {"description": "Code fix and analysis returned", "model": CodeFixResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_fix_code(
    request: CodeFixRequest,
    current_user: User = Depends(get_current_user),
):
    """Fix syntax and logic errors in code snippet."""
    return await fix_code_snippet(request)


@router.post(
    "/sprint-health/{sprint_id}",
    response_model=SprintHealthResponse,
    summary="Evaluate Sprint Health & Risk",
    description="Calculate sprint health score (0-100), risk level (Low/Medium/High/Critical), and generate actionable mitigation advice.",
    responses={
        200: {"description": "Sprint health assessment", "model": SprintHealthResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        404: {"description": "Sprint not found", "model": ErrorResponse},
    },
)
def ai_sprint_health(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Calculate sprint risk metrics and recommendations."""
    return predict_sprint_health(sprint_id, db)


@router.post(
    "/semantic-search",
    response_model=SemanticSearchResponse,
    summary="Semantic Vector Concept Search",
    description="Search defect tickets conceptually using dense vector ontology and semantic similarity math.",
    responses={
        200: {"description": "Ranked conceptual defect matches", "model": SemanticSearchResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search defects by conceptual intent rather than exact keywords."""
    return await semantic_search_defects(request, db)


@router.post(
    "/resolution-assistance",
    response_model=ResolutionAssistanceResponse,
    summary="Resolution Assistance Copilot (Signature Feature)",
    description="Generate developer diagnostic checklist, historical similar defects, past resolution context, and recommended code fix.",
    responses={
        200: {"description": "Resolution assistance package", "model": ResolutionAssistanceResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_resolution_assistance(
    request: ResolutionAssistanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate resolution assistance for a defect."""
    return await generate_resolution_assistance(request, db)


@router.post(
    "/chat",
    response_model=AIChatResponse,
    summary="AI QA & Developer Mentor Chatbot",
    description="Interactive conversational chatbot to answer beginner questions on reporting, diagnosing, reproducing, and solving bugs.",
    responses={
        200: {"description": "Conversational assistant response", "model": AIChatResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
        422: {"description": "Validation error", "model": ErrorResponse},
    },
)
async def ai_chat_mentor(
    request: AIChatRequest,
    current_user: User = Depends(get_current_user),
):
    """Interact with the AI QA & Developer Mentor."""
    return await generate_chat_response(request)


@router.get(
    "/chat/topics",
    response_model=AIChatTopicsResponse,
    summary="AI Chatbot Starter Topics & Beginner Questions",
    description="Fetch categorized starter topics, prompt pills, and beginner guide topics.",
    responses={
        200: {"description": "Curated topic categories returned", "model": AIChatTopicsResponse},
        401: {"description": "Unauthorized access", "model": ErrorResponse},
    },
)
def ai_chat_topics(
    current_user: User = Depends(get_current_user),
):
    """Get curated starter topics and prompt questions for beginners."""
    return get_chat_starter_topics()

