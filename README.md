# 🚀 BugFlow — AI-Powered Defect Intelligence, Sprint Management & Blast-Radius Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/SQLite%20%2F%20PostgreSQL-Supported-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white" alt="Database" />
  <img src="https://img.shields.io/badge/Pytest-60_Passed-0A9EDC.svg?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Vite-6.4+-646CFF.svg?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/AI%20Hybrid%20Engine-100%25%20Uptime-8A2BE2.svg?style=for-the-badge&logo=openai&logoColor=white" alt="AI Engine" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="MIT License" />
</p>

---

## 📌 Overview

**BugFlow** is an enterprise-grade defect tracking, agile sprint management, and architecture blast-radius visualization platform built for software engineering teams, QA testers, and engineering leadership.

It unites a high-throughput **FastAPI** backend, **SQLAlchemy 2.0** relational persistence, a responsive **React 18** client with custom design system, **ReportLab** PDF generation, **Autonomous Blast-Radius Mapping**, and an offline-resilient **Hybrid AI Engine** with zero downtime.

> 📖 **Full System Documentation:** For an in-depth guide covering every feature, architecture, database schema, and all 59 API endpoints, see [DOCUMENTATION.md](DOCUMENTATION.md).

---

## ✨ Key Features & Capabilities

### 1. ⚡ Autonomous Blast-Radius & Architecture Dependency Visualizer
* **Autonomous Defect Allocation:** Automatically allocates defects across system modules based on semantic taxonomy without requiring manual defect selection.
* **Cascading Failure Paths:** Analyzes directed graph dependencies to compute secondary downstream failure risks across microservices.
* **Domain Blueprint Archetypes:** Auto-detects or switches across 5 domain architectures:
  * 🏢 *SaaS & Workflow Platform*
  * 🛒 *E-Commerce & Retail Marketplace*
  * 🤖 *Data & AI Pipeline Platform*
  * 💬 *Social & Messaging Platform*
  * ⚙️ *DevOps & Cloud Infrastructure*
* **Interactive SVG Graph:** Renders dependency nodes, failure epicenters with danger rings, and animated directional flow edges.
* **Failure Impact Matrix Table:** Collapsible table detailing origin components, failure descriptions, impacted downstream services, and linked defect IDs.

### 2. 🎙️ AI Copilot & Voice Bug Dictation
* **Hands-Free Reporting:** Built-in Web Speech API dictation allows testers to speak bug descriptions directly.
* **Line-by-Line Structured Expansion:** Converts raw prompts (e.g., *"checkout crashes on safari with 401 unhandled error"*) into a formatted report with structured titles, descriptions, numbered steps to reproduce, expected vs. actual behaviors, and severity assessments.

### 3. 🏷️ Intelligent Defect Taxonomy & Classification
* **Automatic Categorization:** Classifies defects into standard taxonomies:
  * **Category:** *Payment, Authentication & Security, UI/UX, Performance, Database, API & Backend, etc.*
  * **Module:** *Checkout / Gateway, Auth Session, Kanban Board, Notification Service, etc.*
  * **Defect Type:** *Functional Defect, Crash / Fatal Error, UI Glitch, Security Defect, Performance Bottleneck.*
* **1-Click Suggestion Acceptance:** Auto-populates all form dropdowns with a single click.

### 4. ⚠️ Real-Time Duplicate Defect Prevention
* **Pre-Submission Warning:** Scans existing defects using token Jaccard similarity and Levenshtein distance before submission.
* **Similarity Scoring:** Highlights duplicate tickets *(e.g., `⚠️ Similar Defect Found: DEF-102 (97% Match)`)* to eliminate backlog clutter.

### 5. 🏃 Agile Sprint Management & Burndown Analytics
* **Sprint Lifecycle:** Create sprints with 1-week, 2-week, or 4-week date presets; start and complete sprints.
* **Backlog Planner:** Bulk assign unassigned backlog issues into active or planned sprints.
* **Interactive SVG Burndown Chart:** Visualizes **Ideal Burn Line** vs **Actual Remaining Defects** with hoverable data points.
* **Sprint Completion Workflow:** Rollover remaining issues to Next Sprint or return them to the Backlog.

### 6. 🤖 AI Sprint Copilot Suite
* **AI Sprint Health Analyzer:** Computes real-time Sprint Health Scores (0-100), risk levels, and bottleneck alerts.
* **AI Sprint Retrospective Generator:** Synthesizes *"What Went Well"*, *"What Could Be Improved"*, and *"Action Items"* upon sprint closure.
* **AI Sprint Advisor:** Analyzes developer workloads and recommends optimal defect reassignments to balance team capacity.

