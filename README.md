# AI CyberX - AI-Powered Cybersecurity Learning Platform

An autonomous, AI-powered cybersecurity education platform that teaches students without human tutors, generates personalized learning paths, creates custom labs on-demand, and adapts to individual skill levels.

## 🚀 Quick Links

- **Production**: [https://cyyberaix.in](https://cyyberaix.in)
- **Local Dev**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs (local) | https://cyyberaix.in/api/v1/docs (prod)
- **Admin Login**: `admin@cyberx.com` / `admin123`

## ✅ Current Status (Updated: 2026-01-19)

Both development and production deployments are **fully operational**:

- ✅ **Local Docker Compose**: All services running, API endpoints working
- ✅ **Production Kubernetes**: 5 backend + 2 frontend replicas, database migrated to v005
- ✅ **Database**: PostgreSQL with soft delete support (migration 005_soft_delete)
- ✅ **Fixed**: All 500 errors resolved (courses, labs, course generation endpoints)
- ✅ **SSL**: Let's Encrypt TLS enabled on production

## 📋 Recent Updates

### 2026-01-19 - Critical Bug Fixes
**Issues Resolved:**
1. **Docker Compose Configuration** - Fixed frontend API URL from production domain to `http://localhost:8000`
2. **Database Schema Mismatch** - Applied migration 005 adding soft delete columns (`is_deleted`, `deleted_at`, `deleted_by`)
3. **500 Errors** - Fixed courses, labs, and course generation API endpoints
4. **Kubernetes Deployment** - Rolled out backend pods with database migration

**Database Changes:**
- Added soft delete support to `courses` and `labs` tables
- Added `course_id` foreign key to `labs` table for cascade relationships
- Added indexes on `is_deleted` columns for performance
- Migration version: `005_soft_delete` ✅

**Deployments Updated:**
- **Docker Compose**: Frontend rebuilt with correct API configuration
- **Kubernetes**: All 5 backend pods restarted after migration

## Features

### Core Learning
- **AI Teaching Engine**: Multi-model support (OpenAI GPT, Anthropic Claude, Mistral, Google Gemini) with adaptive teaching
- **RAG Knowledge Base**: ChromaDB-powered retrieval with up-to-date cybersecurity knowledge
- **Dynamic Course Generation**: 9-stage AI pipeline for creating personalized courses
- **Hands-on Labs**: Docker/VM-based lab environments with real-time terminals
- **Skill Assessment**: IRT-based tracking across 8 cybersecurity domains
- **Real-time AI Tutor**: WebSocket-powered chat with streaming responses

### Organization Management
- **Multi-tenant Support**: Organizations with Enterprise, Educational, and Government types
- **Batch/Cohort Management**: Group learners into batches with custom curricula
- **Role-based Access Control**: 60+ granular permissions (Owner, Admin, Instructor, Member)
- **Resource Quotas**: Configurable limits at organization, batch, and user levels

### Admin Features
- **Admin Dashboard**: System monitoring and user management
- **Audit Logging**: Track all user and admin actions
- **Performance Monitoring**: Server health and resource utilization
- **Invitation System**: Email-based user onboarding

## Technology Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand, xterm.js |
| **Backend** | FastAPI, Python 3.11, SQLAlchemy 2.0 (async), Pydantic |
| **Database** | PostgreSQL 15, Redis 7, ChromaDB |
| **AI/ML** | OpenAI, Anthropic, Mistral, Gemini, Sentence-Transformers |
| **Infrastructure** | Docker, Nginx, Certbot (SSL), QEMU/KVM (VMs) |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js + React)                    │
│  Dashboard │ Learning UI │ Lab Terminal │ Admin Panel │ Portal   │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API + WebSocket
┌────────────────────────────▼────────────────────────────────────┐
│                      API LAYER (FastAPI)                         │
│  24 REST Endpoints │ 2 WebSocket Handlers │ JWT Auth │ RBAC     │
│  Auth │ Chat │ Courses │ Labs │ Skills │ Organizations │ Admin   │
└────────────────────────────┬────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  AI SERVICES   │  │  LAB SERVICES  │  │  RAG SYSTEM    │
│ Teaching Engine│  │ Docker Manager │  │ ChromaDB       │
│ Course Gen     │  │ VM Manager     │  │ Embeddings     │
│ Quiz Gen       │  │ Terminal Svc   │  │ Retrieval      │
└────────────────┘  └────────────────┘  └────────────────┘
         │                   │                   │
         └───────────────────┼───────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                │
