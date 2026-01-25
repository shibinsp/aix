# AI CyberX - Application Workflow Documentation

> Comprehensive workflow diagrams and documentation for the AI-powered cybersecurity learning platform.

---

## Table of Contents

1. [Authentication Workflow](#1-authentication-workflow)
2. [AI-Powered Course Generation](#2-ai-powered-course-generation-workflow)
3. [Lab Session Workflow](#3-lab-session-workflow)
4. [AI Chat/Tutoring Workflow](#4-ai-chattutoring-workflow)
5. [Learning & Progress Tracking](#5-learning--progress-tracking-workflow)
6. [Organization & Multi-Tenancy](#6-organization--multi-tenancy-workflow)
7. [Admin Dashboard Workflow](#7-admin-dashboard-workflow)
8. [Real-Time WebSocket Communication](#8-real-time-websocket-communication)
9. [Complete User Journey](#9-complete-user-journey)
10. [System Interactions Summary](#10-summary-key-system-interactions)

---

## 1. Authentication Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         USER AUTHENTICATION FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  User    │────▶│   Frontend   │────▶│   FastAPI   │────▶│  PostgreSQL  │
│ (Browser)│     │  (Next.js)   │     │   Backend   │     │   Database   │
└──────────┘     └──────────────┘     └─────────────┘     └──────────────┘
```

### Registration Flow

```
User ──▶ /register page ──▶ POST /api/v1/auth/register
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            Check email exists?                 Check username exists?
                    │                                   │
                    └─────────────┬─────────────────────┘
                                  ▼
                     ┌────────────────────────┐
                     │  Hash password (bcrypt)│
                     │  Create User record    │
                     │  Generate JWT token    │
                     └────────────────────────┘
                                  │
                                  ▼
                     Return: { access_token, user }
                                  │
                                  ▼
                     Store token in localStorage
                     Redirect to Dashboard
```

### Login Flow

```
User ──▶ /login page ──▶ POST /api/v1/auth/login
                                      │
                                      ▼
                     ┌────────────────────────────┐
                     │ Find user by email/username│
                     │ Verify password (bcrypt)   │
                     │ Check is_active status     │
                     │ Update last_login          │
                     │ Generate JWT token         │
                     └────────────────────────────┘
                                      │
                    ┌─────────────────┴─────────────────┐
                    ▼                                   ▼
            Success: Return token              Fail: 401 Unauthorized
                    │
                    ▼
     Store in Zustand (authStore) + localStorage
     Fetch org membership (if any)
     Redirect to Dashboard
```

### Token Validation (Every API Request)

```
Request ──▶ Authorization: Bearer <token>
                    │
                    ▼
         ┌─────────────────────────┐
         │ Decode JWT (python-jose)│
         │ Extract user_id from sub│
         │ Validate expiration     │
         └─────────────────────────┘
                    │
          ┌────────┴────────┐
          ▼                 ▼
    Valid: Continue    Invalid: 401
```

### Key Files

- `backend/app/api/routes/auth.py` - Authentication endpoints
- `backend/app/core/security.py` - JWT token handling, password hashing
- `frontend/src/store/authStore.ts` - Frontend auth state management

---

## 2. AI-Powered Course Generation Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ADVANCED COURSE GENERATION PIPELINE                       │
│                           (9-Stage Process)                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Pipeline Overview

```
User Request: POST /api/v1/courses/generate/advanced
                    │
                    ▼
    ┌───────────────────────────────────┐
    │ 1. VALIDATION & SETUP             │
    │    • Check user course limits     │
    │    • Check AI generation limits   │
    │    • Create Course placeholder    │
    │    • Create CourseGenerationJob   │
    │    • Start background task        │
    └───────────────────────────────────┘
```

### Stage 1: Structure Generation (5%)

```
    ┌───────────────────────────────────┐    ┌─────────────────────┐
    │ STAGE: STRUCTURE                  │───▶│  LLM API Call       │
    │    • Generate course outline      │    │  (Mistral/OpenAI/   │
    │    • Create modules (3-10)        │    │   Claude/Gemini)    │
    │    • Create lesson placeholders   │    └─────────────────────┘
    └───────────────────────────────────┘
```

### Stage 2: Content Generation (50%)

```
    ┌───────────────────────────────────┐
    │ STAGE: CONTENT                    │
    │    For each lesson:               │
    │    • Generate 2000+ word content  │
    │    • Create ContentBlock (TEXT)   │
    │    • Update lesson word_count     │
    │    • Update job progress          │
    └───────────────────────────────────┘
```

### Stage 3: Lab Generation (15%)

```
    ┌───────────────────────────────────┐
    │ STAGE: LABS                       │
    │    For lab-type lessons:          │
    │    • Generate lab objectives      │
    │    • Generate flags with hints    │
    │    • Generate instructions        │
    │    • Create Lab entity            │
    │    • Link lab_id to lesson        │
    └───────────────────────────────────┘
```

### Stage 4: Code Examples (8%)

```
    ┌───────────────────────────────────┐
    │ STAGE: CODE_EXAMPLES              │
    │    • Identify code-worthy lessons │
    │    • Generate code snippets       │
    │    • Create ContentBlock (CODE)   │
    │    • Add syntax highlighting meta │
    └───────────────────────────────────┘
```

### Stage 5: Diagrams (5%)

```
    ┌───────────────────────────────────┐    ┌─────────────────────┐
    │ STAGE: DIAGRAMS                   │───▶│  Mermaid Generator  │
    │    • Analyze lesson content       │    │  (AI-generated      │
    │    • Generate Mermaid code        │    │   flowcharts, etc.) │
    │    • Create ContentBlock (DIAGRAM)│    └─────────────────────┘
    └───────────────────────────────────┘
```

### Stage 6: Images (5%)

```
    ┌───────────────────────────────────┐    ┌─────────────────────┐
    │ STAGE: IMAGES                     │───▶│  External APIs:     │
    │    • Search relevant images       │    │  • Unsplash         │
    │    • Create ContentBlock (IMAGE)  │    │  • Pexels           │
    │    • Store URL + attribution      │    │  • Wikimedia        │
    └───────────────────────────────────┘    └─────────────────────┘
```

### Stage 7: Wikipedia Integration (5%)

```
    ┌───────────────────────────────────┐    ┌─────────────────────┐
    │ STAGE: WIKIPEDIA                  │───▶│  Wikipedia API      │
    │    • Search related articles      │    │  • Title, Summary   │
    │    • Extract summaries            │    │  • Thumbnail, URL   │
    │    • Create ContentBlock (WIKI)   │    └─────────────────────┘
    └───────────────────────────────────┘
```

### Stage 8: Quiz Generation (5%)

```
    ┌───────────────────────────────────┐    ┌─────────────────────┐
    │ STAGE: QUIZZES                    │───▶│  Quiz Generator     │
    │    • Generate MCQ questions       │    │  (AI-powered)       │
    │    • Generate answers + rationale │    │                     │
    │    • Create ContentBlock (QUIZ)   │    └─────────────────────┘
    └───────────────────────────────────┘
```

### Stage 9: Review (2%)

```
    ┌───────────────────────────────────┐
    │ STAGE: REVIEW                     │
    │    • Verify all content blocks    │
    │    • Calculate estimated_hours    │
    │    • Set is_published = true      │
    │    • Mark job COMPLETED           │
    └───────────────────────────────────┘
                    │
                    ▼
            Course Ready!
```

### Progress Tracking

```
Frontend polls: GET /api/v1/courses/generate/{job_id}/status
                    │
                    ▼
    Returns: {
        current_stage: "CONTENT",
        progress_percent: 45,
        lessons_completed: 8,
        total_lessons: 20,
        current_lesson: "SQL Injection Basics"
    }
                    │
                    ▼
    Frontend displays progress bar + localStorage persistence
```

### Key Files

- `backend/app/api/routes/courses.py` - Course endpoints
- `backend/app/services/ai/course_generator.py` - Generation pipeline
- `backend/app/services/ai/teaching_engine.py` - LLM interactions
- `backend/app/services/ai/diagram_generator.py` - Mermaid generation
- `backend/app/services/ai/quiz_generator.py` - Quiz generation

---

## 3. Lab Session Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          LAB SESSION WORKFLOW                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Start Lab Session

```
User clicks "Start Lab" ──▶ POST /api/v1/labs/{lab_id}/sessions
                                        │
                                        ▼
                    ┌──────────────────────────────────────┐
                    │ 1. Check user lab limits             │
                    │ 2. Check for existing active session │
                    │ 3. Determine environment backend     │
                    └──────────────────────────────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
              Kubernetes            Docker              Simulation
                    │                   │                   │
                    ▼                   ▼                   ▼
    ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
    │ k8s_env_manager    │ │ persistent_env_mgr │ │ Mock connection    │
    │ • Create namespace │ │ • Check docker     │ │ info for dev       │
    │ • Deploy pod       │ │ • Start container  │ │                    │
    │ • Expose service   │ │ • Map ports        │ │                    │
    └────────────────────┘ └────────────────────┘ └────────────────────┘
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                    ┌──────────────────────────────────────┐
                    │ Create LabSession record:            │
                    │ • status: RUNNING                    │
                    │ • access_url (VNC/SSH)               │
                    │ • expires_at (timeout)               │
                    │ • container_ids                      │
                    └──────────────────────────────────────┘
                                        │
                                        ▼
                    Return: { session_id, access_url, vnc_password }
```

### Terminal Access (WebSocket)

```
Frontend ──▶ WebSocket: ws://host/ws/terminal/{session_id}
                    │
                    ▼
    ┌──────────────────────────────────────────────────────┐
    │                  terminal_service.py                  │
    │  ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │
    │  │   xterm.js  │◀──▶│  WebSocket  │◀──▶│ Container│  │
    │  │  (Frontend) │    │   Handler   │    │  stdin/  │  │
    │  │             │    │             │    │  stdout  │  │
    │  └─────────────┘    └─────────────┘    └──────────┘  │
    └──────────────────────────────────────────────────────┘
                    │
                    ▼
    Commands logged for objective verification
```

### Flag Submission

```
User finds flag ──▶ POST /api/v1/labs/sessions/{id}/flags
                            { flag: "FLAG{example}" }
                                        │
                                        ▼
                    ┌──────────────────────────────────────┐
                    │ Loop through lab.flags:              │
                    │ • Compare submitted value            │
                    │ • Check if already captured          │
                    │ • Award points if new                │
                    │ • Update session.flags_captured      │
                    └──────────────────────────────────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    ▼                                       ▼
            Correct: {                              Incorrect: {
                correct: true,                          correct: false,
                flag_name: "flag1",                     message: "Try again!"
                points: 50                          }
            }
```

### Objective Auto-Detection

```
POST /api/v1/labs/sessions/{id}/check-objectives
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ objective_verifier.py                │
    │ • Get command history from session   │
    │ • For each objective:                │
    │   - Check command_pattern regex      │
    │   - Check file existence             │
    │   - Check output patterns            │
    │ • Update session.completed_objectives│
    └──────────────────────────────────────┘
                    │
                    ▼
    Return: { completed_objectives: [0,1,3], total: 5 }
```

### End Lab Session

```
POST /api/v1/labs/sessions/{id}/stop
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ • Mark session TERMINATED            │
    │ • Set completed_at timestamp         │
    │ • Update user.total_labs_completed   │
    │ • NOTE: Desktop env stays running!   │
    └──────────────────────────────────────┘
```

### Key Files

- `backend/app/api/routes/labs.py` - Lab endpoints
- `backend/app/services/labs/lab_manager.py` - Lab orchestration
- `backend/app/services/labs/docker_lab_manager.py` - Docker management
- `backend/app/services/labs/k8s_lab_manager.py` - Kubernetes management
- `backend/app/services/labs/terminal_service.py` - Terminal WebSocket
- `backend/app/services/labs/objective_verifier.py` - Objective checking

---

## 4. AI Chat/Tutoring Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AI TUTORING CHAT WORKFLOW                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Create Chat Session

```
POST /api/v1/chat/sessions
    {
        title: "Learning SQL Injection",
        teaching_mode: "socratic",  // lecture | socratic | hands_on | challenge
        topic: "SQL Injection"
    }
                    │
                    ▼
    Create ChatSession record ──▶ Return session_id
```

### Send Message (Non-Streaming)

```
POST /api/v1/chat/sessions/{id}/messages
    { content: "How do SQL injections work?" }
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ 1. Sanitize user input               │
    │ 2. Save ChatMessage (role: USER)     │
    │ 3. Get RAG context from ChromaDB     │
    │ 4. Build message history (last 20)   │
    └──────────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │         teaching_engine.py           │
    │                                      │
    │  System Prompt based on:             │
    │  • teaching_mode (socratic/lecture)  │
    │  • user.skill_level                  │
    │  • RAG context (knowledge base)      │
    │                                      │
    │  ┌─────────────────────────────────┐ │
    │  │   LLM API (Multi-Provider)     │ │
    │  │   • OpenAI GPT-4               │ │
    │  │   • Anthropic Claude           │ │
    │  │   • Mistral Large              │ │
    │  │   • Google Gemini              │ │
    │  └─────────────────────────────────┘ │
    └──────────────────────────────────────┘
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ • Save ChatMessage (role: ASSISTANT) │
    │ • Attach rag_context sources         │
    │ • Update session.message_count       │
    └──────────────────────────────────────┘
                    │
                    ▼
    Return: { content: "SQL injection is...", sources: [...] }
```

### Send Message (Streaming)

```
POST /api/v1/chat/sessions/{id}/messages/stream
                    │
                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                 Server-Sent Events (SSE)                     │
    │                                                              │
    │  data: {"type": "sources", "data": [...]}                    │
    │  data: {"type": "content", "data": "SQL"}                    │
    │  data: {"type": "content", "data": " injection"}             │
    │  data: {"type": "content", "data": " is a..."}               │
    │  ...                                                         │
    │  data: {"type": "done", "message_id": "uuid"}                │
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
                    │
                    ▼
    Frontend renders tokens incrementally (typing effect)
```

### RAG Knowledge Base Flow

```
User Query ──▶ knowledge_base.py
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ 1. Generate embedding for query      │
    │    (Sentence-Transformers)           │
    │                                      │
    │ 2. Search ChromaDB vector store      │
    │    • Semantic similarity search      │
    │    • Top-K results (default: 5)      │
    │                                      │
    │ 3. Return relevant chunks + sources  │
    └──────────────────────────────────────┘
                    │
                    ▼
    Inject context into LLM system prompt
```

### Teaching Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Lecture** | Direct explanation, comprehensive | Learning new concepts |
| **Socratic** | Question-based, guided discovery | Deep understanding |
| **Hands-on** | Practical, step-by-step guidance | Skill building |
| **Challenge** | Minimal hints, problem-solving | Assessment |

### Key Files

- `backend/app/api/routes/chat.py` - Chat endpoints
- `backend/app/api/websockets/chat.py` - WebSocket handler
- `backend/app/services/ai/teaching_engine.py` - AI response generation
- `backend/app/services/rag/knowledge_base.py` - RAG system

---

## 5. Learning & Progress Tracking Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    LEARNING & PROGRESS TRACKING WORKFLOW                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Course Discovery

```
User visits /learning ──▶ GET /api/v1/courses
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │ Filter by:                       │
                    │ • category (Web Security, etc.)  │
                    │ • difficulty (beginner, etc.)    │
                    │ • search query                   │
                    │ • my_courses=true (user's own)   │
                    └──────────────────────────────────┘
                                    │
                                    ▼
                    Display course cards with:
                    • Title, description, difficulty
                    • Estimated hours, points
                    • Module/lesson count
```

### Lesson Viewing

```
User clicks lesson ──▶ GET /api/v1/courses/{id}/lessons/{lessonId}/full
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │ Return LessonFullResponse:       │
                    │ • Main content (markdown)        │
                    │ • content_blocks[] (ordered)     │
                    │   - TEXT, CODE, DIAGRAM          │
                    │   - IMAGE, VIDEO, QUIZ           │
                    │   - WIKIPEDIA, CALLOUT           │
                    │ • external_resources[]           │
                    │ • lab (if attached)              │
                    └──────────────────────────────────┘
                                    │
                                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                   ContentBlockRenderer                        │
    │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
    │  │  TEXT   │ │  CODE   │ │ DIAGRAM │ │  QUIZ   │ │  IMAGE  │ │
    │  │ (MD)    │ │ (Prism) │ │(Mermaid)│ │  (MCQ)  │ │  (img)  │ │
    │  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
    └──────────────────────────────────────────────────────────────┘
```

### Mark Lesson Complete

```
User finishes lesson ──▶ POST /api/v1/courses/{id}/lessons/{lessonId}/mark-complete
                                    │
                                    ▼
                    ┌──────────────────────────────────┐
                    │ 1. Check if already completed    │
                    │ 2. Create/Update UserLessonProgress│
                    │    • status: "completed"         │
                    │    • completed_at: now           │
                    │    • points_awarded: lesson.points│
                    │ 3. Update user.total_points      │
                    └──────────────────────────────────┘
                                    │
                                    ▼
                    Return: { points_awarded: 10 }
```

### Course Progress

```
GET /api/v1/courses/{id}/progress
                    │
                    ▼
    Return: {
        total_lessons: 20,
        completed_lessons: 8,
        progress_percent: 40,
        total_points_earned: 80,
        is_complete: false
    }
```

### Skill Assessment

```
User completes skill assessment
                    │
                    ▼
    ┌──────────────────────────────────────┐
    │ skill_tracker.py (IRT-based)         │
    │                                      │
    │ • Calculate proficiency (0-5 scale)  │
    │ • Update confidence score            │
    │ • Track assessment history           │
    │ • Map to 8 cybersecurity domains:    │
    │   - Web Security                     │
    │   - Network Security                 │
    │   - Cryptography                     │
    │   - Malware Analysis                 │
    │   - Forensics                        │
    │   - Penetration Testing              │
    │   - Cloud Security                   │
    │   - Incident Response                │
    └──────────────────────────────────────┘
```

### Key Files

- `backend/app/api/routes/courses.py` - Course/lesson endpoints
- `backend/app/models/course.py` - Course, Lesson, UserLessonProgress models
- `backend/app/services/skills/skill_tracker.py` - Skill assessment
- `frontend/src/pages/learning.tsx` - Learning page

---

## 6. Organization & Multi-Tenancy Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    ORGANIZATION MANAGEMENT WORKFLOW                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Create Organization

```
POST /api/v1/organizations
    {
        name: "CyberSec Academy",
        type: "EDUCATIONAL",
        settings: { branding: {...} }
    }
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Create Organization record       │
    │ Create OrganizationMembership:   │
    │ • user_id: creator               │
    │ • org_role: OWNER                │
    │ Create default resource limits   │
    └──────────────────────────────────┘
```

### Invite User

```
POST /api/v1/organizations/{id}/invite
    { email: "user@example.com", role: "MEMBER" }
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Create Invitation record:        │
    │ • token: random UUID             │
    │ • email: target email            │
    │ • org_role: MEMBER               │
    │ • expires_at: +7 days            │
    │ Send email (external service)    │
    └──────────────────────────────────┘
```

### Accept Invitation

```
User clicks invite link ──▶ POST /api/v1/invitations/{token}/accept
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Verify token not expired         │
    │ Create/Update User if needed     │
    │ Create OrganizationMembership    │
    │ Mark invitation as used          │
    └──────────────────────────────────┘
```

### Batch Management

```
POST /api/v1/batches
    {
        name: "Cohort 2024-A",
        organization_id: "...",
        curriculum_id: "...",
        start_date: "2024-01-15"
    }
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ Create Batch record              │
    │ Inherit org resource limits      │
    │ (can override per-batch)         │
    └──────────────────────────────────┘
```

### Resource Limits Hierarchy

```
    ┌─────────────────────────────────────────────────────┐
    │                  LIMIT CHECKING                      │
    │                                                      │
    │   User Request (e.g., start lab)                    │
    │              │                                       │
    │              ▼                                       │
    │   ┌─────────────────────┐                           │
    │   │ User-level override?│──Yes──▶ Use user limit    │
    │   └─────────────────────┘                           │
    │              │ No                                    │
    │              ▼                                       │
    │   ┌─────────────────────┐                           │
    │   │ Batch-level limit?  │──Yes──▶ Use batch limit   │
    │   └─────────────────────┘                           │
    │              │ No                                    │
    │              ▼                                       │
    │   ┌─────────────────────┐                           │
    │   │ Org-level limit?    │──Yes──▶ Use org limit     │
    │   └─────────────────────┘                           │
    │              │ No                                    │
    │              ▼                                       │
    │       Use system defaults                           │
    │                                                      │
    └─────────────────────────────────────────────────────┘
```

### Organization Roles

| Role | Permissions |
|------|-------------|
| **OWNER** | Full control, delete org, transfer ownership |
| **ADMIN** | Manage users, batches, settings |
| **INSTRUCTOR** | View progress, manage content |
| **MEMBER** | Access courses, labs, standard features |

### Key Files

- `backend/app/api/routes/organizations.py` - Organization endpoints
- `backend/app/api/routes/batches.py` - Batch endpoints
- `backend/app/api/routes/invitations.py` - Invitation endpoints
- `backend/app/services/limits/limit_enforcer.py` - Resource limits
- `backend/app/models/organization.py` - Organization models

---

## 7. Admin Dashboard Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ADMIN DASHBOARD WORKFLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Admin Access Check

```
Every admin route:
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ get_current_admin dependency     │
    │ • Validate JWT token             │
    │ • Load user from DB              │
    │ • Check role in [ADMIN, SUPER_ADMIN]│
    │ • Return 403 if not admin        │
    └──────────────────────────────────┘
```

### System Statistics

```
GET /api/v1/admin/stats
                    │
                    ▼
    Return: {
        total_users: 1500,
        active_users_today: 120,
        total_courses: 85,
        total_labs: 42,
        total_organizations: 15,
        active_lab_sessions: 8,
        storage_used_gb: 45.2
    }
```

### User Management

```
GET /api/v1/admin/users?search=john&role=USER
                    │
                    ▼
    Return paginated user list with:
    • id, email, username, role
    • is_active, last_login
    • organization membership
    • total_points, courses_completed
```

### Ban User

```
POST /api/v1/admin/users/{id}/ban
    { reason: "Violation of TOS" }
                    │
                    ▼
    ┌──────────────────────────────────┐
    │ • Set user.is_active = false     │
    │ • Log to AuditLog:               │
    │   - action: "user_banned"        │
    │   - admin_id: current admin      │
    │   - target_user_id: banned user  │
    │   - details: { reason: "..." }   │
    └──────────────────────────────────┘
```

### Audit Log

```
GET /api/v1/admin/audit?action=user_banned&from=2024-01-01
                    │
                    ▼
    Return: [{
        timestamp: "2024-01-15T10:30:00Z",
        admin_id: "...",
        admin_email: "admin@company.com",
        action: "user_banned",
        target_id: "...",
        details: { reason: "..." }
    }, ...]
```

### System Health

```
GET /api/v1/admin/monitoring/health
                    │
                    ▼
    Return: {
        status: "healthy",
        database: { status: "connected", latency_ms: 5 },
        redis: { status: "connected" },
        ai_service: { status: "available", model: "mistral-large" },
        docker: { status: "running", containers: 12 },
        kubernetes: { status: "not_configured" }
    }
```

### Admin Permissions (60+)

| Category | Permissions |
|----------|-------------|
| **Users** | view, create, update, delete, ban, role_assign |
| **Content** | view, create, update, delete, approve, publish |
| **Labs** | view, create, delete, manage_all, vm_start, vm_stop |
| **System** | settings, api_keys, audit, monitoring |
| **Organizations** | create, view, update, delete, manage_members |

### Key Files

- `backend/app/api/routes/admin/` - Admin route modules
- `backend/app/core/dependencies.py` - Admin dependency checks
- `backend/app/models/user.py` - User roles, permissions
- `backend/app/services/audit/audit_service.py` - Audit logging

---

## 8. Real-Time WebSocket Communication

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WEBSOCKET COMMUNICATION FLOWS                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Chat WebSocket

```
Client ──▶ ws://host/ws/chat/{session_id}?token=<jwt>
                    │
                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                    WebSocket Handler                          │
    │                                                               │
    │  on_connect:                                                  │
    │  • Validate JWT token                                         │
    │  • Verify session ownership                                   │
    │  • Add to active connections                                  │
    │                                                               │
    │  on_message({ content: "...", teaching_mode: "..." }):        │
    │  • Save user message to DB                                    │
    │  • Query RAG knowledge base                                   │
    │  • Stream LLM response token by token                         │
    │  • Save complete response to DB                               │
    │                                                               │
    │  on_disconnect:                                               │
    │  • Remove from active connections                             │
    │  • Update session.last_message_at                             │
    └──────────────────────────────────────────────────────────────┘
```

### Terminal WebSocket

```
Client ──▶ ws://host/ws/terminal/{session_id}?token=<jwt>
                    │
                    ▼
    ┌──────────────────────────────────────────────────────────────┐
    │                  Terminal Service                             │
    │                                                               │
    │  ┌─────────┐         ┌────────────┐         ┌─────────────┐  │
    │  │ xterm.js│◀───────▶│  WebSocket │◀───────▶│  Container  │  │
    │  │ Client  │  JSON   │   Handler  │  pty    │   Shell     │  │
    │  └─────────┘  msgs   └────────────┘  I/O    └─────────────┘  │
    │                                                               │
    │  Message Types:                                               │
    │  • { type: "input", data: "ls -la\n" }                       │
    │  • { type: "output", data: "total 64\n..." }                 │
    │  • { type: "resize", cols: 120, rows: 40 }                   │
    │  • { type: "ping" } / { type: "pong" }                       │
    │                                                               │
    │  Command Logging:                                             │
    │  • Log commands for objective verification                   │
    │  • Store in session command_history                          │
    └──────────────────────────────────────────────────────────────┘
```

### Key Files

- `backend/app/api/websockets/chat.py` - Chat WebSocket handler
- `backend/app/api/websockets/terminal.py` - Terminal WebSocket handler
- `backend/app/services/labs/terminal_service.py` - Terminal I/O service

---

## 9. Complete User Journey

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE USER JOURNEY                                 │
└─────────────────────────────────────────────────────────────────────────────┘

    ┌─────────┐
    │  START  │
    └────┬────┘
         │
         ▼
    ┌─────────────────┐
    │   1. REGISTER   │──▶ Create account, JWT token
    └────────┬────────┘
             │
             ▼
    ┌─────────────────┐
    │  2. DASHBOARD   │──▶ View stats, recent activity
    └────────┬────────┘
             │
    ┌────────┴────────┬──────────────────┬──────────────────┐
    │                 │                  │                  │
    ▼                 ▼                  ▼                  ▼
┌─────────┐    ┌───────────┐    ┌───────────────┐    ┌────────────┐
│ COURSES │    │   LABS    │    │  AI TUTOR     │    │   NEWS     │
│         │    │           │    │   (Chat)      │    │            │
└────┬────┘    └─────┬─────┘    └───────┬───────┘    └──────┬─────┘
     │               │                  │                   │
     ▼               ▼                  ▼                   ▼
Browse/       Start lab          Ask questions       Read cyber
Generate      session            Get explanations    news, generate
courses                                              courses from
     │               │                  │            articles
     ▼               ▼                  ▼                   │
Take lessons  Complete          Learn with              │
Mark complete objectives        4 teaching modes         │
     │               │                  │                   │
     ▼               ▼                  ▼                   │
┌─────────────────────────────────────────────────────────────────┐
│                     3. TRACK PROGRESS                            │
│  • Points earned        • Courses completed                      │
│  • Labs completed       • Skills assessed                        │
│  • Streaks maintained   • Leaderboard position                   │
└─────────────────────────────────────────────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │ 4. ORGANIZATION │──▶ Join org, batches, group learning
    │    (Optional)   │
    └─────────────────┘
```

---

## 10. Summary: Key System Interactions

| Component | Interacts With | Purpose |
|-----------|---------------|---------|
| **Frontend** | REST API, WebSocket | User interface, real-time updates |
| **Auth Routes** | PostgreSQL, JWT | User authentication, token management |
| **Course Generator** | LLM APIs, PostgreSQL, External APIs | AI course creation pipeline |
| **Lab Manager** | Docker/K8s, PostgreSQL | Environment provisioning |
| **Teaching Engine** | LLM APIs, RAG, PostgreSQL | AI-powered tutoring |
| **RAG System** | ChromaDB, Embeddings | Knowledge retrieval |
| **Limit Enforcer** | PostgreSQL | Resource quota management |
| **Progress Tracker** | PostgreSQL, Redis | User progress tracking |
| **Admin Dashboard** | PostgreSQL, System APIs | Platform management |

---

## Data Flow Summary

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Browser   │◀───▶│   Next.js   │◀───▶│   FastAPI   │◀───▶│ PostgreSQL  │
│   (User)    │     │  Frontend   │     │   Backend   │     │  Database   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                    ┌──────────┐         ┌──────────┐         ┌──────────┐
                    │  Redis   │         │ ChromaDB │         │  Docker/ │
                    │  Cache   │         │  Vectors │         │   K8s    │
                    └──────────┘         └──────────┘         └──────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                    ┌──────────┐         ┌──────────┐         ┌──────────┐
                    │  OpenAI  │         │ Anthropic│         │  Mistral │
                    │   API    │         │   API    │         │   API    │
                    └──────────┘         └──────────┘         └──────────┘
```

---

## API Endpoint Summary

| Category | Endpoints | Key Routes |
|----------|-----------|------------|
| **Auth** | 5 | `/auth/register`, `/auth/login`, `/auth/me` |
| **Chat** | 7 | `/chat/sessions`, `/chat/quick-ask` |
| **Courses** | 15+ | `/courses`, `/courses/generate`, `/courses/{id}/lessons` |
| **Labs** | 15+ | `/labs`, `/labs/{id}/sessions`, `/labs/alphha/*` |
| **Organizations** | 8 | `/organizations`, `/organizations/{id}/invite` |
| **Admin** | 15+ | `/admin/stats`, `/admin/users`, `/admin/audit` |
| **WebSocket** | 2 | `ws/chat/{id}`, `ws/terminal/{id}` |

---

*Generated for AI CyberX Platform - Last Updated: 2024*
