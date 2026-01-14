# Docker Migration Complete

The AI CyberX platform has been fully migrated from Podman to Docker.

## What Changed

### 1. Container Runtime
- **Before**: Podman with podman-compose
- **After**: Docker with docker-compose

### 2. File Structure
```
OLD:
infrastructure/podman/podman-compose.yml
infrastructure/scripts/start.sh (Podman-specific)

NEW:
docker-compose.yml (in root)
start.sh (in root, Docker-specific)
.env.example (in root)
```

### 3. Dockerfiles
- Updated `infrastructure/docker/Dockerfile.backend` with Docker CLI
- Backend now has Docker socket access for lab management
- Group ID 988 added for Docker socket permissions

### 4. Environment Configuration
- Centralized `.env` file in project root
- `DOCKER_HOST=unix:///var/run/docker.sock`
- Removed `PODMAN_SOCKET` references

### 5. Lab Management
- Lab manager uses Docker socket at `/var/run/docker.sock`
- All lab container operations use `docker` CLI
- No code changes needed (already Docker-compatible)

## How to Use

### Starting the Application

```bash
# Quick start
./start.sh

# Or manually
docker-compose up -d
```

### Useful Docker Commands

```bash
# View logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Rebuild containers
docker-compose up -d --build

# View running containers
docker ps

# View container status
docker-compose ps

# Execute command in container
docker exec -it cyberx-backend bash

# Check backend health
curl http://localhost:8000/health
```

### Environment Variables

Create `.env` file from template:
```bash
cp .env.example .env
```

Required variables:
- `SECRET_KEY` - Generate with: `openssl rand -hex 32`
- `POSTGRES_PASSWORD` - Strong database password
- At least one AI API key:
  - `MISTRAL_API_KEY` (recommended)
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `GEMINI_API_KEY`

### Docker Installation

If Docker is not installed:

**Ubuntu/Debian:**
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

**Docker Compose:**
```bash
sudo apt-get install docker-compose-plugin
```

## Architecture

```
┌─────────────────────────────────────┐
│         Docker Engine                │
├─────────────────────────────────────┤
│  ┌──────────────────────────────┐   │
│  │  cyberx-frontend (Next.js)   │   │
│  │  Port: 3000                   │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  cyberx-backend (FastAPI)    │   │
│  │  Port: 8000                   │   │
│  │  + Docker CLI                 │   │
│  │  + /var/run/docker.sock       │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  cyberx-postgres             │   │
│  │  Port: 5432 (localhost only)  │   │
│  └──────────────────────────────┘   │
│  ┌──────────────────────────────┐   │
│  │  cyberx-redis                │   │
│  │  Port: 6379 (localhost only)  │   │
│  └──────────────────────────────┘   │
│                                      │
│  Network: cyberx-network (bridge)   │
└─────────────────────────────────────┘
```

### Lab Containers

Lab containers are dynamically created by the backend:
```
cyberx-backend creates/manages:
├── lab_<uuid>_<container_name>
├── lab_<uuid>_network
└── Isolated Docker networks per lab
```

## Troubleshooting

### Docker Daemon Not Running
```bash
sudo systemctl start docker
sudo systemctl enable docker
```

### Permission Denied (Docker Socket)
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :8000
sudo lsof -i :3000

# Stop the service or change ports in docker-compose.yml
```

### Backend Can't Create Lab Containers
```bash
# Ensure Docker socket is mounted
docker exec cyberx-backend ls -la /var/run/docker.sock

# Check Docker CLI is available
docker exec cyberx-backend docker --version

# Check permissions
docker exec cyberx-backend groups
```

### Database Connection Issues
```bash
# Check postgres is healthy
docker ps | grep postgres

# Check logs
docker-compose logs postgres

# Test connection
docker exec cyberx-backend curl postgres:5432
```

## Migration from Existing Podman Setup

If you have an existing Podman installation:

1. **Stop Podman containers:**
   ```bash
   cd infrastructure/podman
   podman-compose down
   ```

2. **Backup data:**
   ```bash
   cp -r data data.backup
   ```

3. **Install Docker** (see above)

4. **Use new Docker setup:**
   ```bash
   cd /root/AI_CyberX
   cp .env.example .env
   # Edit .env with your settings
   ./start.sh
   ```

5. **Restore data if needed:**
   ```bash
   # Docker volumes persist automatically
   # If you need to restore from backup:
   docker-compose down -v
   cp -r data.backup/* data/
   docker-compose up -d
   ```

## Performance Notes

Docker performance is generally similar to Podman. Key considerations:

- **Startup time**: ~30-60 seconds for all services to be healthy
- **Memory**: ~2GB RAM minimum, 4GB recommended
- **Disk**: ~10GB for images and data
- **Lab containers**: Each lab adds ~100-500MB depending on preset

## Security

- Database and Redis are bound to localhost only (127.0.0.1)
- Frontend and Backend are publicly accessible (0.0.0.0)
- Lab containers use isolated Docker networks
- Docker socket is read-only mounted for security
- Non-root users run inside containers

## Production Deployment

For production:

1. Update `.env`:
   - Set strong `SECRET_KEY` and `POSTGRES_PASSWORD`
   - Configure production URLs in `CORS_ORIGINS`
   - Set `DEBUG=false`

2. Use reverse proxy (nginx/caddy) for:
   - HTTPS termination
   - Domain routing
   - Rate limiting
   - Static file caching

3. Configure backups:
   ```bash
   # Backup database
   docker exec cyberx-postgres pg_dump -U cyberx cyberx > backup.sql
   
   # Backup volumes
   docker run --rm -v cyberx_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
   ```

4. Monitor resources:
   ```bash
   docker stats
   docker-compose logs --tail=100 -f
   ```

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify health: `curl http://localhost:8000/health`
3. Review environment: `.env` file configuration
4. Check Docker: `docker --version && docker compose version`
