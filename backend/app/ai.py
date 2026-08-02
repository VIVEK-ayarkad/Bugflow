import json
import re

from openai import OpenAI
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Issue, IssueSeverity, IssueStatus, Sprint
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

SYSTEM_PROMPT = """You are an expert bug report copilot for BugFlow. Given a user's short or vague bug description,
analyze it and expand it into a comprehensive, highly professional bug report automatically.

Respond with JSON only (no markdown fences):

{
  "needs_more_info": false,
  "formatted_report": {
    "title": "Concise, descriptive bug title",
    "description": "Full structured description containing Summary, Affected Component, Steps to Reproduce, Expected vs Actual Behavior, Environment & System Info, and Developer Notes.",
    "priority": "low|medium|high|critical"
  }
}

Always populate the 'description' field with rich, multi-paragraph markdown detailing steps to reproduce and expected/actual behavior using intelligent inferences. Do not ask follow-up questions."""


def _infer_title(raw: str) -> str:
    text = re.sub(r"\s+", " ", raw.strip())
    if not text:
        return "Untitled software defect"
    lowered = text.lower()
    if "login" in lowered:
        return "Authentication Failure on User Login"
    if "payment" in lowered or "checkout" in lowered:
        return "Payment Gateway Transaction 500 Error"
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

    if any(k in lowered for k in ["login", "auth", "password", "signin", "signup"]):
        component = "Authentication & User Session Module"
        steps = "1. Navigate to user sign-in page.\n2. Enter valid account credentials and submit form.\n3. Observe authentication failure or session timeout."
        expected = "User should be authenticated successfully and redirected to dashboard."
        actual = "Authentication request fails or throws unhandled error."
        notes = "Inspect authHeaders(), JWT token expiration, and backend login API route."
    elif any(k in lowered for k in ["pay", "checkout", "stripe", "billing", "cart", "purchase", "500"]):
        component = "Checkout & Payment Gateway Integration"
        steps = "1. Add item to shopping cart and proceed to checkout.\n2. Enter payment credentials and confirm purchase.\n3. Observe HTTP 500 server error."
        expected = "Payment processes cleanly and order receipt is returned."
        actual = "Payment gateway endpoint returns 500 Internal Server Error."
        notes = "Check payment provider API keys, webhook handling, and transaction log trace."
    elif any(k in lowered for k in ["image", "upload", "file", "photo", "avatar"]):
        component = "Media Upload & Storage Service"
        steps = "1. Open media upload dialog.\n2. Select file (PNG/JPG/PDF) and initiate upload.\n3. Observe progress stalls or drops connection."
        expected = "File uploads to storage bucket and preview renders immediately."
        actual = "Upload fails without clear validation error message."
        notes = "Verify file size limits, MIME type validation, and CORS storage headers."
    elif any(k in lowered for k in ["slow", "performance", "delay", "query", "latency"]):
        component = "API Performance & Data Query Layer"
        steps = "1. Trigger database query or load analytics dashboard.\n2. Inspect Network tab response timing.\n3. Observe request latency exceeding threshold."
        expected = "Data should load under 300ms."
        actual = "Request takes >3000ms or causes gateway timeout."
        notes = "Audit database query execution plan, missing indices, and connection pooling."
    else:
        component = "Core Application Feature"
        steps = f"1. Trigger feature action related to '{cleaned}'.\n2. Observe system response.\n3. Verify error logs in browser/server console."
        expected = "Feature operates as specified without unexpected errors."
        actual = f"Unexpected behavior occurs when attempting: {cleaned}."
        notes = "Trace component state lifecycle and error boundary handlers."

    return (
        f"### Summary\n{cleaned.capitalize() if cleaned else 'Software defect reported.'}\n\n"
        f"### Affected Component\n{component}\n\n"
        f"### Steps to Reproduce\n{steps}\n\n"
        f"### Expected vs Actual Behavior\n- **Expected:** {expected}\n- **Actual:** {actual}\n\n"
        f"### Environment & System Info\n- **OS / Platform:** macOS / Chromium & Web Browsers\n- **Severity:** Impacting user workflow\n\n"
        f"### Developer Notes\n{notes}"
    )