### 7. 💡 Resolution Assistance Copilot
* **Root Cause Diagnostics:** Generates probable technical root causes for logged defects.
* **Checklist & Fix Suggestions:** Provides verification checklists, recommended code patches with 1-click copy, and historical resolved cases.

### 8. 💬 AI Mentor & Interactive Chatbot
* **24/7 QA & Engineering Coach:** Multi-mode assistant for onboarding junior testers, reviewing draft bug descriptions, and diagnosing HTTP/code errors (500, 401, CORS, stack traces).
* **Dual Modalities:** Available as a persistent floating widget or full-screen workstation with starter chips and conversation export.

### 9. 📊 QA Analytics Dashboard (8 KPIs & 6 Charts)
* **8 KPI Metric Cards:** Total Defects, Open, In Progress/Review, Resolved, Closed, Critical Outages, Avg Resolution Time, and My Queue.
* **6 Visual Charts:** Created vs Resolved Trends, Defects by Category, Severity Breakdown, Status Distribution, Developer Workloads, and Resolution Velocity by Severity.

### 10. 📄 Automated PDF Report Generation
* **Single Defect PDF:** Branded report with metadata, environment details, reproduction steps, and comment history.
* **Project QA Summary PDF:** Executive project summary with overall statistics, resolution rates, and ReportLab tables.

### 11. 🛡️ Role-Based Access Control (RBAC) & Admin Control Center
* **5 Distinct Roles:** `admin`, `project_manager`, `developer`, `qa_tester`, and `reporter`.
* **Admin Center:** Live system metrics, instant role promotion/demotion matrix, and user account management with self-deletion protection.

---

## 🏗️ Architecture & Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 18 + Vite)                    │
│  • SPA Architecture with Light / Dark Theme Engine                      │
│  • Pure Vanilla CSS System (No heavy framework bloat)                   │
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
│                           DATABASE (SQLite / PostgreSQL)                │
│  • Indexed Primary & Foreign Keys with Cascading Deletes                │
│  • Optimized Queries with Eager/Joined Loading                          │
└─────────────────────────────────────────────────────────────────────────┘
```

| Component | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite, Vanilla CSS3, Lucide React, Context API |
| **Backend API** | FastAPI, Pydantic v2, Python 3.12, Uvicorn ASGI |
| **Database & ORM** | SQLAlchemy 2.0, SQLite3 / PostgreSQL 15+ |
| **Authentication** | Passlib (Bcrypt), PyJWT (HS256), Role-Based Access Control (RBAC) |
| **PDF Generation** | ReportLab Document Engine |
| **AI Intelligence** | Hybrid Engine (OpenAI Async Client / Gemini / Deterministic Rules + TTL Cache & Circuit Breaker) |
| **Testing & CI** | Pytest (60/60 passing), GitHub Actions CI/CD |

---

## 🚦 Quick Start Guide

### Prerequisites
* **Python 3.10+** (Python 3.12 recommended)
* **Node.js 18+** & **npm**

---

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the FastAPI development server
uvicorn app.main:app --reload --port 8000
```

* 🚀 **Backend API:** [http://localhost:8000](http://localhost:8000)
* 📚 **Interactive Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```

* 🌐 **Web Application:** [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing & Verification

BugFlow includes an automated 60-point verification test suite:

```bash
cd backend
source venv/bin/activate

# Run the complete test suite
pytest test_api_suite.py -v -s
```

**Verification Results:** `60 PASSED, 0 FAILED (100% Pass Rate)`.

To verify the frontend production build:
```bash
cd frontend
npm run build
```
**Build Result:** `✓ 1807 modules transformed, 0 errors`.

---

## ⚙️ Environment Variables (Optional)

Create a `.env` file inside `backend/`:

```env
# Security & JWT Tokens
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256

# Database (Default: SQLite sqlite:///./bugflow.db)
DATABASE_URL=sqlite:///./bugflow.db

# AI Configuration (Optional: Built-in deterministic heuristics operate offline)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

---

## 🛡️ User Roles & Permissions Matrix

| Role | Permissions |
| :--- | :--- |
| 👑 **Admin** | Full system control, user role management, system audit logs, all projects. |
| 📋 **Project Manager** | Project creation, sprint lifecycle management, team assignments, PDF exports. |
| 💻 **Developer** | Defect resolution, sprint board updates, AI resolution assistance, status transitions. |
| 🧪 **QA Tester** | Defect reporting, voice dictation, classification, duplicate scans, PDF exports. |
| 📝 **Reporter** | Submitting bug reports and monitoring issue progress. |

---

## 📄 License & Attribution

Distributed under the **MIT License**. Engineered for modern software development teams.
