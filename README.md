# 🚀 BugFlow — AI-Powered Defect Intelligence, Sprint Management & Blast-Radius Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/SQLite%20%2F%20PostgreSQL-Supported-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white" alt="Database" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Pytest-54%2B_Passing-0A9EDC.svg?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Vite-6.0+-646CFF.svg?style=for-the-badge&logo=vite&logoColor=white" alt="Vite" />
  <img src="https://img.shields.io/badge/AI%20Hybrid%20Engine-100%25%20Uptime-8A2BE2.svg?style=for-the-badge&logo=openai&logoColor=white" alt="AI Engine" />
  <img src="https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge" alt="MIT License" />
</p>

---

## 📌 Overview

**BugFlow** is a modern, enterprise-grade defect intelligence, agile sprint management, and architecture blast-radius visualization platform engineered for software developers, QA engineers, and engineering leadership.

It unifies a high-throughput **FastAPI** asynchronous backend, **SQLAlchemy 2.0** relational persistence, a responsive **React 18** client with a custom design system, **ReportLab** PDF generation, **Autonomous Blast-Radius Mapping**, and an offline-resilient **Hybrid AI Engine** (OpenAI / Gemini / Deterministic heuristics) with zero downtime.

> 📖 **Comprehensive System Documentation:** For complete documentation covering all schemas, architecture diagrams, and all 59 API endpoints, refer to [DOCUMENTATION.md](DOCUMENTATION.md).

---

## 📋 Table of Contents

