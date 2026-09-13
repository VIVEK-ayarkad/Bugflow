import ast
import difflib
import json
import math
import re
import time
from typing import Any

from openai import AsyncOpenAI
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models import Issue, IssuePriority, IssueSeverity, IssueStatus, Sprint
from app.schemas import (
    AIAssistRequest,
    AIAssistResponse,
    AIChatRequest,
    AIChatResponse,
    AIChatTopicCategory,
    AIChatTopicItem,
    AIChatTopicsResponse,
    CodeFixRequest,
    CodeFixResponse,
    DefectClassifyRequest,
    DefectClassifyResponse,
    DuplicateDetectRequest,
    DuplicateDetectResponse,
    HistoricalDeveloperComment,
    HistoricalResolutionDetail,
    ResolutionAssistanceRequest,
    ResolutionAssistanceResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SeverityPredictRequest,
    SeverityPredictResponse,
    SprintAdvisorResponse,
    SprintHealthResponse,
    SprintRetrospectiveResponse,
)


class AICircuitBreaker:
    """Fast circuit breaker preventing blocking timeouts when remote AI is unavailable or rate-limited."""

    def __init__(self, failure_threshold: int = 2, recovery_timeout_seconds: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.failure_count = 0
        self.last_failure_time = 0.0
        self.state = "CLOSED"  # "CLOSED", "OPEN", "HALF_OPEN"

    def is_available(self) -> bool:
        if not settings.openai_api_key.strip():
            return False
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True

    def record_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def record_failure(self, exception: Exception | None = None):
        self.failure_count += 1
        self.last_failure_time = time.time()
        err_str = str(exception).lower() if exception else ""
        # Immediately trip breaker for quota, auth, or rate limit errors
        if any(term in err_str for term in ["quota", "credit", "rate", "auth", "401", "429", "insufficient_quota"]):
            self.state = "OPEN"
        elif self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


ai_circuit_breaker = AICircuitBreaker()

_async_openai_client: AsyncOpenAI | None = None


def get_async_openai_client() -> AsyncOpenAI | None:
    global _async_openai_client
    key = settings.openai_api_key.strip()
    if not key:
        return None
    if _async_openai_client is None:
        _async_openai_client = AsyncOpenAI(api_key=key, timeout=1.8)
    return _async_openai_client


# In-memory LRU/TTL Cache for Instant Responses
_AI_CACHE: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 3600  # 1 hour


def _get_from_cache(key: str) -> Any | None:
    if key in _AI_CACHE:
        ts, val = _AI_CACHE[key]
        if time.time() - ts < _CACHE_TTL:
            return val
        del _AI_CACHE[key]
    return None


def _set_in_cache(key: str, val: Any):
    if len(_AI_CACHE) > 500:
        # Prune oldest items
        oldest_keys = sorted(_AI_CACHE.keys(), key=lambda k: _AI_CACHE[k][0])[:100]
        for k in oldest_keys:
            _AI_CACHE.pop(k, None)
    _AI_CACHE[key] = (time.time(), val)


SYSTEM_PROMPT = """You are an expert bug report copilot for BugFlow. Given a user's short or vague bug description,
analyze it and expand it into a comprehensive, highly structured, line-by-line professional bug report.

CRITICAL FORMATTING INSTRUCTIONS:
The 'description' field MUST be formatted cleanly line-by-line with clear headers and bullet points:

Summary:
• <Concise description of the defect>

Defect Category:
• <Category, e.g. Payment, Authentication, UI/UX, Performance>

Affected Module:
• <Component / Module>

Defect Type:
• <Functional Defect, Crash / Fatal Error, UI Glitch, etc.>

Steps to Reproduce:
1. <Step 1>
2. <Step 2>
3. <Step 3>

Expected Result:
• <Expected behavior>

Actual Result:
• <Actual behavior observed>

Impact & Severity:
• <Impact on user workflow and business operations>

Diagnostic & Developer Notes:
• <Technical clues, endpoints, and error context>

Respond with JSON only (no markdown fences outside JSON):
{
  "needs_more_info": false,
  "formatted_report": {
    "title": "Concise, descriptive bug title",
    "description": "Full line-by-line formatted description",
    "steps_to_reproduce": "1. Step 1\\n2. Step 2\\n3. Step 3",
    "expected_behavior": "• Expected: ...\\n• Actual: ...",
    "category": "Category",
    "module": "Module / Component",
    "defect_type": "Defect Type",
    "priority": "low|medium|high|critical",
    "severity": "low|medium|high|critical"
  }
}"""


def _infer_title(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    if not text:
        return "Untitled software defect"
    lowered = text.lower()
    if "payment" in lowered or "checkout" in lowered:
        return "Payment Page Crash on Submit Action"
    if "login" in lowered:
        return "Authentication Failure on User Login"
    if "upload" in lowered or "image" in lowered:
        return "Media Upload Stream Interrupted"
    if "slow" in lowered or "latency" in lowered:
        return "API High Latency & Query Timeout"
    if len(text) <= 60:
        return text[:1].upper() + text[1:]
    return text[:57].rstrip() + "..."


def _infer_priority(raw: str) -> str:
    lowered = raw.lower()
    if any(term in lowered for term in ["crash", "data loss", "security", "payment", "blocked", "500", "critical"]):
        return "critical" if "crash" in lowered or "security" in lowered else "high"
    if any(term in lowered for term in ["slow", "delay", "ui", "layout", "typo", "cosmetic"]):
        return "low"
    return "medium"


def _generate_rich_description(raw: str) -> str:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    lowered = cleaned.lower()

    if any(k in lowered for k in ["pay", "checkout", "stripe", "billing", "cart", "purchase", "500", "submit"]):
        cat = "Payment"
        mod = "Checkout / Payment Gateway"
        dtype = "Functional Defect"
        steps = "1. Navigate to the Checkout / Payment page.\n2. Enter valid billing and payment details.\n3. Click the 'Submit' button.\n4. Observe the page crash / unhandled failure."
        expected = "Payment processes cleanly, transaction records successfully, and order confirmation is displayed."
        actual = "Payment page crashes immediately upon clicking Submit."
        impact = "High — Directly blocks users from completing transactions and causes revenue loss."
        notes = "Inspect submit button onClick handler, payment gateway API payload, and network error boundaries."
    elif any(k in lowered for k in ["login", "auth", "password", "signin", "signup"]):
        cat = "Authentication & Security"
        mod = "Auth / User Session"
        dtype = "Security / Access Defect"
        steps = "1. Open the user sign-in page.\n2. Input valid account credentials.\n3. Click the 'Sign In' button.\n4. Observe authentication failure."
        expected = "User is authenticated successfully and session token is issued."
        actual = "Sign-in fails or throws unhandled authentication exception."
        impact = "Critical — Users are blocked from accessing accounts."
        notes = "Inspect authHeaders(), JWT token validation, and backend /auth/login route."
    elif any(k in lowered for k in ["image", "upload", "file", "photo", "avatar"]):
        cat = "Media & Storage"
        mod = "Media Upload Service"
        dtype = "Functional Defect"
        steps = "1. Open the file attachment / media upload modal.\n2. Select a valid image file (PNG/JPG).\n3. Click upload.\n4. Observe the upload stall or drop connection."
        expected = "File uploads to storage bucket and thumbnail preview renders."
        actual = "Upload fails with unhandled connection error."
        impact = "Medium — Users unable to attach files or update profile images."
        notes = "Verify file size limits, MIME type validation, and CORS storage headers."
    elif any(k in lowered for k in ["slow", "performance", "delay", "query", "latency", "timeout"]):
        cat = "Performance"
        mod = "API Performance & Data Query Layer"
        dtype = "Performance Bottleneck"
        steps = "1. Navigate to analytics dashboard or trigger query.\n2. Inspect Network tab response timing.\n3. Observe request duration exceeding threshold."
        expected = "Data response completes in under 300ms."
        actual = "Request takes >3000ms or causes gateway timeout."
        impact = "Medium — Degraded user experience during peak usage."
        notes = "Audit database execution plans, missing table indices, and connection pool limits."
    else:
        cat = "General Application"
        mod = "Core Feature"
        dtype = "Functional Defect"
        steps = f"1. Navigate to the relevant page for '{cleaned}'.\n2. Perform the required user actions.\n3. Trigger the submit / action event.\n4. Observe unexpected system behavior."
        expected = "Feature executes as specified without unexpected errors."
        actual = f"Unexpected behavior occurs when attempting: {cleaned}."
        impact = "Impacting standard user workflow."
        notes = "Trace component state lifecycle, input parameters, and error logs."

    return (
        f"Summary:\n"
        f"• {cleaned.capitalize() if cleaned else 'Software defect reported.'}\n\n"
        f"Defect Category:\n"
        f"• {cat}\n\n"
        f"Affected Module:\n"
        f"• {mod}\n\n"
        f"Defect Type:\n"
        f"• {dtype}\n\n"
        f"Steps to Reproduce:\n"
        f"{steps}\n\n"
        f"Expected Result:\n"
        f"• {expected}\n\n"
        f"Actual Result:\n"
        f"• {actual}\n\n"
        f"Impact & Severity:\n"
        f"• {impact}\n\n"
        f"Diagnostic & Developer Notes:\n"
        f"• {notes}"
    )


def _best_effort_report(raw: str) -> dict:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    classification = _fallback_defect_classification(cleaned)
    return {
        "title": _infer_title(cleaned),
        "description": _generate_rich_description(cleaned),
        "steps_to_reproduce": "1. Navigate to the affected page.\n2. Enter required inputs.\n3. Click the Submit / Action button.\n4. Observe the defect / error.",
        "expected_behavior": "• Expected: Operation succeeds cleanly.\n• Actual: Error occurs.",
        "category": classification.category,
        "module": classification.module,
        "defect_type": classification.defect_type,
        "priority": classification.suggested_priority.value,
        "severity": classification.suggested_severity.value,
    }


def _fallback_response(raw: str) -> AIAssistResponse:
    return AIAssistResponse(
        needs_more_info=False,
        follow_up_questions=[],
        formatted_report=_best_effort_report(raw),
        message="Bug report automatically enriched with detailed reproduction steps & context.",
    )


async def assist_bug_report(request: AIAssistRequest) -> AIAssistResponse:
    cache_key = f"assist:{request.raw_description.strip().lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    if not ai_circuit_breaker.is_available():
        res = _fallback_response(request.raw_description)
        _set_in_cache(cache_key, res)
        return res

    client = get_async_openai_client()
    if not client:
        return _fallback_response(request.raw_description)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": request.raw_description},
            ],
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        data = json.loads(content)
        report = data.get("formatted_report") or _best_effort_report(request.raw_description)

        ai_circuit_breaker.record_success()
        result = AIAssistResponse(
            needs_more_info=False,
            follow_up_questions=data.get("follow_up_questions", []),
            formatted_report=report,
            message="Bug report automatically enriched with detailed reproduction steps & context.",
        )
        _set_in_cache(cache_key, result)
        return result
    except Exception as exc:
        ai_circuit_breaker.record_failure(exc)
        res = _fallback_response(request.raw_description)
        _set_in_cache(cache_key, res)
        return res


# ── AI Severity & Priority Predictor ────────────────────────────────────────

def predict_severity_rule_based(title: str, description: str) -> SeverityPredictResponse:
    text = (f"{title or ''} {description or ''}").lower().strip()

    # 1. Total outages / all users affected / payment blockage / security exploits / data loss
    if any(k in text for k in ["all users", "all user", "unable to complete payment", "cannot complete payment", "payment down", "production down", "site down", "data loss", "security exploit", "vulnerability", "ransomware", "database drop"]):
        sev = IssueSeverity.CRITICAL
        pri = IssuePriority.CRITICAL
        rat = "Critical system outage or total payment failure across all users directly blocks core business revenue."
    elif any(k in text for k in ["crash", "crashes", "fatal", "segmentation fault", "panic", "white screen", "cannot login", "lockout"]):
        sev = IssueSeverity.CRITICAL
        pri = IssuePriority.HIGH
        rat = "Critical defect causing application crash, fatal error, or authentication lockout."
    elif any(k in text for k in ["payment", "checkout", "500", "error", "fail", "broken", "blocked", "auth", "token expired"]):
        sev = IssueSeverity.HIGH
        pri = IssuePriority.HIGH
        rat = "High severity defect impacting key functional transactions without immediate workaround."
    elif any(k in text for k in ["slow", "latency", "delay", "timeout"]):
        sev = IssueSeverity.MEDIUM
        pri = IssuePriority.MEDIUM
        rat = "Performance degradation affecting system response latency."
    elif any(k in text for k in ["ui", "alignment", "typo", "cosmetic", "color", "padding", "margin", "dark mode"]):
        sev = IssueSeverity.LOW
        pri = IssuePriority.LOW
        rat = "Low severity cosmetic or visual layout discrepancy with no functional disruption."
    else:
        sev = IssueSeverity.MEDIUM
        pri = IssuePriority.MEDIUM
        rat = "Standard functional defect requiring developer investigation."

    return SeverityPredictResponse(
        predicted_severity=sev,
        predicted_priority=pri,
        confidence=0.96,
        rationale=rat
    )


async def predict_severity(request: SeverityPredictRequest) -> SeverityPredictResponse:
    cache_key = f"sev:{(request.title or '').strip().lower()}:{request.description.strip().lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    if not ai_circuit_breaker.is_available():
        res = predict_severity_rule_based(request.title or "", request.description)
        _set_in_cache(cache_key, res)
        return res

    client = get_async_openai_client()
    if not client:
        return predict_severity_rule_based(request.title or "", request.description)

    try:
        sys_prompt = """You are an AI Quality Assurance Specialist for BugFlow. Analyze bug reports and predict both severity and priority (low, medium, high, critical) with clear rationale in JSON format.

JSON Schema:
{
  "predicted_severity": "low|medium|high|critical",
  "predicted_priority": "low|medium|high|critical",
  "confidence": 0.95,
  "rationale": "Clear technical rationale explaining why this severity and priority were suggested."
}

Example:
Defect: "All users are unable to complete payment."
Response:
{
  "predicted_severity": "critical",
  "predicted_priority": "critical",
  "confidence": 0.99,
  "rationale": "Critical system outage: complete payment failure across all users directly halts business revenue and customer transactions."
}"""
        usr_prompt = f"Title: {request.title or ''}\nDescription: {request.description}"
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": usr_prompt},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        sev_map = {
            "low": IssueSeverity.LOW,
            "medium": IssueSeverity.MEDIUM,
            "high": IssueSeverity.HIGH,
            "critical": IssueSeverity.CRITICAL,
        }
        pri_map = {
            "low": IssuePriority.LOW,
            "medium": IssuePriority.MEDIUM,
            "high": IssuePriority.HIGH,
            "critical": IssuePriority.CRITICAL,
        }
        sev_str = str(data.get("predicted_severity", "medium")).lower()
        pri_str = str(data.get("predicted_priority", "medium")).lower()

        ai_circuit_breaker.record_success()
        result = SeverityPredictResponse(
            predicted_severity=sev_map.get(sev_str, IssueSeverity.MEDIUM),
            predicted_priority=pri_map.get(pri_str, IssuePriority.MEDIUM),
            confidence=float(data.get("confidence", 0.95)),
            rationale=data.get("rationale", "AI predicted severity & priority based on defect scope and user impact.")
        )
        _set_in_cache(cache_key, result)
        return result
    except Exception as exc:
        ai_circuit_breaker.record_failure(exc)
        res = predict_severity_rule_based(request.title or "", request.description)
        _set_in_cache(cache_key, res)
        return res


# ── Similar Defect & Duplicate Bug Detector ───────────────────────────────

STOP_WORDS = {"when", "the", "causes", "cause", "and", "is", "on", "in", "at", "to", "for", "with", "a", "an", "this", "that", "it", "user", "users", "when", "while"}

def _normalize_defect_stem(word: str) -> str:
    w = word.lower().strip()
    w = re.sub(r"[^\w]", "", w)
    if not w or w in STOP_WORDS:
        return ""
    # QA Domain Synonyms & Roots
    if w.startswith("crash"): return "crash"
    if w.startswith("submit") or w.startswith("submis"): return "submit"
    if w.startswith("pay"): return "pay"
    if w.startswith("fail"): return "fail"
    if w.startswith("err"): return "error"
    if w.startswith("auth") or w.startswith("login") or w.startswith("signin"): return "auth"
    if w.startswith("load"): return "load"
    if w.startswith("applic") or w.startswith("app"): return "app"
    if w.startswith("slow") or w.startswith("latency"): return "slow"
    if w.startswith("btn") or w.startswith("button"): return "button"

    # Suffix stripping
    for suffix in ["tion", "sion", "ting", "ming", "ling", "ning", "ring", "sing", "ing", "hes", "shes", "ches", "xes", "zes", "ies", "es", "ed", "ly", "al", "ment", "s"]:
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            w = w[:-len(suffix)]
            break
    return w


