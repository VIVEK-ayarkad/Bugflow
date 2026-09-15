import re
from typing import Any
from sqlalchemy.orm import Session, joinedload

from app.models import Issue, IssueSeverity, IssueStatus, Project
from app.schemas import BlastRadiusReport, CausedIssueDetail, DefectAllocation, DependencyEdge, ModuleNode


AVAILABLE_ARCHETYPES = [
    {"id": "auto", "name": "Auto-Detect Domain"},
    {"id": "saas_workflow", "name": "🏢 SaaS & Workflow Platform"},
    {"id": "ecommerce", "name": "🛒 E-Commerce & Retail Marketplace"},
    {"id": "data_ai", "name": "🤖 Data & AI Pipeline Platform"},
    {"id": "social_community", "name": "💬 Social & Messaging Platform"},
    {"id": "devops_infra", "name": "⚙️ DevOps & Cloud Infrastructure"},
]


DOMAIN_BLUEPRINTS: dict[str, dict[str, Any]] = {
    "saas_workflow": {
        "title": "SaaS & Workflow Platform",
        "modules": [
            {
                "id": "client_dashboard",
                "name": "Web UI & Workspace Dashboard",
                "category": "Frontend",
                "keywords": ["ui", "frontend", "dashboard", "react", "page", "view", "css", "modal", "kanban", "button", "form", "web", "layout", "render"],
            },
            {
                "id": "api_gateway",
                "name": "API Gateway & Ingress",
                "category": "Infrastructure",
                "keywords": ["gateway", "api", "proxy", "ingress", "route", "cors", "endpoint", "network", "server", "http", "timeout"],
            },
            {
                "id": "auth_rbac",
                "name": "Auth & Access Control (RBAC)",
                "category": "Security",
                "keywords": ["auth", "login", "token", "jwt", "password", "permission", "role", "rbac", "session", "user", "security", "oauth", "credential"],
            },
            {
                "id": "task_engine",
                "name": "Core Workflow & Defect Engine",
                "category": "Core Logic",
                "keywords": ["defect", "issue", "task", "workflow", "ticket", "bug", "engine", "status", "transition", "crud", "module", "board", "backlog"],
            },
            {
                "id": "sprint_analytics",
                "name": "Sprint & Velocity Metrics",
                "category": "Analytics",
                "keywords": ["sprint", "metric", "burndown", "velocity", "chart", "analytics", "report", "stats", "graph", "calculation", "kpi"],
            },
            {
                "id": "attachment_store",
                "name": "Document & Asset Storage",
                "category": "Storage",
                "keywords": ["attachment", "file", "upload", "download", "pdf", "s3", "storage", "image", "asset", "document", "blob"],
            },
            {
                "id": "notification_service",
                "name": "Realtime Alerts & Dispatcher",
                "category": "Messaging",
                "keywords": ["notification", "alert", "email", "push", "message", "webhook", "subscriber", "event", "websocket", "socket"],
            },
            {
                "id": "ai_copilot",
                "name": "AI Intelligence & Copilot",
                "category": "AI / ML",
                "keywords": ["ai", "copilot", "mentor", "llm", "classify", "predict", "chat", "suggestion", "bot", "assistant", "model", "prompt"],
            },
            {
                "id": "audit_logger",
                "name": "Audit Trail & System Logs",
                "category": "Compliance",
                "keywords": ["audit", "log", "activity", "history", "telemetry", "trace", "event", "security", "trail"],
            },
        ],
        "edges": [
            {"source": "client_dashboard", "target": "api_gateway", "relation_type": "dispatches_requests", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "auth_rbac", "relation_type": "authenticates", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "task_engine", "relation_type": "routes_tickets", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "sprint_analytics", "relation_type": "fetches_metrics", "severity_flow": "medium"},
            {"source": "api_gateway", "target": "ai_copilot", "relation_type": "ai_queries", "severity_flow": "medium"},
            {"source": "task_engine", "target": "auth_rbac", "relation_type": "checks_permissions", "severity_flow": "high"},
            {"source": "task_engine", "target": "attachment_store", "relation_type": "attaches_files", "severity_flow": "medium"},
            {"source": "task_engine", "target": "notification_service", "relation_type": "dispatches_events", "severity_flow": "high"},
            {"source": "task_engine", "target": "audit_logger", "relation_type": "logs_mutations", "severity_flow": "low"},
            {"source": "sprint_analytics", "target": "task_engine", "relation_type": "reads_backlog", "severity_flow": "medium"},
            {"source": "ai_copilot", "target": "task_engine", "relation_type": "analyzes_defects", "severity_flow": "medium"},
            {"source": "ai_copilot", "target": "audit_logger", "relation_type": "traces_inference", "severity_flow": "low"},
        ],
    },
    "ecommerce": {
        "title": "E-Commerce & Retail Marketplace",
        "modules": [
            {
                "id": "storefront",
                "name": "Storefront & Mobile App",
                "category": "Frontend",
                "keywords": ["store", "shop", "app", "ui", "mobile", "web", "catalog", "browse", "product"],
            },
            {
                "id": "api_gateway",
                "name": "API Gateway & Edge Router",
                "category": "Infrastructure",
                "keywords": ["gateway", "api", "proxy", "ingress", "route", "endpoint", "network"],
            },
            {
                "id": "auth_accounts",
                "name": "Customer Accounts & Auth",
                "category": "Security",
                "keywords": ["auth", "login", "account", "user", "password", "token", "session", "profile", "customer"],
            },
            {
                "id": "product_catalog",
                "name": "Product Catalog & Search",
                "category": "Catalog",
                "keywords": ["product", "catalog", "item", "search", "inventory", "stock", "warehouse", "sku"],
            },
            {
                "id": "cart_checkout",
                "name": "Cart & Checkout Engine",
                "category": "Orders",
                "keywords": ["cart", "checkout", "basket", "order", "purchase", "buy", "transaction", "discount", "coupon"],
            },
            {
                "id": "payment_gateway",
                "name": "Payment Gateway & Billing",
                "category": "Finance",
                "keywords": ["payment", "stripe", "billing", "card", "invoice", "charge", "refund", "gateway", "currency"],
            },
            {
                "id": "order_fulfillment",
                "name": "Order Fulfillment & Delivery",
                "category": "Fulfillment",
                "keywords": ["fulfillment", "shipping", "tracking", "delivery", "courier", "package", "dispatch"],
            },
            {
                "id": "notifications",
                "name": "Receipts & Push Notifications",
                "category": "Messaging",
                "keywords": ["notification", "email", "sms", "receipt", "alert", "message", "push"],
            },
            {
                "id": "analytics",
                "name": "Sales Telemetry & Conversion",
                "category": "Analytics",
                "keywords": ["analytics", "telemetry", "conversion", "revenue", "metric", "report", "sales"],
            },
        ],
        "edges": [
            {"source": "storefront", "target": "api_gateway", "relation_type": "dispatches_requests", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "auth_accounts", "relation_type": "authenticates", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "product_catalog", "relation_type": "searches_items", "severity_flow": "high"},
            {"source": "api_gateway", "target": "cart_checkout", "relation_type": "routes_orders", "severity_flow": "critical"},
            {"source": "cart_checkout", "target": "product_catalog", "relation_type": "checks_stock", "severity_flow": "high"},
            {"source": "cart_checkout", "target": "auth_accounts", "relation_type": "verifies_buyer", "severity_flow": "critical"},
            {"source": "cart_checkout", "target": "payment_gateway", "relation_type": "processes_payment", "severity_flow": "critical"},
            {"source": "payment_gateway", "target": "order_fulfillment", "relation_type": "dispatches_order", "severity_flow": "high"},
            {"source": "payment_gateway", "target": "notifications", "relation_type": "sends_receipt", "severity_flow": "medium"},
            {"source": "order_fulfillment", "target": "notifications", "relation_type": "shipping_update", "severity_flow": "medium"},
            {"source": "cart_checkout", "target": "analytics", "relation_type": "tracks_conversion", "severity_flow": "low"},
        ],
    },
    "data_ai": {
        "title": "Data & AI Pipeline Platform",
        "modules": [
            {
                "id": "data_portal",
                "name": "Data Portal & Dashboards",
                "category": "Frontend",
                "keywords": ["portal", "dashboard", "ui", "viz", "chart", "graph", "view", "report"],
            },
            {
                "id": "api_gateway",
                "name": "API Gateway & Ingress",
                "category": "Infrastructure",
                "keywords": ["gateway", "api", "webhook", "ingress", "proxy", "route"],
            },
            {
                "id": "auth_iam",
                "name": "Access Control & IAM",
                "category": "Security",
                "keywords": ["auth", "iam", "token", "permission", "key", "role", "access"],
            },
            {
                "id": "ingestion_pipeline",
                "name": "Stream Ingestion & ETL",
                "category": "Data",
                "keywords": ["ingestion", "stream", "kafka", "etl", "source", "sync", "batch", "pipeline"],
            },
            {
                "id": "data_lake",
                "name": "Lakehouse & Feature Store",
                "category": "Storage",
                "keywords": ["storage", "lakehouse", "database", "vector", "s3", "bigquery", "postgres", "table"],
            },
            {
                "id": "query_engine",
                "name": "Query & Aggregation Engine",
                "category": "Compute",
                "keywords": ["query", "sql", "transform", "aggregation", "spark", "compute", "engine"],
            },
            {
                "id": "ml_inference",
                "name": "ML Model Inference & AI",
                "category": "AI / ML",
                "keywords": ["ml", "ai", "model", "inference", "llm", "embedding", "train", "prediction"],
            },
            {
                "id": "alerting_monitor",
                "name": "Anomaly Monitor & Alerts",
                "category": "Observability",
                "keywords": ["alert", "monitor", "anomaly", "sla", "paging", "notification"],
            },
            {
                "id": "telemetry",
                "name": "Data Lineage & Telemetry",
                "category": "Observability",
                "keywords": ["telemetry", "lineage", "metric", "log", "audit", "trace"],
            },
        ],
        "edges": [
            {"source": "data_portal", "target": "api_gateway", "relation_type": "submits_query", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "auth_iam", "relation_type": "verifies_token", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "query_engine", "relation_type": "executes_query", "severity_flow": "high"},
            {"source": "ingestion_pipeline", "target": "data_lake", "relation_type": "persists_stream", "severity_flow": "critical"},
            {"source": "query_engine", "target": "data_lake", "relation_type": "scans_tables", "severity_flow": "high"},
            {"source": "ml_inference", "target": "data_lake", "relation_type": "reads_features", "severity_flow": "high"},
            {"source": "query_engine", "target": "ml_inference", "relation_type": "invokes_scoring", "severity_flow": "medium"},
            {"source": "ingestion_pipeline", "target": "alerting_monitor", "relation_type": "sla_monitoring", "severity_flow": "high"},
            {"source": "query_engine", "target": "telemetry", "relation_type": "records_lineage", "severity_flow": "low"},
        ],
    },
    "social_community": {
        "title": "Social & Messaging Platform",
        "modules": [
            {
                "id": "client_app",
                "name": "Mobile & Web Client",
                "category": "Frontend",
                "keywords": ["client", "mobile", "ios", "android", "web", "app", "ui"],
            },
            {
                "id": "api_gateway",
                "name": "API Gateway & WebSockets",
                "category": "Infrastructure",
                "keywords": ["gateway", "api", "websocket", "ingress", "proxy"],
            },
            {
                "id": "auth_security",
                "name": "Auth & Account Security",
                "category": "Security",
                "keywords": ["auth", "login", "account", "user", "password", "token", "mfa"],
            },
            {
                "id": "user_graph",
                "name": "User Profiles & Social Graph",
                "category": "Core Logic",
                "keywords": ["profile", "friend", "follower", "graph", "relationship", "user"],
            },
            {
                "id": "feed_engine",
                "name": "Realtime Feed & Messaging",
                "category": "Messaging",
                "keywords": ["feed", "chat", "message", "stream", "channel", "post", "comment"],
            },
            {
                "id": "media_cdn",
                "name": "Media Upload & CDN",
                "category": "Storage",
                "keywords": ["media", "video", "photo", "image", "upload", "cdn", "s3"],
            },
            {
                "id": "search_discovery",
                "name": "Search & Recommendations",
                "category": "Discovery",
                "keywords": ["search", "discovery", "explore", "trending", "recommendation"],
            },
            {
                "id": "push_service",
                "name": "Push Notification Dispatcher",
                "category": "Messaging",
                "keywords": ["push", "notification", "alert", "badge", "email"],
            },
            {
                "id": "moderation",
                "name": "Safety & Content Moderation",
                "category": "Security",
                "keywords": ["moderation", "safety", "filter", "report", "abuse", "flag"],
            },
            {
                "id": "analytics",
                "name": "Engagement Telemetry",
                "category": "Analytics",
                "keywords": ["analytics", "telemetry", "engagement", "retention", "metric"],
            },
        ],
        "edges": [
            {"source": "client_app", "target": "api_gateway", "relation_type": "dispatches_requests", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "auth_security", "relation_type": "authenticates", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "feed_engine", "relation_type": "streams_feed", "severity_flow": "critical"},
            {"source": "feed_engine", "target": "user_graph", "relation_type": "resolves_network", "severity_flow": "high"},
            {"source": "feed_engine", "target": "media_cdn", "relation_type": "fetches_media", "severity_flow": "high"},
            {"source": "feed_engine", "target": "moderation", "relation_type": "screens_content", "severity_flow": "high"},
            {"source": "feed_engine", "target": "push_service", "relation_type": "triggers_alerts", "severity_flow": "medium"},
            {"source": "api_gateway", "target": "search_discovery", "relation_type": "discovers_posts", "severity_flow": "medium"},
            {"source": "feed_engine", "target": "analytics", "relation_type": "logs_interactions", "severity_flow": "low"},
        ],
    },
    "devops_infra": {
        "title": "DevOps & Cloud Infrastructure",
        "modules": [
            {
                "id": "cli_console",
                "name": "CLI & Management Console",
                "category": "Client",
                "keywords": ["cli", "console", "terminal", "web", "ui", "sdk", "client"],
            },
            {
                "id": "api_gateway",
                "name": "Control Plane Gateway",
                "category": "Infrastructure",
                "keywords": ["gateway", "api", "control_plane", "ingress", "proxy"],
            },
            {
                "id": "auth_vault",
                "name": "Auth & Secret Vault",
                "category": "Security",
                "keywords": ["auth", "vault", "secret", "token", "cert", "key", "iam"],
            },
            {
                "id": "runner_engine",
                "name": "Execution Engine & Runners",
                "category": "Compute",
                "keywords": ["runner", "job", "build", "ci/cd", "pipeline", "execution", "task"],
            },
            {
                "id": "artifact_registry",
                "name": "Artifact & Package Registry",
                "category": "Storage",
                "keywords": ["artifact", "registry", "package", "docker", "image", "bundle"],
            },
            {
                "id": "cluster_agent",
                "name": "Cluster & Node Agents",
                "category": "Infrastructure",
                "keywords": ["agent", "node", "cluster", "kubernetes", "k8s", "worker", "pod"],
            },
            {
                "id": "webhook_dispatcher",
                "name": "Webhook & Slack Dispatcher",
                "category": "Messaging",
                "keywords": ["webhook", "event", "dispatcher", "slack", "hook", "alert"],
            },
            {
                "id": "observability",
                "name": "Logs, Traces & Telemetry",
                "category": "Observability",
                "keywords": ["observability", "log", "trace", "metric", "grafana", "telemetry"],
            },
        ],
        "edges": [
            {"source": "cli_console", "target": "api_gateway", "relation_type": "commands", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "auth_vault", "relation_type": "authorizes", "severity_flow": "critical"},
            {"source": "api_gateway", "target": "runner_engine", "relation_type": "dispatches_jobs", "severity_flow": "critical"},
            {"source": "runner_engine", "target": "auth_vault", "relation_type": "fetches_secrets", "severity_flow": "high"},
            {"source": "runner_engine", "target": "artifact_registry", "relation_type": "pushes_artifacts", "severity_flow": "high"},
            {"source": "runner_engine", "target": "cluster_agent", "relation_type": "deploys_workloads", "severity_flow": "high"},
            {"source": "runner_engine", "target": "webhook_dispatcher", "relation_type": "notifies_completion", "severity_flow": "medium"},
            {"source": "cluster_agent", "target": "observability", "relation_type": "streams_telemetry", "severity_flow": "low"},
        ],
    },
}


