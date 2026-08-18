import io
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from app.models import Issue, Project


def _get_pdf_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "PDFTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#3b82f6"),
        spaceAfter=6,
    )

    section_header_style = ParagraphStyle(
        "PDFSectionHeader",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=4,
    )

    label_style = ParagraphStyle(
        "PDFLabel",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748b"),
    )

    value_style = ParagraphStyle(
        "PDFValue",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
    )

    body_style = ParagraphStyle(
        "PDFBody",
        fontName="Helvetica",
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#1e293b"),
    )

    meta_pill_style = ParagraphStyle(
        "PDFMetaPill",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2563eb"),
    )

    return {
        "title": title_style,
        "section": section_header_style,
        "label": label_style,
        "value": value_style,
        "body": body_style,
        "meta_pill": meta_pill_style,
    }


def generate_issue_pdf(issue: Issue) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = _get_pdf_styles()
    elements = []

    # 1. Header Banner
    header_table = Table(
        [
            [
                Paragraph("<b>BugFlow</b> QA Defect Report", styles["title"]),
                Paragraph(f"<b>#DEF-{issue.id}</b>", ParagraphStyle("Key", fontName="Helvetica-Bold", fontSize=16, alignment=2, textColor=colors.HexColor("#2563eb")))
            ]
        ],
        colWidths=[380, 160]
    )
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceBefore=4, spaceAfter=12))

    # 2. Defect Title
    elements.append(Paragraph(f"<b>Title:</b> {issue.title}", ParagraphStyle("BugTitle", fontName="Helvetica-Bold", fontSize=13, leading=17, textColor=colors.HexColor("#0f172a"))))
    elements.append(Spacer(1, 10))

    # 3. Metadata Matrix Table
    meta_data = [
        [
            Paragraph("<b>Severity:</b>", styles["label"]),
            Paragraph(f"<b>{(issue.severity.value if hasattr(issue.severity, 'value') else issue.severity).upper()}</b>", styles["value"]),
            Paragraph("<b>Priority:</b>", styles["label"]),
            Paragraph(f"<b>{(issue.priority.value if hasattr(issue.priority, 'value') else issue.priority).upper()}</b>", styles["value"]),
            Paragraph("<b>Status:</b>", styles["label"]),
            Paragraph(f"<b>{(issue.status.value if hasattr(issue.status, 'value') else issue.status).upper()}</b>", styles["value"]),
        ],
        [
            Paragraph("<b>Category:</b>", styles["label"]),
            Paragraph(issue.category or "General", styles["value"]),
            Paragraph("<b>Module:</b>", styles["label"]),
            Paragraph(issue.module or "Core Feature", styles["value"]),
            Paragraph("<b>Defect Type:</b>", styles["label"]),
            Paragraph(issue.defect_type or "Functional Defect", styles["value"]),
        ],
        [
            Paragraph("<b>Reporter:</b>", styles["label"]),
            Paragraph(issue.reporter.username if issue.reporter else "System", styles["value"]),
            Paragraph("<b>Assigned Dev:</b>", styles["label"]),
            Paragraph(issue.assigned_developer.username if issue.assigned_developer else "Unassigned", styles["value"]),
            Paragraph("<b>Created Date:</b>", styles["label"]),
            Paragraph(issue.created_at.strftime("%Y-%m-%d %H:%M") if issue.created_at else "N/A", styles["value"]),
        ]
    ]

    meta_table = Table(meta_data, colWidths=[75, 105, 75, 105, 75, 105])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 14))

    # 4. Description Section (Line by line formatted)
    elements.append(Paragraph("<b>Defect Description & Summary</b>", styles["section"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

    desc_lines = (issue.description or "No description provided.").split("\n")
    for line in desc_lines:
        line_clean = line.strip()
        if not line_clean:
            elements.append(Spacer(1, 4))
        elif line_clean.endswith(":") or line_clean.startswith("###") or line_clean.startswith("##"):
            heading_text = line_clean.replace("#", "").strip()
            elements.append(Paragraph(f"<b>{heading_text}</b>", ParagraphStyle("SubHead", fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=colors.HexColor("#2563eb"), spaceBefore=4)))
        else:
            elements.append(Paragraph(line_clean, styles["body"]))

    elements.append(Spacer(1, 12))

    # 5. Steps to Reproduce
    if issue.steps_to_reproduce:
        elements.append(Paragraph("<b>Steps to Reproduce</b>", styles["section"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))
        for s in issue.steps_to_reproduce.split("\n"):
            if s.strip():
                elements.append(Paragraph(s.strip(), styles["body"]))
        elements.append(Spacer(1, 12))

    # 6. Expected vs Actual Result
    if issue.expected_behavior or issue.actual_behavior:
        elements.append(Paragraph("<b>Expected vs Actual Behavior</b>", styles["section"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))
        if issue.expected_behavior:
            elements.append(Paragraph(f"<b>Expected:</b> {issue.expected_behavior}", styles["body"]))
        if issue.actual_behavior:
            elements.append(Paragraph(f"<b>Actual:</b> {issue.actual_behavior}", styles["body"]))
        elements.append(Spacer(1, 12))

    # 7. Resolution Assistance (AI Intelligence)
    elements.append(Paragraph("<b>Resolution Assistance</b>", styles["section"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))
    
    combined = f"{issue.title} {issue.description or ''} {issue.category or ''}".lower()
    if any(k in combined for k in ["pay", "checkout", "stripe", "billing", "cart", "purchase", "submit"]):
        inv = [
            "Check payment API response.",
            "Check null/undefined handling.",
            "Review frontend error handling.",
            "Check server logs.",
            "Check recent changes to the payment module."
        ]
        prev_res = "A similar defect was resolved by validating the payment API response before processing the transaction result."
        pos_res = "Validate the API response and handle unexpected or null responses before continuing the payment flow."
    elif any(k in combined for k in ["login", "auth", "password", "signin", "session", "jwt"]):
        inv = [
            "Check authentication token expiration and refresh logic.",
            "Inspect user session storage (cookies / localStorage).",
            "Verify CORS headers on auth API endpoints.",
            "Check password hashing and credential verification query.",
            "Review rate limiting and lockout thresholds."
        ]
        prev_res = "A similar defect was resolved by properly catching 401 Unauthorized responses and clearing stale JWT tokens."
        pos_res = "Implement structured error boundary for expired tokens and refresh authorization headers before retrying."
    else:
        inv = [
            "Inspect relevant service controller and API route handlers.",
            "Check parameter validation and type constraints on inputs.",
            "Review recent git commit history on the affected component.",
            "Verify error boundaries and fallback UI states."
        ]
        prev_res = "A similar issue was resolved by strengthening input validation and adding null checks."
        pos_res = "Sanitize input arguments and wrap asynchronous operations in structured try-catch handlers."

    elements.append(Paragraph("<b>Possible Investigation Areas:</b>", ParagraphStyle("SubHead", fontName="Helvetica-Bold", fontSize=9.5, leading=13, textColor=colors.HexColor("#1e293b"))))
    for area in inv:
        elements.append(Paragraph(f"• {area}", styles["body"]))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"<b>Previous Resolution:</b> {prev_res}", styles["body"]))
    elements.append(Spacer(1, 4))
    elements.append(Paragraph(f"<b>Possible Resolution:</b> {pos_res}", styles["body"]))
    elements.append(Spacer(1, 10))

    # 8. Comments Log
    if issue.comments and len(issue.comments) > 0:
        elements.append(Paragraph(f"<b>Activity & Comments ({len(issue.comments)})</b>", styles["section"]))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))
        for c in issue.comments:
            author = c.author.username if c.author else "System"
            c_date = c.created_at.strftime("%Y-%m-%d %H:%M") if c.created_at else ""
            elements.append(Paragraph(f"<b>{author}</b> ({c_date}): {c.content}", styles["body"]))
            elements.append(Spacer(1, 3))
        elements.append(Spacer(1, 12))

    # 8. Footer
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceBefore=8, spaceAfter=6))
    footer_text = f"Report generated automatically by BugFlow QA Intelligence on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}."
    elements.append(Paragraph(footer_text, ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748b"), alignment=1)))

    doc.build(elements)
    return buffer.getvalue()


def generate_project_summary_pdf(project: Project, issues: list[Issue]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = _get_pdf_styles()
    elements = []

    # 1. Header
    header_table = Table(
        [
            [
                Paragraph("<b>BugFlow</b> Project Defect Summary", styles["title"]),
                Paragraph(f"<b>{project.name}</b>", ParagraphStyle("ProjName", fontName="Helvetica-Bold", fontSize=13, alignment=2, textColor=colors.HexColor("#2563eb")))
            ]
        ],
        colWidths=[360, 180]
    )
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceBefore=4, spaceAfter=10))

    # 2. Metrics Calculation
    total = len(issues)
    open_count = sum(1 for i in issues if getattr(i.status, 'value', str(i.status)).lower() == 'open')
    prog_count = sum(1 for i in issues if getattr(i.status, 'value', str(i.status)).lower() == 'in_progress')
    rev_count = sum(1 for i in issues if getattr(i.status, 'value', str(i.status)).lower() == 'in_review')
    res_count = sum(1 for i in issues if getattr(i.status, 'value', str(i.status)).lower() in ['resolved', 'closed'])
    crit_count = sum(1 for i in issues if getattr(i.severity, 'value', str(i.severity)).lower() == 'critical')
    high_count = sum(1 for i in issues if getattr(i.severity, 'value', str(i.severity)).lower() == 'high')

    # 3. Metrics Summary Grid
    metrics_data = [
        [
            Paragraph("<b>Total Defects</b>", styles["label"]),
            Paragraph("<b>Open</b>", styles["label"]),
            Paragraph("<b>In Progress</b>", styles["label"]),
            Paragraph("<b>In Review</b>", styles["label"]),
            Paragraph("<b>Resolved/Closed</b>", styles["label"]),
            Paragraph("<b>Critical Severity</b>", styles["label"]),
        ],
        [
            Paragraph(f"<font size=13><b>{total}</b></font>", styles["value"]),
            Paragraph(f"<font size=13 color='#3b82f6'><b>{open_count}</b></font>", styles["value"]),
            Paragraph(f"<font size=13 color='#eab308'><b>{prog_count}</b></font>", styles["value"]),
            Paragraph(f"<font size=13 color='#8b5cf6'><b>{rev_count}</b></font>", styles["value"]),
            Paragraph(f"<font size=13 color='#22c55e'><b>{res_count}</b></font>", styles["value"]),
            Paragraph(f"<font size=13 color='#ef4444'><b>{crit_count}</b></font>", styles["value"]),
        ]
    ]

    metrics_table = Table(metrics_data, colWidths=[90, 90, 90, 90, 90, 90])
    metrics_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(metrics_table)
    elements.append(Spacer(1, 14))

    # 4. Defect Breakdown Table
    elements.append(Paragraph("<b>Defect Inventory</b>", styles["section"]))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceBefore=2, spaceAfter=8))

    table_data = [
        [
            Paragraph("<b>Key</b>", styles["label"]),
            Paragraph("<b>Title</b>", styles["label"]),
            Paragraph("<b>Category</b>", styles["label"]),
            Paragraph("<b>Severity</b>", styles["label"]),
            Paragraph("<b>Priority</b>", styles["label"]),
            Paragraph("<b>Status</b>", styles["label"]),
            Paragraph("<b>Assignee</b>", styles["label"]),
        ]
    ]

    for i in issues:
        sev_str = getattr(i.severity, 'value', str(i.severity)).upper()
        pri_str = getattr(i.priority, 'value', str(i.priority)).upper()
        stat_str = getattr(i.status, 'value', str(i.status)).upper()
        assignee_str = i.assigned_developer.username if i.assigned_developer else "Unassigned"
        
        table_data.append([
            Paragraph(f"<b>DEF-{i.id}</b>", ParagraphStyle("KeyCell", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#2563eb"))),
            Paragraph(i.title[:38] + ("..." if len(i.title) > 38 else ""), ParagraphStyle("TitleCell", fontName="Helvetica", fontSize=8)),
            Paragraph(i.category or "General", ParagraphStyle("CatCell", fontName="Helvetica", fontSize=8)),
            Paragraph(f"<b>{sev_str}</b>", ParagraphStyle("SevCell", fontName="Helvetica-Bold", fontSize=8, textColor=colors.HexColor("#ef4444") if sev_str == "CRITICAL" else colors.HexColor("#0f172a"))),
            Paragraph(pri_str, ParagraphStyle("PriCell", fontName="Helvetica", fontSize=8)),
            Paragraph(stat_str, ParagraphStyle("StatCell", fontName="Helvetica", fontSize=8)),
            Paragraph(assignee_str, ParagraphStyle("AssCell", fontName="Helvetica", fontSize=8)),
        ])

    issue_table = Table(table_data, colWidths=[45, 170, 75, 60, 55, 65, 70])
    issue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(issue_table)

    # 5. Footer
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceBefore=8, spaceAfter=6))
    footer_text = f"Report generated automatically by BugFlow QA Intelligence on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}."
    elements.append(Paragraph(footer_text, ParagraphStyle("Footer", fontName="Helvetica", fontSize=8, textColor=colors.HexColor("#64748b"), alignment=1)))

    doc.build(elements)
    return buffer.getvalue()