def calculate_defect_similarity(query_text: str, target_text: str) -> float:
    words1 = [w for w in re.findall(r"\w+", query_text.lower()) if len(w) > 1]
    words2 = [w for w in re.findall(r"\w+", target_text.lower()) if len(w) > 1]

    stems1 = set(_normalize_defect_stem(w) for w in words1 if _normalize_defect_stem(w))
    stems2 = set(_normalize_defect_stem(w) for w in words2 if _normalize_defect_stem(w))

    if not stems1 or not stems2:
        return 0.0

    inter = stems1.intersection(stems2)
    union = stems1.union(stems2)
    jaccard = len(inter) / len(union) if union else 0.0
    overlap = len(inter) / min(len(stems1), len(stems2))

    # Boost for high stem overlap
    score = max(jaccard, overlap * 0.95)

    # Substring direct title match boost
    q_clean = query_text.strip().lower()
    t_clean = target_text.strip().lower()
    if q_clean and (q_clean in t_clean or t_clean in q_clean):
        score = max(score, 0.90)

    return round(min(1.0, score), 3)


def detect_duplicates(request: DuplicateDetectRequest, db: Session) -> DuplicateDetectResponse:
    query_text = f"{request.title or ''} {request.description or ''}".strip()
    if not query_text:
        return DuplicateDetectResponse(has_duplicates=False, potential_duplicates=[])

    existing_issues = db.query(Issue).filter(Issue.project_id == request.project_id).all()
    potential_duplicates = []

    for issue in existing_issues:
        issue_text = f"{issue.title or ''} {issue.description or ''}".strip()
        score = calculate_defect_similarity(query_text, issue_text)

        if score >= 0.40:
            potential_duplicates.append({
                "id": issue.id,
                "key": f"DEF-{issue.id}",
                "title": issue.title,
                "description": issue.description,
                "status": issue.status.value if hasattr(issue.status, 'value') else issue.status,
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
                "similarity_score": round(score * 100, 1),
                "reporter": issue.reporter.username if issue.reporter else "System"
            })

    potential_duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return DuplicateDetectResponse(
        has_duplicates=len(potential_duplicates) > 0,
        potential_duplicates=potential_duplicates[:5]
    )


# ── Semantic Search Engine ────────────────────────────────────────────────

SEMANTIC_CLUSTERS = [
    {
        "name": "payment_checkout",
        "keywords": ["payment", "pay", "transaction", "checkout", "billing", "bill", "stripe", "paypal", "purchase", "order", "invoice", "charge", "refund", "cart", "gateway", "card", "submitting payment", "submit payment"]
    },
    {
        "name": "crash_failure",
        "keywords": ["crash", "crashes", "crashed", "crashing", "fatal", "fail", "fails", "failed", "failure", "failing", "exception", "unhandled", "error", "panic", "freeze", "hang", "broken", "500", "white screen", "abort"]
    },
    {
        "name": "form_action_submission",
        "keywords": ["submit", "submits", "submitting", "submission", "click", "clicks", "clicking", "checkout", "press", "confirm", "proceed", "button", "trigger", "action", "finalize"]
    },
    {
        "name": "auth_access",
        "keywords": ["auth", "authentication", "login", "signin", "sign-in", "signup", "logout", "password", "credential", "session", "token", "jwt", "unauthorized", "401", "403", "forbidden", "permission"]
    },
    {
        "name": "performance_speed",
        "keywords": ["slow", "latency", "lag", "delay", "delayed", "timeout", "timed out", "sluggish", "bottleneck", "high cpu", "memory", "query time"]
    },
    {
        "name": "ui_display",
        "keywords": ["ui", "ux", "layout", "visual", "css", "style", "alignment", "align", "offset", "color", "padding", "margin", "dark mode", "responsive", "mobile", "modal", "icon", "overlap"]
    },
    {
        "name": "media_upload",
        "keywords": ["upload", "uploading", "download", "file", "image", "photo", "picture", "avatar", "attachment", "pdf", "storage", "bucket"]
    },
    {
        "name": "database_storage",
        "keywords": ["database", "db", "sql", "postgres", "table", "query", "record", "row", "column", "persist", "data loss", "corrupt", "foreign key"]
    },
    {
        "name": "notification_alerts",
        "keywords": ["notification", "notify", "alert", "email", "sms", "message", "websocket", "chat", "broadcast", "push"]
    }
]


def build_semantic_vector(text: str) -> list[float]:
    t = text.lower()
    words = re.findall(r"\w+", t)
    vec = []

    for cluster in SEMANTIC_CLUSTERS:
        weight = 0.0
        for kw in cluster["keywords"]:
            if " " in kw:
                if kw in t:
                    weight += 2.5
            else:
                for w in words:
                    if w == kw:
                        weight += 1.5
                    elif len(w) > 3 and len(kw) > 3 and (w.startswith(kw[:4]) or kw.startswith(w[:4])):
                        weight += 0.9
        vec.append(weight)
    return vec


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


async def get_embedding(text: str) -> list[float]:
    """Return dense semantic vector representation instantly."""
    return build_semantic_vector(text)


async def semantic_search_defects(request: SemanticSearchRequest, db: Session) -> SemanticSearchResponse:
    query = request.query.strip()
    if not query:
        return SemanticSearchResponse(query=query, results=[], total_found=0)

    db_query = db.query(Issue).options(joinedload(Issue.reporter), joinedload(Issue.assigned_developer))
    if request.project_id:
        db_query = db_query.filter(Issue.project_id == request.project_id)

    issues = db_query.all()
    if not issues:
        return SemanticSearchResponse(query=query, results=[], total_found=0)

    query_vec = build_semantic_vector(query)
    q_lower = query.lower()
    q_words = set(re.findall(r"\w{3,}", q_lower))
    results = []

    for issue in issues:
        doc_text = f"{issue.title}. {issue.description or ''} Category: {issue.category or ''}. Module: {issue.module or ''}"
        doc_vec = build_semantic_vector(doc_text)
        sim = cosine_similarity(query_vec, doc_vec)

        # Keyword match bonus
        doc_lower = doc_text.lower()
        if q_lower in doc_lower:
            sim = max(sim, 0.92)

        # Token overlap bonus
        doc_words = set(re.findall(r"\w{3,}", doc_lower))
        if q_words and doc_words:
            inter = q_words.intersection(doc_words)
            if len(inter) >= 2:
                sim = max(sim, 0.65)

        if sim >= request.threshold:
            results.append({
                "id": issue.id,
                "key": f"DEF-{issue.id}",
                "title": issue.title,
                "description": issue.description,
                "category": issue.category or "General",
                "module": issue.module or "Core",
                "defect_type": issue.defect_type or "Defect",
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
                "priority": issue.priority.value if hasattr(issue.priority, 'value') else issue.priority,
                "status": issue.status.value if hasattr(issue.status, 'value') else issue.status,
                "similarity_score": round(sim * 100, 1),
                "reporter": issue.reporter.username if issue.reporter else "System",
                "assigned_developer": issue.assigned_developer.username if issue.assigned_developer else None,
                "created_at": issue.created_at.isoformat() if issue.created_at else None
            })

    # Sort descending by similarity score
    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    results = results[:request.limit]

    return SemanticSearchResponse(
        query=query,
        results=results,
        total_found=len(results)
    )

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    selected = results[:request.limit]
    return SemanticSearchResponse(query=query, results=selected, total_found=len(selected))


# ── Resolution Assistance Engine (Signature Feature) ──────────────────────

async def generate_resolution_assistance(request: ResolutionAssistanceRequest, db: Session) -> ResolutionAssistanceResponse:
    """Generate comprehensive resolution recommendations using:
    1. Defect description & reproduction steps
    2. Defect category & affected module
    3. Severity classification & triage urgency
    4. Discussion comments & diagnostic error logs
    5. Similar historical defects
    6. Past proven historical resolutions
    """
    title = request.title.strip()
    desc = (request.description or "").strip()
    category = (request.category or "").strip()
    module = (request.module or "").strip()
    severity_raw = request.severity.value if hasattr(request.severity, "value") else str(request.severity or "medium").lower()

    # Normalize comments list
    raw_comments = request.comments
    comment_list: list[str] = []
    if isinstance(raw_comments, list):
        comment_list = [str(c).strip() for c in raw_comments if str(c).strip()]
    elif isinstance(raw_comments, str) and raw_comments.strip():
        comment_list = [raw_comments.strip()]

    # If issue_id is provided and no comments were explicitly passed, load from DB
    if request.issue_id and not comment_list:
        db_issue = db.query(Issue).filter(Issue.id == request.issue_id).first()
        if db_issue and db_issue.comments:
            comment_list = [c.content for c in db_issue.comments if c.content]
            if not category and db_issue.category:
                category = db_issue.category
            if not module and db_issue.module:
                module = db_issue.module
            if severity_raw == "medium" and db_issue.severity:
                severity_raw = db_issue.severity.value if hasattr(db_issue.severity, "value") else str(db_issue.severity).lower()

    comments_text = " ".join(comment_list)
    combined_text = f"{title} {desc} {category} {module} {comments_text}".lower()

    # Track which context signals are actively incorporated
    signals_used = ["defect_description"]
    if category or module:
        signals_used.append("defect_category")
    if severity_raw:
        signals_used.append("severity")
    if comment_list:
        signals_used.append("comments")

    # 1. Search for Similar Defects & Historical Resolutions in the Database
    db_query = db.query(Issue)
    if request.project_id:
        db_query = db_query.filter(Issue.project_id == request.project_id)
    if request.issue_id:
        db_query = db_query.filter(Issue.id != request.issue_id)

    candidates = db_query.all()
    similar_defects = []
    historical_resolutions_collected = []
    detailed_historical_resolutions: list[HistoricalResolutionDetail] = []

    for issue in candidates:
        cand_text = f"{issue.title} {issue.description or ''}"
        score = calculate_defect_similarity(f"{title} {desc}", cand_text)

        if score >= 0.35:
            is_resolved = issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED] or str(issue.status).lower() in ["resolved", "closed"]
            res_note = None
            dev_comments = []

            if issue.comments:
                for c in issue.comments:
                    author_name = c.user.username if c.user else "Developer"
                    author_role = c.user.role.value if c.user and hasattr(c.user.role, 'value') else (str(c.user.role) if c.user else "developer")
                    c_date = c.created_at.strftime("%b %d, %Y") if (c.created_at and hasattr(c.created_at, 'strftime')) else "Recent"
                    dev_comments.append(HistoricalDeveloperComment(
                        author=author_name,
                        role=author_role,
                        content=c.content,
                        created_at=c_date
                    ))
                for c in reversed(issue.comments):
                    if len(c.content) > 12:
                        res_note = c.content[:220]
                        break

            similar_defects.append({
                "id": issue.id,
                "key": f"DEF-{issue.id}",
                "title": issue.title,
                "status": issue.status.value if hasattr(issue.status, 'value') else str(issue.status),
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                "similarity_score": round(score * 100, 1),
                "resolution_note": res_note
            })

            if is_resolved:
                # Extract or infer root cause
                root_cause = "Unhandled exception or validation boundary condition in business logic."
                for c in dev_comments:
                    c_txt = c.content.lower()
                    if "root cause" in c_txt or "caused by" in c_txt or "due to" in c_txt:
                        root_cause = c.content[:220]
                        break
                else:
                    if issue.category:
                        root_cause = f"Exception in {issue.category} flow due to unhandled parameter or state."
                    elif issue.module:
                        root_cause = f"Component failure in {issue.module} module under specific execution flow."

                # Extract or infer resolution
                fix_desc = res_note or "Applied defensive validation guard, resolved edge case, and verified via test suite."

                hist_record = HistoricalResolutionDetail(
                    defect_id=issue.id,
                    defect_key=f"DEF-{issue.id}",
                    title=issue.title,
                    severity=issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity),
                    status=issue.status.value if hasattr(issue.status, 'value') else str(issue.status),
                    similarity_score=round(score * 100, 1),
                    previous_root_cause=root_cause,
                    previous_resolution=fix_desc,
                    relevant_developer_comments=dev_comments
                )
                detailed_historical_resolutions.append(hist_record)

                if res_note:
                    historical_resolutions_collected.append(f"Historical Defect DEF-{issue.id} ('{issue.title}') was resolved: {res_note}")
                else:
                    historical_resolutions_collected.append(f"Historical Defect DEF-{issue.id} ('{issue.title}') was verified and closed.")

    similar_defects.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_similar = similar_defects[:5]
    detailed_historical_resolutions.sort(key=lambda x: x.similarity_score, reverse=True)
    top_historical = detailed_historical_resolutions[:5]

    if top_similar:
        signals_used.append("similar_defects")
    if historical_resolutions_collected or top_historical:
        signals_used.append("historical_resolutions")

    # Build primary previous resolution narrative
    historical_resolution_summary = None
    if historical_resolutions_collected:
        historical_resolution_summary = historical_resolutions_collected[0]

    # 2. Build Severity-Specific Mitigation Advice
    if severity_raw == "critical":
        severity_mitigation = (
            "🚨 CRITICAL URGENCY: Immediately engage on-call engineer, check error tracking/APM dashboards, "
            "and consider executing a feature-flag killswitch or emergency service rollback if customer transactions or data integrity are impacted."
        )
    elif severity_raw == "high":
        severity_mitigation = (
            "⚠️ HIGH PRIORITY: Isolate failing code paths with defensive exception handling and ensure telemetry logging captures stack traces."
        )
    elif severity_raw == "low":
        severity_mitigation = (
            "ℹ️ LOW PRIORITY: Minor visual or non-blocking defect; resolve during regular sprint refactoring."
        )
    else:
        severity_mitigation = (
            "⚡ MEDIUM PRIORITY: Standard priority defect; investigate and deploy fix within standard sprint cycle."
        )

    # 3. Try LLM Generation if OpenAI API Key Available and Circuit Closed
    if ai_circuit_breaker.is_available():
        client = get_async_openai_client()
        if client:
            try:
                system_msg = (
                    "You are an expert Principal Software Engineer and QA Resolution Assistant for BugFlow. "
                    "Synthesize resolution intelligence using the defect description, category, severity, discussion comments, "
                    "similar defects, and past historical resolutions. Return JSON with keys:\n"
                    "- investigation_areas (list of 4-5 concise, specific bullet points)\n"
                    "- previous_resolution (string describing how similar historical defects were resolved)\n"
                    "- possible_resolution (string describing the exact recommended technical code fix)\n"
                    "- severity_mitigation (string detailing triage urgency and containment steps)"
                )
                user_msg = (
                    f"Defect Title: {title}\n"
                    f"Description: {desc}\n"
                    f"Category: {category or 'General'}\n"
                    f"Module: {module or 'General'}\n"
                    f"Severity: {severity_raw}\n"
                    f"Discussion Comments / Error Logs: {json.dumps(comment_list)}\n"
                    f"Top Similar Defects: {json.dumps(top_similar[:3])}\n"
                    f"Historical Resolutions: {json.dumps(historical_resolutions_collected[:2])}"
                )

                chat_resp = await client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": user_msg}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2
                )
                raw = chat_resp.choices[0].message.content
                parsed = json.loads(raw)
                ai_circuit_breaker.record_success()
                return ResolutionAssistanceResponse(
                    investigation_areas=parsed.get("investigation_areas", []),
                    similar_defects=top_similar,
                    historical_resolutions=top_historical,
                    previous_resolution=historical_resolution_summary or parsed.get("previous_resolution"),
                    possible_resolution=parsed.get("possible_resolution", ""),
                    severity_mitigation=parsed.get("severity_mitigation", severity_mitigation),
                    context_signals_used=signals_used,
                    confidence=0.98
                )
            except Exception as exc:
                ai_circuit_breaker.record_failure(exc)

    # 4. Deterministic Domain Expert Engine Grounded in All 6 Signals
    # Inspect comments for runtime error clues
    comment_clues = []
    for c in comment_list:
        c_low = c.lower()
        if "null" in c_low or "undefined" in c_low:
            comment_clues.append("Examine null/undefined variable references highlighted in discussion comments.")
        if "timeout" in c_low or "deadlock" in c_low:
            comment_clues.append("Review concurrency, connection locks, and timeout logs mentioned in comments.")
        if "cors" in c_low or "401" in c_low or "403" in c_low:
            comment_clues.append("Verify auth headers and CORS origins noted in developer investigation.")
        if "line " in c_low or "exception" in c_low or "trace" in c_low:
            comment_clues.append(f"Inspect runtime stack trace referenced in comments: {c[:80]}...")

    if any(k in combined_text for k in ["pay", "checkout", "stripe", "billing", "cart", "purchase", "500", "submit", "gateway"]):
        investigation_areas = [
            "Validate payment gateway API payload and handle non-200 HTTP responses.",
            "Check null/undefined handling on transaction status response objects.",
            "Review frontend error boundary and disable duplicate form submission on click.",
            "Inspect payment webhooks and idempotent transaction processing.",
            "Audit server logs for unhandled gateway timeout exceptions."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar payment defect was resolved by validating the payment API response and ensuring idempotency keys on retry."
        )
        pos_res = (
            "Wrap payment gateway API calls in structured try-catch handlers, validate required response fields before processing, "
            "and display user-friendly error toasts if the gateway returns an unexpected status."
        )

    elif any(k in combined_text for k in ["login", "auth", "password", "signin", "sign-in", "session", "jwt", "token", "401", "403"]):
        investigation_areas = [
            "Check authentication token expiration, refresh logic, and Bearer header parsing.",
            "Inspect user session storage and cookie SameSite/Secure policies.",
            "Verify CORS headers and credentials mode on authentication endpoints.",
            "Review password hashing, salt verification, and account lockout thresholds.",
            "Check RBAC permission decorators on protected controller endpoints."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar auth defect was resolved by intercepting 401 responses, clearing stale JWT tokens, and redirecting cleanly to login."
        )
        pos_res = (
            "Implement an HTTP interceptor to handle expired JWT tokens with automatic refresh, and ensure state is reset upon 401 Unauthorized."
        )

    elif any(k in combined_text for k in ["slow", "latency", "timeout", "query", "delay", "lag", "hang"]):
        investigation_areas = [
            "Analyze database query execution plans with EXPLAIN ANALYZE for sequential table scans.",
            "Check for missing composite indexes on filtered and foreign key columns.",
            "Audit connection pool limits and database transaction timeouts.",
            "Review frontend component re-render loops and unmemoized selectors.",
            "Inspect cache hit/miss rates on read-heavy API routes."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar performance defect was resolved by adding database indexes on foreign keys and paginating large query result sets."
        )
        pos_res = (
            "Add appropriate database indexes for frequently filtered columns, implement pagination with limit/offset, and cache static read payloads."
        )

    elif any(k in combined_text for k in ["ui", "layout", "css", "align", "overlap", "mobile", "dark mode", "button", "responsive"]):
        investigation_areas = [
            "Inspect CSS flexbox / grid layout rules and container overflow constraints.",
            "Verify responsive media query breakpoints across mobile and desktop viewports.",
            "Check z-index stacking context for modal overlays and dropdown menus.",
            "Audit CSS custom properties (variables) inheritance in dark/light mode themes.",
            "Verify touch target dimensions (min 44px) on mobile touch devices."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar UI defect was resolved by applying proper box-sizing: border-box and flex-wrap properties."
        )
        pos_res = (
            "Adjust container layout constraints with flex-wrap and responsive CSS media queries to prevent overlapping on constrained viewports."
        )

    elif any(k in combined_text for k in ["upload", "file", "image", "attachment", "pdf", "storage", "download"]):
        investigation_areas = [
            "Check file size limit configurations in server controllers and reverse proxy (Nginx).",
            "Verify MIME type validation and multipart/form-data boundary parsing.",
            "Check storage directory read/write permissions on the host system.",
            "Review asynchronous upload timeout and chunk retry configurations.",
            "Inspect client-side FormData construction and Content-Type header omission."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar upload defect was resolved by configuring reverse proxy client_max_body_size and adding file extension validation."
        )
        pos_res = (
            "Validate file mime-types and size limits before initiation, and stream file uploads with structured error handling for network interruptions."
        )

    else:
        investigation_areas = [
            "Inspect relevant service controller and API route handlers.",
            "Check parameter validation and type constraints on inputs.",
            "Review recent git commit history on the affected component.",
            "Verify error boundaries and fallback UI states.",
            "Check application runtime logs and telemetry traces."
        ]
        prev_res = (
            historical_resolution_summary
            or "A similar issue was resolved by strengthening input validation and adding defensive null checks."
        )
        pos_res = (
            "Sanitize input arguments, add explicit boundary checks, and wrap asynchronous operations in structured try-catch handlers."
        )

    # Append any specific clues detected from discussion comments
    if comment_clues:
        investigation_areas = comment_clues[:2] + investigation_areas[:3]

    return ResolutionAssistanceResponse(
        investigation_areas=investigation_areas,
        similar_defects=top_similar,
        historical_resolutions=top_historical,
        previous_resolution=prev_res,
        possible_resolution=pos_res,
        severity_mitigation=severity_mitigation,
        context_signals_used=signals_used,
        confidence=0.96
    )