DIRECTIONAL_FAILURE_PATTERNS: dict[tuple[str, str], str] = {
    # SaaS & Workflow
    ("auth_rbac", "api_gateway"): "Invalidates JWT token verification, triggering 401 unauthenticated request drops for incoming web clients.",
    ("auth_rbac", "task_engine"): "Blocks role-based permission checks, preventing users from creating, updating, or transitioning task states.",
    ("api_gateway", "client_dashboard"): "Causes HTTP 502/504 gateway timeouts and breaks UI rendering of workspace views.",
    ("api_gateway", "auth_rbac"): "Prevents ingress gateway from forwarding login credentials to authentication provider.",
    ("api_gateway", "task_engine"): "Halts task API routing, causing defect board sync failures across connected clients.",
    ("api_gateway", "sprint_analytics"): "Blocks velocity metric query forwarding, causing empty sprint analytics widgets.",
    ("api_gateway", "ai_copilot"): "Blocks copilot query routing, disabling AI mentor suggestions and assistant responses.",
    ("task_engine", "auth_rbac"): "Fails permission check handshakes, causing unauthorized role escalation risks.",
    ("task_engine", "attachment_store"): "Prevents file upload attachments from linking to defect tickets.",
    ("task_engine", "notification_service"): "Halts real-time WebSocket event dispatch and email notifications for bug state updates.",
    ("task_engine", "audit_logger"): "Drops audit log records for ticket state changes and user mutations.",
    ("sprint_analytics", "task_engine"): "Skews velocity calculation and burndown trajectory charts due to broken backlog queries.",
    ("ai_copilot", "task_engine"): "Denies AI copilot access to ticket history, disabling smart defect triage and auto-classification.",
    ("ai_copilot", "audit_logger"): "Fails AI telemetry and model inference audit logging.",

    # E-Commerce
    ("storefront", "api_gateway"): "Causes mobile and web client drop-offs during page load and catalog navigation.",
    ("api_gateway", "auth_accounts"): "Prevents customer sign-in and session token refresh on edge routers.",
    ("api_gateway", "product_catalog"): "Fails search queries and category listing on customer storefront.",
    ("api_gateway", "cart_checkout"): "Blocks checkout payload submission and order creation requests.",
    ("cart_checkout", "product_catalog"): "Prevents real-time inventory and stock validation before payment.",
    ("cart_checkout", "auth_accounts"): "Fails buyer identity and saved payment profile verification.",
    ("cart_checkout", "payment_gateway"): "Stalls transaction submission and triggers payment gateway timeout exceptions.",
    ("payment_gateway", "order_fulfillment"): "Blocks invoice generation and delays automatic dispatch of shipping fulfillment orders.",
    ("payment_gateway", "notifications"): "Suppresses order confirmation emails and digital receipt notifications.",
    ("order_fulfillment", "notifications"): "Suppresses parcel tracking numbers and delivery status notifications.",
    ("cart_checkout", "analytics"): "Disrupts sales conversion telemetry and revenue reporting dashboards.",

    # Data & AI
    ("data_portal", "api_gateway"): "Fails dashboard telemetry data fetching and query dashboard widgets.",
    ("api_gateway", "auth_iam"): "Rejects authenticated dataset ingestion and API query requests with 403 Forbidden.",
    ("api_gateway", "query_engine"): "Blocks distributed SQL and aggregation query submissions.",
    ("ingestion_pipeline", "data_lake"): "Halts streaming ingestion; accumulates backpressure and uncommitted partition lag.",
    ("query_engine", "data_lake"): "Blocks distributed SQL query execution across table partitions.",
    ("ml_inference", "data_lake"): "Starves machine learning inference pipelines of live feature vectors.",
    ("query_engine", "ml_inference"): "Fails real-time scoring and model prediction transformations.",
    ("ingestion_pipeline", "alerting_monitor"): "Triggers false-positive anomaly alerts and paging alarms.",
    ("query_engine", "telemetry"): "Disrupts data lineage tracking and audit trail generation.",

    # Social & Messaging
    ("client_app", "api_gateway"): "Fails mobile client feed polling and WebSocket handshake requests.",
    ("api_gateway", "auth_security"): "Prevents user credential validation and account security screening.",
    ("api_gateway", "feed_engine"): "Interrupts real-time feed streaming and channel message dispatches.",
    ("feed_engine", "user_graph"): "Fails to resolve social graph relationships, friendships, and follower feeds.",
    ("feed_engine", "media_cdn"): "Fails media uploads and image preview rendering in channel feeds.",
    ("feed_engine", "moderation"): "Bypasses automated safety filters and abuse screening.",
    ("feed_engine", "push_service"): "Suppresses push notifications for direct messages and mentions.",
    ("api_gateway", "search_discovery"): "Fails search indexing and trending content recommendation.",
    ("feed_engine", "analytics"): "Drops engagement telemetry and user activity event tracking.",

    # DevOps & Infra
    ("cli_console", "api_gateway"): "Fails CLI commands and deployment trigger requests.",
    ("api_gateway", "auth_vault"): "Denies authorization for CLI commands and control-plane management.",
    ("api_gateway", "runner_engine"): "Blocks build runner job dispatch and pipeline orchestration.",
    ("runner_engine", "auth_vault"): "Prevents build runners from fetching deployment secrets and TLS certs.",
    ("runner_engine", "artifact_registry"): "Blocks pushing and tagging container images and build bundles.",
    ("runner_engine", "cluster_agent"): "Halts rolling deployments to Kubernetes worker nodes.",
    ("runner_engine", "webhook_dispatcher"): "Suppresses CI/CD completion webhooks and Slack notifications.",
    ("cluster_agent", "observability"): "Interrupts telemetry streaming and node health metrics to Grafana.",
}