│      PostgreSQL (ORM)  │  ChromaDB (Vectors)  │  Redis (Cache)  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- **Docker** (v20.0+) and **Docker Compose** (v2.0+)
- **AI API Key**: At least one of OpenAI, Anthropic, Mistral, or Gemini
- **8GB RAM** minimum (16GB recommended for labs)

### 1. Clone and Configure

```bash
git clone https://github.com/yourusername/AI_CyberX.git
cd AI_CyberX

# Copy environment template from infrastructure/docker
cp infrastructure/docker/.env.example .env

# Edit configuration
nano .env
```

### 2. Required Environment Variables

```bash
# Security (REQUIRED)
SECRET_KEY=<generate with: openssl rand -hex 32>
POSTGRES_USER=cyberx
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=cyberx

# AI API Keys (at least ONE required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
MISTRAL_API_KEY=...
GEMINI_API_KEY=...

# Server
SERVER_HOST=localhost
CORS_ORIGINS=["http://localhost:3000"]
DEFAULT_AI_MODEL=mistral-large-latest
```

### 3. Start the Platform

```bash
# Option 1: Using the startup script (recommended)
chmod +x start.sh
./start.sh

# Option 2: Using Docker Compose directly
docker compose up -d

# Check service status
docker compose ps
```

### 4. Access the Platform

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | admin@cyberx.com / admin123 |
| **Backend API** | http://localhost:8000 | - |
| **API Docs** | http://localhost:8000/docs | Interactive Swagger UI |
| **Health Check** | http://localhost:8000/health | System status |

> **Note**: Admin user is automatically created on first startup. Use credentials above to login.

### 5. Verify Installation

```bash
# Check all services are running
docker compose ps

# View backend logs
docker logs cyberx-backend

# View frontend logs
docker logs cyberx-frontend

# Test API health
curl http://localhost:8000/health
```

## Production Deployment

### Option 1: Kubernetes (Recommended for Production)

The platform is production-ready on Kubernetes with high availability:

```bash
# Prerequisites
# - Kubernetes cluster (k3s, EKS, GKE, AKS, etc.)
# - kubectl configured
# - cert-manager installed for SSL

# 1. Create namespace
kubectl create namespace cyberaix-system
kubectl create namespace cyberaix-data

# 2. Configure secrets
kubectl create secret generic api-secrets -n cyberaix-system \
  --from-literal=SECRET_KEY=<your-secret-key> \
  --from-literal=OPENAI_API_KEY=<your-key> \
  --from-literal=MISTRAL_API_KEY=<your-key>

kubectl create secret generic db-secrets -n cyberaix-data \
  --from-literal=POSTGRES_USER=cyberx \
  --from-literal=POSTGRES_PASSWORD=<your-password> \
  --from-literal=POSTGRES_DB=cyberx

# 3. Deploy database
kubectl apply -f kubernetes/database/

# 4. Deploy application
kubectl apply -f kubernetes/backend/
kubectl apply -f kubernetes/frontend/
kubectl apply -f kubernetes/ingress/

# 5. Apply database migrations
kubectl exec -n cyberaix-system deployment/backend -- alembic upgrade head

# 6. Check deployment status
kubectl get pods -n cyberaix-system
kubectl get ingress -n cyberaix-system
```

**Current Production Setup**:
- **Domain**: https://cyyberaix.in
- **Backend**: 5 replicas with horizontal pod autoscaling
- **Frontend**: 2 replicas with horizontal pod autoscaling
- **Database**: StatefulSet with persistent storage
- **Ingress**: Traefik with Let's Encrypt TLS
- **Monitoring**: Built-in health checks and readiness probes

### Option 2: Docker Compose with Nginx + SSL

For simpler production deployments:

