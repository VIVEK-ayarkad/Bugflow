from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai import (
    assist_bug_report,
    detect_duplicates,
    fix_code_snippet,
    predict_severity,
    predict_sprint_health,
)
from app.auth import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import (
    AIAssistRequest,
    AIAssistResponse,
    CodeFixRequest,
    CodeFixResponse,
    DuplicateDetectRequest,
    DuplicateDetectResponse,
    SeverityPredictRequest,
    SeverityPredictResponse,
    SprintHealthResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


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