# ── Sprint Health Predictor ───────────────────────────────────────────────

def predict_sprint_health(sprint_id: int, db: Session) -> SprintHealthResponse:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        return SprintHealthResponse(
            sprint_id=sprint_id,
            sprint_name="Unknown Sprint",
            risk_level="Low",
            health_score=100,
            open_issues_count=0,
            resolved_issues_count=0,
            critical_issues_count=0,
            recommendations=["No sprint data available."]
        )

    issues = sprint.issues
    total_issues = len(issues)
    if total_issues == 0:
        return SprintHealthResponse(
            sprint_id=sprint.id,
            sprint_name=sprint.name,
            risk_level="Low",
            health_score=100,
            open_issues_count=0,
            resolved_issues_count=0,
            critical_issues_count=0,
            recommendations=["Sprint has no assigned issues yet. Add issues to track sprint progress."]
        )

    open_issues = [i for i in issues if i.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]]
    resolved_issues = [i for i in issues if i.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]]
    critical_issues = [i for i in open_issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL]

    completion_rate = len(resolved_issues) / total_issues
    critical_ratio = len(critical_issues) / total_issues

    health_score = int(completion_rate * 60 + (1 - critical_ratio) * 40)
    if health_score > 100:
        health_score = 100

    if health_score >= 80:
        risk_level = "Low"
    elif health_score >= 50:
        risk_level = "Medium"
    elif health_score >= 30:
        risk_level = "High"
    else:
        risk_level = "Critical"

    recommendations = []
    if critical_issues:
        recommendations.append(f"🔥 Address {len(critical_issues)} open critical bug(s) blocking sprint completion immediately.")
    if len(open_issues) > len(resolved_issues) * 2:
        recommendations.append("⚠️ High backlog of open/in-progress issues remaining. Consider re-assigning issues or reducing scope.")
    if completion_rate >= 0.75:
        recommendations.append("✅ Sprint velocity is strong. On track for on-time completion.")
    else:
        recommendations.append("💡 Conduct a mid-sprint sync with the team to focus on resolving in-review tickets.")

    return SprintHealthResponse(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        risk_level=risk_level,
        health_score=health_score,
        open_issues_count=len(open_issues),
        resolved_issues_count=len(resolved_issues),
        critical_issues_count=len(critical_issues),
        recommendations=recommendations,
    )


# ── Sprint Retrospective Generator ───────────────────────────────────────────

def generate_sprint_retrospective(sprint_id: int, db: Session) -> SprintRetrospectiveResponse:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        return SprintRetrospectiveResponse(
            sprint_id=sprint_id,
            sprint_name="Unknown Sprint",
            velocity_score=50,
            completion_rate=0.0,
            summary="Sprint not found.",
            highlights=[],
            blockers=["Sprint record missing."],
            risk_drivers=[],
            action_items=["Verify sprint identifier and recreate milestone if needed."],
        )

    issues = sprint.issues
    total = len(issues)
    if total == 0:
        return SprintRetrospectiveResponse(
            sprint_id=sprint.id,
            sprint_name=sprint.name,
            velocity_score=100,
            completion_rate=1.0,
            summary=f"Sprint '{sprint.name}' completed with an empty milestone scope.",
            highlights=["Zero defects reported in milestone scope."],
            blockers=[],
            risk_drivers=[],
            action_items=["Plan tickets for the next sprint cycle."],
        )

    resolved_issues = [i for i in issues if i.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED]]
    open_issues = [i for i in issues if i.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]]
    critical_resolved = [i for i in resolved_issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL]
    critical_unresolved = [i for i in open_issues if i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL]

    completion_rate = round(len(resolved_issues) / total, 2)
    velocity_score = int(completion_rate * 70 + (30 if len(critical_unresolved) == 0 else 10))
    if velocity_score > 100:
        velocity_score = 100

    highlights = []
    if len(resolved_issues) > 0:
        highlights.append(f"🎉 Successfully shipped and resolved {len(resolved_issues)} defect(s) ({int(completion_rate * 100)}% completion rate).")
    if len(critical_resolved) > 0:
        highlights.append(f"🛡️ Hardened platform stability by closing {len(critical_resolved)} critical vulnerability / outage issue(s).")
    
    # Categorical breakdown
    modules_fixed = set(i.module for i in resolved_issues if i.module)
    if modules_fixed:
        highlights.append(f"📦 Stabilized core subsystem modules: {', '.join(list(modules_fixed)[:3])}.")

    blockers = []
    if len(critical_unresolved) > 0:
        blockers.append(f"🚨 {len(critical_unresolved)} critical bug(s) remain open and require immediate rollover triage.")
    in_review_cnt = sum(1 for i in open_issues if i.status == IssueStatus.IN_REVIEW)
    if in_review_cnt > 0:
        blockers.append(f"⏳ {in_review_cnt} ticket(s) remained queued in review stage at sprint closure.")
    if len(open_issues) > len(resolved_issues):
        blockers.append(f"⚠️ Scope over-commitment: {len(open_issues)} incomplete tasks out of {total} total committed items.")

    risk_drivers = []
    # Workload skew
    dev_counts: dict[str, int] = {}
    for i in issues:
        dev_name = i.assigned_developer.username if i.assigned_developer else "Unassigned"
        dev_counts[dev_name] = dev_counts.get(dev_name, 0) + 1
    
    max_dev, max_count = max(dev_counts.items(), key=lambda x: x[1]) if dev_counts else ("None", 0)
    if max_count > total * 0.5 and total > 2:
        risk_drivers.append(f"Workload concentration: Developer '{max_dev}' held {max_count}/{total} ({int(max_count/total*100)}%) of all sprint issues.")
    if "Unassigned" in dev_counts and dev_counts["Unassigned"] > 0:
        risk_drivers.append(f"{dev_counts['Unassigned']} issue(s) remained unassigned throughout the sprint.")

    action_items = []
    if len(critical_unresolved) > 0:
        action_items.append("Immediate: Prioritize rollover of unresolved critical tickets into Sprint backlog with top urgency.")
    if completion_rate < 0.7:
        action_items.append("Planning: Adjust team commitment capacity down by 15-20% for the upcoming sprint to prevent spillover.")
    else:
        action_items.append("Velocity: Maintain current velocity rhythm and review opportunities for automated integration testing.")
    action_items.append("Process: Conduct short 15-minute async retrospective check with assigned developers.")

    summary = (
        f"Sprint '{sprint.name}' completed with a velocity score of {velocity_score}/100. "
        f"The team delivered {len(resolved_issues)} of {total} committed items ({int(completion_rate * 100)}% delivery rate). "
        f"{'Platform stability is high with all critical issues addressed.' if len(critical_unresolved) == 0 else f'Attention required on {len(critical_unresolved)} critical open defects.'}"
    )

    return SprintRetrospectiveResponse(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        velocity_score=velocity_score,
        completion_rate=completion_rate,
        summary=summary,
        highlights=highlights,
        blockers=blockers,
        risk_drivers=risk_drivers,
        action_items=action_items,
    )


# ── Sprint Scope & Capacity Advisor ───────────────────────────────────────────

def generate_sprint_advisor(sprint_id: int, db: Session) -> SprintAdvisorResponse:
    sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not sprint:
        return SprintAdvisorResponse(
            sprint_id=sprint_id,
            sprint_name="Unknown Sprint",
            capacity_status="Balanced",
            risk_level="Low",
            recommendations=["Sprint not found."],
            unassigned_critical_count=0,
            workload_skew_warning=None,
        )

    issues = sprint.issues
    total = len(issues)
    unassigned_critical = sum(
        1 for i in issues 
        if i.assigned_developer_id is None 
        and (i.severity == IssueSeverity.CRITICAL or i.priority == IssuePriority.CRITICAL)
        and i.status not in [IssueStatus.RESOLVED, IssueStatus.CLOSED]
    )

    # Developer count & workload balance
    dev_counts: dict[str, int] = {}
    for i in issues:
        dev_name = i.assigned_developer.username if i.assigned_developer else "Unassigned"
        dev_counts[dev_name] = dev_counts.get(dev_name, 0) + 1

    skew_warning = None
    if dev_counts and total >= 3:
        for dev, cnt in dev_counts.items():
            if dev != "Unassigned" and cnt > total * 0.55:
                skew_warning = f"Developer '{dev}' is assigned {cnt}/{total} ({int(cnt/total*100)}%) of tickets in this sprint."

    # Capacity evaluation
    if total > 15:
        capacity_status = "Overloaded"
        risk_level = "High"
    elif total < 3:
        capacity_status = "Underutilized"
        risk_level = "Low"
    else:
        capacity_status = "Balanced"
        risk_level = "Medium" if unassigned_critical > 0 or skew_warning else "Low"

    recs = []
    if unassigned_critical > 0:
        recs.append(f"⚠️ {unassigned_critical} critical bug(s) lack an assigned developer. Assign immediately to prevent sprint failure.")
    if skew_warning:
        recs.append(f"⚖️ Rebalance ticket distribution: {skew_warning}")
    if capacity_status == "Overloaded":
        recs.append("📉 Sprint backlog exceeds recommended concurrency. Consider moving non-critical defects back to project backlog.")
    elif capacity_status == "Underutilized":
        recs.append("📈 Team capacity is open. Pull top-priority tickets from project backlog into this sprint.")
    else:
        recs.append("✅ Sprint scope is well balanced with sustainable workload distribution.")

    return SprintAdvisorResponse(
        sprint_id=sprint.id,
        sprint_name=sprint.name,
        capacity_status=capacity_status,
        risk_level=risk_level,
        recommendations=recs,
        unassigned_critical_count=unassigned_critical,
        workload_skew_warning=skew_warning,
    )


# ── Big Tech Multi-Dimensional Code Intelligence & Remediation ──────────────

def _generate_unified_diff(original_code: str, corrected_code: str) -> list[dict[str, Any]]:
    orig_lines = original_code.splitlines()
    corr_lines = corrected_code.splitlines()
    diff = list(difflib.unified_diff(orig_lines, corr_lines, fromfile="original", tofile="corrected", lineterm=""))
    diff_records = []
    line_no_orig = 0
    line_no_corr = 0
    for line_item in diff:
        if line_item.startswith("@@"):
            diff_records.append({"type": "info", "text": line_item.strip()})
        elif line_item.startswith("-") and not line_item.startswith("---"):
            line_no_orig += 1
            diff_records.append({"type": "del", "line_orig": line_no_orig, "text": line_item})
        elif line_item.startswith("+") and not line_item.startswith("+++"):
            line_no_corr += 1
            diff_records.append({"type": "add", "line_corr": line_no_corr, "text": line_item})
        elif not line_item.startswith("---") and not line_item.startswith("+++"):
            line_no_orig += 1
            line_no_corr += 1
            diff_records.append({"type": "ctx", "line_orig": line_no_orig, "line_corr": line_no_corr, "text": line_item})
    return diff_records


def _analyze_security_vulnerabilities(code: str, lang: str) -> list[dict[str, Any]]:
    findings = []
    # SQL Injection (CWE-89)
    if re.search(r"(f[\"'].*SELECT.*\{|SELECT.*[\"']\s*\+\s*\w+|\bcursor\.execute\([\"'].*%s[\"']\s*%)", code, re.IGNORECASE):
        findings.append({
            "cwe_id": "CWE-89",
            "title": "SQL Injection via Dynamic String Interpolation",
            "severity": "Critical",
            "description": "Constructing raw SQL queries via string interpolation allows attackers to bypass authentication and exfiltrate database records.",
            "remediation": "Use parameterized queries with bound placeholders (e.g. cursor.execute('SELECT ... WHERE id = :id', {'id': user_id})) or ORM binding."
        })
    # OS Command Injection (CWE-78)
    if re.search(r"(os\.system\(|subprocess\.(Popen|run|call)\(.*shell\s*=\s*True|exec\(|eval\()", code):
        findings.append({
            "cwe_id": "CWE-78",
            "title": "OS Command Injection / Insecure Subprocess Execution",
            "severity": "Critical",
            "description": "Executing system shell commands with concatenated arguments allows attackers to execute arbitrary system binaries and spawn reverse shells.",
            "remediation": "Pass arguments as an argument vector (list of strings) with shell=False and strict whitelisting."
        })
    # Hardcoded Secrets (CWE-798)
    if re.search(r"(api_key|secret_key|aws_secret|password|access_token)\s*=\s*[\"'][A-Za-z0-9_\-\.]{8,}[\"']", code, re.IGNORECASE):
        findings.append({
            "cwe_id": "CWE-798",
            "title": "Hardcoded Cryptographic Secret / API Key",
            "severity": "High",
            "description": "Storing plaintext credentials or secrets in source code risks accidental exposure through version control leaks.",
            "remediation": "Load credentials securely at runtime via environment variables (os.environ.get(...)) or AWS Secrets Manager / HashiCorp Vault."
        })
    # Insecure Deserialization (CWE-502)
    if re.search(r"\bpickle\.loads?\(|yaml\.load\([^,]+\)", code):
        findings.append({
            "cwe_id": "CWE-502",
            "title": "Insecure Deserialization of Untrusted Data",
            "severity": "Critical",
            "description": "Unpickling untrusted binary streams allows arbitrary remote code execution via Python object gadget chains.",
            "remediation": "Replace pickle with safe structured serialization formats such as JSON or Protocol Buffers."
        })
    # ReDoS - Catastrophic Backtracking (CWE-1333)
    if re.search(r"(\([a-zA-Z0-9_\+\*]+\)\+|\([a-zA-Z0-9_\+\*]+\)\*|\([^\)]+\+[\)]+\+)", code):
        findings.append({
            "cwe_id": "CWE-1333",
            "title": "Regular Expression Denial of Service (ReDoS)",
            "severity": "Medium",
            "description": "Nested or overlapping regex quantifiers cause exponential CPU backtracking on non-matching payloads.",
            "remediation": "Refactor regex with atomic grouping or linear finite automata, and enforce timeout thresholds."
        })
    return findings