- [✨ Key Features](#-key-features)
- [🏗️ Architecture & Technology Stack](#️-architecture--technology-stack)
- [📁 Project Structure](#-project-structure)
- [🚦 Quick Start Guide](#-quick-start-guide)
  - [Prerequisites](#prerequisites)
  - [Option A: Local Development (Recommended)](#option-a-local-development)
  - [Option B: Docker Compose (Full Stack)](#option-b-docker-compose)
- [🧪 Testing & Verification](#-testing--verification)
- [⚙️ Configuration & Environment Variables](#️-configuration--environment-variables)
- [🛡️ Role-Based Access Control (RBAC)](#️-role-based-access-control-rbac)
- [📄 License](#-license)

---

## ✨ Key Features

### 1. ⚡ Autonomous Blast-Radius & Architecture Dependency Visualizer
* **Autonomous Defect Allocation:** Automatically allocates defects across microservice modules based on semantic taxonomy without requiring manual tagging.
* **Cascading Downstream Failure Paths:** Analyzes directed graph dependencies to trace and highlight secondary cascading outage risks.
* **Domain Blueprint Archetypes:** Includes 5 out-of-the-box domain blueprints:
  * 🏢 *SaaS & Workflow Platform*
  * 🛒 *E-Commerce & Retail Marketplace*
  * 🤖 *Data & AI Pipeline Platform*
  * 💬 *Social & Messaging Platform*
  * ⚙️ *DevOps & Cloud Infrastructure*
* **Interactive SVG Graph:** Renders real-time dependency nodes, failure epicenters with animated danger pulses, and directional flow edges.
* **Failure Impact Matrix:** Detailed breakdown table containing origin components, failure descriptions, impacted downstream services, and linked defect IDs.

### 2. 🎙️ AI Copilot & Voice Bug Dictation
* **Hands-Free Reporting:** Built-in Web Speech API dictation enables testers to describe defects by voice.
* **Structured Expansion:** Converts informal natural language (e.g., *"checkout crashes on safari with 401 unhandled error"*) into a formatted report with reproduction steps, environment parameters, expected vs. actual outcomes, and severity classification.

### 3. 🏷️ Intelligent Defect Taxonomy & Classification
* **Instant Auto-Categorization:** AI automatically tags defects across three critical dimensions:
  * **Category:** *Payment, Authentication & Security, UI/UX, Performance, Database, API & Backend, etc.*
  * **Module:** *Checkout / Gateway, Auth Session, Kanban Board, Notification Service, etc.*
  * **Defect Type:** *Functional Defect, Crash / Fatal Error, UI Glitch, Security Defect, Performance Bottleneck.*
* **1-Click Suggestion Acceptance:** Auto-populates defect creation forms with a single click.

### 4. ⚠️ Real-Time Duplicate Defect Prevention
* **Pre-Submission Scanning:** Evaluates candidate bugs against existing defects using token Jaccard similarity and Levenshtein distance metrics.
* **Similarity Scoring:** Flags potential duplicates *(e.g., `⚠️ Similar Defect Found: DEF-102 (97% Match)`)* in real time to avoid redundant triage.

### 5. 🏃 Agile Sprint Management & Burndown Analytics
* **Sprint Lifecycle:** Create sprints with 1-week, 2-week, or 4-week presets; activate, track, and complete sprints.
* **Backlog Planner:** Bulk assign unassigned backlog issues into active or planned sprints.
* **Interactive SVG Burndown Chart:** Visualizes **Ideal Burn Line** vs **Actual Remaining Defects** with hoverable daily data points.
* **Sprint Completion Workflow:** Rollover unfinished tickets into the next sprint or return them to the backlog.

### 6. 🤖 AI Sprint Copilot Suite
* **AI Sprint Health Analyzer:** Evaluates sprint delivery risks, computing a real-time Health Score (0–100) and bottleneck diagnoses.
* **AI Retrospective Generator:** Automatically synthesizes *"What Went Well"*, *"What Could Be Improved"*, and *"Action Items"* upon sprint completion.
* **AI Sprint Advisor:** Analyzes developer workloads and recommends defect reassignments to balance team capacity.

### 7. 💡 Resolution Assistance Copilot
* **Root Cause Diagnostics:** Generates probable technical root causes for logged defects.
* **Suggested Code Fixes & Checklists:** Provides copyable code snippets, verification checklists, and references to similar resolved defects.

### 8. 💬 AI Mentor & Interactive Chatbot
* **24/7 QA & Engineering Coach:** Multi-mode assistant for onboarding junior testers, reviewing draft bug descriptions, and diagnosing HTTP/code errors (500, 401, CORS, stack traces).
* **Dual Modalities:** Available as a persistent floating widget or full-screen workstation with starter chips and conversation export.

### 9. 📊 QA Analytics Dashboard (8 KPIs & 6 Charts)
* **8 KPI Metric Cards:** Total Defects, Open, In Progress/Review, Resolved, Closed, Critical Outages, Avg Resolution Time, and My Queue.
* **6 Visual Charts:** Created vs Resolved Trends, Defects by Category, Severity Breakdown, Status Distribution, Developer Workloads, and Resolution Velocity.

### 10. 📄 Automated PDF Report Generation
* **Single Defect PDF:** Export professional, branded reports with metadata, environment details, reproduction steps, and comment history.
* **Project QA Summary PDF:** Comprehensive executive reports with statistical breakdowns and resolution velocity tables.

### 11. 🛡️ Role-Based Access Control (RBAC) & Admin Control Center
* **5 Roles:** `admin`, `project_manager`, `developer`, `qa_tester`, and `reporter`.
* **Admin Center:** Live system metrics, instant role promotion/demotion matrix, and user account management with self-deletion protection.

---

## 🏗️ Architecture & Technology Stack

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 18 + Vite)                    │
│  • SPA Architecture with Light / Dark Theme Engine                      │
│  • Pure Vanilla CSS System (Zero framework overhead)                    │
│  • Interactive SVG Topologies, Burndown Curves & Multi-KPI Analytics   │
│  • Lucide React Icons & Web Speech API Dictation Engine                 │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ JSON / REST API (HTTP & JWT)
┌────────────────────────────────────▼────────────────────────────────────┐
│                           BACKEND (FastAPI / Python 3.12)               │
│  • Modular API Routers (Auth, Users, Projects, Issues, Sprints, AI)     │
│  • Pydantic v2 Validation & Custom Error Handlers                       │
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

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 18, Vite 6, React Router v7, Vanilla CSS3, Lucide React, Context API |
| **Backend API** | FastAPI, Pydantic v2, Python 3.12, Uvicorn ASGI |
| **Database & ORM** | SQLAlchemy 2.0, SQLite3 (Dev) / PostgreSQL 15+ (Prod) |
| **Authentication** | Passlib (Bcrypt), PyJWT (HS256), Role-Based Access Control (RBAC) |
| **PDF Generation** | ReportLab Document Engine |
| **AI Intelligence** | Hybrid Engine (OpenAI Async Client / Gemini / Deterministic Rules + TTL Cache & Circuit Breaker) |
| **Testing & CI** | Pytest, GitHub Actions CI/CD |
| **Containerization** | Docker, Docker Compose |

---

## 📁 Project Structure

```
Bug/
├── backend/
│   ├── app/
│   │   ├── routers/            # API Route handlers (auth, issues, sprints, dashboard, etc.)
│   │   ├── ai_service.py       # Hybrid AI Engine with fallback & circuit breaker
│   │   ├── blast_radius_service.py # Graph & failure propagation analysis
│   │   ├── database.py         # SQLAlchemy engine & session lifecycle
│   │   ├── models.py           # Database models (User, Project, Issue, Sprint, etc.)
│   │   ├── schemas.py          # Pydantic v2 validation models
│   │   ├── pdf_service.py      # ReportLab PDF generation
│   │   └── main.py             # FastAPI entrypoint & middleware configuration
│   ├── tests/                  # Pytest modular unit & integration test suites
│   ├── test_api_suite.py       # Comprehensive end-to-end API verification suite
│   ├── Dockerfile              # Backend container definition
│   └── requirements.txt        # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/         # React components (Dashboard, Issues, Sprints, BlastRadius, etc.)
│   │   ├── AuthContext.jsx     # Authentication state provider
│   │   ├── api.js              # Centralized Axios/fetch HTTP client
│   │   ├── index.css           # Global CSS variables, themes, and utility classes
│   │   └── App.jsx             # Root application router & shell
│   ├── index.html              # HTML5 entrypoint
│   ├── Dockerfile              # Frontend multi-stage Nginx container definition
│   └── package.json            # NPM dependencies & scripts
├── docker-compose.yml          # Multi-container orchestration (Postgres + Backend + Frontend)
├── DOCUMENTATION.md            # Comprehensive technical documentation & API reference
└── README.md                   # Project overview & quickstart guide
```

---

## 🚦 Quick Start Guide

### Prerequisites
* **Python 3.10+** (Python 3.12 recommended)
* **Node.js 18+** & **npm**
* *(Optional)* **Docker & Docker Compose**

---

### Option A: Local Development

#### 1. Backend Setup
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

#### 2. Frontend Setup
```bash
# In a new terminal, navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start the Vite development server
npm run dev
```

* 🌐 **Web Application:** [http://localhost:5173](http://localhost:5173)

---

### Option B: Docker Compose

To spin up the complete stack with PostgreSQL, FastAPI, and the React frontend in containers:

```bash
docker-compose up --build
```

* **Frontend:** [http://localhost](http://localhost) (Port 80)
* **Backend API:** [http://localhost:8000](http://localhost:8000)
* **PostgreSQL:** `localhost:5432`

---

## 🧪 Testing & Verification

BugFlow comes with extensive automated test suites covering authentication, defect lifecycles, status transitions, RBAC permissions, and AI copilot services.

### Run Backend Pytest Suite
```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

### Run End-to-End API Test Suite
```bash
cd backend
source venv/bin/activate
python -m pytest test_api_suite.py -v
```

### Run Frontend Production Build Check
```bash
cd frontend
npm run build
```

---

## ⚙️ Configuration & Environment Variables

Create an optional `.env` file in the `backend/` directory:

```env
# Security & JWT Tokens
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256

# Database (Default: SQLite sqlite:///./bugflow.db)
DATABASE_URL=sqlite:///./bugflow.db
# For PostgreSQL: DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bugflow_db

# AI Configuration (Optional: Deterministic heuristics work offline automatically)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

---

## 🛡️ Role-Based Access Control (RBAC)

| Role | Permissions |
| :--- | :--- |
| 👑 **Admin** | Full system control, user role management, system audit logs, access to all projects. |
| 📋 **Project Manager** | Project creation & configuration, sprint lifecycle management, team workload balancing, PDF exports. |
| 💻 **Developer** | Defect resolution, sprint board task progression, AI resolution assistance, status transitions. |
| 🧪 **QA Tester** | Defect reporting, voice dictation, automated classification, duplicate scanning, PDF exports. |
| 📝 **Reporter** | Submitting bug reports and monitoring tracked issue progress. |

---

## 📄 License

This project is licensed under the **MIT License**.
