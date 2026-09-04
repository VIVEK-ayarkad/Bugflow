# 🚀 BugFlow — AI-Powered Defect Intelligence & Bug Tracking Platform

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18.3+-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PostgreSQL-15+-4169E1.svg?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/Pytest-60_Passed-0A9EDC.svg?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest" />
  <img src="https://img.shields.io/badge/Ruff-Linted-D7FF64.svg?style=for-the-badge&logo=ruff&logoColor=black" alt="Ruff" />
  <img src="https://img.shields.io/badge/CI%2FCD-GitHub_Actions-2088FF.svg?style=for-the-badge&logo=githubactions&logoColor=white" alt="GitHub Actions" />
</p>

---

## 📌 Overview

**BugFlow** is an enterprise-grade defect tracking and software QA intelligence platform designed for modern agile engineering teams. It unites a high-throughput **FastAPI** backend, **PostgreSQL** relational persistence, a responsive **React 18** client, **ReportLab** PDF generation, **Dense Semantic Vector Intelligence**, and automated **CI/CD pipeline workflows** to streamline the complete bug lifecycle.

From automated defect classification and semantic duplicate detection to our signature **Resolution Assistance Copilot**, BugFlow empowers QA testers to file crystal-clear bug reports and enables developers to diagnose and resolve issues in record time.

---

## ✨ Core Features & Capabilities

### 1. 🔍 Intelligent Defect Classification
* **Real-time Domain Taxonomy:** Automatically analyzes raw defect descriptions to suggest:
  * **Defect Category:** *(e.g., Payment, Authentication, UI, Performance, Database)*
  * **Affected Module:** *(e.g., Checkout / Payment Gateway, Session Manager, Cart)*
  * **Defect Type:** *(e.g., Functional Defect, Security Vulnerability, Visual Flaw)*
  * **Suggested Severity & Priority:** *(e.g., High Severity, High Priority)*
* **1-Click Acceptance:** Testers can accept all AI suggestions instantly with a single button or fine-tune individual fields.

### 2. 📝 Line-by-Line Structured Expansion
* **Standardized Bug Formatting:** AI Copilot formats descriptions into clean, vertical line-by-line sections:
  * `Summary:`
  * `Steps to Reproduce:` (Numbered 1, 2, 3...)
  * `Expected Result:`
  * `Actual Result:`
  * `Impact & Severity Assessment:`

### 3. 🎯 Intelligent Severity & Outage Predictor
* **Impact Evaluation:** Scores business risk and outage severity *(e.g., "All users unable to complete checkout" → Critical)*.
* **Compliance & Transparency:** Displays explicit disclaimers ensuring final decision authority remains with authorized project leads.

### 4. ⚠️ Similar Defect Detection & Duplicate Prevention
* **Real-Time Warning Banner:** Compares newly typed defects against existing project issues using QA-domain word-stemming and token overlap metrics.
* **Instant Alert:** Prevents redundant tickets by highlighting matching keys *(e.g., `⚠️ Similar Defect Found: DEF-102 (97% Match)`)*.

### 5. 🔮 Semantic Vector Search Engine
* **Concept-Based Search:** Goes beyond keyword matching to search by conceptual intent.
* **Example Query:** Searching *"Payment fails after clicking submit"* accurately retrieves *"Transaction crashes during checkout"* with confidence match badges (`✨ 97% Match`).
* **Hybrid Engine:** Dense domain ontology vector math with optional OpenAI embedding fallback.

### 6. 💡 Resolution Assistance Copilot (Signature Feature)
* **Instant Developer Guidance:** Opening any defect produces actionable engineering assistance:
  * **Investigation Areas:** Interactive checklist (API response, null/undefined checks, server logs, error handling).
  * **Similar Defect History:** Direct links to related historical tickets (`DEF-xxx`).
  * **Previous Resolution Context:** Summary of how similar historical bugs were resolved.
  * **Recommended Technical Fix:** Specific code fix with **1-Click Copy** and **"Post to Comments"** actions.

### 7. 🩺 Code Doctor (Pure Direct Syntax & Semantic Repair)
* **Direct Code Repair:** Submitting faulty code (e.g. `print("hell)`) outputs pure corrected code (`print("hell")`) without wrapping in unnecessary `try...catch` blocks.
* **AST Validation:** Confirms valid code with `is_correct: true`.