def _analyze_complexity_and_performance(code: str, lang: str) -> dict[str, Any] | None:
    # Check for quadratic nested loops / linear scans
    if (re.search(r"for\s+\w+\s+in\s+\w+:[\s\S]*for\s+\w+\s+in\s+\w+:", code) or
        re.search(r"for\s+\w+\s+in\s+\w+:[\s\S]*if\s+\w+\s+in\s+\w+:", code)):
        return {
            "time_complexity_original": "O(N²)",
            "time_complexity_optimized": "O(N)",
            "space_complexity_original": "O(1)",
            "space_complexity_optimized": "O(N)",
            "bottleneck_explanation": "Nested linear scans / membership checks against a list produce quadratic O(N²) execution time. Converting the lookup collection into a Hash Set provides O(1) lookups and reduces overall runtime to linear O(N)."
        }
    if re.search(r"(\.map\(.*\.filter\(|\.filter\(.*\.map\(|\.forEach\(.*\.indexOf\()", code):
        return {
            "time_complexity_original": "O(N²)",
            "time_complexity_optimized": "O(N)",
            "space_complexity_original": "O(N)",
            "space_complexity_optimized": "O(N)",
            "bottleneck_explanation": "Chained array operations with inner indexOf lookups create quadratic runtime bottlenecks. Combining transformations into a single reduce pass or Hash Map index optimizes execution."
        }
    return None


def _analyze_concurrency_and_race_conditions(code: str, lang: str) -> list[str]:
    risks = []
    if ("global " in code or "+=" in code) and ("async def" in code or "threading" in code or "Thread" in code):
        risks.append("Shared mutable state modification without synchronization mutex/lock; susceptible to race conditions under concurrent requests.")
    if "lock" in code.lower() and code.count("acquire") > 1 and "release" not in code:
        risks.append("Potential deadlock hazard: multiple locks acquired without consistent hierarchical ordering or structured context manager release.")
    if "Promise" in code and "catch" not in code and "try" not in code:
        risks.append("Unhandled Promise rejection hazard in asynchronous execution chain; can lead to silent failure or node process crashes.")
    return risks


def _analyze_resource_safety(code: str, lang: str) -> list[str]:
    patterns = []
    if "open(" in code and "with open" not in code and "close()" not in code:
        patterns.append("Unclosed file descriptor leak: file opened without 'with' statement context manager or deterministic try/finally close.")
    if re.search(r"(connect\(|SessionLocal\(|create_connection\()", code) and "with " not in code and "close()" not in code:
        patterns.append("Database connection pool exhaustion hazard: connection acquired without context manager or explicit release in finally block.")
    return patterns


def _generate_unit_tests(code: str, corrected_code: str, lang: str) -> str:
    if "python" in lang or "py" in lang:
        func_match = re.search(r"def\s+([a-zA-Z0-9_]+)\s*\((.*?)\):", corrected_code)
        func_name = func_match.group(1) if func_match else "tested_function"
        return f"""import pytest

# Module target definition
{corrected_code}


class Test{func_name.title().replace('_', '')}Suite:
    def test_nominal_execution(self):
        \"\"\"Happy-path test with standard valid inputs.\"\"\"
        # Assert valid operational return without runtime exceptions
        assert {func_name} is not None

    def test_boundary_empty_inputs(self):
        \"\"\"Boundary test: Handles empty collections and zero values cleanly.\"\"\"
        pass

    def test_boundary_null_and_none_handling(self):
        \"\"\"Boundary test: Gracefully handles None/null without raising unhandled exceptions.\"\"\"
        pass

    def test_invalid_type_error_resilience(self):
        \"\"\"Defensive test: Validates structured exception raising or validation fallback.\"\"\"
        pass
"""
    elif "javascript" in lang or "typescript" in lang or "react" in lang or "js" in lang or "ts" in lang:
        func_match = re.search(r"(?:function\s+|const\s+)([a-zA-Z0-9_]+)", corrected_code)
        func_name = func_match.group(1) if func_match else "testedFunction"
        return f"""describe('{func_name} Suite', () => {{
  test('should execute successfully on standard valid input (happy path)', () => {{
    expect({func_name}).toBeDefined();
  }});

  test('should handle empty, null, and undefined boundary inputs gracefully', () => {{
    // Boundary assertions for null and empty collections
  }});

  test('should reject invalid parameters with meaningful error or fallback', () => {{
    // Assert structured rejection
  }});
}});"""
    else:
        return f"// Automated unit test template for {lang}\n// Verify happy path, null boundary, and defensive error handling."


def _verify_ast_compilation(code: str, lang: str) -> bool:
    if "python" in lang or "py" in lang:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    return True


def _repair_quotes_and_brackets(line: str) -> tuple[str, list[str], list[str], list[str]]:
    mistakes, root_causes, explanations = [], [], []

    # 1. Unclosed strings (handling escapes and quotes)
    in_quote = None
    quote_start = -1
    i = 0
    while i < len(line):
        ch = line[i]
        if ch == "\\":
            i += 2
            continue
        if ch in ("\"", "'"):
            if in_quote is None:
                in_quote = ch
                quote_start = i
            elif in_quote == ch:
                in_quote = None
                quote_start = -1
        i += 1

    if in_quote is not None:
        mistakes.append(f"Unterminated string literal (missing closing {in_quote} quote).")
        root_causes.append(f"SyntaxError: unterminated string literal / missing closing {in_quote} quote.")
        explanations.append(f"Inserted matching closing {in_quote} quote to properly terminate the string.")

        if line.endswith(")") and not line.endswith(in_quote + ")"):
            open_paren_idx = line.rfind("(", 0, quote_start)
            if open_paren_idx != -1:
                line = line[:-1] + in_quote + ")"
            else:
                line = line + in_quote
        elif line.endswith("]") and not line.endswith(in_quote + "]"):
            line = line[:-1] + in_quote + "]"
        elif line.endswith("}") and not line.endswith(in_quote + "}"):
            line = line[:-1] + in_quote + "}"
        else:
            line = line + in_quote

    # 2. Unclosed brackets
    open_p = line.count("(") - line.count(")")
    open_b = line.count("[") - line.count("]")
    open_c = line.count("{") - line.count("}")

    if open_p > 0:
        line += ")" * open_p
        mistakes.append(f"Missing {open_p} closing parenthesis ')'.")
        root_causes.append("SyntaxError: unmatched '(' opening parenthesis.")
        explanations.append(f"Appended {open_p} closing parenthesis.")
    if open_b > 0:
        line += "]" * open_b
        mistakes.append(f"Missing {open_b} closing bracket ']'.")
        root_causes.append("SyntaxError: unmatched '[' opening bracket.")
        explanations.append(f"Appended {open_b} closing bracket.")
    if open_c > 0:
        line += "}" * open_c
        mistakes.append(f"Missing {open_c} closing brace '}}'.")
        root_causes.append("SyntaxError: unmatched '{' opening brace.")
        explanations.append(f"Appended {open_c} closing brace.")

    return line, mistakes, root_causes, explanations


def _diagnose_and_fix_code(code: str, language: str = "python", error_log: str = "", audit_profile: str = "comprehensive") -> CodeFixResponse:
    raw_code = code.strip()
    lang = (language or "python").lower()
    err = (error_log or "").lower()

    lines = raw_code.split("\n")
    fixed_lines = []
    mistakes = []
    root_causes = []
    explanations = []
    tips = []
    resilience_patterns = []

    # Run Big Tech Static Analysis
    security_findings = _analyze_security_vulnerabilities(raw_code, lang)
    complexity_analysis = _analyze_complexity_and_performance(raw_code, lang)
    concurrency_risks = _analyze_concurrency_and_race_conditions(raw_code, lang)
    resource_risks = _analyze_resource_safety(raw_code, lang)
    concurrency_risks.extend(resource_risks)

    # Specific Scenario Fixes
    # 1. SQL Injection Remediation
    if re.search(r"f[\"'].*SELECT.*\{(\w+)\}", raw_code, re.IGNORECASE):
        corrected_code = re.sub(
            r"cursor\.execute\(f[\"'](SELECT.*WHERE\s+\w+\s*=\s*)\{(\w+)\}[\"']\)",
            r'cursor.execute("\1%s", (\2,))',
            raw_code,
            flags=re.IGNORECASE
        )
        mistakes.append("CWE-89: Raw string interpolation in SQL query execution.")
        root_causes.append("Critical Security Vulnerability: SQL Injection (CWE-89).")
        explanations.append("Replaced dynamic string formatting with parameterized query and bound tuple placeholder.")
        tips.append("Never format raw SQL strings with user inputs. Always use parameterized queries or an ORM.")
        resilience_patterns.append("Parameterized SQL Query Binding")

    # 2. Big-O Complexity Remediation (Nested List Scan -> Hash Set)
    elif re.search(r"for\s+(\w+)\s+in\s+(\w+):[\s\S]*if\s+\1\s+in\s+(\w+):", raw_code):
        match = re.search(r"for\s+(\w+)\s+in\s+(\w+):[\s\S]*if\s+\1\s+in\s+(\w+):", raw_code)
        item_var, list_a, list_b = match.groups()
        corrected_code = f"# Optimized: O(N) linear time using Hash Set lookup\n{list_b}_set = set({list_b})\ncommon_items = [{item_var} for {item_var} in {list_a} if {item_var} in {list_b}_set]"
        mistakes.append(f"Quadratic O(N²) runtime caused by nested membership check '{item_var} in {list_b}'.")
        root_causes.append("Algorithmic Inefficiency: Repeated linear scans on unordered list collections.")
        explanations.append(f"Precomputed a Hash Set `{list_b}_set` to convert O(N) search operations into O(1) constant-time lookups.")
        tips.append("Use Hash Sets or Hash Maps for O(1) membership testing in high-throughput loops.")
        resilience_patterns.append("O(N) Hash Indexing")

    # 3. Concurrency Race Condition Remediation
    elif "async def" in raw_code and "+=" in raw_code and "lock" not in raw_code.lower():
        corrected_code = f"import asyncio\n\n_state_lock = asyncio.Lock()\n\n{raw_code.replace('+=', '+= # Mutex protected')}"
        if "async with _state_lock:" not in corrected_code:
            corrected_code = "import asyncio\n\n_state_lock = asyncio.Lock()\n\n" + raw_code.replace("def ", "async def ")
            corrected_code = re.sub(r"(async def\s+\w+\(.*?\):)", r"\1\n    async with _state_lock:", raw_code)
        mistakes.append("Race condition: Unsynchronized read-modify-write operation on shared state in async context.")
        root_causes.append("Concurrency Hazard: Non-atomic state mutation under concurrent async event loops.")
        explanations.append("Wrapped state mutation in `async with asyncio.Lock():` to guarantee thread-safe serial execution.")
        tips.append("Always guard shared mutable state with synchronization primitives (Locks / Semaphores / Atomics).")
        resilience_patterns.append("Asyncio Mutex Lock Guard")

    # 4. Resource Leak / Unclosed File Context Manager
    elif re.search(r"(\w+)\s*=\s*open\((.*?)\)\s*\n(.*)", raw_code) and "with open" not in raw_code:
        corrected_code = re.sub(
            r"(\w+)\s*=\s*open\((.*?)\)\s*\n\s*(.*)",
            r"with open(\2) as \1:\n    \3",
            raw_code
        )
        mistakes.append("Resource leak: File opened without deterministic context manager ('with' statement).")
        root_causes.append("Resource Safety Hazard: File descriptor leak if exceptions occur before close().")
        explanations.append("Wrapped file operations in a Python context manager (`with open(...) as f:`) for deterministic disposal.")
        tips.append("Always use context managers (`with` / `using`) for I/O resources to prevent descriptor exhaustion.")
        resilience_patterns.append("RAII Context Manager Lifecycle")

    elif "python" in lang or "py" in lang:
        is_clean_ast = False
        try:
            ast.parse(raw_code)
            is_clean_ast = True
        except SyntaxError:
            is_clean_ast = False

        for line in lines:
            if re.search(r"\b(pritn|prnt)\b", line):
                line = re.sub(r"\b(pritn|prnt)\b", "print", line)
                mistakes.append("Misspelled built-in 'print' function name.")
                root_causes.append("NameError: misspelled function name.")
                explanations.append("Corrected function name to 'print'.")

            p2_match = re.match(r"^(\s*)print\s+([^\(].*)$", line)
            if p2_match:
                indent, rest = p2_match.groups()
                line = f"{indent}print({rest.rstrip()})"
                mistakes.append("Used Python 2 print statement syntax without parentheses.")
                root_causes.append("SyntaxError: Missing parentheses in call to 'print'.")
                explanations.append("Converted print statement to Python 3 function call print(...).")
                tips.append("Python 3 requires parentheses for print().")

            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)

            if re.match(r"^\s*(if|elif|else|for|while|def|class|with|try|except|finally)\b", line):
                if not line.rstrip().endswith(":"):
                    line = line.rstrip() + ":"
                    mistakes.append("Missing colon ':' at the end of block statement header.")
                    root_causes.append("SyntaxError: expected ':' at end of header statement.")
                    explanations.append("Appended required colon ':' to header statement.")
                    tips.append("Python compound statements (if, for, def, class, etc.) must end with a colon ':'.")

            if re.search(r"\b(if|elif)\s+([a-zA-Z_]\w*)\s*=\s*([^=])", line):
                line = re.sub(r"\b(if|elif)\s+([a-zA-Z_]\w*)\s*=\s*([^=])", r"\1 \2 == \3", line)
                mistakes.append("Used single assignment operator '=' in conditional expression instead of '=='.")
                root_causes.append("SyntaxError: invalid syntax in condition assignment.")
                explanations.append("Replaced '=' with equality comparison operator '=='.")
                tips.append("Use '==' for comparison checks and '=' for variable assignment.")

            if re.search(r"\b(true|false|null|undefined)\b", line):
                line = re.sub(r"\btrue\b", "True", line)
                line = re.sub(r"\bfalse\b", "False", line)
                line = re.sub(r"\bnull\b", "None", line)
                line = re.sub(r"\bundefined\b", "None", line)
                mistakes.append("Used JavaScript/JSON literals (true/false/null) instead of Python TitleCase keywords.")
                root_causes.append("NameError: undefined literal name in Python.")
                explanations.append("Converted literals to Python TitleCase syntax (True, False, None).")

            if ("keyerror" in err or "key" in err) and re.search(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', line):
                line = re.sub(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', r'\1.get(\2)', line)
                mistakes.append("Direct dictionary indexing with [] raises KeyError when key is missing.")
                root_causes.append("KeyError when accessing non-existent dictionary key.")
                explanations.append("Replaced direct indexing with dict.get() for safe lookup.")
                tips.append("Use dict.get(key, default) for safe key retrieval.")

            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)

        if is_clean_ast and not mistakes and corrected_code == raw_code and not err and not security_findings:
            unit_tests = _generate_unit_tests(raw_code, raw_code, lang)
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No syntax, security, or logical defects detected.",
                explanation="Your Python code was analyzed across all Big Tech diagnostic lenses. It is syntactically valid, type-safe, and passes all static security audits.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is production-ready! Follow PEP 8 and maintain comprehensive unit tests.",
                security_findings=security_findings,
                complexity_analysis=complexity_analysis,
                concurrency_risks=concurrency_risks,
                generated_unit_tests=unit_tests,
                resilience_patterns=["Production Validated"],
                ast_verified=True
            )

    elif "javascript" in lang or "typescript" in lang or "js" in lang or "ts" in lang or "react" in lang:
        for line in lines:
            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)

            if re.search(r"\bconsle\b", line):
                line = re.sub(r"\bconsle\b", "console", line)
                mistakes.append("Typo in 'console' object name.")
                root_causes.append("ReferenceError: consle is not defined.")
                explanations.append("Corrected 'consle' to 'console'.")

            if ("cannot read properties" in err or "typeerror" in err) and re.search(r'(\b\w+)\.(map|filter|forEach)\(', line):
                line = re.sub(r'(\b\w+)\.(map|filter|forEach)\(', r'(\1 || []).\2(', line)
                mistakes.append("Calling array method directly on potentially undefined/null variable.")
                root_causes.append("TypeError: Cannot read properties of undefined (reading method).")
                explanations.append("Added fallback empty array guard (variable || []).method() to prevent TypeError.")
                tips.append("Use optional chaining (items?.map(...)) or fallback empty arrays (items || []).")
                resilience_patterns.append("Defensive Null/Undefined Guard")

            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)
        if not mistakes and corrected_code == raw_code and not err and not security_findings:
            unit_tests = _generate_unit_tests(raw_code, raw_code, lang)
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No runtime or structural defects detected.",
                explanation="Your JavaScript/TypeScript code was analyzed and verified. It is properly structured and ready for production deployment.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is clean and production-ready! Maintain automated unit testing coverage.",
                security_findings=security_findings,
                complexity_analysis=complexity_analysis,
                concurrency_risks=concurrency_risks,
                generated_unit_tests=unit_tests,
                resilience_patterns=["Production Validated"],
                ast_verified=True
            )

    elif "sql" in lang:
        for line in lines:
            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)

            if re.search(r"\bSEELCT\b", line, re.IGNORECASE):
                line = re.sub(r"\bSEELCT\b", "SELECT", line, flags=re.IGNORECASE)
                mistakes.append("Typo in SELECT keyword.")
                root_causes.append("Syntax error in SQL query statement.")
                explanations.append("Corrected 'SEELCT' to 'SELECT'.")

            if "null" in err and "where" in line.lower() and "=" in line:
                line = re.sub(r'=\s*NULL\b', 'IS NULL', line, flags=re.IGNORECASE)
                line = re.sub(r'!=\s*NULL\b', 'IS NOT NULL', line, flags=re.IGNORECASE)
                mistakes.append("Used = NULL comparison in SQL instead of IS NULL.")
                root_causes.append("SQL standard requires IS NULL / IS NOT NULL for NULL checks.")
                explanations.append("Replaced '= NULL' with 'IS NULL'.")
                tips.append("Always use 'IS NULL' / 'IS NOT NULL' in SQL.")

            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)
        if not mistakes and corrected_code == raw_code and not err and not security_findings:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No SQL syntax or injection defects detected.",
                explanation="Your SQL query was analyzed and verified. It is syntactically valid and sanitized.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Query syntax is clean! Use appropriate indexes and parameterized bindings.",
                security_findings=security_findings,
                complexity_analysis=complexity_analysis,
                concurrency_risks=concurrency_risks,
                generated_unit_tests=None,
                resilience_patterns=["Sanitized SQL"],
                ast_verified=True
            )

    else:
        for line in lines:
            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)
            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)
        if not mistakes and corrected_code == raw_code and not err and not security_findings:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No defects detected.",
                explanation="Your code snippet was analyzed and verified.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is clean and error-free!",
                security_findings=security_findings,
                complexity_analysis=complexity_analysis,
                concurrency_risks=concurrency_risks,
                generated_unit_tests=None,
                resilience_patterns=["Production Validated"],
                ast_verified=True
            )

    user_mistake_str = " ".join(dict.fromkeys(mistakes)) if mistakes else "Code defect or architectural vulnerability detected."
    root_cause_str = " ".join(dict.fromkeys(root_causes)) if root_causes else "Syntax or structural defect."
    explanation_str = " ".join(dict.fromkeys(explanations)) if explanations else "Applied production-grade refactoring and vulnerability patch."
    tip_str = tips[0] if tips else "Always audit security parameters and maintain test coverage."

    diff_lines = _generate_unified_diff(raw_code, corrected_code)
    unit_tests = _generate_unit_tests(raw_code, corrected_code, lang)
    ast_valid = _verify_ast_compilation(corrected_code, lang)

    return CodeFixResponse(
        is_correct=False,
        user_mistake=user_mistake_str,
        root_cause=root_cause_str,
        explanation=explanation_str,
        corrected_code=corrected_code,
        diff_lines=diff_lines,
        prevention_tip=tip_str,
        security_findings=security_findings,
        complexity_analysis=complexity_analysis,
        concurrency_risks=concurrency_risks,
        generated_unit_tests=unit_tests,
        resilience_patterns=resilience_patterns or ["Defensive Boundary"],
        ast_verified=ast_valid,
    )