```bash
cd infrastructure/docker

# Configure production environment
cp .env.example .env.production
nano .env.production  # Set production values

# Start with production compose
docker compose -f docker-compose.prod.yml up -d
```

### Production Checklist

- [x] Set `DEBUG=false`
- [x] Use strong `SECRET_KEY` and `POSTGRES_PASSWORD`
- [x] Configure proper `CORS_ORIGINS` for your domain
- [x] Set up SSL certificates (cert-manager/Certbot)
- [x] Apply all database migrations
- [ ] Configure firewall rules
- [ ] Set up backup for PostgreSQL data
- [x] Configure rate limiting (60/min general, 10/min auth)
- [x] Enable audit logging
- [ ] Configure monitoring and alerting

## Project Structure

```
AI_CyberX/
├── backend/                      # FastAPI Backend
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/          # 24 REST endpoint modules
│   │   │   └── websockets/      # Chat & Terminal WebSocket
│   │   ├── core/                # Config, Auth, Security, DB
│   │   ├── models/              # 13 SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic request/response
│   │   ├── services/
│   │   │   ├── ai/              # Teaching Engine, Course Gen
│   │   │   ├── rag/             # Knowledge Base, Doc Processor
│   │   │   ├── labs/            # Lab Manager, VM Manager
│   │   │   └── skills/          # Skill Assessment
│   │   └── main.py
│   ├── alembic/                 # Database migrations
│   └── requirements.txt
│
├── frontend/                     # Next.js Frontend
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/          # Layout, Header, Sidebar
│   │   │   ├── labs/            # LabTerminal, SplitScreen
│   │   │   └── courses/         # ContentBlockRenderer
│   │   ├── pages/               # 30+ Next.js pages
│   │   │   ├── admin/           # Admin panel
│   │   │   ├── org/             # Organization management
│   │   │   └── portal/          # Organization portal
│   │   ├── services/api.ts      # Axios API client
│   │   └── store/               # Zustand state management
│   └── package.json
│
├── infrastructure/
│   └── docker/
│       ├── Dockerfile.backend
│       ├── Dockerfile.frontend
│       ├── docker-compose.yml       # Development
│       ├── docker-compose.prod.yml  # Production
│       ├── nginx/                   # Nginx config
│       └── certbot/                 # SSL certificates
│
├── data/
│   ├── knowledge_base/          # RAG documents
│   ├── lab_templates/           # Lab configurations
│   └── vector_db/               # ChromaDB storage
│
└── docker-compose.yml           # Symlink to docker config
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login (returns JWT) |
| GET | `/api/v1/auth/me` | Get current user profile |

### AI Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat/sessions` | Create chat session |
| GET | `/api/v1/chat/sessions` | List user's sessions |
| POST | `/api/v1/chat/sessions/{id}/messages` | Send message |
| POST | `/api/v1/chat/quick-ask` | Quick question (no session) |
| WS | `/ws/chat/{session_id}` | Real-time chat WebSocket |

### Courses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/courses` | List all courses |
| GET | `/api/v1/courses/{id}` | Get course details |
| POST | `/api/v1/courses/generate` | Generate AI course |
| GET | `/api/v1/courses/{id}/lessons/{lessonId}` | Get lesson content |

### Labs
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/labs` | List available labs |
| POST | `/api/v1/labs/{id}/sessions` | Start lab session |
| POST | `/api/v1/labs/sessions/{id}/flags` | Submit flag |
| DELETE | `/api/v1/labs/sessions/{id}` | Stop lab session |
| WS | `/ws/terminal/{session_id}` | Lab terminal WebSocket |

### Organizations (Multi-tenant)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/organizations` | List organizations |
| POST | `/api/v1/organizations` | Create organization |
| GET | `/api/v1/organizations/{id}/members` | List members |
| POST | `/api/v1/organizations/{id}/invite` | Invite member |