def detect_project_domain(project_name: str, project_desc: str | None, issues: list[Issue]) -> str:
    """Intelligently detect project domain archetype from project metadata and issue context."""
    text_corpus = f"{project_name} {project_desc or ''} " + " ".join(
        f"{i.module or ''} {i.category or ''} {i.title} {i.description or ''}" for i in issues[:35]
    ).lower()

    scores = {
        "ecommerce": sum(text_corpus.count(w) for w in ["shop", "store", "cart", "checkout", "product", "retail", "payment", "stripe", "billing", "order", "inventory", "purchase"]),
        "data_ai": sum(text_corpus.count(w) for w in ["pipeline", "data", "ml", "ai", "model", "analytics", "lakehouse", "dataset", "etl", "inference", "training", "bigquery"]),
        "social_community": sum(text_corpus.count(w) for w in ["social", "chat", "message", "feed", "friend", "follower", "media", "stream", "video", "post", "channel"]),
        "devops_infra": sum(text_corpus.count(w) for w in ["deploy", "ci/cd", "kubernetes", "docker", "cluster", "runner", "infra", "cli", "devops", "cloud", "agent", "vault"]),
        "saas_workflow": sum(text_corpus.count(w) for w in ["bug", "defect", "task", "workflow", "ticket", "sprint", "kanban", "dashboard", "jira", "crm", "project", "workspace", "lead", "burndown", "auth", "user", "file", "attachment", "pdf"]) + 3,
    }

    if scores["ecommerce"] >= 8 and scores["ecommerce"] > scores["saas_workflow"]:
        return "ecommerce"
    elif scores["data_ai"] >= 5 and scores["data_ai"] > scores["saas_workflow"]:
        return "data_ai"
    elif scores["social_community"] >= 5 and scores["social_community"] > scores["saas_workflow"]:
        return "social_community"
    elif scores["devops_infra"] >= 5 and scores["devops_infra"] > scores["saas_workflow"]:
        return "devops_infra"
    
    return "saas_workflow"