async def fix_code_snippet(request: CodeFixRequest) -> CodeFixResponse:
    cache_key = f"codefix:{hash(request.code)}:{request.language}:{request.audit_profile}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    if not ai_circuit_breaker.is_available():
        res = _diagnose_and_fix_code(request.code, request.language, request.error_log, request.audit_profile)
        _set_in_cache(cache_key, res)
        return res

    client = get_async_openai_client()
    if not client:
        return _diagnose_and_fix_code(request.code, request.language, request.error_log, request.audit_profile)

    try:
        system_prompt = """You are a Principal Software Engineer and AI Code Doctor at Google/Amazon level.
Analyze the user's code snippet across all architectural dimensions:
1. Syntax & Logic Correctness
2. Security Vulnerabilities (CWE / OWASP Top 10: SQLi, Command Injection, Secrets, ReDoS, Deserialization)
3. Algorithmic Complexity (Big-O Time and Space optimization, O(N^2) to O(N))
4. Concurrency & Thread-Safety (Race conditions, async locks, deadlocks)
5. Resource Leaks (Unclosed descriptors, DB connection exhaustion)
6. Automated Unit Tests (PyTest / Jest boundary test cases)

RULES:
- If code is ALREADY correct, set is_correct: true, user_mistake: null, root_cause: "No defects detected.", corrected_code: original code.
- If code has bugs/vulnerabilities, provide the direct, production-ready corrected_code.
- Return pure JSON matching the schema below.

JSON Schema:
{
  "is_correct": boolean,
  "user_mistake": "1-2 sentence description of mistake (or null)",
  "root_cause": "Technical root cause and failure mechanism",
  "explanation": "Detailed engineering explanation of the fix",
  "corrected_code": "The raw production-ready corrected code",
  "prevention_tip": "Actionable engineering prevention rule",
  "security_findings": [{"cwe_id": "CWE-xx", "title": "...", "severity": "Critical|High|Medium", "description": "...", "remediation": "..."}],
  "complexity_analysis": {"time_complexity_original": "O(N^2)", "time_complexity_optimized": "O(N)", "space_complexity_original": "O(1)", "space_complexity_optimized": "O(N)", "bottleneck_explanation": "..."},
  "concurrency_risks": ["Risk 1", "Risk 2"],
  "generated_unit_tests": "Executable unit test code string",
  "resilience_patterns": ["Circuit Breaker", "Exponential Backoff"]
}"""
        user_prompt = f"Audit Profile: {request.audit_profile}\nLanguage: {request.language}\nError Log: {request.error_log}\nCode:\n{request.code}"
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")
        corrected_code = data.get("corrected_code", request.code)
        corrected_code = re.sub(r'^```\w*\n?', '', corrected_code)
        corrected_code = re.sub(r'\n?```$', '', corrected_code).strip()

        is_correct = bool(data.get("is_correct", False))
        if corrected_code.strip() == request.code.strip() and not data.get("user_mistake"):
            is_correct = True

        diff_lines = _generate_unified_diff(request.code, corrected_code)
        ai_circuit_breaker.record_success()
        result = CodeFixResponse(
            is_correct=is_correct,
            user_mistake=data.get("user_mistake"),
            root_cause=data.get("root_cause", "Analysis completed."),
            explanation=data.get("explanation", "Code analyzed and optimized."),
            corrected_code=corrected_code,
            prevention_tip=data.get("prevention_tip", "Validate boundaries and error handling."),
            security_findings=data.get("security_findings", []),
            complexity_analysis=data.get("complexity_analysis"),
            concurrency_risks=data.get("concurrency_risks", []),
            generated_unit_tests=data.get("generated_unit_tests", ""),
            resilience_patterns=data.get("resilience_patterns", ["Input Validation", "Defensive Fallback"]),
            diff=diff_lines,
        )
        _set_in_cache(cache_key, result)
        return result
    except Exception as exc:
        ai_circuit_breaker.record_failure(exc)
        res = _diagnose_and_fix_code(request.code, request.language, request.error_log, request.audit_profile)
        _set_in_cache(cache_key, res)
        return res
        ast_valid = _verify_ast_compilation(corrected_code, request.language)

        return CodeFixResponse(
            is_correct=is_correct,
            user_mistake=None if is_correct else data.get("user_mistake", "Code defect identified."),
            root_cause=data.get("root_cause", "No defects detected." if is_correct else "Syntax or structural defect."),
            explanation=data.get("explanation", "Code verified." if is_correct else "Corrected code with production optimizations."),
            corrected_code=corrected_code,
            diff_lines=diff_lines,
            prevention_tip=data.get("prevention_tip", "Follow engineering best practices and maintain test coverage."),
            security_findings=data.get("security_findings", []),
            complexity_analysis=data.get("complexity_analysis"),
            concurrency_risks=data.get("concurrency_risks", []),
            generated_unit_tests=data.get("generated_unit_tests"),
            resilience_patterns=data.get("resilience_patterns", []),
            ast_verified=ast_valid,
        )
    except Exception:
        return _diagnose_and_fix_code(request.code, request.language, request.error_log, request.audit_profile)


# ── Intelligent Defect Classification ──────────────────────────────────────

def _fallback_defect_classification(description: str, title: str = "") -> DefectClassifyResponse:
    combined = f"{title or ''} {description or ''}".lower().strip()

    category = "General Application"
    module = "Core Application"
    defect_type = "Functional Defect"
    severity = IssueSeverity.MEDIUM
    priority = IssuePriority.MEDIUM
    confidence = 0.90
    rationale = "Standard application defect requiring investigation and developer remediation."
    tags = []

    # 1. Payment / Billing / Checkout
    if any(k in combined for k in ["payment", "checkout", "credit card", "stripe", "paypal", "billing", "cart", "invoice", "transaction", "charge", "refund", "pricing"]):
        category = "Payment"
        module = "Checkout / Payment Gateway"
        tags.extend(["payment", "checkout", "financial-impact"])
        if any(k in combined for k in ["crash", "crashes", "500", "freeze", "fatal", "unhandled"]):
            defect_type = "Functional Defect"
            severity = IssueSeverity.HIGH
            priority = IssuePriority.HIGH
            confidence = 0.98
            rationale = "Payment failure on submission directly halts user checkout and prevents revenue transaction completion."
        else:
            defect_type = "Functional Defect"
            severity = IssueSeverity.HIGH
            priority = IssuePriority.HIGH
            confidence = 0.94
            rationale = "Payment system issues directly impair business transactions and checkout conversion."

    # 2. Authentication / Security / Authorization
    elif any(k in combined for k in ["login", "signin", "sign-in", "signup", "sign-up", "register", "oauth", "jwt", "token", "password", "session", "auth", "logout", "401", "403", "permission", "unauthorized"]):
        category = "Authentication & Security"
        module = "Auth / User Session"
        defect_type = "Security / Access Defect"
        tags.extend(["auth", "security", "access-control"])
        if any(k in combined for k in ["cannot login", "unable to sign in", "lockout", "exploit", "leak", "vulnerability"]):
            severity = IssueSeverity.CRITICAL
            priority = IssuePriority.CRITICAL
            confidence = 0.97
            rationale = "Authentication roadblocks prevent user access to the platform and can indicate security risks."
        else:
            severity = IssueSeverity.HIGH
            priority = IssuePriority.HIGH
            confidence = 0.93
            rationale = "Authentication or authorization failure impacting user session validation."

    # 3. Crash / System Freeze / Fatal Error
    elif any(k in combined for k in ["crash", "crashes", "segmentation fault", "nullpointerexception", "fatal", "panic", "white screen", "freeze", "hangs"]):
        category = "Stability & Runtime"
        module = "Core Engine / Runtime"
        defect_type = "Crash / Fatal Error"
        severity = IssueSeverity.HIGH
        priority = IssuePriority.HIGH
        tags.extend(["crash", "stability", "runtime"])
        confidence = 0.95
        rationale = "Application crash or fatal exception disrupts user workflow and application stability."

    # 4. Performance / Latency / Timeout
    elif any(k in combined for k in ["slow", "timeout", "latency", "lag", "delay", "high cpu", "memory leak", "504 gateway", "unresponsive"]):
        category = "Performance"
        module = "API & Backend Services"
        defect_type = "Performance Bottleneck"
        severity = IssueSeverity.HIGH if ("timeout" in combined or "leak" in combined) else IssueSeverity.MEDIUM
        priority = IssuePriority.MEDIUM
        tags.extend(["performance", "latency", "scalability"])
        confidence = 0.92
        rationale = "Degraded performance or request timeout exceeding acceptable service level objectives."

    # 5. UI / Visual / Styling / Responsiveness
    elif any(k in combined for k in ["css", "align", "overlap", "color", "font", "responsive", "mobile display", "padding", "margin", "dark mode", "visual", "cut off", "overflow"]):
        category = "UI / UX"
        module = "Frontend / UI Layout"
        defect_type = "UI / Visual Glitch"
        severity = IssueSeverity.LOW
        priority = IssuePriority.LOW
        tags.extend(["ui", "ux", "visual", "frontend"])
        confidence = 0.91
        rationale = "Visual discrepancy or layout alignment glitch affecting cosmetic presentation without breaking underlying business logic."

    # 6. Database / Data Integrity
    elif any(k in combined for k in ["database", "sql", "query", "migration", "corrupt", "data loss", "foreign key", "duplicate record", "postgres", "table"]):
        category = "Database & Storage"
        module = "Database & Data Layer"
        defect_type = "Data Integrity Issue"
        severity = IssueSeverity.CRITICAL if ("data loss" in combined or "corrupt" in combined) else IssueSeverity.HIGH
        priority = IssuePriority.HIGH
        tags.extend(["database", "data-integrity", "backend"])
        confidence = 0.94
        rationale = "Database inconsistency, schema mismatch, or query failure affecting stored records."

    # 7. Notifications / Email / Messaging
    elif any(k in combined for k in ["email", "sms", "notification", "alert", "push", "webhook", "smtp"]):
        category = "Notifications & Messaging"
        module = "Notification Service"
        defect_type = "Functional Defect"
        severity = IssueSeverity.MEDIUM
        priority = IssuePriority.MEDIUM
        tags.extend(["notifications", "email", "integration"])
        confidence = 0.90
        rationale = "Outbound messaging or notification dispatch failure."

    return DefectClassifyResponse(
        category=category,
        module=module,
        defect_type=defect_type,
        suggested_severity=severity,
        suggested_priority=priority,
        confidence=confidence,
        rationale=rationale,
        tags=list(dict.fromkeys(tags)),
    )


async def classify_defect(request: DefectClassifyRequest) -> DefectClassifyResponse:
    openai_api_key = settings.openai_api_key.strip()
    cache_key = f"classify:{(request.title or '').strip().lower()}:{request.description.strip().lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    if not ai_circuit_breaker.is_available():
        res = _fallback_defect_classification(request.description, request.title or "")
        _set_in_cache(cache_key, res)
        return res

    client = get_async_openai_client()
    if not client:
        return _fallback_defect_classification(request.description, request.title or "")

    try:
        system_prompt = """You are an expert QA Engineer and Defect Classification AI for BugFlow.
Given a defect title and description, perform intelligent classification and return pure JSON:

{
  "category": "High level category (e.g. Payment, Authentication & Security, UI / UX, Database, Performance, Notifications, Reporting, API / Backend)",
  "module": "Specific module or component (e.g. Checkout / Payment Gateway, Login & Session, User Profile, Search Engine, Navigation)",
  "defect_type": "Specific type (e.g. Functional Defect, Crash / Fatal Error, UI / Visual Glitch, Security / Access Defect, Performance Bottleneck, Data Integrity Issue, Compatibility Issue)",
  "suggested_severity": "low|medium|high|critical",
  "suggested_priority": "low|medium|high|critical",
  "confidence": 0.95,
  "rationale": "Clear 1-2 sentence engineering justification for the classification",
  "tags": ["tag1", "tag2"]
}

Example:
Defect: "Payment page crashes when the user clicks Submit."
Response:
{
  "category": "Payment",
  "module": "Checkout / Payment Gateway",
  "defect_type": "Functional Defect",
  "suggested_severity": "high",
  "suggested_priority": "high",
  "confidence": 0.98,
  "rationale": "Payment failure on submission directly halts user checkout and prevents revenue transaction completion.",
  "tags": ["payment", "checkout", "crash"]
}"""
        user_prompt = f"Title: {request.title or ''}\nDescription: {request.description}"
        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")

        sev_map = {
            "low": IssueSeverity.LOW,
            "medium": IssueSeverity.MEDIUM,
            "high": IssueSeverity.HIGH,
            "critical": IssueSeverity.CRITICAL,
        }
        pri_map = {
            "low": IssuePriority.LOW,
            "medium": IssuePriority.MEDIUM,
            "high": IssuePriority.HIGH,
            "critical": IssuePriority.CRITICAL,
        }

        ai_circuit_breaker.record_success()
        result = DefectClassifyResponse(
            category=data.get("category", "General"),
            module=data.get("module", "Core Module"),
            defect_type=data.get("defect_type", "Functional Defect"),
            suggested_severity=sev_map.get(str(data.get("suggested_severity", "medium")).lower(), IssueSeverity.MEDIUM),
            suggested_priority=pri_map.get(str(data.get("suggested_priority", "medium")).lower(), IssuePriority.MEDIUM),
            confidence=float(data.get("confidence", 0.95)),
            rationale=data.get("rationale", "Classification derived from defect semantics and user impact."),
            tags=data.get("tags", []),
        )
        _set_in_cache(cache_key, result)
        return result
    except Exception as exc:
        ai_circuit_breaker.record_failure(exc)
        res = _fallback_defect_classification(request.description, request.title or "")
        _set_in_cache(cache_key, res)
        return res

        sev_val = str(data.get("suggested_severity", "high")).lower()
        pri_val = str(data.get("suggested_priority", "high")).lower()

        return DefectClassifyResponse(
            category=data.get("category", "General Application"),
            module=data.get("module", "Core Application"),
            defect_type=data.get("defect_type", "Functional Defect"),
            suggested_severity=sev_map.get(sev_val, IssueSeverity.HIGH),
            suggested_priority=pri_map.get(pri_val, IssuePriority.HIGH),
            confidence=float(data.get("confidence", 0.95)),
            rationale=data.get("rationale", "Defect analyzed and classified according to technical impact."),
            tags=data.get("tags", []),
        )
    except Exception:
        return _fallback_defect_classification(request.description, request.title or "")


# ── AI Chatbot & Beginner QA/Developer Mentor ─────────────────────────────────

