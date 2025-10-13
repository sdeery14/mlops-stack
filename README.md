# MLOps Stack

Local development environment for **MLflow 3.4.0** (model tracking) and **Langfuse v3** (LLM observability) with full production-ready architecture.

> **Note**: The Langfuse configuration follows the [official docker-compose.yml structure](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) for best practices and compatibility.

## Prerequisites

- Docker Desktop
- OpenSSL (for generating security keys)
- Minimum: 4 CPU cores, 8GB RAM, 20GB disk space

## Quick Start

### 1. Generate Security Keys

Generate the required security keys for Langfuse:

```bash
# Windows PowerShell - Generate NEXTAUTH_SECRET and SALT
openssl rand -base64 32

# Generate ENCRYPTION_KEY (must be 64 hex characters)
openssl rand -hex 32
```

Run the first command **twice** to generate two different keys for `NEXTAUTH_SECRET` and `SALT`.
Run the second command **once** to generate `ENCRYPTION_KEY`.

Update these three values in the `.env` file.

### 2. Update Environment Variables

Edit the `.env` file and:
- Replace the placeholder security keys with your generated keys
- Update passwords for databases (Postgres, ClickHouse, MinIO)
- Update MLflow admin credentials
- Adjust ports if needed (default: MLflow 5000, Langfuse 3000)

### 3. Start Services

```bash
docker-compose up -d
```

**First startup takes 2-3 minutes** for database migrations. Watch progress:
```bash
docker-compose logs -f langfuse-web
```

### 4. Access UIs

- **MLflow**: http://localhost:5000 (username: `admin`, password: from `.env`)
- **Langfuse**: http://localhost:3000 (create account on first visit)
- **MinIO Console**: http://localhost:9001 (optional, for debugging)

### 5. Stop Services

```bash
docker-compose down
```

To remove volumes (databases and artifacts):
```bash
docker-compose down -v
```

## Architecture

### MLflow (2 containers)
- **MLflow Server** (port 5000) - Experiment tracking UI/API
- **PostgreSQL** - Backend store for experiments/runs
- **Volumes** - Local filesystem for artifacts

### Langfuse (7 containers - production architecture)
- **Web Server** (port 3000) - UI and API
- **Worker** - Async event processing
- **PostgreSQL** - Transactional data (users, projects, configs)
- **ClickHouse** - Analytics database (traces, observations)
- **Redis** - Cache and job queue
- **MinIO** (ports 9000, 9001) - S3-compatible object storage
- **MinIO Client** - One-time bucket setup (exits after completion)

## Environment Configuration

### Local Development
Use the `.env` file for local development. All services run in Docker containers with local PostgreSQL instances.

### Production
1. Copy `.env.production.example` to `.env.production`
2. Update all placeholder values with production credentials
3. Consider using:
   - Managed PostgreSQL services (AWS RDS, Azure Database, etc.)
   - Cloud object storage (S3, Azure Blob, GCS) for MLflow artifacts
   - Proper SSL/TLS certificates
   - Secure secret management (AWS Secrets Manager, Azure Key Vault, etc.)

To use production config:
```bash
docker-compose --env-file .env.production up -d
```

## Data Persistence

All data is stored in Docker volumes:

### MLflow
- `mlflow-db-data`: MLflow PostgreSQL database
- `mlflow-artifacts`: MLflow experiment artifacts

### Langfuse
- `langfuse-db-data`: Langfuse PostgreSQL database (transactional data)
- `langfuse-clickhouse-data`: ClickHouse database (traces, observations, analytics)
- `langfuse-redis-data`: Redis cache and queue data
- `langfuse-minio-data`: MinIO object storage (events, multi-modal data)

## Networking

All services run on a shared Docker network (`mlops-network`) for inter-service communication.

## Health Checks

Both PostgreSQL databases have health checks configured to ensure they're ready before dependent services start.

## Security Notes

⚠️ **Important**: 
- Never commit `.env` files with real credentials to version control
- Change all default passwords before using in production
- Rotate security keys regularly
- Use strong, unique passwords for each service
- Consider implementing additional authentication layers for production

## Troubleshooting

| Issue | Solution |
|-------|----------|
| **Langfuse won't start** | Check `ENCRYPTION_KEY` is exactly 64 hex chars. Verify ClickHouse/Redis are healthy: `docker-compose ps` |
| **Slow startup** | Normal on first run (2-3 min for migrations). Watch: `docker-compose logs -f langfuse-web` |
| **MinIO/S3 errors** | Check bucket created: `docker-compose logs langfuse-minio-client` |
| **Worker not processing** | Verify Redis: `docker exec langfuse-redis redis-cli ping` |
| **Port conflicts** | Change `MLFLOW_PORT` or `LANGFUSE_PORT` in `.env` |
| **Out of memory** | ClickHouse needs 2GB RAM. Increase Docker Desktop resources |

**View logs**: `docker-compose logs -f [service-name]`  
**Check health**: `docker-compose ps`

## Useful Commands

```bash
# View logs for all services
docker-compose logs -f

# View logs for specific services
docker-compose logs -f langfuse-web langfuse-worker

# Restart a specific service
docker-compose restart mlflow
docker-compose restart langfuse-web

# Stop without removing volumes
docker-compose stop

# Remove everything including volumes
docker-compose down -v

# Rebuild images (if using custom builds)
docker-compose build --no-cache

# Check service health
docker-compose ps

# Access MinIO console (for debugging S3 storage)
# Open http://localhost:9001 in browser
# Login with LANGFUSE_MINIO_ROOT_USER and LANGFUSE_MINIO_ROOT_PASSWORD
```

## MLflow Usage Example

```python
import mlflow

# Set tracking URI
mlflow.set_tracking_uri("http://localhost:5000")

# Set experiment
mlflow.set_experiment("my-experiment")

# Log parameters and metrics
with mlflow.start_run():
    mlflow.log_param("param1", 5)
    mlflow.log_metric("metric1", 0.85)
```

## Langfuse Usage Example

```python
from langfuse import Langfuse

# Initialize Langfuse client
langfuse = Langfuse(
    public_key="<your-public-key>",
    secret_key="<your-secret-key>",
    host="http://localhost:3000"
)

# Create a trace
trace = langfuse.trace(name="my-llm-app")
```

## License

See LICENSE file for details.