MODULE_ALIAS_MAP: dict[str, list[str]] = {
    # Auth & Security
    "auth_rbac": ["auth", "authentication", "login", "signup", "register", "rbac", "jwt", "token", "password", "permission", "roles", "session", "oauth", "security", "credentials", "access control", "unauthorized", "forbidden"],
    "auth_accounts": ["auth", "authentication", "account", "login", "signup", "user", "password", "session", "profile", "customer", "buyer", "member"],
    "auth_iam": ["auth", "iam", "token", "permission", "key", "role", "access", "credentials", "privilege"],
    "auth_security": ["auth", "security", "login", "password", "session", "token", "privacy", "block", "ban", "moderation"],
    "auth_vault": ["auth", "vault", "secrets", "iam", "keys", "certificate", "credentials", "token lease"],

    # Client / UI / Frontend
    "client_dashboard": ["dashboard", "ui", "frontend", "react", "view", "page", "modal", "css", "layout", "render", "button", "kanban", "table", "dropdown", "navbar", "sidebar", "theme", "dark mode", "light mode", "client", "interface", "display"],
    "storefront": ["storefront", "store", "shop", "browse", "catalog", "cart", "product", "mobile app", "ui", "frontend", "app"],
    "data_portal": ["data portal", "portal", "dashboard", "ui", "viz", "chart", "graph", "view", "report"],
    "client_app": ["client app", "client", "app", "mobile", "ios", "android", "web", "ui", "feed"],
    "cli_console": ["cli", "console", "terminal", "command", "shell", "ui"],

    # API Gateway
    "api_gateway": ["api gateway", "gateway", "api", "ingress", "proxy", "route", "endpoint", "cors", "network", "server", "http", "timeout", "rest", "router", "load balancer", "500", "502", "504"],

    # Workflow & Core Engine
    "task_engine": ["task", "defect", "issue", "bug", "workflow", "ticket", "engine", "status", "transition", "crud", "board", "backlog", "priority", "severity", "lifecycle", "assign", "resolution"],
    "cart_checkout": ["cart", "checkout", "basket", "order", "purchase", "buy", "coupon", "discount", "transaction"],
    "ingestion_pipeline": ["ingestion", "stream", "kafka", "etl", "sync", "batch", "pipeline", "extractor"],
    "feed_engine": ["feed", "timeline", "stream", "post", "social", "stories", "channel"],
    "runner_engine": ["runner", "pipeline", "build", "ci/cd", "job", "worker", "execution", "action"],

    # Metrics / Analytics
    "sprint_analytics": ["sprint", "analytics", "burndown", "velocity", "metrics", "chart", "report", "stats", "graph", "mttr", "resolution time", "kpi", "calculation", "trend", "summary"],
    "analytics": ["analytics", "conversion", "sales", "revenue", "telemetry", "metric", "report", "stats"],
    "query_engine": ["query", "sql", "spark", "aggregation", "compute", "engine", "transform"],
    "telemetry": ["telemetry", "lineage", "metric", "log", "audit", "trace", "observability"],

    # Storage / Assets
    "attachment_store": ["attachment", "file", "upload", "download", "pdf", "s3", "storage", "asset", "document", "image", "blob", "avatar", "file size", "export"],
    "data_lake": ["data lake", "lakehouse", "feature store", "database", "vector", "s3", "bigquery", "postgres", "table", "storage"],
    "media_cdn": ["media", "cdn", "image", "video", "asset", "blob", "storage", "photos"],
    "artifact_registry": ["artifact", "docker", "registry", "image", "package", "helm", "repo"],

    # Notifications & Alerts
    "notification_service": ["notification", "alert", "email", "push", "message", "webhook", "subscriber", "event", "websocket", "socket", "drawer", "bell", "inbox", "notify"],
    "notifications": ["notification", "email", "sms", "receipt", "alert", "message", "push"],
    "push_service": ["push", "fcm", "apns", "notification", "inbox", "message"],
    "alerting_monitor": ["alert", "monitor", "anomaly", "sla", "paging", "notification"],
    "webhook_dispatcher": ["webhook", "event", "dispatcher", "pubsub", "queue", "listener"],

    # AI / Copilot
    "ai_copilot": ["ai", "copilot", "mentor", "llm", "classify", "predict", "chat", "suggestion", "bot", "assistant", "model", "prompt", "gemini", "intelligence", "semantic search", "duplicate", "blast radius", "summary", "recommendation"],
    "ml_inference": ["ml", "ai", "model", "inference", "llm", "embedding", "train", "prediction"],

    # Compliance / Audit / Infra
    "audit_logger": ["audit", "log", "activity", "history", "telemetry", "trace", "event", "security", "trail", "timeline", "ledger"],
    "order_fulfillment": ["fulfillment", "shipping", "tracking", "delivery", "courier", "package", "dispatch"],
    "payment_gateway": ["payment", "stripe", "billing", "card", "invoice", "charge", "refund", "gateway", "currency", "checkout"],
    "product_catalog": ["product", "catalog", "item", "search", "inventory", "stock", "warehouse", "sku"],
    "cluster_agent": ["cluster", "kubernetes", "agent", "pod", "node", "daemon", "server"],
    "observability": ["observability", "metrics", "prometheus", "grafana", "logs", "traces", "health"],
    "moderation": ["moderation", "filter", "spam", "safety", "trust", "abuse"],
}


