# Docker Setup Guide - AI CyberX

## Current Docker Configuration

Your AI CyberX application is running using Docker containers managed from:
```
/root/AI_CyberX/infrastructure/docker/
```

The containers are **already running** and you should **NOT create new containers**.

## Container Management

### Using the Management Script (Recommended)

We've created a convenient management script at the root of the project:

```bash
cd /root/AI_CyberX

# Show help
./docker.sh

# Check container status
./docker.sh status

# Check application health
./docker.sh health

# View logs
./docker.sh logs              # All services
./docker.sh logs backend      # Specific service

# Restart containers
./docker.sh restart

# Stop containers
./docker.sh stop

# Start containers
./docker.sh start

# Execute command in container
./docker.sh exec backend bash
./docker.sh exec backend python

# Rebuild containers (if needed)
./docker.sh rebuild
```

### Using Docker Compose Directly

The actual docker-compose.yml is located in:
```
/root/AI_CyberX/infrastructure/docker/docker-compose.yml
```

To manage containers directly:

```bash
# Navigate to docker directory
cd /root/AI_CyberX/infrastructure/docker

# Check status
docker compose ps

# View logs
docker compose logs -f

# Restart specific service
docker compose restart backend

# Stop all services
docker compose down

# Start all services
docker compose up -d
```

Or from the root directory (symlink):
```bash
cd /root/AI_CyberX
docker compose ps
docker compose logs -f
```

## Running Containers

Your application has 4 containers:

| Container | Service | Ports | Status |
|-----------|---------|-------|--------|
| **cyberx-backend** | FastAPI Backend | 8000 | Healthy ✓ |
| **cyberx-frontend** | Next.js Frontend | 3000 | Running ✓ |
| **cyberx-postgres** | PostgreSQL 15 | 5432 (localhost only) | Healthy ✓ |
| **cyberx-redis** | Redis 7 | 6379 (localhost only) | Healthy ✓ |

## Access URLs

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## Environment Configuration

Environment variables are stored in:
```
/root/AI_CyberX/infrastructure/docker/.env
```

To edit configuration:
```bash
nano /root/AI_CyberX/infrastructure/docker/.env

# After editing, restart containers
./docker.sh restart
```

## Important Notes

### ⚠️ DO NOT Create New Containers

The containers are **already running**. Do not run:
- `docker compose up` from the root directory
- `docker run` commands for these services

Always use the existing containers managed from `/root/AI_CyberX/infrastructure/docker/`

### Container Images

Current images:
- `docker-backend` - Built from `infrastructure/docker/Dockerfile.backend`
- `docker-frontend` - Built from `infrastructure/docker/Dockerfile.frontend`
- `postgres:15-alpine` - Official PostgreSQL image
- `redis:7-alpine` - Official Redis image

### Volumes

Data is persisted in Docker volumes:
- `postgres_data` - Database storage
- `redis_data` - Cache storage
- `../../data` - Application data (bind mount)

## Troubleshooting

### Containers not responding?

```bash
# Check container status
./docker.sh status

# Check logs
./docker.sh logs backend
./docker.sh logs frontend

# Restart containers
./docker.sh restart
```

### Need to rebuild?

```bash
# Rebuild and restart
./docker.sh rebuild

# Or manually
cd /root/AI_CyberX/infrastructure/docker
docker compose down
docker compose build
docker compose up -d
```

### Port conflicts?

```bash
# Check what's using ports
sudo lsof -i :8000
sudo lsof -i :3000

# If needed, stop the conflicting service
```

### Database connection issues?

```bash
# Check postgres is running
docker exec cyberx-postgres pg_isready -U cyberx

# View postgres logs
./docker.sh logs postgres

# Restart postgres
cd /root/AI_CyberX/infrastructure/docker
docker compose restart postgres
```

### Backend can't create labs?

```bash
# Verify Docker socket access
docker exec cyberx-backend docker ps

# Check Docker CLI
docker exec cyberx-backend docker --version

# View backend logs
./docker.sh logs backend
```

## Maintenance

### View System Resources

```bash
# Container resource usage
docker stats

# Disk usage
docker system df
```

### Cleanup Old Images

```bash
# Remove unused images
docker image prune

# Remove all unused data
docker system prune -a
```

### Backup Database

```bash
# Backup database
docker exec cyberx-postgres pg_dump -U cyberx cyberx > backup.sql

# Restore database
cat backup.sql | docker exec -i cyberx-postgres psql -U cyberx cyberx
```

## Development Workflow

### Making Code Changes

**Backend changes:**
```bash
# Edit code in /root/AI_CyberX/backend/
# Restart backend container
./docker.sh restart backend

# Or rebuild if dependencies changed
cd /root/AI_CyberX/infrastructure/docker
docker compose build backend
docker compose up -d backend
```

**Frontend changes:**
```bash
# Edit code in /root/AI_CyberX/frontend/
# Restart frontend container
./docker.sh restart frontend

# Or rebuild if dependencies changed
cd /root/AI_CyberX/infrastructure/docker
docker compose build frontend
docker compose up -d frontend
```

### Viewing Real-time Logs

```bash
# Follow all logs
./docker.sh logs

# Follow specific service
./docker.sh logs backend

# With docker compose
cd /root/AI_CyberX/infrastructure/docker
docker compose logs -f backend
```

## Quick Reference

```bash
# Essential commands from anywhere
cd /root/AI_CyberX

./docker.sh status      # Check containers
./docker.sh health      # Check app health
./docker.sh logs        # View logs
./docker.sh restart     # Restart all
./docker.sh exec backend bash  # Shell access

# Or use docker compose
cd infrastructure/docker
docker compose ps
docker compose logs -f
docker compose restart
```

## Support

If you encounter issues:

1. Check logs: `./docker.sh logs`
2. Verify health: `./docker.sh health`
3. Check container status: `./docker.sh status`
4. Review environment: `cat infrastructure/docker/.env`

For more details, see:
- `README.md` - Main documentation
- `DOCKER_MIGRATION.md` - Migration details
- Docker compose file: `infrastructure/docker/docker-compose.yml`