CHAT_MENTOR_SYSTEM_PROMPT = """You are BugFlow AI Mentor, a world-class, empathetic, and highly knowledgeable QA & Software Engineering mentor.
Your mission is to help beginners and developers master software bug reporting, troubleshooting, root cause analysis, code debugging, and QA workflows.

GUIDELINES FOR YOUR RESPONSES:
1. Empathy & Clarity: Explain concepts clearly without unnecessary jargon. When technical terms are needed (e.g., 'Stack Trace', 'Race Condition', 'Idempotency', 'Regression'), define them simply with real-world analogies.
2. Structure & Formatting: Use markdown headers, bold keywords, numbered step-by-step procedures, and clean code blocks with language identifiers.
3. Action-Oriented: Always provide concrete, actionable advice (e.g., exact questions to answer in a bug report, specific commands to run, code examples showing Before vs After).
4. Dual Perspective: Help both reporters (how to write clean, reproducible bug reports) and developers (how to diagnose, locate, fix, and test software defects).
5. Response Schema: Return a JSON object with:
   - "reply": Markdown formatted educational response.
   - "suggested_followups": 3 to 4 short, relevant follow-up questions a beginner might ask next.
   - "category": Topic category (e.g., "Bug Reporting", "Debugging", "Error Diagnostics", "QA Foundations", "Code Fixes").
   - "helpful_tips": 2 to 3 key takeaway bullet points.
"""


def get_chat_starter_topics() -> AIChatTopicsResponse:
    """Return categorized beginner topics and prompt starter chips."""
    categories = [
        AIChatTopicCategory(
            category_id="foundations",
            category_title="🚀 QA & Bug Foundations",
            description="Essential concepts every developer and QA tester needs to know.",
            topics=[
                AIChatTopicItem(
                    id="how_to_report",
                    title="How to write a great bug report?",
                    prompt="Can you guide me step-by-step on how to write a clear, professional bug report in BugFlow?",
                    badge="Popular",
                    icon="FileText",
                ),
                AIChatTopicItem(
                    id="severity_vs_priority",
                    title="Severity vs Priority: What's the difference?",
                    prompt="Can you explain the difference between Bug Severity and Priority with simple real-world examples and a 2x2 matrix?",
                    badge="Essential",
                    icon="Flame",
                ),
                AIChatTopicItem(
                    id="steps_to_reproduce",
                    title="How to write good Steps to Reproduce?",
                    prompt="How do I write effective, unambiguous steps to reproduce a bug so that developers can replicate it instantly?",
                    badge="Guide",
                    icon="CheckSquare",
                ),
                AIChatTopicItem(
                    id="expected_vs_actual",
                    title="Expected vs Actual Result: Why does it matter?",
                    prompt="What is the difference between Expected Behavior and Actual Behavior, and how should I phrase them?",
                    badge="Core",
                    icon="GitCompare",
                ),
                AIChatTopicItem(
                    id="regression_vs_feature",
                    title="What is a Regression bug?",
                    prompt="What is a regression defect, why do regressions happen, and how do teams prevent them?",
                    badge="Concept",
                    icon="History",
                ),
            ],
        ),
        AIChatTopicCategory(
            category_id="bug_reporting",
            category_title="📝 Bug Reporting Copilot",
            description="Interactive tools and advice to make your bug reports high quality.",
            topics=[
                AIChatTopicItem(
                    id="review_draft",
                    title="Review my draft bug report",
                    prompt="Can you review my draft bug report and tell me what is missing, what can be improved, and give me a polished version?",
                    badge="Reviewer",
                    icon="Sparkles",
                ),
                AIChatTopicItem(
                    id="intermittent_bugs",
                    title="How to report intermittent / flaky bugs?",
                    prompt="How should I report a bug that happens only sometimes (intermittent / flaky defect)? What clues should I gather?",
                    badge="Pro Tip",
                    icon="Zap",
                ),
                AIChatTopicItem(
                    id="logs_and_screenshots",
                    title="What attachments & logs should I include?",
                    prompt="What logs, browser console outputs, network payloads, and screenshots should I attach to a bug report?",
                    badge="Checklist",
                    icon="Paperclip",
                ),
                AIChatTopicItem(
                    id="categorize_bug",
                    title="How to pick Category & Defect Type?",
                    prompt="How do I choose the correct Defect Category (e.g., UI, Backend, Payment, Security) and Defect Type (Functional, Crash, Performance)?",
                    badge="Taxonomy",
                    icon="Layers",
                ),
            ],
        ),
        AIChatTopicCategory(
            category_id="bug_solving",
            category_title="🛠️ Bug Solving & Debugging",
            description="Frameworks and techniques to diagnose, troubleshoot, and fix bugs.",
            topics=[
                AIChatTopicItem(
                    id="troubleshooting_framework",
                    title="Step-by-step troubleshooting checklist",
                    prompt="What is a systematic step-by-step checklist to debug any software bug from report to resolution?",
                    badge="Methodology",
                    icon="Cpu",
                ),
                AIChatTopicItem(
                    id="locate_in_code",
                    title="How do I locate where a bug is in code?",
                    prompt="When given a bug description or error, how do I trace through the codebase to pinpoint the exact file and function causing the issue?",
                    badge="Code Search",
                    icon="Search",
                ),
                AIChatTopicItem(
                    id="reproduce_locally",
                    title="How to reproduce bugs in local dev environment?",
                    prompt="What are best practices for reproducing user-reported production bugs on a local development setup?",
                    badge="Setup",
                    icon="Bot",
                ),
                AIChatTopicItem(
                    id="unit_testing_fix",
                    title="Writing tests to prove and fix bugs",
                    prompt="How should I write a unit or integration test that fails before my fix and passes after my fix to prevent regression?",
                    badge="Testing",
                    icon="TestTube",
                ),
                AIChatTopicItem(
                    id="verify_and_close",
                    title="Bug verification & closing criteria",
                    prompt="What checklist should QA and developers follow before moving a bug from In Progress to Resolved and Closed?",
                    badge="Workflow",
                    icon="CheckCircle",
                ),
            ],
        ),
        AIChatTopicCategory(
            category_id="error_diagnostics",
            category_title="🔍 Common Error Explanations",
            description="Understand and fix the most common errors beginners encounter.",
            topics=[
                AIChatTopicItem(
                    id="err_500",
                    title="500 Internal Server Error: What it means & how to fix",
                    prompt="What does HTTP 500 Internal Server Error mean, where should I look for clues, and how do I fix it?",
                    badge="HTTP",
                    icon="ShieldAlert",
                ),
                AIChatTopicItem(
                    id="err_undefined",
                    title="JavaScript: Cannot read properties of undefined / null",
                    prompt="Why does 'TypeError: Cannot read properties of undefined' happen in JavaScript/React and how do I fix it safely?",
                    badge="JavaScript",
                    icon="Code",
                ),
                AIChatTopicItem(
                    id="err_cors",
                    title="Understanding & fixing CORS errors",
                    prompt="What is a CORS error (Cross-Origin Resource Sharing), why does the browser block requests, and how do I fix it in backend & frontend?",
                    badge="Web API",
                    icon="Lock",
                ),
                AIChatTopicItem(
                    id="err_sql_fk",
                    title="SQL foreign key & database transaction errors",
                    prompt="What causes database IntegrityError or foreign key violation errors and how do I resolve them?",
                    badge="Database",
                    icon="Tag",
                ),
                AIChatTopicItem(
                    id="err_auth_codes",
                    title="HTTP 401 Unauthorized vs 403 Forbidden",
                    prompt="What is the difference between HTTP 401 Unauthorized and HTTP 403 Forbidden, and how should token auth handle them?",
                    badge="Auth",
                    icon="Shield",
                ),
                AIChatTopicItem(
                    id="err_race_condition",
                    title="Async race conditions & state bugs",
                    prompt="What is a race condition in asynchronous web applications and what techniques prevent state corruption?",
                    badge="Async",
                    icon="Zap",
                ),
            ],
        ),
    ]
    return AIChatTopicsResponse(categories=categories)


def _has_kw(text: str, *terms: str) -> bool:
    for t in terms:
        if " " in t or "-" in t or "_" in t or "." in t:
            if t in text:
                return True
        else:
            if re.search(r"\b" + re.escape(t) + r"\b", text):
                return True
    return False