### 8. 🤖 AI Mentor & Chatbot (Multi-Domain Engineering & QA Intelligence)
* **Interactive Guidance:** Dedicated conversational mentor to guide developers and QA engineers through bug reproduction, error diagnosis, testing, and debugging.
* **Multi-Domain Intelligence:** Answers technical doubts across REST/HTTP status codes (500, 401, 403, 404, 422), CORS, JavaScript/React state & hooks, Python exceptions, database transactions & rollbacks, race conditions, Git PR workflows, and QA testing methodologies.
* **Dual Access Modalities:** Available as a persistent floating assistant widget on every dashboard page and as a full-screen workstation via sidebar navigation.
* **Context-Aware Debugging:** Pass active defect tickets or draft bug descriptions directly into the AI Mentor for instant critique and tailored remediation advice.

### 9. 📄 1-Click PDF Report Generation
* **Defect Investigation Reports:** Export complete bug metadata, reproduction steps, resolution assistance, and full comment thread as a PDF (`GET /api/issues/{id}/pdf`).
* **Project QA Summary Reports:** Executive PDF summarizing project statistics, open defect inventories, and severity charts (`GET /api/projects/{id}/pdf`).

### 10. ✏️ Full Defect Lifecycle & In-Place Editing
* Modify and update defects directly from:
  * **Bug Detail Modal:** Inline **"✏️ Edit Bug"** toggle.
  * **Table View:** Dedicated **"✏️ Edit"** button in row actions.
  * **Kanban Board:** Quick **"✏️"** card action.

### 11. 👤 User Profile & Account Settings
* Click your user card in the sidebar footer to:
  * Update **Username** and **Email Address**.
  * Change **Security Password** (with current password verification).
  * View assigned role badge and membership duration.

### 12. 📊 Sprints, Interactive Kanban Board & Analytics
* **5-Stage Kanban Workflow:** `Open` ➔ `In Progress` ➔ `In Review` ➔ `Resolved` ➔ `Closed`.
* **Sprint Health Analytics:** Automatic sprint risk scoring (`Low`, `Medium`, `High`, `Critical`).
* **Visual Charts:** Interactive SVG charts for severity distributions, status breakdowns, monthly defect volume, and team workload.

---

## 🏗️ Architecture & Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                    React 18 Frontend                        │
│   (Vite • Vanilla CSS • Lucide Icons • Real-Time Modals)    │
└──────────────────────────────┬──────────────────────────────┘
                               │  REST API / JWT
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Engine                   │
│   (Python 3.12+ • Pydantic v2 • SQLAlchemy 2.0 • ReportLab) │
└──────┬───────────────────────┬───────────────────────┬──────┘
       │                       │                       │
┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
│ PostgreSQL  │         │ Dense Vector│         │ ReportLab   │
│  Database   │         │  AI Engine  │         │ PDF Builder │
└─────────────┘         └─────────────┘         └─────────────┘
```

| Layer | Technologies & Tools |
| :--- | :--- |
| **Frontend** | React 18, Vite, Vanilla CSS, Lucide React, Context API |
| **Backend API** | FastAPI, Pydantic v2, Python 3.12 / 3.13 |
| **Database** | PostgreSQL 15+, SQLite (test/dev), SQLAlchemy 2.0 ORM |
| **AI Intelligence** | Dense Concept Vector Ontology, OpenAI Embeddings, GPT-4o-mini |
| **PDF Generation** | ReportLab Document Engine |
| **Authentication** | Passlib (bcrypt), PyJWT (HS256), Role-Based Access Control (RBAC) |
| **Testing & CI** | Pytest, Ruff Linter, GitHub Actions CI/CD Pipeline |
| **Containerization** | Docker, Multi-Stage Builds, Nginx Reverse Proxy, Docker Compose |

---

## 🚦 Quick Start Guide

### Option 1: Run with Docker Compose (Recommended)

Start the full stack (PostgreSQL + FastAPI Backend + React/Nginx Frontend) in one command:

```bash
# Clone the repository
git clone https://github.com/VIVEK-ayarkad/Bugflow.git
cd Bugflow

# Start all services
docker compose up --build
```

- 🌐 **Frontend Web UI:** [http://localhost:5173](http://localhost:5173)
- 🚀 **Backend API:** [http://localhost:8000](http://localhost:8000)
- 📚 **Swagger API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Option 2: Local Development Setup

#### Prerequisites
* **Python 3.12+**
* **Node.js 18+** & **npm**
* **PostgreSQL** (or SQLite for local rapid dev)

#### 1. Backend Setup
```bash
# Navigate to backend directory
cd backend

