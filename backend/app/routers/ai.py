from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import (
    assist_bug_report,
    classify_defect,
    detect_duplicates,
    fix_code_snippet,
    generate_resolution_assistance,
    predict_severity,
    predict_sprint_health,
    semantic_search_defects,
)
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    AIAssistRequest,
    AIAssistResponse,
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


@router.post("/classify-defect", response_model=DefectClassifyResponse)
async def ai_classify_defect(
    request: DefectClassifyRequest,
    current_user: User = Depends(get_current_user),
):
    return await classify_defect(request)


@router.post("/assist", response_model=AIAssistResponse)
async def ai_assist_bug_report(
    request: AIAssistRequest,
    current_user: User = Depends(get_current_user),
):
    return await assist_bug_report(request)


@router.post("/predict-severity", response_model=SeverityPredictResponse)
async def ai_predict_severity(
    request: SeverityPredictRequest,
    current_user: User = Depends(get_current_user),
):
    return await predict_severity(request)


@router.post("/detect-duplicates", response_model=DuplicateDetectResponse)
def ai_detect_duplicates(
    request: DuplicateDetectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return detect_duplicates(request, db)


@router.post("/fix-code", response_model=CodeFixResponse)
async def ai_fix_code(
    request: CodeFixRequest,
    current_user: User = Depends(get_current_user),
):
    return await fix_code_snippet(request)


@router.post("/sprint-health/{sprint_id}", response_model=SprintHealthResponse)
def ai_sprint_health(
    sprint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return predict_sprint_health(sprint_id, db)


@router.post("/semantic-search", response_model=SemanticSearchResponse)
async def ai_semantic_search(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await semantic_search_defects(request, db)


@router.post("/resolution-assistance", response_model=ResolutionAssistanceResponse)
async def ai_resolution_assistance(
    request: ResolutionAssistanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await generate_resolution_assistance(request, db)
