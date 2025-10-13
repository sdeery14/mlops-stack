# MLOps Stack

Local development environment for **MLflow 3.4.0** (model tracking) and **Langfuse v3** (LLM observability).

> **Note**: The Langfuse configuration follows the [official docker-compose.yml structure](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) for best practices and compatibility.

## Quick Reference

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| MLflow | http://localhost:5000 | `admin` / (from `.env`) |
| Langfuse | http://localhost:3000 | Create account on first visit |
| MinIO Console | http://localhost:9001 | (from `.env`) |

## Prerequisites

- Docker Desktop (min: 4 CPU cores, 8GB RAM, 20GB disk)
- OpenSSL (for generating security keys)
- Poetry (optional, for running tests)

## Quick Start

**1. Generate security keys and update `.env`:**

```bash
# Generate NEXTAUTH_SECRET and SALT (run twice for two different keys)
openssl rand -base64 32

# Generate ENCRYPTION_KEY (run once, must be 64 hex characters)
openssl rand -hex 32
```

Edit `.env` and replace:
- `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` with generated keys
- Database passwords (Postgres, ClickHouse, MinIO)
- MLflow admin credentials

**2. Start services:**

```bash
docker-compose up -d
```

*First startup takes 2-3 minutes for database migrations. Watch progress: `docker-compose logs -f langfuse-web`*

**3. Access the UIs** using the URLs in the Quick Reference table above.

**4. Stop services:**

```bash
docker-compose down              # Keep data
docker-compose down -v           # Remove all data
```

## What's Included

**MLflow** (2 containers):
- MLflow Server (port 5000) - Experiment tracking UI/API
- PostgreSQL - Backend store for experiments/runs

**Langfuse** (7 containers - production architecture):
- Web Server (port 3000) - UI and API
- Worker - Async event processing
- PostgreSQL - Transactional data (users, projects, configs)
- ClickHouse - Analytics database (traces, observations)
- Redis - Cache and job queue
- MinIO (ports 9000, 9001) - S3-compatible object storage
- MinIO Client - One-time bucket setup

All services run on a shared Docker network (`mlops-network`). Data persists in Docker volumes.

## Testing

```bash
poetry install
poetry run pytest tests/test_stack.py -v
```

## Security Notes

⚠️ **Important**: 
- Never commit `.env` files with real credentials to version control
- Change all default passwords before using in production
- Use strong, unique passwords for each service
- For production: use managed databases, cloud storage, SSL/TLS, and secret management services

## Common Issues

| Issue | Solution |
|-------|----------|
| **Langfuse won't start** | Check `ENCRYPTION_KEY` is exactly 64 hex chars. Verify services: `docker-compose ps` |
| **Slow startup** | Normal on first run (2-3 min for migrations). Watch: `docker-compose logs -f langfuse-web` |
| **Port conflicts** | Change `MLFLOW_PORT` or `LANGFUSE_PORT` in `.env` |
| **Out of memory** | ClickHouse needs 2GB RAM. Increase Docker Desktop resources |

**Debugging**: `docker-compose logs -f [service-name]` | **Check health**: `docker-compose ps`

## Useful Commands

```bash
# View logs
docker-compose logs -f                              # All services
docker-compose logs -f langfuse-web langfuse-worker # Specific services

# Restart services
docker-compose restart mlflow
docker-compose restart langfuse-web

# Stop and remove
docker-compose stop           # Keep data
docker-compose down -v        # Remove all data

# Rebuild
docker-compose build --no-cache
```

## Usage Examples

**MLflow:**
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-experiment")

with mlflow.start_run():
    mlflow.log_param("param1", 5)
    mlflow.log_metric("metric1", 0.85)
```

**Langfuse:**
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="<your-public-key>",
    secret_key="<your-secret-key>",
    host="http://localhost:3000"
)

trace = langfuse.trace(name="my-llm-app")
```

## License

See LICENSE file for details.