def _match_module_id_with_confidence(issue: Issue, module_templates: list[dict[str, Any]]) -> tuple[str, int, str]:
    """
    Classify an issue to a module ID from the active blueprint using multi-attribute weighted scoring.
    Returns: (module_id, confidence_percentage, human_readable_allocation_reason)
    """
    tmpl_map = {t["id"]: t for t in module_templates}

    best_id = None
    best_score = 0
    best_reasons = []

    issue_mod = (issue.module or "").strip().lower()
    issue_cat = (issue.category or "").strip().lower()
    issue_type = (issue.defect_type or "").strip().lower()
    issue_title = (issue.title or "").strip().lower()
    issue_desc = (issue.description or "").strip().lower()
    issue_steps = (issue.steps_to_reproduce or "").strip().lower()
    issue_actual = (issue.actual_behavior or "").strip().lower()

    title_words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", issue_title))
    body_text = f"{issue_desc} {issue_steps} {issue_actual}"
    body_words = set(re.findall(r"\b[a-zA-Z0-9_-]+\b", body_text))

    for tmpl in module_templates:
        score = 0
        reasons = []
        tmpl_id = tmpl["id"]
        tmpl_name = tmpl["name"].lower()
        tmpl_cat = tmpl["category"].lower()
        keywords = tmpl.get("keywords", [])
        aliases = MODULE_ALIAS_MAP.get(tmpl_id, [])

        # 1. Direct match on issue.module field (highest weight)
        if issue_mod:
            if tmpl_id == issue_mod or issue_mod in tmpl_id or tmpl_name in issue_mod or issue_mod in tmpl_name:
                score += 60
                reasons.append(f"Module match '{issue.module}'")
            else:
                for alias in aliases:
                    if alias in issue_mod or issue_mod in alias:
                        score += 50
                        reasons.append(f"Module alias '{issue.module}' -> '{alias}'")
                        break

        # 2. Match on issue.category field
        if issue_cat:
            if tmpl_cat in issue_cat or issue_cat in tmpl_cat or tmpl_id in issue_cat:
                score += 35
                reasons.append(f"Category '{issue.category}'")
            else:
                for alias in aliases:
                    if alias == issue_cat or (len(alias) >= 4 and alias in issue_cat):
                        score += 25
                        reasons.append(f"Category '{issue.category}'")
                        break

        # 3. Match on issue.defect_type field
        if issue_type:
            if "security" in issue_type and "auth" in tmpl_id:
                score += 20
                reasons.append("Security defect type")
            elif ("ui" in issue_type or "ux" in issue_type) and ("dashboard" in tmpl_id or "storefront" in tmpl_id or "client" in tmpl_id or "portal" in tmpl_id):
                score += 20
                reasons.append("UI/UX defect type")
            elif "performance" in issue_type and ("gateway" in tmpl_id or "engine" in tmpl_id):
                score += 15
                reasons.append("Performance defect type")

        # 4. Keyword matches in Title (High weight)
        matched_title_kws = []
        for kw in (keywords + aliases[:6]):
            kw_clean = kw.lower()
            if " " in kw_clean:
                if kw_clean in issue_title:
                    score += 15
                    matched_title_kws.append(kw_clean)
            elif kw_clean in title_words:
                score += 12
                matched_title_kws.append(kw_clean)

        if matched_title_kws:
            reasons.append(f"Title keywords ({', '.join(matched_title_kws[:3])})")

        # 5. Keyword matches in Description / Steps / Actual behavior
        matched_body_kws = []
        for kw in keywords:
            kw_clean = kw.lower()
            if " " in kw_clean:
                if kw_clean in body_text:
                    score += 6
                    matched_body_kws.append(kw_clean)
            elif kw_clean in body_words:
                score += 5
                matched_body_kws.append(kw_clean)

        if matched_body_kws and not matched_title_kws:
            reasons.append(f"Content keywords ({', '.join(matched_body_kws[:2])})")

        if score > best_score:
            best_score = score
            best_id = tmpl_id
            best_reasons = reasons

    if best_id and best_score >= 50:
        conf = 98
    elif best_id and best_score >= 25:
        conf = 92
    elif best_id and best_score >= 10:
        conf = 85
    elif best_id:
        conf = 78
    else:
        # Fallback to second module (often core/task engine) or first
        fallback_id = module_templates[1]["id"] if len(module_templates) > 1 else module_templates[0]["id"]
        return fallback_id, 70, "Allocated to primary core workflow engine by default"

    matched_tmpl = tmpl_map.get(best_id, {})
    mod_display_name = matched_tmpl.get("name", best_id.replace("_", " ").title())

    if best_reasons:
        reason_text = f"Allocated to {mod_display_name} via {', '.join(best_reasons[:2])}."
    else:
        reason_text = f"Allocated to {mod_display_name} based on architectural workflow patterns."

    return best_id, conf, reason_text