### Admin
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/admin/stats` | System statistics |
| GET | `/api/v1/admin/users` | List all users |
| GET | `/api/v1/admin/audit` | Audit logs |

## Database Models

| Model | Description |
|-------|-------------|
| User | User profile with skills, progress, org membership |
| Organization | Multi-tenant organization container |
| Batch | Cohort within organization |
| Course | AI-generated or manual course |
| Module | Course module with lessons |
| Lesson | Lesson with content blocks |
| Lab | Lab definition and configuration |
| LabSession | Active lab instance |
| ChatSession | Chat conversation |
| Skill | Cybersecurity skill taxonomy |
| UserSkill | User's skill proficiency |

## Skill Domains

The platform tracks proficiency (0-5 scale) across 8 domains:

| Domain | Topics |
|--------|--------|
| **Network Security** | TCP/IP, scanning, packet analysis, firewalls |
| **Web Security** | OWASP Top 10, SQL injection, XSS, CSRF |
| **System Security** | Linux/Windows hardening, privilege escalation |
| **Cryptography** | Encryption, hashing, PKI, TLS |
| **Digital Forensics** | Disk, memory, network forensics |
| **Malware Analysis** | Static/dynamic analysis, reverse engineering |
| **Cloud Security** | AWS, Azure, Kubernetes, containers |
| **SOC Operations** | SIEM, threat hunting, incident response |

## Teaching Modes

| Mode | Description |
|------|-------------|
| **Lecture** | Structured educational content with examples |
| **Socratic** | Guided learning through questioning |
| **Hands-on** | Step-by-step practical exercises |
| **Challenge** | Problems to solve independently |

## Lab Types

| Type | Description |
|------|-------------|
| **Tutorial** | Guided walkthrough labs |
| **Challenge** | Independent problem-solving |
| **CTF** | Capture the flag competitions |
| **Simulation** | Real-world scenario simulations |
| **Red vs Blue** | Attack/defense exercises |

## Environment Variables

### Required
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (32+ hex chars) |
| `POSTGRES_USER` | Database username |
| `POSTGRES_PASSWORD` | Database password |
| `POSTGRES_DB` | Database name |
| AI API Key | At least one of OPENAI/ANTHROPIC/MISTRAL/GEMINI |

### Optional
| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | false | Enable debug mode |
| `SERVER_HOST` | localhost | Server hostname |
| `DEFAULT_AI_MODEL` | mistral-large-latest | Default AI model |
| `MAX_CONCURRENT_LABS` | 50 | Max simultaneous labs |
| `LAB_TIMEOUT_MINUTES` | 120 | Lab session timeout |
| `UNSPLASH_ACCESS_KEY` | - | For course images |
| `PEXELS_API_KEY` | - | For course images |

## Security Features

- **Authentication**: JWT tokens with configurable expiry
- **Password Security**: bcrypt hashing via passlib
- **Authorization**: Role-based access control (RBAC)
- **Rate Limiting**: slowapi integration (60/min general, 10/min auth)
- **Lab Isolation**: Containerized environments with network isolation
- **Auto-cleanup**: Labs auto-terminate after timeout
- **Input Validation**: Pydantic (backend) + Zod (frontend)
- **CORS**: Configurable origin whitelist

## Development

### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend
npm install --legacy-peer-deps

# Run with hot reload
npm run dev
```

### Database Migrations

```bash
cd backend

# Check current migration version
alembic current

# View migration history
alembic history

# Create new migration
alembic revision --autogenerate -m "description"

# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision>

# Rollback to previous migration
alembic downgrade -1

# Rollback to specific migration
alembic downgrade <revision>
```

**Current Migration Version**: `005_soft_delete`

**Migration History**:
1. `001_admin_system` - Initial schema with user roles and permissions
2. `002_organization_system` - Multi-tenant organizations and batches
3. `003_lab_course_integration` - Lab and course models
4. `004_user_lesson_progress` - Progress tracking
5. `005_soft_delete` - Soft delete support + course-lab linking ✅

**Important**: Always apply migrations in both development and production:
```bash
# Docker Compose
docker exec cyberx-backend alembic upgrade head

# Kubernetes
kubectl exec -n cyberaix-system deployment/backend -- alembic upgrade head
```

## Troubleshooting

### Common Issues

**500 Errors on API Endpoints (Fixed)**

If you encounter errors like `"column courses.is_deleted does not exist"`:

```bash
# For Docker Compose
docker exec cyberx-backend alembic upgrade head

# For Kubernetes
kubectl exec -n cyberaix-system deployment/backend -- alembic upgrade head
```