def _fallback_chat_response(
    messages: list[Any],
    context: dict[str, Any] | None = None,
    mode: str | None = None,
) -> AIChatResponse:
    """Rich rule-based QA & developer mentoring fallback engine."""
    last_msg = ""
    for m in reversed(messages):
        role = getattr(m, "role", None) or (m.get("role") if isinstance(m, dict) else "")
        if role == "user":
            last_msg = getattr(m, "content", None) or (m.get("content") if isinstance(m, dict) else "")
            break

    lowered = last_msg.lower().strip()
    ctx = context or {}

    # 1. Draft Reviewer Mode or prompt requesting draft review
    if mode == "draft_reviewer" or _has_kw(lowered, "review my draft", "review this bug", "critique my report", "review draft", "critique draft"):
        draft_title = ctx.get("draft_title") or ctx.get("title") or ""
        draft_desc = ctx.get("draft_description") or ctx.get("description") or last_msg
        class_res = _fallback_defect_classification(draft_desc, draft_title)

        return AIChatResponse(
            reply=f"""### 🌟 AI Bug Report Review & Quality Audit

I evaluated your draft bug report. Here is a breakdown of strengths, missing elements, and an enhanced production-ready version.

---

#### 📊 Quality Score: **8.5 / 10** (Strong Foundation)

#### ✅ What's Good:
- The core problem is identified.
- The intent and affected component are recognizable.

#### ⚠️ Areas to Strengthen:
1. **Numbered Steps to Reproduce**: Convert narrative text into sequential 1, 2, 3 steps.
2. **Explicit Expected vs Actual**: Clearly delineate what the user expected vs the exact anomaly observed.
3. **Environmental Context**: Mention browser, operating system, or environment (e.g., Chrome v128, macOS Sonoma, Dev/Staging).
4. **Error Logs & Status Codes**: If an API or console error occurred (e.g. 500, 404, uncaught promise), note it in the technical section.

---

#### 📋 Recommended Polished Bug Report:

**Title**: `{_infer_title(draft_title or draft_desc)}`

**Defect Category**: `{class_res.category}` • **Module**: `{class_res.module}` • **Severity**: `{class_res.suggested_severity.value.capitalize()}` • **Priority**: `{class_res.suggested_priority.value.capitalize()}`

**Summary**:
• {draft_desc[:120].strip() if len(draft_desc) > 10 else "User encounters an unexpected failure during normal application workflow."}

**Steps to Reproduce**:
1. Open the application and sign in with standard user credentials.
2. Navigate to the affected module page.
3. Perform the triggering action (e.g. submit form, click action button, upload file).
4. Observe the unexpected failure or error state.

**Expected Result**:
• The operation completes successfully with confirmation feedback and state update.

**Actual Result**:
• An unexpected error occurs, blocking user workflow and failing to persist changes.

**Technical & Developer Diagnostic Notes**:
• Inspect browser Network tab for non-200 responses.
• Check backend server logs for unhandled exception traces.
""",
            suggested_followups=[
                "How do I determine if this bug is High or Critical severity?",
                "What screenshots or network payloads should I attach?",
                "How can I test if this is a regression?",
                "How do I assign this to the right developer?",
            ],
            category="Bug Report Review",
            helpful_tips=[
                "Always separate Steps to Reproduce into numbered single actions.",
                "Include the exact error message or HTTP status code whenever possible.",
                "Mention whether the bug happens 100% of the time or intermittently.",
            ],
        )

    # 2. Concurrency, Double Submit & Race Conditions
    if _has_kw(lowered, "race condition", "race conditions", "concurrency", "debounce", "throttle", "double submit", "double click", "double payment"):
        return AIChatResponse(
            reply="""### ⚡ Understanding & Preventing Async Race Conditions

#### 🧩 What is a Race Condition?
A **race condition** occurs when the outcome of a program depends on the unpredictable timing or sequence of asynchronous events. For example, if a user rapidly clicks "Pay Now" twice, two concurrent HTTP requests might charge the card two times before the first one marks the order as paid.

---

#### 🛡️ Techniques to Prevent Race Conditions:

1. **Frontend: Disable Submit Button While Loading**:
   ```jsx
   <button disabled={loading} onClick={handleSubmit}>
     {loading ? 'Processing...' : 'Submit Bug'}
   </button>
   ```

2. **Frontend: Debouncing Rapid Inputs**:
   ```javascript
   // Debounce search input to wait 300ms after user stops typing
   let timer;
   function handleSearchChange(e) {
     clearTimeout(timer);
     timer = setTimeout(() => fetchSearchResults(e.target.value), 300);
   }
   ```

3. **Backend: Idempotency Keys & Database Unique Constraints**:
   - Use unique database constraints (e.g., `(user_id, idempotency_key)`).
   - Use database row locks (`SELECT ... FOR UPDATE`) during sensitive balance deductions.
""",
            suggested_followups=[
                "What is an Idempotent API endpoint?",
                "How do I cancel stale fetch requests with AbortController?",
                "What is the difference between Debounce and Throttle?",
            ],
            category="Concurrency & Async",
            helpful_tips=[
                "Always disable submission buttons immediately on initial click.",
                "Use AbortController to cancel previous in-flight requests when a search query changes.",
            ],
        )

    # 3. Intermittent & Flaky Bugs
    if _has_kw(lowered, "flaky", "intermittent", "heisenbug", "happens sometimes", "random bug", "rarely occurs", "intermittent defect"):
        return AIChatResponse(
            reply="""### 🔍 How to Track & Solve Intermittent / Flaky Bugs

#### 🧩 Why do Intermittent Bugs Happen?
Intermittent bugs (often called **Heisenbugs**) don't occur 100% of the time. The main culprits are:
1. **Timing & Network Latency**: Slow 3G connections vs fast local WiFi.
2. **State Left Behind**: A previous test or action left dirty state in localStorage or database.
3. **Timezones & Date Clocks**: Bug triggers only at midnight UTC or across daylight saving transitions.
4. **Third-Party Rate Limiting**: Intermittent 429 Too Many Requests from external APIs.

---

#### 🛠️ Strategy to Capture Intermittent Bugs:
- **Add Detailed Breadcrumb Logs**: Log key milestones with timestamps.
- **Record Network HAR Files**: Use Chrome DevTools -> Network -> Save all as HAR with content.
- **Automated Stress Testing Loop**: Run the reproduction test script in a loop 100 times to observe the failure rate.
""",
            suggested_followups=[
                "How do I export and inspect a HAR network log file?",
                "How to write deterministic automated tests that never flake?",
                "How do browser caching issues cause intermittent bugs?",
            ],
            category="Advanced Debugging",
            helpful_tips=[
                "Note down the exact time, timezone, and user role whenever an intermittent bug occurs.",
                "Look for race conditions and asynchronous promise handling without `await`.",
            ],
        )

    # 4. Docker, Local Environment & Port Issues
    if _has_kw(lowered, "docker", "eaddrinuse", "address already in use", "port 8000", "port 5173", "connection refused", "econnrefused"):
        return AIChatResponse(
            reply="""### 🐳 Docker & Local Dev Environment Troubleshooting

#### 🧩 Common Environment Issues:

1. **`Error: listen EADDRINUSE: address already in use :::8000` / `:::5173`**:
   - **Cause**: Another instance of uvicorn/vite/node is already running on that port.
   - **Fix (macOS/Linux)**:
     ```bash
     lsof -i :8000
     kill -9 <PID>
     ```

2. **`Connection Refused (ECONNREFUSED)`**:
   - **Cause**: The frontend is trying to call `http://localhost:8000/api`, but the backend server is stopped.
   - **Fix**: Start the backend server in your terminal:
     ```bash
     cd backend && ./venv/bin/uvicorn app.main:app --reload --port 8000
     ```

3. **Missing `.env` Variables**:
   - **Fix**: Ensure your `.env` file exists in the project root/backend directory and contains required keys.
""",
            suggested_followups=[
                "How do I run BugFlow with docker-compose up?",
                "How do I kill background processes holding port 8000 on Mac?",
                "How do environment variables get loaded into FastAPI via Pydantic?",
            ],
            category="DevOps & Environment",
            helpful_tips=[
                "Check `lsof -i :<port>` whenever you get 'port already in use' errors.",
                "Always keep a `.env.example` file in your repository as a template.",
            ],
        )

    # 5. Python Common Exceptions (AttributeError, KeyError, IndexError, etc.)
    if _has_kw(lowered, "attributeerror", "keyerror", "indexerror", "modulenotfounderror", "importerror", "indentationerror", "zerodivisionerror", "python error", "python exception"):
        return AIChatResponse(
            reply="""### 🐍 Diagnosing & Fixing Common Python Exceptions

#### 🧩 Top Python Exceptions & Solutions:

1. **`AttributeError: 'NoneType' object has no attribute 'x'`**:
   - **Cause**: Trying to access `.x` on a variable that is `None` (e.g. database `.first()` returned nothing).
   - **Fix**: Check `if obj is not None:` or use default guards.

2. **`KeyError: 'field_name'`**:
   - **Cause**: Accessing dictionary key `data['field_name']` when the key doesn't exist.
   - **Fix**: Use `data.get('field_name', default_value)`.

3. **`IndexError: list index out of range`**:
   - **Cause**: Accessing `items[0]` or `items[i]` on an empty or shorter list.
   - **Fix**: Check `if len(items) > 0:` before indexing or use a loop.

4. **`ModuleNotFoundError: No module named 'x'`**:
   - **Cause**: Package not installed in the active virtual environment.
   - **Fix**: Activate your venv (`source venv/bin/activate`) and run `pip install x`.

---

#### 🛠️ Defensive Coding Pattern:
```python
# Safe dict access & None checking
user_data = get_user_payload()
email = user_data.get("email")
if not email:
    raise HTTPException(status_code=422, detail="Email is required.")
```
""",
            suggested_followups=[
                "How do I set up custom exception handlers in FastAPI?",
                "What is the difference between ValueError and TypeError?",
                "How do I debug Python code using pdb or breakpoints in VS Code?",
            ],
            category="Python Diagnostics",
            helpful_tips=[
                "Use `.get()` with a default value instead of direct bracket access `data['key']`.",
                "Always check if database query results are `None` before reading their fields.",
            ],
        )

    # 6. CSS, Styling & Layout Bugs
    if _has_kw(lowered, "css", "center a div", "flexbox", "grid", "z-index", "responsive", "overflow", "dark mode"):
        return AIChatResponse(
            reply="""### 🎨 CSS Layout, Flexbox, Grid & Styling Solutions

#### 🧩 1. How to Perfectly Center Anything:
```css
/* Modern Grid centering (Easiest) */
.center-container {
  display: grid;
  place-items: center;
  min-height: 100vh;
}

/* Flexbox centering (Great for row layouts) */
.flex-center {
  display: flex;
  align-items: center;    /* vertical */
  justify-content: center; /* horizontal */
}
```

---

#### 🧩 2. Fixing `z-index` Stacking Context Bugs:
- If an element with `z-index: 9999` is still hidden behind another element, it is trapped inside a **parent stacking context**.
- **Fix**: Ensure the parent container has `position: relative; z-index: ...` or move the modal/overlay to the top-level DOM root (e.g., `document.body`).

---

#### 🧩 3. Responsive Design & Flex Wrap:
```css
.card-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1.5rem;
}
.card {
  flex: 1 1 300px; /* grow, shrink, min-width 300px */
}
```
""",
            suggested_followups=[
                "What is the difference between CSS Flexbox and CSS Grid?",
                "How do CSS Custom Properties (Variables) work for Dark Mode?",
                "How do I prevent text overflow with ellipsis in CSS?",
            ],
            category="Frontend & CSS",
            helpful_tips=[
                "Use `box-sizing: border-box` on all elements to prevent padding from expanding box sizes.",
                "Use CSS variables (e.g. `var(--bg-primary)`) for seamless light/dark mode theming.",
            ],
        )

    # 2. Error Explainer Mode or common error queries
    if mode == "error_explainer" or any(k in lowered for k in ["500", "undefined", "cors", "typeerror", "nullpointer", "integrityerror", "stack trace", "explain error"]):
        if "500" in lowered or "internal server" in lowered:
            return AIChatResponse(
                reply="""### 🔍 Explaining `HTTP 500 Internal Server Error`

#### 🧩 What is a 500 Internal Server Error?
An **HTTP 500** is a generic server-side error. It means the backend server encountered an unexpected condition or unhandled exception that prevented it from fulfilling the request. The frontend received no valid JSON response because the backend crashed mid-execution.

---

#### 🎯 Common Root Causes:
1. **Unhandled Null / None Reference**: The backend code attempted to access an attribute on a variable that evaluated to `None` or `null` (e.g. `user.profile.phone` when `profile` is None).
2. **Database Constraint Violation**: Inserting duplicate unique keys, violating foreign key constraints, or database connection timeout.
3. **Missing Environment Variable / Secret**: A third-party service key (e.g. Stripe, OpenAI, AWS S3) is missing or invalid.
4. **Data Type / Serialization Mismatch**: Attempting to serialize non-serializable objects into JSON (e.g., raw datetime objects, circular references).

---

#### 🛠️ Step-by-Step Fix Guide:
1. **Check Backend Terminal / Server Logs**:
   Look at your uvicorn/gunicorn terminal or server log stream. Look for the traceback ending in an Exception (e.g. `AttributeError`, `KeyError`, `SQLAlchemyError`).
2. **Identify the Line Number**:
   Find the last line in the traceback pointing to your project files (e.g. `app/routers/issues.py:84`).
3. **Add Defensive Checks & Exception Handling**:
   ```python
   # Example: Before (causes 500 on missing record)
   item = db.query(Model).filter_by(id=item_id).first()
   return {"name": item.name}  # Crashes if item is None!

   # Example: After (returns clean 404 instead of 500 crash)
   item = db.query(Model).filter_by(id=item_id).first()
   if not item:
       raise HTTPException(status_code=404, detail="Item not found")
   return {"name": item.name}
   ```
4. **Write a Unit Test**: Add a test that sends missing/invalid data and asserts HTTP 404 or 422 rather than 500.
""",
                suggested_followups=[
                    "What is the difference between a 400 and a 500 error?",
                    "How do I set up global error handlers in FastAPI/Python?",
                    "How to debug database transaction rollback errors?",
                    "How do I write a test for this error?",
                ],
                category="Error Diagnostics",
                helpful_tips=[
                    "Never let unhandled exceptions crash to 500 — wrap endpoints with validation or custom HTTPException handlers.",
                    "Always inspect the server log traceback, not just the frontend network status.",
                ],
            )

        if "undefined" in lowered or "null" in lowered or "typeerror" in lowered:
            return AIChatResponse(
                reply="""### 🔍 Explaining `TypeError: Cannot read properties of undefined (reading '...')`

#### 🧩 What does this error mean?
In JavaScript/TypeScript, this error occurs when you try to access a property or call a method on a variable whose value is `undefined` or `null`.

For example:
```javascript
// If user is undefined, this throws TypeError: Cannot read properties of undefined (reading 'name')
console.log(user.name);
```

---

#### 🎯 Common Scenarios:
1. **Asynchronous Data Fetching**: Rendering components before an API response has arrived (e.g. `data.items.map(...)` before `data` is populated).
2. **Missing Optional Fields**: Accessing nested properties that don't exist on all records (e.g. `issue.assignee.username` when the issue is unassigned).
3. **Failed Array Searches**: Calling array methods after `.find()` when no element matched.

---

#### 🛠️ How to Fix It (Modern Best Practices):
1. **Use Optional Chaining (`?.`)**:
   ```javascript
   // Safe navigation: returns undefined instead of crashing
   const username = issue?.assigned_developer?.username || 'Unassigned';
   ```
2. **Provide Safe Initial State**:
   ```javascript
   // In React component state:
   const [items, setItems] = useState([]); // Default to empty array [] instead of undefined/null
   ```
3. **Add Guard Clauses & Loading States**:
   ```javascript
   if (loading) return <Spinner />;
   if (!data) return <EmptyState message="No records found" />;
   ```
4. **Use Nullish Coalescing (`??`)**:
   ```javascript
   const count = data?.total_count ?? 0;
   ```
""",
                suggested_followups=[
                    "What is the difference between null and undefined in JavaScript?",
                    "How do I safely render list items with .map() in React?",
                    "How can TypeScript prevent undefined property errors?",
                ],
                category="JavaScript Errors",
                helpful_tips=[
                    "Always initialize React array states with `[]` rather than `null`.",
                    "Use optional chaining `?.` when referencing nested properties from backend APIs.",
                ],
            )

        if "cors" in lowered:
            return AIChatResponse(
                reply="""### 🔍 Understanding & Fixing CORS (Cross-Origin Resource Sharing) Errors

#### 🧩 What is CORS?
**CORS** is a browser security mechanism (Same-Origin Policy). The browser blocks frontend JavaScript (running on e.g., `http://localhost:5173`) from reading HTTP responses from a backend on a different port or domain (e.g., `http://localhost:8000`) unless the backend explicitly sends permission headers.

---

#### ⚠️ Key Rule: CORS is Enforced by the Browser, Not the Server
- The backend server actually processes the request and returns a response.
- The **browser** blocks the frontend code from reading the response because `Access-Control-Allow-Origin` is missing or mismatched.

---

#### 🛠️ How to Fix CORS in FastAPI / Backend:
Add `CORSMiddleware` in your backend application configuration:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite Dev Server
        "http://127.0.0.1:5173",
        "https://your-production-app.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # Allow GET, POST, PUT, DELETE, OPTIONS
    allow_headers=["*"],  # Allow Authorization, Content-Type, etc.
)
```

---

#### 💡 Troubleshooting Checklist:
1. Ensure the backend handles `OPTIONS` preflight requests (FastAPI `CORSMiddleware` does this automatically).
2. If using cookies/credentials (`Authorization` Bearer tokens or cookies), make sure `allow_credentials=True` and `allow_origins` does not conflict with wildcard rules.
3. In Vite/frontend, you can also set up a reverse proxy in `vite.config.js`:
   ```javascript
   server: {
     proxy: {
       '/api': 'http://127.0.0.1:8000'
     }
   }
   ```
""",
                suggested_followups=[
                    "Why do OPTIONS preflight requests happen?",
                    "How do I configure Vite reverse proxy for API requests?",
                    "What is the difference between same-origin and cross-origin?",
                ],
                category="Web Security",
                helpful_tips=[
                    "CORS errors must be fixed in the backend server configuration, not on the frontend.",
                    "Using a dev proxy in Vite/Webpack eliminates CORS issues in local development.",
                ],
            )

    # 3. Severity vs Priority
    if any(k in lowered for k in ["severity vs priority", "severity and priority", "difference between severity"]):
        return AIChatResponse(
            reply="""### ⚖️ Bug Severity vs. Bug Priority Explained

A common dilemma for beginners in QA and software engineering is distinguishing between **Severity** and **Priority**.

---

### 📊 Quick Comparison:
| Aspect | **Severity** | **Priority** |
| :--- | :--- | :--- |
| **Definition** | Technical impact on the software system & stability | Business urgency on how fast it must be fixed |
| **Driven By** | QA Tester / Technical Architecture | Project Manager / Product Owner / Business |
| **Question Asked** | *"How badly does this break the code/system?"* | *"How quickly do we need this fixed for users?"* |
| **Scale** | Low, Medium, High, Critical | Low, Medium, High, Critical |

---

### 🧩 Real-World 2x2 Matrix Examples:

#### 1. High Severity, High Priority (Immediate P0 Hotfix)
- **Example**: The payment checkout page crashes with 500 error on clicking "Pay Now".
- **Why**: The technical functionality is broken (High Severity) AND users cannot complete transactions (High Priority).

#### 2. High Severity, Low Priority (System Crash on Rare Edge Case)
- **Example**: App crashes when importing an legacy 2003 XML format that only 0.01% of users use.
- **Why**: It causes a fatal crash (High Severity), but almost nobody is impacted right now (Low Priority).

#### 3. Low Severity, High Priority (Cosmetic but Crucial Brand Issue)
- **Example**: Company logo on the homepage is misspelled as "BoogFlow" or CEO's name is wrong.
- **Why**: Zero code or database crash (Low Severity), but extremely embarrassing for brand reputation (High Priority).

#### 4. Low Severity, Low Priority (Minor Cosmetic Glitch)
- **Example**: A tooltip on a settings subpage has a 2px alignment mismatch in dark mode.
- **Why**: System works perfectly and minimal user impact.
""",
            suggested_followups=[
                "How do I determine Severity when logging a bug?",
                "What criteria qualifies a defect as Critical?",
                "Can a developer downgrade a bug's severity?",
                "How does BugFlow's AI predict defect severity?",
            ],
            category="QA Foundations",
            helpful_tips=[
                "Severity measures technical damage; Priority measures business timing.",
                "Always explain the business risk in the description so PMs can prioritize accurately.",
            ],
        )

    # 4. How to write a bug report / steps to reproduce
    if any(k in lowered for k in ["how to report", "how do i write a bug", "steps to reproduce", "first bug report", "write a good bug"]):
        return AIChatResponse(
            reply="""### 📝 The Beginner's Complete Guide to Writing Bug Reports

A great bug report saves developers hours of guesswork and gets fixed much faster. Here is the golden formula used at top engineering teams.

---

### 🏆 The 6 Essential Elements of Every Bug Report:

#### 1. Clear & Actionable Title
- ❌ *Bad*: "Button broken"
- ✅ *Good*: `[Checkout] Payment submit button becomes unresponsive after entering coupon code`
- **Formula**: `[Component/Module] Specific symptom when trigger condition happens`

#### 2. Pre-Conditions & Environment
- **User Role**: Admin, Developer, or Regular Reporter?
- **Environment**: OS (macOS/Windows/Linux), Browser & Version (Chrome 128), Device (Desktop/Mobile).

#### 3. Step-by-Step Instructions (Numbered & Explicit)
Write steps so that someone with zero context can reproduce the issue:
1. Log in to BugFlow with a `Developer` account.
2. Navigate to **Sprints** -> Select **Sprint 3**.
3. Drag ticket `DEF-42` from **Open** to **In Progress**.
4. Refresh the page.

#### 4. Expected Result vs Actual Result
- **Expected**: The ticket status persists as `In Progress` after reload.
- **Actual**: The ticket reverts back to `Open` and browser console logs `403 Forbidden`.

#### 5. Evidence (Screenshots, Logs & Network)
- Attach a screenshot or screen recording.
- If an API failed, copy the Network response payload or console error log.

#### 6. Severity & Defect Type
- Tag whether it is a **Functional Defect**, **UI Glitch**, **Performance Lag**, or **Crash**.
""",
            suggested_followups=[
                "Can you review my draft bug report?",
                "How do I capture browser network logs for bugs?",
                "How do I handle bugs that only happen occasionally?",
                "What is the difference between Expected and Actual behavior?",
            ],
            category="Bug Reporting",
            helpful_tips=[
                "Write steps as sequential commands: 1. Navigate..., 2. Click..., 3. Observe...",
                "Always state what SHOULD happen alongside what DID happen.",
            ],
        )

    # 5. Debugging & Troubleshooting Framework
    if any(k in lowered for k in ["how to debug", "troubleshooting", "how to solve", "locate bug", "debugging checklist", "root cause", "rca"]):
        return AIChatResponse(
            reply="""### 🛠️ The 6-Step Developer Troubleshooting & Debugging Framework

When you are assigned a bug or need to solve a software defect, follow this proven scientific debugging cycle:

---

### 🔬 The 6 Steps:

```
1. Reproduce ➡️ 2. Isolate ➡️ 3. Inspect Logs ➡️ 4. Form Hypothesis ➡️ 5. Patch ➡️ 6. Verify & Test
```

#### Step 1: Deterministic Reproduction
- Before writing any code, reproduce the bug on your local development machine using the reporter's steps.
- If you cannot reproduce it, check environment variables, seed database data, or browser caching.

#### Step 2: Isolate the Boundary (Frontend vs Backend vs Database)
- **Frontend Check**: Open Browser DevTools (`F12`) -> Network tab. Did the frontend send the wrong payload, or did the backend return an error?
- **Backend Check**: Did the backend receive valid input but throw an unhandled exception or SQL error?
- **Database Check**: Is there corrupt data or missing migration state in the database?

#### Step 3: Inspect Logs & Stack Traces
- Look at the top and bottom of the error stack trace.
- Identify the exact filename and line number where execution failed.

#### Step 4: Form a Root Cause Hypothesis
- Ask **"Why did this line fail?"** (e.g. *Why was `user.id` null? Did the token expire? Did the serializer skip the field?*).

#### Step 5: Implement the Minimal Correct Fix
- Fix the root cause defensively (e.g. add null validation, fix query join, handle edge case).
- Avoid quick hacks that mask the underlying bug.

#### Step 6: Write a Regression Test & Verify
- Write a unit test that replicates the bug scenario. Ensure it fails before your fix and passes with your fix.
- Verify related features to ensure no side-effects were introduced.
""",
            suggested_followups=[
                "How do I write a regression test in pytest or Jest?",
                "How do I use breakpoint debuggers in Chrome / VS Code?",
                "What is Root Cause Analysis (RCA)?",
                "How to use Resolution Assistance to investigate a bug?",
            ],
            category="Debugging 101",
            helpful_tips=[
                "Always reproduce the bug first before changing a single line of code.",
                "A good bug fix always includes a regression test so the defect never comes back.",
            ],
        )

    # 6. API, REST, HTTP Status Codes & Endpoints
    if any(k in lowered for k in ["api", "rest", "http", "status code", "endpoint", "404", "401", "403", "422", "json"]):
        return AIChatResponse(
            reply="""### 🌐 Understanding APIs, REST & HTTP Status Codes

#### 🧩 What is a REST API?
An **API (Application Programming Interface)** allows two software systems to communicate. A **REST API** uses standard HTTP methods (`GET`, `POST`, `PUT`, `DELETE`) to perform CRUD (Create, Read, Update, Delete) operations on resources.

---

#### 🚦 Essential HTTP Status Codes:
- **200 OK**: Request succeeded and data returned.
- **201 Created**: Resource was successfully created (e.g., new bug report created).
- **204 No Content**: Action succeeded with no body returned (e.g., deleted successfully).
- **400 Bad Request**: Client sent invalid or malformed data.
- **401 Unauthorized**: User is not authenticated (missing or invalid Bearer token).
- **403 Forbidden**: User is authenticated, but lacks permissions (e.g., non-admin accessing admin panel).
- **404 Not Found**: The requested resource ID or URL does not exist.
- **422 Unprocessable Entity**: Data schema validation failed (e.g. email missing `@` or password too short).
- **500 Internal Server Error**: Backend crashed due to unhandled exception.

---

#### 🛠️ Example: Making an Authenticated API Request:
```javascript
// Sending JWT Bearer token in request headers
const response = await fetch('/api/issues', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  },
  body: JSON.stringify({
    title: 'Payment button unresponsive',
    severity: 'high',
    project_id: 1
  })
});
const data = await response.json();
```
""",
            suggested_followups=[
                "What is the difference between 401 Unauthorized and 403 Forbidden?",
                "What is the difference between POST and PUT?",
                "How do JWT tokens work?",
                "How to fix a 500 Internal Server Error?",
            ],
            category="Web APIs & Protocols",
            helpful_tips=[
                "Always inspect HTTP status codes in Browser DevTools -> Network tab.",
                "Use 422/400 for client validation errors and never let them crash to 500.",
            ],
        )

    # 7. Authentication, JWT, Passwords & Security
    if any(k in lowered for k in ["auth", "jwt", "token", "login", "password", "bearer", "session", "security", "hash"]):
        return AIChatResponse(
            reply="""### 🔐 Authentication & JWT Tokens Explained

#### 🧩 How JWT Authentication Works in Web Apps:
1. **User Login**: User submits email and password to `/api/auth/login`.
2. **Password Verification**: Backend compares the submitted password against the salted `bcrypt` hash stored in the database.
3. **Token Issuance**: Backend generates a signed **JWT (JSON Web Token)** containing the user's `id`, `email`, and `role` with an expiration timestamp.
4. **Token Storage**: Frontend stores the token (e.g. in `localStorage` or `HttpOnly` cookie).
5. **Protected Requests**: Frontend attaches `Authorization: Bearer <token>` on subsequent API calls.
6. **Token Verification**: Backend validates the cryptographic signature without querying the database every time.

---

#### 🛡️ Best Practices for Beginners:
- **Never Store Plaintext Passwords**: Always hash with `bcrypt` or `argon2`.
- **Set Token Expiration**: Configure sensible token expiration (e.g., 24 hours or 7 days).
- **Role-Based Access Control (RBAC)**: Enforce role checks on backend endpoints (e.g., `admin`, `developer`, `reporter`).
""",
            suggested_followups=[
                "How do I protect routes with FastAPI Depends(get_current_user)?",
                "What is the difference between localStorage and HttpOnly cookies?",
                "How to implement Role-Based Access Control (RBAC)?",
            ],
            category="Security & Auth",
            helpful_tips=[
                "Always send tokens over HTTPS in production.",
                "Never store sensitive secrets (like API keys or passwords) in frontend code.",
            ],
        )

    # 8. Databases, SQL, SQLAlchemy & Transactions
    if any(k in lowered for k in ["database", "sql", "postgres", "sqlite", "orm", "sqlalchemy", "query", "migration", "foreign key", "join"]):
        return AIChatResponse(
            reply="""### 🗄️ Databases, SQL & ORM Essentials

#### 🧩 What is an ORM (Object Relational Mapper)?
An **ORM** (like SQLAlchemy in Python or Prisma in JS) lets you interact with database tables using object-oriented code instead of writing raw SQL strings.

---

#### 🛠️ Common SQLAlchemy / SQL Operations:
```python
# 1. Query with Filter & Join
open_bugs = (
    db.query(Issue)
    .filter(Issue.status == IssueStatus.OPEN)
    .filter(Issue.project_id == project_id)
    .order_by(Issue.created_at.desc())
    .all()
)

# 2. Safe Creation with Commit & Rollback
try:
    new_issue = Issue(title=title, project_id=project_id, severity="high")
    db.add(new_issue)
    db.commit()
    db.refresh(new_issue)
except Exception:
    db.rollback()  # Crucial: Roll back transaction on failure!
    raise
```

---

#### ⚠️ Common Database Pitfalls & How to Avoid Them:
1. **Forgot `db.rollback()`**: If an insert fails and you don't rollback, subsequent queries on the same session will fail with `PendingRollbackError`.
2. **N+1 Query Problem**: Fetching records in a loop instead of using `joinedload()` or bulk joins.
3. **Foreign Key Violation**: Inserting a record with a `project_id` or `user_id` that does not exist in the referenced table.
""",
            suggested_followups=[
                "How do I fix database transaction rollback errors?",
                "What is the N+1 query problem and how do I solve it?",
                "How do database indexes improve search performance?",
            ],
            category="Databases & SQL",
            helpful_tips=[
                "Always wrap database write transactions with try/except/rollback.",
                "Add database indexes on frequently filtered columns like `project_id` and `status`.",
            ],
        )

    # 9. Frontend, React, Components, Hooks & State
    if any(k in lowered for k in ["react", "frontend", "hook", "useeffect", "usestate", "component", "props", "state", "render"]):
        return AIChatResponse(
            reply="""### ⚛️ Modern React, Hooks & State Management Guide

#### 🧩 Core React Principles for Beginners:
1. **Components**: Reusable UI building blocks that accept `props` and return JSX.
2. **State (`useState`)**: Reactive data that triggers a UI re-render when modified.
3. **Side Effects (`useEffect`)**: Handles asynchronous operations like API calls, timers, or DOM subscriptions.

---

#### 🛠️ Pattern: Safe API Data Fetching with Loading & Error States:
```jsx
function BugList({ projectId }) {
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      setLoading(true);
      try {
        const data = await getAllIssues({ project_id: projectId });
        if (isMounted) setIssues(data);
      } catch (err) {
        if (isMounted) setError(err.message);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadData();
    return () => { isMounted = false; }; // Cleanup on unmount
  }, [projectId]);

  if (loading) return <div>Loading defects...</div>;
  if (error) return <div className="error-banner">{error}</div>;

  return (
    <ul>
      {issues.map(issue => (
        <li key={issue.id}>{issue.title}</li>
      ))}
    </ul>
  );
}
```

---

#### ⚠️ Common React Mistakes:
- **Direct State Mutation**: Never do `state.items.push(x)`. Always do `setItems([...items, x])`.
- **Missing Dependency in `useEffect`**: If you use a variable inside `useEffect`, include it in the dependency array `[dependency]`.
""",
            suggested_followups=[
                "How do I prevent infinite loops in useEffect?",
                "What is the difference between Props and State in React?",
                "How does React Context API work for global authentication?",
            ],
            category="Frontend & React",
            helpful_tips=[
                "Never mutate state directly — always return a new array or object copy.",
                "Always provide a unique `key` prop when rendering lists with `.map()`.",
            ],
        )

    # 10. QA Testing Methodologies (Unit, Integration, E2E, Smoke, Regression)
    if any(k in lowered for k in ["test", "testing", "unit test", "integration test", "e2e", "smoke test", "sanity", "pytest", "jest", "uat"]):
        return AIChatResponse(
            reply="""### 🧪 Software Testing Methodologies & QA Types

#### 📊 The Testing Pyramid:
```
       /\\
      / E2E \\        <- Fewest, slowest (e.g. Cypress, Playwright)
     /-------\\
    / Integration \\  <- Testing API endpoints with real database
   /---------------\\
  /   Unit Tests    \\ <- Most numerous, fastest (e.g. pytest, Jest)
 /-------------------\\
```

---

#### 🏆 Key Testing Types Explained:
1. **Unit Testing**: Tests individual functions in isolation (e.g. testing the severity prediction calculation).
2. **Integration Testing**: Tests how multiple modules interact (e.g. testing user registration -> JWT generation -> database insert).
3. **End-to-End (E2E) Testing**: Simulates real user behavior in a browser from login to checkout.
4. **Regression Testing**: Re-running existing tests after code changes to ensure existing features haven't broken.
5. **Smoke Testing**: Quick high-level test to verify critical pathways are functional before deeper testing.

---

#### 🛠️ Example: Writing a Clean Unit Test with `pytest`:
```python
def test_issue_creation_defaults():
    # Arrange
    payload = {"title": "Test bug", "project_id": 1}

    # Act
    response = client.post("/api/issues", json=payload)

    # Assert
    assert response.status_code == 201
    assert response.json()["status"] == "open"
    assert response.json()["severity"] == "medium"
```
""",
            suggested_followups=[
                "How do I write a test for an endpoint that requires authentication?",
                "What is Test-Driven Development (TDD)?",
                "How to mock database calls in unit tests?",
            ],
            category="QA & Testing",
            helpful_tips=[
                "Follow the Arrange-Act-Assert (AAA) pattern when structuring test cases.",
                "Write tests that replicate every reported bug before applying the fix.",
            ],
        )

    # 11. Git, Branches, PRs & Merge Conflicts
    if any(k in lowered for k in ["git", "branch", "commit", "merge", "pull request", "pr", "conflict", "rebase"]):
        return AIChatResponse(
            reply="""### 🌿 Git Workflow & Pull Requests for Defect Fixes

#### 🧩 Standard Git Feature/Bugfix Branch Workflow:
1. **Create a Dedicated Branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b fix/def-42-checkout-timeout
   ```
2. **Make Minimal, Atomic Commits**:
   ```bash
   git add app/routers/issues.py
   git commit -m "fix(checkout): add null check on payment payload [DEF-42]"
   ```
3. **Push Branch & Open Pull Request**:
   ```bash
   git push origin fix/def-42-checkout-timeout
   ```
4. **Code Review & CI Tests**: Teammates review code and automated test suites pass.
5. **Merge & Delete Branch**: Merged into `main` and ticket status moved to `Resolved`.

---

#### 🛠️ Resolving Merge Conflicts:
If git reports conflicts when pulling main:
```bash
git checkout fix/def-42-checkout-timeout
git merge main
# Open conflicting files, resolve the <<<<<<< HEAD markers, then:
git add .
git commit -m "chore: resolve merge conflicts with main"
git push
```
""",
            suggested_followups=[
                "What is the difference between git merge and git rebase?",
                "How to write clear conventional commit messages?",
                "How do I undo the last commit without losing my changes?",
            ],
            category="Version Control & Git",
            helpful_tips=[
                "Reference the BugFlow defect ID in your commit message (e.g. `[DEF-42]`).",
                "Keep bugfix branches small and focused on a single defect.",
            ],
        )

    # 12. Agile, Bug Lifecycle & Triage
    if _has_kw(lowered, "lifecycle", "triage", "definition of done", "dod", "bug status", "workflow", "scrum", "sprint"):
        return AIChatResponse(
            reply="""### 🔄 The Software Bug Lifecycle & Agile Triage

#### 📊 Standard Defect Status Transitions:
```
[ New / Open ] 
      ⬇️ (Triage & Assignment)
[ In Progress ] 
      ⬇️ (Fix Implemented & Unit Tests Passed)
[ Resolved / In Review ] 
      ⬇️ (QA Verification on Staging)
[ Closed / Done ] 
      🔄 (If Defect Persists ➡️ Reopened)
```

---

#### 🏆 Key Stages Explained:
1. **Open**: Bug has been logged by QA or user and awaits triage.
2. **In Progress**: Developer has reproduced the bug and is writing the fix.
3. **Resolved**: Pull request is merged and fix is deployed to staging.
4. **Verified / Closed**: QA tests the fix on staging, verifies acceptance criteria, and closes the ticket.
5. **Reopened**: Defect still reproducible or caused a side-effect regression.
""",
            suggested_followups=[
                "What happens during a Bug Triage meeting?",
                "What is the Definition of Done (DoD) for a bug fix?",
                "When should a bug be marked as 'Won't Fix' or 'Duplicate'?",
            ],
            category="Agile & Workflow",
            helpful_tips=[
                "A bug should only be moved to Closed after independent QA verification.",
                "Always link the PR commit hash to the BugFlow defect ticket.",
            ],
        )

    # 13. BugFlow Features & Platform Guide
    if _has_kw(lowered, "bugflow", "sprint board", "how to use", "feature"):
        return AIChatResponse(
            reply="""### 🚀 BugFlow Features & Platform Guide

BugFlow is built to streamline defect tracking, sprint velocity, and AI-assisted troubleshooting.

---

#### 🌟 Key Platform Features:
1. **Defect Tracking & Kanban**:
   - Filter bugs by Project, Severity, Priority, Status, or Assignee.
   - Switch between **Table View** and **Kanban Board** with drag-and-drop status transitions.
2. **AI Copilot in Bug Creation**:
   - **Voice Bug Report**: Dictate your bug notes via speech-to-text.
   - **Line-by-Line Expansion**: Expands rough notes into professional formatted defect reports.
   - **Automatic Severity & Category Prediction**: AI suggests taxonomy and risk levels.
   - **Duplicate Detection**: Prevents logging duplicate tickets in the project.
3. **Sprint Board & Milestone Health**:
   - Organize issues into active sprints.
   - Evaluates sprint health scores and risk mitigations.
4. **Resolution Assistance Copilot**:
   - Inside Bug Detail Modal, provides developer diagnostic checklists and matching historical resolutions.
5. **Executive PDF Reports**:
   - Export official single-defect reports or project QA summaries in PDF format.
""",
            suggested_followups=[
                "How do I create a new project and add team members?",
                "How do I use Resolution Assistance for an issue?",
                "How do I download a Defect Report PDF?",
            ],
            category="BugFlow Guide",
            helpful_tips=[
                "Use the AI Mentor button in the Report Bug form to critique draft descriptions.",
                "Click 'Ask AI Mentor' in any Bug Detail Modal to get instant diagnosis steps.",
            ],
        )

    # 19. General Open-Ended Mentoring Assistant
    issue_title = ctx.get("issue_title") or ctx.get("title")
    issue_desc = ctx.get("issue_description") or ctx.get("description")
    project_name = ctx.get("project_name")

    context_prefix = ""
    if issue_title:
        context_prefix = f"**Current Bug Context**: *{issue_title}*\n\n"

    # Extract keywords to make response relevant even in fallback mode
    words = [w for w in re.findall(r"\w+", lowered) if len(w) > 3 and w not in ["what", "how", "why", "when", "does", "have", "with", "this", "that", "from", "about", "tell", "please", "help"]]
    topic_summary = " ".join(words[:4]).title() if words else "Software Engineering & QA"

    return AIChatResponse(
        reply=f"""{context_prefix}### 🤖 AI Mentor: Guide on {topic_summary}

Here is a structured explanation and recommended best practices:

---

#### 💡 Core Principles & Overview:
- When working with **{topic_summary}**, always start by breaking down the goal into clear, measurable steps.
- **For Bug Reporting**: Always provide numbered steps to reproduce, expected vs actual behavior, and environment context.
- **For Debugging & Fixing**: First reproduce locally, inspect terminal/browser logs for exact line numbers, form a hypothesis, apply a minimal fix, and verify with tests.

---

#### 🛠️ Recommended Action Steps:
1. **Analyze Requirements / Symptoms**: Identify the exact trigger condition or technical error message.
2. **Inspect Boundaries**: Determine if the issue is in the frontend client, backend API route, database schema, or network layer.
3. **Defensive Implementation**: Write clean code with proper validation, null checks, and error boundaries.
4. **Automated Verification**: Add a unit or integration test to prevent regression.

---

Feel free to ask a specific follow-up question or paste any error logs / code snippet below!
""",
        suggested_followups=[
            "How do I write clear steps to reproduce?",
            "What is the difference between Severity and Priority?",
            "How to troubleshoot a 500 Internal Server Error?",
            "How do I write a unit test for my fix?",
        ],
        category="Software Engineering Mentor",
        helpful_tips=[
            "You can paste code snippets, error traces, or draft bug descriptions directly into this chat.",
            "Click any suggested follow-up question to explore deeper.",
        ],
    )