def _match_module_id(issue: Issue, module_templates: list[dict[str, Any]]) -> str:
    """Convenience wrapper for matching module ID."""
    m_id, _, _ = _match_module_id_with_confidence(issue, module_templates)
    return m_id


def _generate_caused_issue_description(
    source_module_id: str,
    target_module_id: str,
    source_name: str,
    target_name: str,
    relation_type: str,
    impact_level: str,
) -> str:
    """Synthesize precise, domain-aware operational problem description caused in target module."""
    key = (source_module_id, target_module_id)
    if key in DIRECTIONAL_FAILURE_PATTERNS:
        desc = DIRECTIONAL_FAILURE_PATTERNS[key]
        if impact_level == "cascade_risk":
            return f"Secondary ripple: {desc}"
        return desc

    rev_key = (target_module_id, source_module_id)
    if rev_key in DIRECTIONAL_FAILURE_PATTERNS:
        desc = DIRECTIONAL_FAILURE_PATTERNS[rev_key]
        return f"Compromises upstream communication with '{target_name}': {desc}"

    rel_name = relation_type.replace("_", " ")
    if impact_level == "direct_impact":
        return f"Directly disrupts '{target_name}' communication during '{rel_name}'; risks latency spike or request drops."
    else:
        return f"Downstream cascading risk: '{target_name}' experiences degraded throughput and transient dependencies via '{source_name}'."


def _generate_defect_containment_advice(module_id: str, module_name: str, severity: IssueSeverity | str) -> str:
    """Produce immediate containment action tailored for a single defect."""
    sev_str = str(severity).lower()
    if "critical" in sev_str:
        return f"🚨 Immediate Circuit Breaker: Isolate {module_name} with fallback read cache and rate-limit upstream traffic until hotfix lands."
    elif "high" in sev_str:
        return f"🛡️ Defensive Retry Guard: Apply exponential backoff between {module_name} and connected callers to prevent cascading thread exhaustion."
    elif "medium" in sev_str:
        return f"⚡ Queue Decoupling: Buffer downstream mutations from {module_name} to async dead-letter queue."
    else:
        return f"🔍 Telemetry Sampling: Enable high-fidelity error tracing on {module_name} to track non-blocking anomalies."


def compute_all_defect_allocations(
    issues: list[Issue],
    base_module_templates: list[dict[str, Any]],
    base_edges: list[dict[str, Any]],
    domain_key: str,
) -> list[DefectAllocation]:
    """Autonomously allocate every defect to its host module and calculate downstream issues it causes."""
    module_name_map = {m["id"]: m["name"] for m in base_module_templates}

    # Precompute module -> defect_ids mapping
    module_defects_map: dict[str, list[int]] = {m["id"]: [] for m in base_module_templates}
    for iss in issues:
        if iss.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]:
            m_id = _match_module_id(iss, base_module_templates)
            if m_id in module_defects_map:
                module_defects_map[m_id].append(iss.id)

    allocations: list[DefectAllocation] = []

    for issue in issues:
        m_id, confidence, alloc_reason = _match_module_id_with_confidence(issue, base_module_templates)
        m_name = module_name_map.get(m_id, m_id.replace("_", " ").title())

        # 1st Degree Direct Dependents
        direct_modules: set[str] = set()
        direct_relations: dict[str, str] = {}
        for e in base_edges:
            if e["target"] == m_id:
                direct_modules.add(e["source"])
                direct_relations[e["source"]] = e["relation_type"]
            elif e["source"] == m_id:
                direct_modules.add(e["target"])
                direct_relations[e["target"]] = e["relation_type"]

        # 2nd Degree Cascade Dependents
        cascade_modules: set[str] = set()
        cascade_relations: dict[str, str] = {}
        for d in direct_modules:
            for e in base_edges:
                if e["target"] == d and e["source"] != m_id and e["source"] not in direct_modules:
                    cascade_modules.add(e["source"])
                    cascade_relations[e["source"]] = e["relation_type"]
                elif e["source"] == d and e["target"] != m_id and e["target"] not in direct_modules:
                    cascade_modules.add(e["target"])
                    cascade_relations[e["target"]] = e["relation_type"]

        # Build CausedIssueDetail list
        caused_issues: list[CausedIssueDetail] = []

        for tgt_id in sorted(list(direct_modules)):
            tgt_name = module_name_map.get(tgt_id, tgt_id.replace("_", " ").title())
            rel = direct_relations.get(tgt_id, "depends_on")
            desc = _generate_caused_issue_description(m_id, tgt_id, m_name, tgt_name, rel, "direct_impact")
            other_defects = [did for did in module_defects_map.get(tgt_id, []) if did != issue.id]
            caused_issues.append(CausedIssueDetail(
                target_module_id=tgt_id,
                target_module_name=tgt_name,
                impact_level="direct_impact",
                failure_description=desc,
                affected_defect_ids=other_defects,
            ))

        for tgt_id in sorted(list(cascade_modules)):
            tgt_name = module_name_map.get(tgt_id, tgt_id.replace("_", " ").title())
            rel = cascade_relations.get(tgt_id, "depends_on")
            desc = _generate_caused_issue_description(m_id, tgt_id, m_name, tgt_name, rel, "cascade_risk")
            other_defects = [did for did in module_defects_map.get(tgt_id, []) if did != issue.id]
            caused_issues.append(CausedIssueDetail(
                target_module_id=tgt_id,
                target_module_name=tgt_name,
                impact_level="cascade_risk",
                failure_description=desc,
                affected_defect_ids=other_defects,
            ))

        direct_names = [module_name_map.get(d, d) for d in sorted(list(direct_modules))]
        cascade_names = [module_name_map.get(c, c) for c in sorted(list(cascade_modules))]
        advice = _generate_defect_containment_advice(m_id, m_name, issue.severity)

        allocations.append(DefectAllocation(
            defect_id=issue.id,
            title=issue.title,
            severity=issue.severity.value if hasattr(issue.severity, "value") else str(issue.severity),
            status=issue.status.value if hasattr(issue.status, "value") else str(issue.status),
            allocated_module_id=m_id,
            allocated_module_name=m_name,
            allocation_confidence=confidence,
            allocation_reason=alloc_reason,
            direct_impact_count=len(direct_modules),
            cascade_risk_count=len(cascade_modules),
            direct_impact_module_names=direct_names,
            cascade_risk_module_names=cascade_names,
            caused_issues=caused_issues,
            containment_advice=advice,
        ))

    return allocations


