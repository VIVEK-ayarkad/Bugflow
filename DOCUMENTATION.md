# 🚀 BugFlow — Complete Technical & Functional Documentation

> **AI-Assisted Defect Tracking, Agile Sprint Intelligence & Autonomous Architecture Blast-Radius Visualizer**  
> *Version: 2.0.0 | Production Ready*

---

## 📑 Table of Contents
1. [Executive Summary & System Overview](#1-executive-summary--system-overview)
2. [System Architecture & Technology Stack](#2-system-architecture--technology-stack)
3. [Database Schema & Entity Relationships](#3-database-schema--entity-relationships)
4. [Complete Feature Breakdown & Workflow Capabilities](#4-complete-feature-breakdown--workflow-capabilities)
   - [4.1 Authentication, RBAC & Profile Management](#41-authentication-rbac--profile-management)
   - [4.2 Defect Management & Multi-View Tracking](#42-defect-management--multi-view-tracking)
   - [4.3 Autonomous Blast-Radius & Architecture Visualizer](#43-autonomous-blast-radius--architecture-visualizer)
   - [4.4 Agile Sprint Management & Burndown Analytics](#44-agile-sprint-management--burndown-analytics)
   - [4.5 QA Analytics, KPI Metrics & Interactive Charts](#45-qa-analytics-kpi-metrics--interactive-charts)
   - [4.6 Automated PDF Report Generation](#46-automated-pdf-report-generation)
   - [4.7 System Audit Trail & Notifications](#47-system-audit-trail--notifications)
   - [4.8 Administrator Control Center](#48-administrator-control-center)
5. [Complete AI Defect Intelligence Suite](#5-complete-ai-defect-intelligence-suite)
   - [5.1 AI Engine Architecture & Circuit Breaker](#51-ai-engine-architecture--circuit-breaker)
   - [5.2 AI Copilot & Voice Bug Dictation](#52-ai-copilot--voice-bug-dictation)
   - [5.3 AI Defect Taxonomy & Classification Engine](#53-ai-defect-taxonomy--classification-engine)
   - [5.4 AI Severity & Priority Prediction Engine](#54-ai-severity--priority-prediction-engine)
   - [5.5 AI Semantic Duplicate Detection & Prevention](#55-ai-semantic-duplicate-detection--prevention)
   - [5.6 AI Semantic Search Engine](#56-ai-semantic-search-engine)
   - [5.7 AI Sprint Copilot (Health, Retrospective & Advisor)](#57-ai-sprint-copilot-health-retrospective--advisor)
   - [5.8 AI Resolution Assistance & Root Cause Analyzer](#58-ai-resolution-assistance--root-cause-analyzer)
   - [5.9 AI Mentor & Interactive Chatbot](#59-ai-mentor--interactive-chatbot)
6. [Complete REST API Reference (59 Endpoints)](#6-complete-rest-api-reference-59-endpoints)
7. [Installation, Configuration & Running Guide](#7-installation-configuration--running-guide)
8. [Testing & Verification Suite](#8-testing--verification-suite)

---

## 1. Executive Summary & System Overview

**BugFlow** is an enterprise-grade, full-stack defect tracking and agile sprint management platform engineered for software engineering teams, QA testers, and project managers.

### 🌟 Key Value Propositions:
- **Intelligent Defect Lifecycle**: From AI-assisted voice/text bug reporting and automatic taxonomy classification to instant duplicate prevention and status workflows.
- **Autonomous Blast-Radius Mapping**: Computes architectural dependency graphs, detects failure epicenters, and automatically allocates defects to system modules without requiring manual defect selection.
- **Agile Sprint Velocity & Burndown**: Sprints planning, intraday & milestone burndown analytics, rollover management, and AI Sprint Health & Retrospectives.
- **Robust Role-Based Access Control (RBAC)**: Fine-grained permissions for 5 roles: `admin`, `project_manager`, `developer`, `qa_tester`, and `reporter`.
- **Hybrid AI Engine with 100% Uptime**: Seamless dual-mode execution combining LLM capabilities with deterministic heuristics, TTL caching, and a circuit breaker.

---

## 2. System Architecture & Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 18 + Vite)                    │
│  • SPA Architecture with Theme Engine (Light / Dark Mode)               │
│  • Pure Vanilla CSS System (No heavy CSS framework overhead)           │
│  • Interactive SVG Topologies, Burndown Curves & Multi-KPI Analytics   │
│  • Lucide React Icons & Web Speech API Dictation Engine                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ JSON / REST API (HTTP & JWT)
┌────────────────────────────────────▼────────────────────────────────────┐
│                           BACKEND (FastAPI / Python 3.12)               │
│  • Modular API Routers (Auth, Users, Projects, Issues, Sprints, AI)     │
│  • Pydantic v2 Strict Validation & Custom Exception Handlers           │
│  • ReportLab Vector PDF Engine for Defect & Project Reports             │
│  • Circuit-Breaker Protected AI Defect Intelligence Engine              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ SQLAlchemy ORM 2.0
┌────────────────────────────────────▼────────────────────────────────────┐
│                           DATABASE (SQLite / Relational)                │
│  • Indexed Primary & Foreign Keys with Cascading Deletes                │
│  • Optimized Queries with Eager/Joined Loading                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 🛠️ Technology Stack Breakdown:

| Layer | Technologies Used | Key Purpose |
| :--- | :--- | :--- |
| **Frontend** | React 18, Vite 6, Modern CSS3 | Ultra-fast client, responsive layout, dark/light themes |
| **Icons** | `lucide-react` | Crisp, scalable UI iconography |
| **Voice Dictation** | Web Speech API (`webkitSpeechRecognition`) | Hands-free speech-to-text defect logging |
| **Backend API** | FastAPI, Python 3.12, Uvicorn (ASGI) | Async, high-throughput REST API with OpenAPI/Swagger |
| **ORM & Database** | SQLAlchemy 2.0, SQLite3, Alembic-ready | Type-safe queries, relational integrity, migrations |
| **Authentication** | `python-jose` (JWT), `passlib` (Bcrypt) | Secure salted password hashing and stateless token auth |
| **PDF Generation** | `reportlab` | Vector-rendered executive QA defect and sprint summary PDFs |
| **AI Intelligence** | Hybrid Engine (OpenAI Async SDK / Gemini / Heuristics) | Defect generation, classification, burndown analysis, chatbot |

---

## 3. Database Schema & Entity Relationships

The relational data model consists of 8 primary entities:

```
┌──────────────┐       1:N       ┌──────────────────┐       1:N       ┌──────────────────┐
│    User      ├────────────────►│  ProjectMember   │◄────────────────┤     Project      │
└──────┬───────┘                 └──────────────────┘                 └────────┬─────────┘
       │                                                                       │
       │ 1:N (Assigned/Reported)                                               │ 1:N
       ▼                                                                       ▼
┌──────────────┐                         1:N                          ┌──────────────────┐
│    Issue     │◄─────────────────────────────────────────────────────┤      Sprint      │
└──┬────┬────┬─┘                                                      └──────────────────┘
   │    │    │
   │    │    └──────────────► ┌──────────────────┐
   │    │          1:N        │    Attachment    │
   │    │                     └──────────────────┘
   │    └───────────────────► ┌──────────────────┐
   │               1:N        │     Comment      │
   │                          └──────────────────┘
   └────────────────────────► ┌──────────────────┐
                   1:N        │   ActivityLog    │
                              └──────────────────┘
```

### Table Definitions & Column Types:

1. **`users`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `username` (VARCHAR(50), Unique, Indexed)
   - `email` (VARCHAR(120), Unique, Indexed)
   - `hashed_password` (VARCHAR(255))
   - `role` (VARCHAR(30)) — `admin`, `project_manager`, `developer`, `qa_tester`, `reporter`
   - `created_at` (DATETIME, Default: UTC Now)

2. **`projects`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `name` (VARCHAR(100), Indexed)
   - `description` (TEXT)
   - `created_by` (INTEGER, FK -> `users.id`)
   - `created_at` (DATETIME)

3. **`project_members`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `project_id` (INTEGER, FK -> `projects.id`, OnDelete CASCADE)
   - `user_id` (INTEGER, FK -> `users.id`, OnDelete CASCADE)
   - `role_in_project` (VARCHAR(30))

4. **`sprints`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `project_id` (INTEGER, FK -> `projects.id`, OnDelete CASCADE)
   - `name` (VARCHAR(100))
   - `goal` (TEXT)
   - `start_date` (DATE)
   - `end_date` (DATE)
   - `status` (VARCHAR(20)) — `planned`, `active`, `completed`
   - `created_at` (DATETIME)

5. **`issues`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `project_id` (INTEGER, FK -> `projects.id`, OnDelete CASCADE)
   - `sprint_id` (INTEGER, FK -> `sprints.id`, Nullable, OnDelete SET NULL)
   - `title` (VARCHAR(200), Indexed)
   - `description` (TEXT)
   - `steps_to_reproduce` (TEXT)
   - `expected_behavior` (TEXT)
   - `actual_behavior` (TEXT)
   - `category` (VARCHAR(80))
   - `module` (VARCHAR(80))
   - `defect_type` (VARCHAR(80))
   - `severity` (VARCHAR(20)) — `low`, `medium`, `high`, `critical`
   - `priority` (VARCHAR(20)) — `low`, `medium`, `high`, `critical`
   - `status` (VARCHAR(30)) — `open`, `in_progress`, `in_review`, `resolved`, `closed`
   - `reporter_id` (INTEGER, FK -> `users.id`)
   - `assigned_developer_id` (INTEGER, FK -> `users.id`, Nullable)
   - `os` (VARCHAR(50)), `browser` (VARCHAR(50))
   - `resolved_at` (DATETIME, Nullable)
   - `created_at` (DATETIME), `updated_at` (DATETIME)

6. **`comments`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `issue_id` (INTEGER, FK -> `issues.id`, OnDelete CASCADE)
   - `user_id` (INTEGER, FK -> `users.id`, OnDelete CASCADE)
   - `text` (TEXT)
   - `created_at` (DATETIME), `updated_at` (DATETIME)

7. **`attachments`**:
   - `id` (INTEGER, PK, Autoincrement)
   - `issue_id` (INTEGER, FK -> `issues.id`, OnDelete CASCADE)
   - `filename` (VARCHAR(255))
   - `file_path` (VARCHAR(500))
   - `file_size` (INTEGER)
   - `uploaded_by` (INTEGER, FK -> `users.id`)
   - `created_at` (DATETIME)

8. **`notifications`** & **`activity_logs`**:
   - Stores real-time assignment notifications, read states, and user audit trails with timestamps.

---

## 4. Complete Feature Breakdown & Workflow Capabilities

### 4.1 Authentication, RBAC & Profile Management
- **Industrial Split-Screen Portal**: Sleek authentication interface with brand logo, product feature highlights, and secure input handling.
- **Role-Based Access Control**:
  - `admin`: Complete platform control, user role modification, user removal, system audit logs.
  - `project_manager`: Full project creation, sprint management, member assignment, PDF exports.
  - `developer`: Defect resolution, sprint board updates, AI resolution assistance, status transitions.
  - `qa_tester`: Defect logging, AI copilot reporting, duplicate detection, test verification.
  - `reporter`: Read and report permissions for logging bugs.
- **Account Settings Modal**: Users can update their username, email address, and securely change their password.

### 4.2 Defect Management & Multi-View Tracking
- **Table View**: Comprehensive data table featuring inline status changers, bug key tags (`#BUG-12`), severity badges, developer avatar chips, and action buttons.
- **Kanban Board**: Drag-and-drop or 1-click status transitions across 5 workflow columns: `Open`, `In Progress`, `In Review`, `Resolved`, and `Closed`.
- **Search & Filter Suite**:
  - Exact ID (`#14`), title, and description search.
  - AI Semantic Search for concept-based queries.
  - Multi-dimensional filters for Status, Severity, and Priority.
- **Interactive Defect Modal**: View full reproduction steps, expected vs actual behaviors, add comments, upload/download attachments, view audit history, or launch AI Resolution Assistance.

### 4.3 Autonomous Blast-Radius & Architecture Visualizer
- **Autonomous Defect Allocation**: Automatically assigns every defect in the project to its corresponding architecture component based on semantic matching and defect taxonomy.
- **Cascade Impact Calculation**: Evaluates downstream risks and calculates cascading failure chains across service boundaries.
- **System Blast Score**: Calculates a 0-100 system risk score based on open defects, failure epicenters, and dependency flows.
- **Domain Blueprints Supported**:
  1. *SaaS & Workflow Platform*
  2. *E-Commerce & Retail Marketplace*
  3. *Data & AI Pipeline Platform*
  4. *Social & Community Platform*
  5. *DevOps & Cloud Infrastructure*
- **Interactive SVG Topology Graph**: Renders nodes, dependency edges, failure epicenters, and color-coded impact routes.
- **Defect Failure Matrix Table**: Collapsible matrix detailing origin modules, failure descriptions, impacted downstream services, and related defect IDs.

### 4.4 Agile Sprint Management & Burndown Analytics
- **Sprint Lifecycle Management**: Create sprints with goal definitions, date presets (1 week, 2 weeks, 4 weeks), start active sprints, and complete sprints.
- **Backlog Planner**: Bulk select and allocate unassigned backlog defects into active or planned sprints.
- **Intraday & Milestone Burndown Chart**: Interactive SVG burndown chart comparing Ideal Burn Line vs Actual Remaining Defects with hoverable data points.
- **Sprint Completion Workflow**: Flexible defect handling upon sprint closure — move remaining issues to Next Sprint, return to Backlog, or keep in Sprint.

### 4.5 QA Analytics, KPI Metrics & Interactive Charts
The real-time QA dashboard provides 8 core KPI cards and 6 visual charts:
- **8 KPI Metrics**: Total Defects, Open Defects, In Progress/Review, Resolved Defects, Closed Defects, Critical Defects, Avg Resolution Time, and My Queue.
- **6 Visual Analytics Charts**:
  1. *Defect Trends*: Monthly Created vs Resolved comparison bars.
  2. *Defects by Category*: Segmented distribution across Payment, Auth, UI/UX, Performance, etc.
  3. *Defects by Severity*: Proportion of Low, Medium, High, and Critical issues.
  4. *Defects by Status*: Open, In Progress, In Review, Resolved, Closed.
  5. *Developer Workload Matrix*: Defect count distribution per engineer.
  6. *Resolution Time by Severity*: Average hours taken to resolve defects by severity tier.

### 4.6 Automated PDF Report Generation
- **Defect Summary PDF**: Generates a branded, printable PDF report for any defect containing all metadata, environment details, reproduction steps, and comment history.
- **Project QA Executive PDF**: Generates an executive project report summarizing total defect counts, resolution velocities, sprint statuses, and complete bug lists formatted in ReportLab tables.

### 4.7 System Audit Trail & Notifications
- **Activity Timeline**: Records every action (defect created, status updated, assigned, sprint started, comment added) with user attribution and timestamp.
- **Real-Time Notification Drawer**: Alerts developers when assigned to an issue, with 1-click "Mark as Read" and "Mark All as Read".

### 4.8 Administrator Control Center
- **RBAC Role Matrix**: Admins can promote/demote user roles on the fly via a select dropdown.
- **User Account Management**: Remove accounts with self-deletion protection.
- **System Metrics Overview**: Live summary of platform users, active projects, and recorded bugs.

---

## 5. Complete AI Defect Intelligence Suite

BugFlow includes an extensive, enterprise AI defect intelligence engine powered by `backend/app/ai.py`.

```
┌────────────────────────────────────────────────────────────────────────┐
│                          BugFlow AI Engine                             │
├────────────────────────────────┬───────────────────────────────────────┤
│  ⚡ Fast In-Memory TTL Cache    │  🛡️ AICircuitBreaker (Auto-Recovery)  │
├────────────────────────────────┴───────────────────────────────────────┤
│  Dual-Mode Architecture:                                               │
│   • Remote LLM Client (OpenAI / Gemini compatible with 1.8s timeout)   │
│   • Deterministic Offline Rule & Heuristic Engine (Fallback)           │
└────────────────────────────────────────────────────────────────────────┘
```

### 5.1 AI Engine Architecture & Circuit Breaker
- **TTL Cache**: 1-hour in-memory cache for frequent queries, preventing redundant API calls and latency.
- **Circuit Breaker (`AICircuitBreaker`)**: Automatically trips on rate-limits, auth failures, or quota limits to immediately switch to local deterministic intelligence without slowing down user interactions.

### 5.2 AI Copilot & Voice Bug Dictation
- **Input**: Raw text (e.g., `"checkout crashes on mobile with 500 error"`) or audio dictation.
- **Output**: Formatted bug report with structured title, detailed description, numbered reproduction steps, expected behavior, and actual behavior.

### 5.3 AI Defect Taxonomy & Classification Engine
- Automatically parses bug reports and categorizes into standard taxonomies:
  - **Category**: `Payment`, `Authentication & Security`, `UI / UX`, `Database & Storage`, `Performance`, `API & Backend`, `Notifications`, `Analytics`.
  - **Module**: Specific architectural component (e.g., `Checkout / Payment Gateway`, `Auth / User Session`).
  - **Defect Type**: `Functional Defect`, `Crash / Fatal Error`, `UI / Visual Glitch`, `Security / Access Defect`, `Performance Bottleneck`, etc.
  - **Suggested Severity & Priority**: With confidence percentage and explanatory rationale.

### 5.4 AI Severity & Priority Prediction Engine
- Analyzes crash keywords, customer impact phrases (e.g., `"all users unable to login"`, `"payment failure"`), and assigns `critical`, `high`, `medium`, or `low` severity with a clear rationale.

### 5.5 AI Semantic Duplicate Detection & Prevention
- Scans active project defects using Levenshtein distance, token Jaccard similarity, and n-gram keyword weighting.
- Flags similar existing defects with a similarity match percentage to prevent duplicate ticket creation.

### 5.6 AI Semantic Search Engine
- Evaluates meaning and concepts beyond exact keywords (e.g., searching `"money problem"` matches `"payment gateway 500 timeout"`).

### 5.7 AI Sprint Copilot (Health, Retrospective & Advisor)
- **AI Sprint Health**: Evaluates open vs resolved defects, remaining days, and velocity to output a Health Score (0-100), Risk Level, and Actionable Recommendations.
- **AI Sprint Retrospective**: Automatically synthesizes "What Went Well", "What Could Be Improved", and "Key Takeaways" upon sprint closure.
- **AI Sprint Advisor**: Analyzes developer workloads and suggests optimal defect assignments to balance capacity.

### 5.8 AI Resolution Assistance & Root Cause Analyzer
- Analyzes reproduction steps and error logs to provide:
  - Probable Root Cause Analysis
  - Suggested Code Fix / Architectural Patch
  - Step-by-Step QA Verification Checklist
  - Similar Historical Resolved Issues in the workspace

### 5.9 AI Mentor & Interactive Chatbot
- Interactive AI chatbot supporting multiple operational modes:
  - **General Beginner Mentor**: Guides junior engineers and testers on QA concepts (e.g., Severity vs Priority).
  - **Draft Bug Reviewer**: Critiques draft bug descriptions and suggests improvements.
  - **Error Code Diagnostics**: Explains stack traces and HTTP status codes (500, 401, CORS).
  - **Starter Topics**: Categorized starter prompts for instant guidance.

---

## 6. Complete REST API Reference (59 Endpoints)

All endpoints are prefixed with `/api` and document strict Pydantic schemas:

### 🔐 Authentication (`/api/auth`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user | No |
| `POST` | `/api/auth/login` | Login with JSON payload | No |
| `POST` | `/api/auth/token` | OAuth2 form login for Swagger UI | No |
| `GET` | `/api/auth/me` | Retrieve authenticated user profile | Yes |
| `PUT` | `/api/auth/profile` | Update user profile & password | Yes |
| `POST` | `/api/auth/logout` | Logout user | Yes |

### 👥 Users & Roles (`/api/users`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/users` | List all users | Yes |
| `GET` | `/api/users/{id}` | Retrieve user by ID | Yes |
| `PUT` | `/api/users/{id}/role` | Update user role (Admin only) | Yes (Admin) |

### 📁 Projects (`/api/projects`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/projects` | List projects for user | Yes |
| `POST` | `/api/projects` | Create a new project | Yes |
| `GET` | `/api/projects/{id}` | Retrieve project details | Yes |
| `PUT` | `/api/projects/{id}` | Update project | Yes |
| `DELETE` | `/api/projects/{id}` | Delete project | Yes |
| `GET` | `/api/projects/{id}/members` | List project members | Yes |
| `POST` | `/api/projects/{id}/members` | Add project member | Yes |
| `DELETE` | `/api/projects/{id}/members/{u_id}` | Remove project member | Yes |
| `GET` | `/api/projects/{id}/pdf` | Stream Project QA Summary PDF | Yes |
| `GET` | `/api/projects/{id}/blast-radius` | Get project blast-radius topology | Yes |

### ⚡ Sprints (`/api/sprints`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/projects/{id}/sprints` | List sprints for a project | Yes |
| `POST` | `/api/sprints` | Create a sprint | Yes |
| `GET` | `/api/sprints/{id}` | Retrieve sprint details | Yes |
| `PUT` | `/api/sprints/{id}` | Update sprint dates / goal | Yes |
| `DELETE` | `/api/sprints/{id}` | Delete sprint | Yes |
| `POST` | `/api/sprints/{id}/start` | Start sprint (set to active) | Yes |
| `POST` | `/api/sprints/{id}/complete` | Complete sprint & handle remaining issues | Yes |
| `GET` | `/api/sprints/{id}/metrics` | Retrieve sprint burndown metrics | Yes |
| `POST` | `/api/sprints/{id}/issues/bulk-assign`| Bulk assign issues to sprint | Yes |

### 🐛 Issues & Defects (`/api/issues`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/issues` | List issues with filters & search | Yes |
| `POST` | `/api/projects/{id}/issues` | Create defect in project | Yes |
| `GET` | `/api/issues/{id}` | Retrieve defect details | Yes |
| `PUT` | `/api/issues/{id}` | Update defect details | Yes |
| `DELETE` | `/api/issues/{id}` | Delete defect | Yes |
| `PUT` | `/api/issues/{id}/status` | Update defect workflow status | Yes |
| `PUT` | `/api/issues/{id}/assign` | Assign defect to developer | Yes |
| `GET` | `/api/issues/{id}/activity` | Retrieve defect audit history | Yes |
| `GET` | `/api/issues/{id}/pdf` | Stream single Defect PDF report | Yes |
| `GET` | `/api/issues/{id}/resolution-assistance` | Get AI root cause & fix assistance | Yes |
| `GET` | `/api/issues/{id}/blast-radius` | Get defect-focused blast radius | Yes |

### 💬 Comments & Attachments (`/api/comments`, `/api/attachments`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/issues/{id}/comments` | List defect comments | Yes |
| `POST` | `/api/issues/{id}/comments` | Add comment to defect | Yes |
| `PUT` | `/api/comments/{id}` | Edit comment | Yes |
| `DELETE` | `/api/comments/{id}` | Delete comment | Yes |
| `GET` | `/api/issues/{id}/attachments` | List defect attachments | Yes |
| `POST` | `/api/issues/{id}/attachments` | Upload file attachment | Yes |
| `GET` | `/api/attachments/{id}/download`| Download attachment file | Yes |
| `DELETE` | `/api/attachments/{id}` | Delete attachment | Yes |

### 🤖 AI Defect Intelligence (`/api/ai`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/ai/assist` | Auto-format raw bug description | Yes |
| `POST` | `/api/ai/classify-defect` | Classify category, module & type | Yes |
| `POST` | `/api/ai/predict-severity` | Predict severity & rationale | Yes |
| `POST` | `/api/ai/detect-duplicates` | Detect similar defects | Yes |
| `POST` | `/api/ai/semantic-search` | Concept-based defect search | Yes |
| `POST` | `/api/ai/sprint-health/{id}` | Evaluate sprint health | Yes |
| `POST` | `/api/ai/sprint-retrospective/{id}` | Generate sprint retrospective | Yes |
| `POST` | `/api/ai/sprint-advisor/{id}` | Generate sprint advisory recommendations | Yes |
| `GET` | `/api/ai/chat/topics` | Get starter mentor topics | Yes |
| `POST` | `/api/ai/chat` | AI Mentor chat conversation | Yes |

### 📊 Dashboard & System Control (`/api/dashboard`, `/api/admin`, `/api/notifications`)
| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/dashboard/stats` | Retrieve 8 KPIs & 6 charts data | Yes |
| `GET` | `/api/dashboard/activity` | Retrieve recent activity stream | Yes |
| `GET` | `/api/notifications` | List user notifications | Yes |
| `PUT` | `/api/notifications/{id}/read` | Mark notification as read | Yes |
| `PUT` | `/api/notifications/read-all` | Mark all notifications as read | Yes |
| `GET` | `/api/admin/reports` | Get platform-wide admin metrics | Yes (Admin) |
| `GET` | `/api/admin/users` | List all users for RBAC management | Yes (Admin) |
| `DELETE` | `/api/admin/users/{id}` | Remove user account | Yes (Admin) |
| `GET` | `/api/admin/logs` | System audit logs | Yes (Admin) |
| `GET` | `/api/health` | Service health status | No |

---

## 7. Installation, Configuration & Running Guide

### Prerequisites:
- **Node.js**: v18+ and `npm`
- **Python**: v3.10+ (Python 3.12 recommended)

### 1. Backend Setup:
```bash
# Navigate to backend directory
cd /path/to/Bug/backend

# Create virtual environment & activate
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# (Optional) Configure environment variables in .env
# OPENAI_API_KEY=your_key_here  (Optional: deterministic fallback works out of the box)
# SECRET_KEY=your_jwt_secret_key

# Run the FastAPI server
uvicorn app.main:app --reload --port 8000
```

Backend will be active at `http://localhost:8000` with interactive Swagger API docs at `http://localhost:8000/docs`.

### 2. Frontend Setup:
```bash
# Navigate to frontend directory
cd /path/to/Bug/frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

Frontend will be active at `http://localhost:5173`.

### 3. Production Build:
```bash
cd /path/to/Bug/frontend
npm run build
```

---

## 8. Testing & Verification Suite

BugFlow includes an automated end-to-end REST API verification suite in `backend/test_api_suite.py` covering all 7 operational domains:
1. Health & OpenAPI/Swagger Schema Validation
2. Authentication & Route Security
3. Users & Role-Based Access Control
4. Projects & Sprints APIs
5. Defects, Comments, Attachments & PDF Streaming
6. Dashboard Analytics, Notifications & Admin Controls
7. AI Defect Intelligence Endpoints

### Running the Test Suite:
```bash
cd /path/to/Bug/backend
source venv/bin/activate
pytest test_api_suite.py -v -s
```

**Result:** `60 PASSED, 0 FAILED (100% Pass Rate)`.

---
*BugFlow — Enterprise Defect Intelligence & Agile Sprint Platform*
