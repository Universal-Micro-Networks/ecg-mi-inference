# Docker & Development Environment Setup

## Overview

This project uses Docker and Docker Compose to provide a consistent development and deployment environment for the ECG MI Inference system.

- **Frontend**: React 18 + TypeScript (Vite) - runs on port 5173
- **Backend**: FastAPI (Python 3.13) - runs on port 8000
- **Database**: SQLite with auto-initialization on startup

## Prerequisites

- Docker Desktop (version 20.10+)
- Docker Compose (version 1.29+)
- Make (optional, but recommended)
- Git

### Installation

**macOS (with Homebrew):**
```bash
brew install docker docker-compose
```

**Linux:**
```bash
sudo apt-get install docker.io docker-compose
```

**Windows:**
Install Docker Desktop from https://www.docker.com/products/docker-desktop

## Quick Start

### Option 1: Using Make (Recommended)

```bash
# Initial setup - builds and starts all services
make setup

# Start development environment
make dev

# View logs
make logs

# Stop services
make down
```

### Option 2: Using Docker Compose Directly

```bash
# Build images
docker-compose build

# Start services in the background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Available Make Commands

### Development
- `make dev` - Start development environment with hot reload
- `make setup` - Initial setup with build and start
- `make build` - Build Docker images
- `make up` - Start services
- `make down` - Stop services
- `make restart` - Restart all services
- `make reset` - Full reset (clean + build + up)

### Logging
- `make logs` - View all service logs
- `make logs-frontend` - View frontend logs only
- `make logs-backend` - View backend logs only

### Direct Access
- `make shell-frontend` - Open shell in frontend container
- `make shell-backend` - Open bash shell in backend container

### Database
- `make db-reset` - Reset database and reinitialize
- `make db-shell` - Open SQLite shell

### Testing
- `make test-backend` - Run backend tests
- `make test-frontend` - Run frontend tests
- `make lint-backend` - Lint backend code
- `make lint-frontend` - Lint frontend code
- `make format-backend` - Format backend code (black)
- `make format-frontend` - Format frontend code (prettier)

### Utilities
- `make status` - Check health status of services
- `make ps` - Show running containers
- `make stats` - Show container resource usage
- `make clean` - Remove all containers and volumes

## Service Details

### Frontend Service

**Dockerfile**: `Dockerfile.frontend`
**Port**: 5173
**Key Features**:
- Hot reload development server (Vite)
- Source code live sync via volumes
- Node modules cached to avoid reinstalls

**Environment Variables**:
- `VITE_API_URL` - Backend API URL (default: `http://localhost:8000/api`)

**Volume Mounts**:
- `./frontend/src` - React source code
- `./frontend/public` - Static assets
- `/app/node_modules` - Cached dependencies (named volume)

**Health Check**: Wget test on port 5173 every 30 seconds

### Backend Service

**Dockerfile**: `Dockerfile.backend`
**Port**: 8000
**Key Features**:
- FastAPI with automatic OpenAPI documentation
- SQLite database auto-initialization
- ECG image caching
- CORS configured for frontend

**Environment Variables**:
- `DATABASE_URL` - SQLite database path (default: `sqlite:////app/data/ecg_mi.db`)

**Volume Mounts**:
- `./backend/app` - Python application code
- `./backend/data` - Database and cache files

**Health Check**: curl test on `/health` endpoint every 30 seconds

**Initial Startup**:
On first startup, the backend automatically:
1. Creates SQLite database
2. Initializes schema (patients, examinations, inferences tables)
3. Populates sample data

### Database

**Type**: SQLite
**Location**: `backend/data/ecg_mi.db`
**Schema**:
- `patients` - Patient demographic information
- `examinations` - ECG examination records with CSV file paths
- `inferences` - Inference execution results and status

**Reset Database**:
```bash
make db-reset
# OR manually:
rm backend/data/ecg_mi.db
docker-compose restart backend
```

**Shell Access**:
```bash
make db-shell
# Then use SQLite commands: .tables, SELECT * FROM patients; etc.
```

## Environment Configuration

### Frontend Configuration

Edit `frontend/.env` or set environment variables:

```bash
VITE_API_URL=http://localhost:8000/api
```

### Backend Configuration

Edit `backend/pyproject.toml` or environment variables:

```bash
DATABASE_URL=sqlite:////app/data/ecg_mi.db
```

## Common Workflows

### Starting Fresh

```bash
# Complete reset
make reset

# Access frontend
open http://localhost:5173

# Access API docs
open http://localhost:8000/docs
```

### Debugging Backend

```bash
# Open Python shell in running container
docker-compose exec backend python

# View logs with filtering
docker-compose logs backend | grep ERROR

# Execute Python script
docker-compose exec backend python -c "from app.models import Patient; print('OK')"
```

### Debugging Frontend

```bash
# Open browser DevTools
# Frontend is at http://localhost:5173

# View frontend logs
make logs-frontend

# Open frontend shell
make shell-frontend
```

### Running Tests

```bash
# Backend tests
make test-backend

# Frontend tests
make test-frontend

# All tests
make test-backend && make test-frontend
```

### Code Formatting

```bash
# Format all backend code
make format-backend

# Format all frontend code
make format-frontend

# Lint code
make lint-backend
make lint-frontend
```

## Troubleshooting

### Port Already in Use

If port 5173 or 8000 is already in use:

```bash
# Find process using port 5173
lsof -i :5173

# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>
```

Or change port in `docker-compose.yml`:
```yaml
services:
  frontend:
    ports:
      - "3000:5173"  # Changed from 5173:5173
  backend:
    ports:
      - "8001:8000"  # Changed from 8000:8000
```

### Database Issues

```bash
# Check database exists
ls -lh backend/data/ecg_mi.db

# Reset database
make db-reset

# Verify tables
make db-shell
.tables
```

### Service Won't Start

```bash
# Check service logs
make logs-backend
make logs-frontend

# Check health status
make status

# Rebuild without cache
make clean
make build
make up
```

### Out of Disk Space

```bash
# Clean Docker cache
make clean-cache

# Remove unused Docker resources
docker system prune -a
```

## Production Deployment

For production deployment:

1. **Use specific image tags** instead of `latest`
2. **Set environment variables** properly:
   ```bash
   VITE_API_URL=https://api.example.com
   DATABASE_URL=postgresql://user:pass@db:5432/ecg_mi
   ```
3. **Use reverse proxy** (nginx/Caddy) for HTTPS
4. **Use managed database** (PostgreSQL instead of SQLite)
5. **Configure proper secrets** management
6. **Set resource limits** in docker-compose.yml:
   ```yaml
   services:
     backend:
       deploy:
         resources:
           limits:
             cpus: '1'
             memory: 1024M
   ```

## Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Vite Documentation](https://vitejs.dev/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

## Support

For issues or questions about the Docker setup, refer to:
- `backend/README.md` - Backend-specific documentation
- `frontend/README.md` - Frontend-specific documentation
- `.kiro/specs/` - Feature specification documents