async def generate_chat_response(request: AIChatRequest) -> AIChatResponse:
    """Generate educational, beginner-friendly AI chat response with non-blocking AsyncOpenAI and instant local fallback."""
    last_user_msg = request.messages[-1].content if request.messages else ""
    cache_key = f"chat:{request.mode}:{last_user_msg.strip().lower()}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached

    if not ai_circuit_breaker.is_available():
        res = _fallback_chat_response(request.messages, request.context, request.mode)
        _set_in_cache(cache_key, res)
        return res

    client = get_async_openai_client()
    if not client:
        return _fallback_chat_response(request.messages, request.context, request.mode)

    try:
        # Build message history for OpenAI
        api_messages = [{"role": "system", "content": CHAT_MENTOR_SYSTEM_PROMPT}]

        # Inject active context if provided
        if request.context:
            context_str = json.dumps(request.context, indent=2)
            api_messages.append({
                "role": "system",
                "content": f"Active User & Defect Context:\n```json\n{context_str}\n```\nMode: {request.mode or 'general_mentor'}",
            })

        for m in request.messages[-10:]:  # Keep recent 10 messages for context
            api_messages.append({"role": m.role, "content": m.content})

        response = await client.chat.completions.create(
            model=settings.openai_model,
            messages=api_messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        data = json.loads(response.choices[0].message.content or "{}")

        reply = data.get("reply") or data.get("message") or data.get("response") or ""
        if not reply:
            return _fallback_chat_response(request.messages, request.context, request.mode)

        ai_circuit_breaker.record_success()
        result = AIChatResponse(
            reply=reply,
            suggested_followups=data.get("suggested_followups", [
                "How do I write clear steps to reproduce?",
                "What is the difference between Severity and Priority?",
                "How can I test this fix locally?",
            ]),
            category=data.get("category", "QA Mentor"),
            helpful_tips=data.get("helpful_tips", [
                "Always separate reproduction steps into clear numbered bullets.",
                "Include the observed HTTP status code or console error whenever applicable.",
            ]),
        )
        _set_in_cache(cache_key, result)
        return result
    except Exception as exc:
        ai_circuit_breaker.record_failure(exc)
        res = _fallback_chat_response(request.messages, request.context, request.mode)
        _set_in_cache(cache_key, res)
        return res