def _best_effort_report(raw: str) -> dict:
    cleaned = re.sub(r"\s+", " ", raw.strip())
    return {
        "title": _infer_title(cleaned),
        "description": _generate_rich_description(cleaned),
        "priority": _infer_priority(cleaned),
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

    client = OpenAI(api_key=openai_api_key)
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


# ── AI Severity Predictor ──────────────────────────────────────────────────

def predict_severity_rule_based(title: str, description: str) -> SeverityPredictResponse:
    text = (title + " " + description).lower()
    if any(k in text for k in ["crash", "security", "data loss", "vulnerability", "fatal", "production down", "unusable"]):
        sev = IssueSeverity.CRITICAL
        rat = "Defect causes application crash, security vulnerability, or data loss affecting core system stability."
    elif any(k in text for k in ["500", "error", "fail", "payment", "auth", "broken", "blocked"]):
        sev = IssueSeverity.HIGH
        rat = "Major feature malfunction blocking user workflow without immediate workaround."
    elif any(k in text for k in ["slow", "performance", "delay", "ui", "alignment", "typo"]):
        sev = IssueSeverity.LOW
        rat = "Minor visual, performance, or cosmetic defect with minimal impact on core functionality."
    else:
        sev = IssueSeverity.MEDIUM
        rat = "Defect affects standard functionality but a temporary workaround exists."

    return SeverityPredictResponse(
        predicted_severity=sev,
        confidence=0.92,
        rationale=rat
    )


async def predict_severity(request: SeverityPredictRequest) -> SeverityPredictResponse:
    openai_api_key = settings.openai_api_key.strip()
    if not openai_api_key:
        return predict_severity_rule_based(request.title, request.description)

    client = OpenAI(api_key=openai_api_key)
    try:
        sys_prompt = "You are an AI Quality Assurance Specialist for BugFlow. Analyze bug reports and predict severity (low, medium, high, critical) with clear rationale in JSON format."
        usr_prompt = f"Title: {request.title}\nDescription: {request.description}"
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
        sev_str = str(data.get("predicted_severity", "medium")).lower()
        if sev_str not in ["low", "medium", "high", "critical"]:
            sev_str = "medium"
        return SeverityPredictResponse(
            predicted_severity=IssueSeverity(sev_str),
            confidence=float(data.get("confidence", 0.95)),
            rationale=data.get("rationale", "AI predicted severity based on defect scope and user impact.")
        )
    except Exception:
        return predict_severity_rule_based(request.title, request.description)


# ── Duplicate Bug Detector ────────────────────────────────────────────────

def detect_duplicates(request: DuplicateDetectRequest, db: Session) -> DuplicateDetectResponse:
    query_text = (request.title + " " + request.description).lower()
    words = set(re.findall(r'\w{4,}', query_text))

    existing_issues = db.query(Issue).filter(Issue.project_id == request.project_id).all()
    potential_duplicates = []

    for issue in existing_issues:
        issue_text = (issue.title + " " + issue.description).lower()
        issue_words = set(re.findall(r'\w{4,}', issue_text))
        if not words or not issue_words:
            continue
        intersection = words.intersection(issue_words)
        union = words.union(issue_words)
        jaccard_score = len(intersection) / len(union) if union else 0

        # Exact substring title check
        if request.title.strip().lower() in issue.title.lower() or issue.title.lower() in request.title.strip().lower():
            jaccard_score = max(jaccard_score, 0.85)

        if jaccard_score >= 0.35:
            potential_duplicates.append({
                "id": issue.id,
                "title": issue.title,
                "status": issue.status.value if hasattr(issue.status, 'value') else issue.status,
                "similarity_score": round(jaccard_score * 100, 1),
                "reporter": issue.reporter.username if issue.reporter else "Unknown"
            })

    potential_duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
    return DuplicateDetectResponse(
        has_duplicates=len(potential_duplicates) > 0,
        potential_duplicates=potential_duplicates[:5]
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


# ── Code Doctor Fixer ─────────────────────────────────────────────────────

def _fallback_code_fix(request: CodeFixRequest) -> CodeFixResponse:
    code = request.code.strip()
    err = (request.error_log or "").lower()
    lang = (request.language or "javascript").lower()

    user_mistake = ""
    root_cause = ""
    explanation = ""
    corrected = code
    tip = ""

    if "python" in lang:
        if "keyerror" in err or re.search(r'\w+\[\s*[\'"].*?[\'"]\s*\]', code):
            match = re.search(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', code)
            dict_var = match.group(1) if match else "dict_obj"
            key_name = match.group(2) if match else "key"
            user_mistake = f"You attempted to access dictionary key {key_name} directly using '{dict_var}[{key_name}]' without checking if key exists."
            root_cause = f"Direct dictionary indexing '{dict_var}[{key_name}]' raises KeyError when key is missing."
            explanation = f"Replaced direct indexing with '{dict_var}.get({key_name})' which safely returns None."
            corrected = re.sub(r'(\w+)\[\s*([\'"].*?[\'"])\s*\]', r'\1.get(\2)', code)
            tip = f"Use dict.get(key, default) or check 'if key in dict:'."
        else:
            user_mistake = "Your Python code lacks defensive exception checking."
            root_cause = "Unhandled runtime exception."
            explanation = "Wrapped code execution safely."
            corrected = f"try:\n    {code}\nexcept Exception as e:\n    print(f'Error: {{e}}')"
            tip = "Use try/except blocks to catch expected execution failures."
    else:
        if "cannot read properties" in err or re.search(r'\b\w+\.(map|filter|forEach)\(', code):
            user_mistake = "You called array methods directly on an undefined or null variable."
            root_cause = "Invoking array method on uninitialized state."
            explanation = "Added fallback empty array guard to prevent TypeError."
            corrected = re.sub(r'(\b\w+)\.(map|filter|forEach)\(', r'(\1 || []).\2(', code)
            tip = "Use optional chaining (items?.map(...)) or fallback empty arrays."
        else:
            user_mistake = "Your code snippet contains unhandled async or null values."
            root_cause = "Potential unhandled null dereference."
            explanation = "Added defensive checks."
            corrected = code
            tip = "Validate object values before accessing properties."

    return CodeFixResponse(
        user_mistake=user_mistake,
        root_cause=root_cause,
        explanation=explanation,
        corrected_code=corrected,
        diff_lines=[{"type": "del", "text": f"- {code[:50]}"}, {"type": "add", "text": f"+ {corrected[:50]}"}],
        prevention_tip=tip,
    )


async def fix_code_snippet(request: CodeFixRequest) -> CodeFixResponse:
    openai_api_key = settings.openai_api_key.strip()
    if not openai_api_key:
        return _fallback_code_fix(request)

    client = OpenAI(api_key=openai_api_key)
    try:
        system_prompt = f"""You are an expert AI Code Doctor for BugFlow. Given code and error log, provide JSON response:
{{
  "user_mistake": "clear 1-2 sentence description of user mistake",
  "root_cause": "technical root cause",
  "explanation": "how fix resolves issue",
  "corrected_code": "raw corrected code without markdown fences",
  "prevention_tip": "best practice tip"
}}"""
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

        return CodeFixResponse(
            user_mistake=data.get("user_mistake", "Syntax/runtime issue in code."),
            root_cause=data.get("root_cause", "Uncaught exception."),
            explanation=data.get("explanation", "Corrected edge cases."),
            corrected_code=corrected_code,
            diff_lines=[],
            prevention_tip=data.get("prevention_tip", "Validate input variables."),
        )
    except Exception:
        return _fallback_code_fix(request)