# Create and activate Python virtual environment
python3 -m venv venv
source venv/bin/activate       # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables (optional)
cp .env.example .env

# Start the FastAPI development server
uvicorn app.main:app --reload --port 8000
```
> 📚 **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

#### 2. Frontend Setup
```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Start Vite development server
npm run dev
```
> 🌐 **Web Application UI:** [http://localhost:5173](http://localhost:5173)

---

## 🧪 Testing & Code Quality

BugFlow includes a comprehensive automated test suite and linter configuration:

```bash
cd backend

# 1. Run full unit & integration test suite (60 Tests)
./venv/bin/pytest

# 2. Run standalone 51-point REST API verification suite (7 Phases)
./venv/bin/python test_api_suite.py

# 3. Run Ruff code linter
./venv/bin/ruff check .

# 4. Verify Frontend Production Build
cd ../frontend
npm run build
```

---

## 🔄 CI/CD Pipeline (GitHub Actions)

The repository includes automated CI/CD workflows under [`.github/workflows/`](.github/workflows/):

```mermaid
graph LR
    A["1. Validate & Lint<br/>(Ruff + Syntax + Audit)"] --> B["2. Backend Tests<br/>(PyTest on Py3.12 & 3.13)"]
    A --> C["3. Frontend Build<br/>(Vite Production Dist)"]
    B --> D["4. Container Builds<br/>(Docker Images)"]
    C --> D
    D --> E["5. Continuous Deployment<br/>(Staging / Production)"]
```

1. **`ci.yml`**: Triggers on every push & pull request to `main`/`master`/`develop`. Executes code validation, multi-version test matrices, frontend production builds, container builds, and deployment verification.
2. **`deploy.yml`**: Dispatches target environment deployments to staging or production with container registry publishing (`ghcr.io`).

---

## ⚙️ Environment Configuration

Create a `.env` file inside `backend/`:

```env
# Database Connection
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bugflow_db

# Security & JWT Tokens
SECRET_KEY=your-super-secret-jwt-key-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=1440
ALGORITHM=HS256

# AI Configuration (Optional — built-in dense vector math works offline)
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

---

## 🔑 Key API Endpoints Matrix

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/auth/register` | Register new user account |
| `POST` | `/api/auth/login` | Login and receive JWT access token |
| `GET` | `/api/auth/me` | Retrieve authenticated user profile |
| `PUT` | `/api/auth/profile` | Update profile (username, email, password) |
| `GET` | `/api/issues` | List defects with filtering & search |
| `POST` | `/api/projects/{id}/issues` | Create new defect ticket |
| `PUT` | `/api/issues/{id}` | Update defect details & workflow status |
| `GET` | `/api/issues/{id}/pdf` | Stream individual defect PDF report |
| `GET` | `/api/projects/{id}/pdf` | Stream complete project summary PDF |
| `GET` | `/api/attachments/{id}/download` | Authenticated attachment file stream |
| `POST` | `/api/ai/classify-defect` | Suggest Category, Module, Type, Severity |
| `POST` | `/api/ai/semantic-search` | Conceptual vector similarity search |
| `GET` | `/api/issues/{id}/resolution-assistance` | Generate checklist, similar bugs & fix |
| `POST` | `/api/ai/fix-code` | Code Doctor direct syntax & semantic repair |
| `POST` | `/api/ai/sprint-health/{id}` | Predict sprint delivery health & risk score |
| `POST` | `/api/ai/chat` | AI Mentor conversational Q&A and defect guidance |
| `GET` | `/api/ai/chat/topics` | Fetch categorized starter questions & prompt topics |

---

## 🛡️ User Roles & Permissions

BugFlow includes fine-grained **Role-Based Access Control (RBAC)**:
* 👑 **Admin:** Full access across all projects, system metrics, and user role management.
* 📋 **Project Manager:** Project configuration, sprint management, and team assignment.
* 💻 **Developer:** Issue resolution, status transitions, Code Doctor, and resolution assistance.
* 🧪 **QA Tester:** Defect creation, classification assistance, verification, and PDF report export.
* 📝 **Reporter:** Submitting bug tickets and tracking issue progress.

---

## 📄 License & Attribution

Distributed under the **MIT License**. Created with ❤️ for software engineering teams.