def compute_project_blast_radius(
    project_id: int,
    db: Session,
    focused_issue_id: int | None = None,
    domain_override: str | None = None,
) -> BlastRadiusReport:
    """Compute module dependency topology, failure blast radius, and AI containment advice for any project domain."""
    project = db.query(Project).options(
        joinedload(Project.issues).joinedload(Issue.assigned_developer),
        joinedload(Project.issues).joinedload(Issue.reporter),
    ).filter(Project.id == project_id).first()

    if not project:
        return BlastRadiusReport(
            project_id=project_id,
            project_name="Unknown Project",
            system_blast_score=0,
            overall_status="Operational",
            domain_archetype="General Application",
            available_archetypes=AVAILABLE_ARCHETYPES,
            estimated_user_impact="Project not found.",
            containment_strategies=["Ensure project ID is valid."],
            nodes=[],
            edges=[],
            defect_allocations=[],
            auto_allocated_summary="No project found.",
            total_defects_analyzed=0,
        )

    issues = project.issues

    # 1. Determine active domain blueprint
    active_domain_key = domain_override if domain_override and domain_override in DOMAIN_BLUEPRINTS else None
    if not active_domain_key:
        active_domain_key = detect_project_domain(project.name, project.description, issues)

    blueprint = DOMAIN_BLUEPRINTS.get(active_domain_key, DOMAIN_BLUEPRINTS["saas_workflow"])
    domain_title = blueprint["title"]
    base_module_templates = list(blueprint["modules"])
    base_edges = list(blueprint["edges"])

    # 2. Compute Autonomous Defect Allocations for all issues in project
    defect_allocations = compute_all_defect_allocations(issues, base_module_templates, base_edges, active_domain_key)

    # 3. Aggregate module statistics & map all issues
    module_data: dict[str, dict[str, Any]] = {
        t["id"]: {
            "id": t["id"],
            "name": t["name"],
            "category": t["category"],
            "open_defects": 0,
            "critical_defects": 0,
            "developers": set(),
            "defect_ids": [],
        }
        for t in base_module_templates
    }

    open_issues = [i for i in issues if i.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]]

    for issue in issues:
        m_id = _match_module_id(issue, base_module_templates)
        if m_id not in module_data:
            m_id = base_module_templates[0]["id"]

        module_data[m_id]["defect_ids"].append(issue.id)
        if issue.status in [IssueStatus.OPEN, IssueStatus.IN_PROGRESS, IssueStatus.IN_REVIEW]:
            module_data[m_id]["open_defects"] += 1
            if issue.severity in [IssueSeverity.CRITICAL, IssueSeverity.HIGH]:
                module_data[m_id]["critical_defects"] += 1

        if issue.assigned_developer:
            module_data[m_id]["developers"].add(issue.assigned_developer.username)

    # 4. Determine Active Epicenters & Graph Traversal
    focused_issue: Issue | None = None
    if focused_issue_id:
        focused_issue = next((i for i in issues if i.id == focused_issue_id), None)

    direct_dependents: set[str] = set()
    cascade_dependents: set[str] = set()
    active_edge_keys: set[str] = set()
    epicenter_module_ids: set[str] = set()

    if focused_issue:
        # Scoped to single defect
        epicenter_id = _match_module_id(focused_issue, base_module_templates)
        epicenter_module_ids.add(epicenter_id)

        # 1st Degree
        for e in base_edges:
            if e["target"] == epicenter_id:
                direct_dependents.add(e["source"])
                active_edge_keys.add(f"{e['source']}->{e['target']}")
            elif e["source"] == epicenter_id:
                direct_dependents.add(e["target"])
                active_edge_keys.add(f"{e['source']}->{e['target']}")

        # 2nd Degree
        for direct_node in list(direct_dependents):
            for e in base_edges:
                if e["target"] == direct_node and e["source"] != epicenter_id and e["source"] not in direct_dependents:
                    cascade_dependents.add(e["source"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")
                elif e["source"] == direct_node and e["target"] != epicenter_id and e["target"] not in direct_dependents:
                    cascade_dependents.add(e["target"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")
    else:
        # Autonomous Full-Project Multi-Defect Mode
        for m_id, data in module_data.items():
            if data["open_defects"] > 0:
                epicenter_module_ids.add(m_id)

        # Direct dependents of any epicenter
        for epic in epicenter_module_ids:
            for e in base_edges:
                if e["target"] == epic:
                    if e["source"] not in epicenter_module_ids:
                        direct_dependents.add(e["source"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")
                elif e["source"] == epic:
                    if e["target"] not in epicenter_module_ids:
                        direct_dependents.add(e["target"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")

        # Cascade dependents of direct dependents
        for direct_node in list(direct_dependents):
            for e in base_edges:
                if e["target"] == direct_node and e["source"] not in epicenter_module_ids and e["source"] not in direct_dependents:
                    cascade_dependents.add(e["source"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")
                elif e["source"] == direct_node and e["target"] not in epicenter_module_ids and e["target"] not in direct_dependents:
                    cascade_dependents.add(e["target"])
                    active_edge_keys.add(f"{e['source']}->{e['target']}")

    # 5. Build Module Nodes
    nodes: list[ModuleNode] = []
    for m_id, data in module_data.items():
        is_epicenter = (m_id in epicenter_module_ids)

        if is_epicenter:
            blast_zone = "epicenter"
        elif m_id in direct_dependents:
            blast_zone = "direct_impact"
        elif m_id in cascade_dependents:
            blast_zone = "cascade_risk"
        else:
            blast_zone = "safe"

        health = max(15, 100 - (data["critical_defects"] * 30 + data["open_defects"] * 12))
        if is_epicenter and data["critical_defects"] > 0:
            health = min(health, 25)

        risk_tier = "Critical" if (is_epicenter and data["critical_defects"] > 0 or health < 45) else ("High" if health < 65 else ("Medium" if health < 85 else "Low"))

        nodes.append(ModuleNode(
            id=m_id,
            name=data["name"],
            category=data["category"],
            open_defects_count=data["open_defects"],
            critical_defects_count=data["critical_defects"],
            health_score=health,
            risk_tier=risk_tier,
            assigned_developers=sorted(list(data["developers"])),
            is_epicenter=is_epicenter,
            blast_zone=blast_zone,
            defect_ids=data["defect_ids"],
        ))

    # 6. Build Dependency Edges
    edges: list[DependencyEdge] = []
    for e in base_edges:
        edge_key = f"{e['source']}->{e['target']}"
        is_active = edge_key in active_edge_keys

        severity_flow = e["severity_flow"]
        if is_active:
            if (e["source"] in epicenter_module_ids) or (e["target"] in epicenter_module_ids):
                severity_flow = "critical"
            else:
                severity_flow = "high"

        edges.append(DependencyEdge(
            source=e["source"],
            target=e["target"],
            relation_type=e["relation_type"],
            severity_flow=severity_flow,
            is_active_impact_path=is_active,
        ))

    # 7. Calculate System Blast Score
    if focused_issue:
        if focused_issue.severity == IssueSeverity.CRITICAL:
            sev_weight = 50
        elif focused_issue.severity == IssueSeverity.HIGH:
            sev_weight = 35
        elif focused_issue.severity == IssueSeverity.MEDIUM:
            sev_weight = 20
        else:
            sev_weight = 10
        total_blast = min(100, sev_weight + len(direct_dependents) * 12 + len(cascade_dependents) * 6)
    else:
        critical_count = sum(1 for i in open_issues if i.severity == IssueSeverity.CRITICAL)
        high_count = sum(1 for i in open_issues if i.severity == IssueSeverity.HIGH)
        med_count = sum(1 for i in open_issues if i.severity == IssueSeverity.MEDIUM)

        if not open_issues:
            total_blast = 0
        else:
            base_score = min(55, critical_count * 25 + high_count * 15 + med_count * 8)
            propagation_score = len(direct_dependents) * 10 + len(cascade_dependents) * 5
            total_blast = min(100, base_score + propagation_score)

    if total_blast >= 75:
        overall_status = "Critical Cascade"
    elif total_blast >= 50:
        overall_status = "Degraded Flow"
    elif total_blast >= 25:
        overall_status = "Elevated Risk"
    else:
        overall_status = "Operational"

    # 8. User Impact & Containment Strategies
    direct_names = [module_data[d]["name"] for d in direct_dependents if d in module_data]
    cascade_names = [module_data[c]["name"] for c in cascade_dependents if c in module_data]
    epicenter_names = [module_data[ep]["name"] for ep in epicenter_module_ids if ep in module_data]

    if focused_issue:
        epicenter_label = module_data[list(epicenter_module_ids)[0]]["name"] if epicenter_module_ids else "System Core"
        estimated_user_impact = (
            f"Failure in '{epicenter_label}' directly threatens {len(direct_dependents)} connected services "
            f"({', '.join(direct_names[:3]) or 'None'}). "
            f"Cascading failure risk propagates downstream to {len(cascade_dependents)} secondary systems in the {domain_title} topology. "
            f"Immediate isolation recommended to prevent systemic service disruption."
        )
    elif open_issues:
        estimated_user_impact = (
            f"Autonomous architectural scan identified {len(open_issues)} active defect(s) across {len(epicenter_module_ids)} origin module(s) "
            f"({', '.join(epicenter_names[:3]) or 'None'}). "
            f"Propagating ripple threatens {len(direct_dependents)} direct dependent services and {len(cascade_dependents)} cascading components."
        )
    else:
        estimated_user_impact = f"All monitored services in {domain_title} operating within nominal latency and stability thresholds. Zero open defects detected."

    auto_allocated_summary = (
        f"Autonomous AI allocation evaluated {len(issues)} defect(s). {len(epicenter_module_ids)} architectural module(s) currently host active defects, "
        f"creating direct failure exposure for {len(direct_dependents)} connected service(s) and cascading risk for {len(cascade_dependents)} secondary component(s) across the {domain_title} blueprint."
    )

    containment_strategies: list[str] = []
    if active_domain_key == "saas_workflow":
        if any(ep in ["auth_rbac", "api_gateway"] for ep in epicenter_module_ids):
            containment_strategies.append("🚨 Session Vault: Extend token grace windows to prevent mass user disconnects across workspace.")
            containment_strategies.append("🛡️ Rate Limiter: Buffer API Gateway ingress requests on authentication endpoints.")
            containment_strategies.append("⚡ Memory Cache: Serve cached user permissions from Redis to relieve auth service load.")
        if any(ep in ["task_engine", "sprint_analytics"] for ep in epicenter_module_ids):
            containment_strategies.append("🚨 Read-Only State: Place defect board updates in optimistic client cache while database recovers.")
            containment_strategies.append("🛡️ Queue Decoupling: Offload sprint metrics and burndown calculations to async background tasks.")
            containment_strategies.append("⚡ Health Check: Ping relational database connection pool every 30 seconds.")
        if not containment_strategies:
            containment_strategies.append("🚨 Module Isolation: Activate circuit-breaker proxy between compromised modules and upstream UI clients.")
            containment_strategies.append("🛡️ Event Queue: Buffer downstream notification dispatches to prevent thread starvation.")
            containment_strategies.append("⚡ Log Auditing: Stream structured error stack traces to central log collector.")
    elif active_domain_key == "ecommerce":
        containment_strategies.append("🚨 Circuit Breaker: Isolate payment & checkout bottlenecks with cached fallback responses.")
        containment_strategies.append("🛡️ Cart Preservation: Persist buyer cart state in browser localStorage to avoid lost sales.")
        containment_strategies.append("⚡ Payment Protection: Idempotency keys enforced on payment dispatch to prevent double-charges.")
    elif active_domain_key == "data_ai":
        containment_strategies.append("🚨 Pipeline Throttle: Pause upstream ingestion stream to prevent data lake buffer overflow during downtime.")
        containment_strategies.append("🛡️ Dead Letter Queue: Route failed batch transformations to DLQ for zero-data-loss replay.")
        containment_strategies.append("⚡ Fallback Model: Switch LLM inference to lightweight fallback model until primary engine recovers.")
    elif active_domain_key == "devops_infra":
        containment_strategies.append("🚨 Build Isolation: Cancel queued build runners connecting to unhealthy runner nodes.")
        containment_strategies.append("🛡️ Secret Rotation: Verify IAM token leases on worker cluster nodes.")
        containment_strategies.append("⚡ Safe Mode: Prevent automated deployments to production environments.")
    else:
        containment_strategies.append("🚨 Module Containment: Activate circuit breaker between origin modules and dependent services.")
        containment_strategies.append("🛡️ Telemetry Sampling: Increase trace sampling rate to 100% for error diagnostics.")
        containment_strategies.append("⚡ Health Ping: Run automated health-check probe every 60 seconds.")

    primary_epicenter_name = module_data[list(epicenter_module_ids)[0]]["name"] if epicenter_module_ids else None

    return BlastRadiusReport(
        project_id=project.id,
        project_name=project.name,
        focused_issue_id=focused_issue.id if focused_issue else None,
        focused_issue_title=focused_issue.title if focused_issue else None,
        focused_module_id=list(epicenter_module_ids)[0] if epicenter_module_ids else None,
        system_blast_score=total_blast,
        overall_status=overall_status,
        domain_archetype=domain_title,
        available_archetypes=AVAILABLE_ARCHETYPES,
        epicenter_module=primary_epicenter_name,
        direct_impact_count=len(direct_dependents),
        cascade_risk_count=len(cascade_dependents),
        direct_impact_modules=direct_names,
        cascade_risk_modules=cascade_names,
        estimated_user_impact=estimated_user_impact,
        containment_strategies=containment_strategies,
        nodes=nodes,
        edges=edges,
        defect_allocations=defect_allocations,
        auto_allocated_summary=auto_allocated_summary,
        total_defects_analyzed=len(issues),
    )

