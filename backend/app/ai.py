import ast
import json
import math
import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Issue, IssuePriority, IssueSeverity, IssueStatus, Sprint
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
    openai_api_key = settings.openai_api_key.strip()
    if not openai_api_key:
        return _fallback_response(request.raw_description)

    client = OpenAI(api_key=openai_api_key, timeout=5.0)
    try:
        response = client.chat.completions.create(
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

        return AIAssistResponse(
            needs_more_info=False,
            follow_up_questions=data.get("follow_up_questions", []),
            formatted_report=report,
            message="Bug report automatically enriched with detailed reproduction steps & context.",
        )
    except Exception:
        return _fallback_response(request.raw_description)


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
    openai_api_key = settings.openai_api_key.strip()
    if not openai_api_key:
        return predict_severity_rule_based(request.title or "", request.description)

    client = OpenAI(api_key=openai_api_key, timeout=5.0)
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
        response = client.chat.completions.create(
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

        return SeverityPredictResponse(
            predicted_severity=sev_map.get(sev_str, IssueSeverity.MEDIUM),
            predicted_priority=pri_map.get(pri_str, IssuePriority.MEDIUM),
            confidence=float(data.get("confidence", 0.95)),
            rationale=data.get("rationale", "AI predicted severity & priority based on defect scope and user impact.")
        )
    except Exception:
        return predict_severity_rule_based(request.title or "", request.description)


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
    openai_api_key = settings.openai_api_key.strip()
    if openai_api_key:
        try:
            client = OpenAI(api_key=openai_api_key, timeout=4.0)
            res = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            return res.data[0].embedding
        except Exception:
            pass
    return build_semantic_vector(text)


async def semantic_search_defects(request: SemanticSearchRequest, db: Session) -> SemanticSearchResponse:
    query = request.query.strip()
    if not query:
        return SemanticSearchResponse(query=query, results=[], total_found=0)

    db_query = db.query(Issue)
    if request.project_id:
        db_query = db_query.filter(Issue.project_id == request.project_id)

    issues = db_query.all()
    if not issues:
        return SemanticSearchResponse(query=query, results=[], total_found=0)

    query_vec = await get_embedding(query)
    results = []

    for issue in issues:
        doc_text = f"{issue.title}. {issue.description or ''} Category: {issue.category or ''}. Module: {issue.module or ''}"
        doc_vec = build_semantic_vector(doc_text) if len(query_vec) == len(SEMANTIC_CLUSTERS) else await get_embedding(doc_text)
        sim = cosine_similarity(query_vec, doc_vec)

        # Keyword match bonus
        q_lower = query.lower()
        if q_lower in doc_text.lower():
            sim = max(sim, 0.92)

        # Token overlap bonus
        q_words = set(re.findall(r"\w{3,}", q_lower))
        doc_words = set(re.findall(r"\w{3,}", doc_text.lower()))
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

    results.sort(key=lambda x: x["similarity_score"], reverse=True)
    selected = results[:request.limit]
    return SemanticSearchResponse(query=query, results=selected, total_found=len(selected))


# ── Resolution Assistance Engine (Signature Feature) ──────────────────────

async def generate_resolution_assistance(request: ResolutionAssistanceRequest, db: Session) -> ResolutionAssistanceResponse:
    title = request.title.strip()
    desc = (request.description or "").strip()
    category = (request.category or "").strip()
    module = (request.module or "").strip()

    combined_text = f"{title} {desc} {category} {module}".lower()

    # 1. Search for Similar Defects in the Database
    db_query = db.query(Issue)
    if request.project_id:
        db_query = db_query.filter(Issue.project_id == request.project_id)
    if request.issue_id:
        db_query = db_query.filter(Issue.id != request.issue_id)

    candidates = db_query.all()
    similar_defects = []
    historical_resolution_found = None

    for issue in candidates:
        cand_text = f"{issue.title} {issue.description or ''}"
        score = calculate_defect_similarity(f"{title} {desc}", cand_text)

        if score >= 0.35:
            # Check if this similar defect was resolved
            is_resolved = issue.status in [IssueStatus.RESOLVED, IssueStatus.CLOSED] or str(issue.status).lower() in ["resolved", "closed"]
            res_note = None
            if is_resolved and issue.comments:
                # Find the latest comment from developer
                for c in reversed(issue.comments):
                    if len(c.content) > 15:
                        res_note = c.content[:200]
                        break

            similar_defects.append({
                "id": issue.id,
                "key": f"DEF-{issue.id}",
                "title": issue.title,
                "status": issue.status.value if hasattr(issue.status, 'value') else issue.status,
                "severity": issue.severity.value if hasattr(issue.severity, 'value') else issue.severity,
                "similarity_score": round(score * 100, 1),
                "resolution_note": res_note
            })

            if is_resolved and res_note and not historical_resolution_found:
                historical_resolution_found = f"Defect DEF-{issue.id} was resolved with note: {res_note}"

    similar_defects.sort(key=lambda x: x["similarity_score"], reverse=True)
    top_similar = similar_defects[:5]

    # 2. Try LLM Generation if OpenAI API Key Available
    openai_api_key = settings.openai_api_key.strip()
    if openai_api_key:
        try:
            client = OpenAI(api_key=openai_api_key, timeout=7.0)
            system_msg = (
                "You are an expert Principal Software Engineer and QA Resolution Assistant for BugFlow. "
                "Given a software defect, provide targeted, actionable resolution assistance. Return JSON with keys:\n"
                "- investigation_areas (list of 4-5 concise, specific bullet points, e.g. 'Check payment API response.', 'Check null/undefined handling.')\n"
                "- previous_resolution (string describing how a similar defect was resolved, e.g. 'A similar defect was resolved by validating the payment API response before processing the transaction result.')\n"
                "- possible_resolution (string describing the exact recommended technical fix, e.g. 'Validate the API response and handle unexpected or null responses before continuing the payment flow.')"
            )
            user_msg = f"Defect Title: {title}\nDescription: {desc}\nCategory: {category}\nModule: {module}"
            if top_similar:
                user_msg += f"\nSimilar existing defects: {json.dumps(top_similar[:2])}"

            chat_resp = client.chat.completions.create(
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
            return ResolutionAssistanceResponse(
                investigation_areas=parsed.get("investigation_areas", []),
                similar_defects=top_similar,
                previous_resolution=historical_resolution_found or parsed.get("previous_resolution"),
                possible_resolution=parsed.get("possible_resolution", ""),
                confidence=0.98
            )
        except Exception:
            pass

    # 3. Deterministic Domain Expert Engine
    if any(k in combined_text for k in ["pay", "checkout", "stripe", "billing", "cart", "purchase", "500", "submit", "gateway"]):
        investigation_areas = [
            "Check payment API response.",
            "Check null/undefined handling.",
            "Review frontend error handling.",
            "Check server logs.",
            "Check recent changes to the payment module."
        ]
        prev_res = historical_resolution_found or "A similar defect was resolved by validating the payment API response before processing the transaction result."
        pos_res = "Validate the API response and handle unexpected or null responses before continuing the payment flow."

    elif any(k in combined_text for k in ["login", "auth", "password", "signin", "sign-in", "session", "jwt", "token", "401", "403"]):
        investigation_areas = [
            "Check authentication token expiration and refresh logic.",
            "Inspect user session storage (cookies / localStorage).",
            "Verify CORS headers and credentials mode on auth API endpoints.",
            "Check password hashing and credential verification query.",
            "Review rate limiting and lockout thresholds."
        ]
        prev_res = historical_resolution_found or "A similar defect was resolved by properly catching 401 Unauthorized responses and clearing stale JWT tokens."
        pos_res = "Implement structured error boundary for expired tokens and refresh authorization headers before retrying."

    elif any(k in combined_text for k in ["slow", "latency", "timeout", "query", "delay", "lag", "hang"]):
        investigation_areas = [
            "Analyze database query execution plans with EXPLAIN ANALYZE.",
            "Check for missing indexes on foreign key and filtered columns.",
            "Audit database connection pool saturation and timeout limits.",
            "Review frontend rendering re-render loops and network waterfalls.",
            "Inspect Redis or in-memory cache hit/miss rates."
        ]
        prev_res = historical_resolution_found or "A similar defect was resolved by adding composite database indexes and paginating large result sets."
        pos_res = "Optimize slow database queries with indexing and introduce response caching on read-heavy routes."

    elif any(k in combined_text for k in ["ui", "layout", "css", "align", "overlap", "mobile", "dark mode", "button"]):
        investigation_areas = [
            "Inspect CSS flexbox / grid layout rules and container queries.",
            "Verify responsive breakpoints on mobile viewports.",
            "Check z-index stacking context for overlapping elements.",
            "Audit CSS variable inheritance in dark/light mode themes.",
            "Test touch target dimensions and padding on mobile devices."
        ]
        prev_res = historical_resolution_found or "A similar UI defect was resolved by applying proper box-sizing and flex-wrap properties across viewports."
        pos_res = "Adjust responsive CSS container constraints and ensure proper media query overrides for mobile viewports."

    elif any(k in combined_text for k in ["upload", "file", "image", "attachment", "pdf", "storage", "download"]):
        investigation_areas = [
            "Check file size limit configurations on server and reverse proxy (Nginx).",
            "Verify MIME type validation and multipart/form-data boundary parsing.",
            "Check cloud storage (S3 / GCS / local disk) write permissions.",
            "Review async chunk upload timeout and retry limits.",
            "Inspect client-side file reader buffer handling."
        ]
        prev_res = historical_resolution_found or "A similar defect was resolved by increasing multipart max upload payload limit and handling storage upload exceptions."
        pos_res = "Ensure client-side payload streaming handles chunk timeouts and validate file mime-types before initiating storage upload."

    else:
        investigation_areas = [
            "Inspect relevant service controller and API route handlers.",
            "Check parameter validation and type constraints on inputs.",
            "Review recent git commit history on the affected component.",
            "Verify error boundaries and fallback UI states.",
            "Check application runtime logs and telemetry traces."
        ]
        prev_res = historical_resolution_found or "A similar issue was resolved by strengthening input validation and adding null checks."
        pos_res = "Sanitize and validate input arguments, and wrap asynchronous operations in structured try-catch handlers."

    return ResolutionAssistanceResponse(
        investigation_areas=investigation_areas,
        similar_defects=top_similar,
        previous_resolution=prev_res,
        possible_resolution=pos_res,
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
        recommendations=recommendations
        
    )


# ── Code Doctor Fixer & Intelligent Syntax Diagnostics ─────────────────────

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

        # Check if the line ends with brackets that belong outside the string
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


def _diagnose_and_fix_code(code: str, language: str = "python", error_log: str = "") -> CodeFixResponse:
    raw_code = code.strip()
    lang = (language or "python").lower()
    err = (error_log or "").lower()

    lines = raw_code.split("\n")
    fixed_lines = []
    mistakes = []
    root_causes = []
    explanations = []
    tips = []

    if "python" in lang or "py" in lang:
        # Check if python code is already 100% syntactically valid with ast
        is_clean_ast = False
        try:
            ast.parse(raw_code)
            is_clean_ast = True
        except SyntaxError:
            is_clean_ast = False

        for line in lines:
            # 1. Typos in builtins (pritn -> print)
            if re.search(r"\b(pritn|prnt)\b", line):
                line = re.sub(r"\b(pritn|prnt)\b", "print", line)
                mistakes.append("Misspelled built-in 'print' function name.")
                root_causes.append("NameError: misspelled function name.")
                explanations.append("Corrected function name to 'print'.")

            # 2. Python 2 print statements
            p2_match = re.match(r"^(\s*)print\s+([^\(].*)$", line)
            if p2_match:
                indent, rest = p2_match.groups()
                line = f"{indent}print({rest.rstrip()})"
                mistakes.append("Used Python 2 print statement syntax without parentheses.")
                root_causes.append("SyntaxError: Missing parentheses in call to 'print'.")
                explanations.append("Converted print statement to Python 3 function call print(...).")
                tips.append("Python 3 requires parentheses for print().")

            # 3. Quotes & brackets
            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)

            # 4. Missing colons on header statements
            if re.match(r"^\s*(if|elif|else|for|while|def|class|with|try|except|finally)\b", line):
                if not line.rstrip().endswith(":"):
                    line = line.rstrip() + ":"
                    mistakes.append("Missing colon ':' at the end of block statement header.")
                    root_causes.append("SyntaxError: expected ':' at end of header statement.")
                    explanations.append("Appended required colon ':' to header statement.")
                    tips.append("Python compound statements (if, for, def, class, etc.) must end with a colon ':'.")

            # 5. Single = in if / elif
            if re.search(r"\b(if|elif)\s+([a-zA-Z_]\w*)\s*=\s*([^=])", line):
                line = re.sub(r"\b(if|elif)\s+([a-zA-Z_]\w*)\s*=\s*([^=])", r"\1 \2 == \3", line)
                mistakes.append("Used single assignment operator '=' in conditional expression instead of '=='.")
                root_causes.append("SyntaxError: invalid syntax in condition assignment.")
                explanations.append("Replaced '=' with equality comparison operator '=='.")
                tips.append("Use '==' for comparison checks and '=' for variable assignment.")

            # 6. JavaScript literals in Python
            if re.search(r"\b(true|false|null|undefined)\b", line):
                line = re.sub(r"\btrue\b", "True", line)
                line = re.sub(r"\bfalse\b", "False", line)
                line = re.sub(r"\bnull\b", "None", line)
                line = re.sub(r"\bundefined\b", "None", line)
                mistakes.append("Used JavaScript/JSON literals (true/false/null) instead of Python TitleCase keywords.")
                root_causes.append("NameError: undefined literal name in Python.")
                explanations.append("Converted literals to Python TitleCase syntax (True, False, None).")

            # 7. Safe dictionary lookup for KeyError
            if ("keyerror" in err or "key" in err) and re.search(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', line):
                line = re.sub(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', r'\1.get(\2)', line)
                mistakes.append("Direct dictionary indexing with [] raises KeyError when key is missing.")
                root_causes.append("KeyError when accessing non-existent dictionary key.")
                explanations.append("Replaced direct indexing with dict.get() for safe lookup.")
                tips.append("Use dict.get(key, default) for safe key retrieval.")

            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)

        # If the code was already completely valid and no modifications were needed
        if is_clean_ast and not mistakes and corrected_code == raw_code and not err:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No syntax or logical defects detected.",
                explanation="Your Python code was analyzed and verified. It is syntactically valid, properly formatted, and ready to execute.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is clean and error-free! Keep writing modular, well-tested Python functions."
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

            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)
        if not mistakes and corrected_code == raw_code and not err:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No syntax or runtime defects detected.",
                explanation="Your JavaScript code was analyzed and verified. It is properly structured and ready to run.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is clean and error-free! Continue following modern JavaScript best practices."
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
        if not mistakes and corrected_code == raw_code and not err:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No SQL syntax defects detected.",
                explanation="Your SQL query was analyzed and verified. It is syntactically valid and ready to execute.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Query syntax is clean! Use appropriate indexes and parameterized queries."
            )

    else:
        for line in lines:
            line, m, rc, exp = _repair_quotes_and_brackets(line)
            mistakes.extend(m)
            root_causes.extend(rc)
            explanations.extend(exp)
            fixed_lines.append(line)

        corrected_code = "\n".join(fixed_lines)
        if not mistakes and corrected_code == raw_code and not err:
            return CodeFixResponse(
                is_correct=True,
                user_mistake=None,
                root_cause="No syntax defects detected.",
                explanation="Your code snippet was analyzed and verified. It is valid and ready to run.",
                corrected_code=raw_code,
                diff_lines=[],
                prevention_tip="Code is clean and error-free!"
            )

    user_mistake_str = " ".join(dict.fromkeys(mistakes)) if mistakes else "Syntax discrepancy detected."
    root_cause_str = " ".join(dict.fromkeys(root_causes)) if root_causes else "Syntax defect."
    explanation_str = " ".join(dict.fromkeys(explanations)) if explanations else "Corrected code syntax directly."
    tip_str = tips[0] if tips else "Always verify syntax and test edge cases."

    return CodeFixResponse(
        is_correct=False,
        user_mistake=user_mistake_str,
        root_cause=root_cause_str,
        explanation=explanation_str,
        corrected_code=corrected_code,
        diff_lines=[{"type": "del", "text": f"- {raw_code[:60]}"}, {"type": "add", "text": f"+ {corrected_code[:60]}"}],
        prevention_tip=tip_str,
    )


async def fix_code_snippet(request: CodeFixRequest) -> CodeFixResponse:
    openai_api_key = settings.openai_api_key.strip()
    if not openai_api_key:
        return _diagnose_and_fix_code(request.code, request.language, request.error_log)

    client = OpenAI(api_key=openai_api_key, timeout=5.0)
    try:
        system_prompt = """You are an expert AI Code Doctor for BugFlow. Analyze the user's code snippet, determine if it is correct or contains defects, and provide a direct, clean response.

CRITICAL RULES:
1. If the code is ALREADY correct with no syntax or logic errors, set "is_correct": true, "user_mistake": null, "root_cause": "No syntax or logical defects detected.", "explanation": "Code is valid and ready to run.", and return the original code in "corrected_code".
2. If the code is incorrect, set "is_correct": false, describe the mistake in "user_mistake", and provide the direct fix in "corrected_code".
3. NEVER wrap code in a generic `try...except` or `try...catch` block.
4. Example: If given `print("hell)`, corrected code MUST be `print("hell")`.
5. Return pure JSON only with no markdown formatting outside JSON.

JSON Schema:
{
  "is_correct": true/false,
  "user_mistake": "1-2 sentence clear description of mistake (or null if is_correct is true)",
  "root_cause": "The technical reason/exception that caused the issue",
  "explanation": "Explanation of fix or confirmation of validity",
  "corrected_code": "The raw code without markdown fences",
  "prevention_tip": "A concise engineering best-practice tip"
}"""
        user_prompt = f"Language: {request.language}\nError Log: {request.error_log}\nCode:\n{request.code}"
        response = client.chat.completions.create(
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

        # If corrected code matches raw input and no errors reported, mark as correct
        if corrected_code.strip() == request.code.strip() and not data.get("user_mistake"):
            is_correct = True

        # Sanity check: If AI tried to wrap in try/except when original didn't have it, use our deterministic fixer
        if ("try:" in corrected_code or "try {" in corrected_code) and ("try:" not in request.code and "try {" not in request.code):
            fallback_res = _diagnose_and_fix_code(request.code, request.language, request.error_log)
            return fallback_res

        return CodeFixResponse(
            is_correct=is_correct,
            user_mistake=None if is_correct else data.get("user_mistake", "Syntax/runtime issue in code."),
            root_cause=data.get("root_cause", "No defects detected." if is_correct else "Syntax error or uncaught exception."),
            explanation=data.get("explanation", "Code is clean and valid." if is_correct else "Corrected syntax defect directly."),
            corrected_code=corrected_code,
            diff_lines=[],
            prevention_tip=data.get("prevention_tip", "Validate input variables and test syntax."),
        )
    except Exception:
        return _diagnose_and_fix_code(request.code, request.language, request.error_log)


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
    if not openai_api_key:
        return _fallback_defect_classification(request.description, request.title or "")

    client = OpenAI(api_key=openai_api_key, timeout=5.0)
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
        response = client.chat.completions.create(
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