**Container won't start**
```bash
# Check logs
docker logs cyberx-backend
docker logs cyberx-frontend

# Check service status
docker compose ps

# Rebuild images
docker compose build --no-cache
docker compose up -d
```

**Database connection error**
```bash
# Check PostgreSQL is running
docker exec cyberx-postgres pg_isready

# Check database version
docker exec cyberx-postgres psql -U cyberx -d cyberx -c "SELECT version_num FROM alembic_version;"

# Reset database (WARNING: Deletes all data)
docker compose down -v
docker compose up -d
```

**Frontend API connection issues**

If the frontend shows network errors:
```bash
# Check frontend API URL configuration
docker exec cyberx-frontend env | grep NEXT_PUBLIC_API_URL

# Should be: http://localhost:8000 for local dev
# Should be: https://your-domain.com for production

# If incorrect, rebuild frontend:
docker compose stop frontend
docker compose rm -f frontend
docker compose build frontend
docker compose up -d frontend
```

**Frontend hydration errors**
- Ensure `hasHydrated` check is in place for auth-dependent components
- Check browser console for specific error messages
- Clear browser localStorage: `localStorage.clear()`

**Kubernetes Pod CrashLoopBackOff**
```bash
# Check pod logs
kubectl logs -n cyberaix-system deployment/backend

# Check pod events
kubectl describe pod -n cyberaix-system <pod-name>

# Verify database migrations
kubectl exec -n cyberaix-system deployment/backend -- alembic current

# Apply missing migrations
kubectl exec -n cyberaix-system deployment/backend -- alembic upgrade head
```

**Admin user not found**
```bash
# Docker Compose: Create admin user manually
docker exec cyberx-backend python -c "
import asyncio
from app.core.database import async_session_maker
from app.models.user import User
from app.models.admin import UserRole
from app.core.security import get_password_hash
from sqlalchemy import select

async def create_admin():
    async with async_session_maker() as db:
        result = await db.execute(select(User).where(User.email == 'admin@cyberx.com'))
        if result.scalar_one_or_none():
            print('Admin user already exists')
            return
        admin = User(
            email='admin@cyberx.com',
            username='admin',
            full_name='Admin User',
            hashed_password=get_password_hash('admin123'),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        db.add(admin)
        await db.commit()
        print('Admin user created')

asyncio.run(create_admin())
"

# Kubernetes: Similar but use kubectl exec
kubectl exec -n cyberaix-system deployment/backend -- python -c "..."
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - See LICENSE file for details.

## Support

- **Issues**: Open an issue on GitHub
- **API Docs**: Visit `/docs` endpoint for Swagger UI
- **Health Check**: GET `/health` for system status
- **Production Site**: https://cyyberaix.in

## Changelog

### Version 1.0.1 (2026-01-19)
**Fixed:**
- Database schema mismatch causing 500 errors on courses/labs endpoints
- Docker Compose frontend API URL configuration for local development
- Applied migration 005_soft_delete to production Kubernetes cluster

**Added:**
- Soft delete support for courses and labs tables
- Course-lab cascade relationship via course_id foreign key
- Comprehensive troubleshooting documentation
- Kubernetes deployment instructions

**Changed:**
- Updated README with current deployment status
- Enhanced database migration documentation
- Improved error handling in API responses

### Version 1.0.0 (2026-01-17)
**Initial Release:**
- AI-powered cybersecurity learning platform
- Multi-model LLM support (OpenAI, Anthropic, Mistral, Gemini)
- Docker/Kubernetes-based lab environments
- Multi-tenant organization support
- RAG knowledge base with ChromaDB
- Full RBAC with 60+ permissions
- Kubernetes production deployment

## Deployment Environments

| Environment | Status | URL | Resources |
|-------------|--------|-----|-----------|
| **Production (K8s)** | ✅ Live | https://cyyberaix.in | 5 backend + 2 frontend pods |
| **Development (Docker)** | ✅ Ready | http://localhost:3000 | 1 backend + 1 frontend |
| **Database** | ✅ Healthy | PostgreSQL 15 | Migration v005 |
