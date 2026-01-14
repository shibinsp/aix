# AI CyberX - AI-Powered Cybersecurity Learning Platform

An autonomous, AI-powered cybersecurity education platform that teaches students without human tutors, generates personalized learning paths, creates custom labs on-demand, and adapts to individual skill levels.

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

# Copy environment template
cp .env.example .env

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
```

### 3. Start the Platform

```bash
# Using Docker Compose
cd infrastructure/docker
docker-compose up -d

# Or use the quick start script
chmod +x start.sh
./start.sh
```

### 4. Access the Platform

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### 5. Create Admin User

```bash
# Connect to backend container
docker exec -it cyberx-backend bash

# Create super admin
python -m app.cli create-admin --email admin@example.com --password <password>
```

## Production Deployment

### With Nginx + SSL

```bash
cd infrastructure/docker

# Configure production environment
cp .env.example .env.production
nano .env.production  # Set production values

# Start with production compose
docker-compose -f docker-compose.prod.yml up -d
```

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use strong `SECRET_KEY` and `POSTGRES_PASSWORD`
- [ ] Configure proper `CORS_ORIGINS` for your domain
- [ ] Set up SSL certificates (Certbot included)
- [ ] Configure firewall rules
- [ ] Set up backup for PostgreSQL data
- [ ] Configure rate limiting

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

# Create migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

## Troubleshooting

### Common Issues

**Container won't start**
```bash
# Check logs
docker logs cyberx-backend
docker logs cyberx-frontend

# Rebuild images
docker-compose build --no-cache
```

**Database connection error**
```bash
# Check PostgreSQL is running
docker exec -it cyberx-postgres pg_isready

# Reset database
docker-compose down -v
docker-compose up -d
```

**Frontend hydration errors**
- Ensure `hasHydrated` check is in place for auth-dependent components
- Check browser console for specific error messages

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
