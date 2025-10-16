# MLOps Stack

Local development environment for **MLflow 3.4.0** (model tracking) and **Langfuse v3** (LLM observability).

> **Note**: The Langfuse configuration follows the [official docker-compose.yml structure](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) for best practices and compatibility.

## Why Two Services?

This stack uses **Langfuse for tracing** and **MLflow for model management** because each excels at different tasks:

**Langfuse** - LLM Observability & Tracing:
- ✅ **Native async support**: Designed for modern async agent workflows (OpenAI Agents SDK, LangGraph, etc.)
- ✅ **Rich LLM traces**: Captures nested spans, function calls, streaming responses, and token usage automatically
- ✅ **No race conditions**: Handles concurrent agent executions without duplicate key errors
- ✅ **Built-in evaluations**: Supports human feedback, automated scoring, and A/B testing
- ✅ **Cost tracking**: Automatic token counting and cost calculation per trace

**MLflow** - Experiment Tracking & Model Registry:
- ✅ **Model versioning**: Complete model lifecycle management and registry
- ✅ **Artifact storage**: Centralized storage for models, plots, and datasets
- ✅ **Experiment comparison**: Compare runs across different model architectures
- ✅ **Production deployment**: Model serving and deployment integrations
- ✅ **Industry standard**: Widely adopted with extensive integrations

**In practice**: Use Langfuse's `@observe` decorator for detailed LLM traces, and MLflow's `start_run()` for experiment metadata and model artifacts. This gives you the best of both worlds without the limitations of `mlflow.openai.autolog()` (which doesn't support async agents).

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

### Langfuse for Tracing (Recommended for OpenAI Agents SDK)

```python
import mlflow
import asyncio
from agents import Agent, Runner
from langfuse.decorators import observe, langfuse_context

# Setup
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-experiment")

@observe()  # Langfuse handles async agent tracing automatically
async def run_agent(user_input: str):
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )
    result = await Runner.run(agent, user_input)
    return result

async def main():
    with mlflow.start_run() as run:
        # Langfuse captures detailed traces
        result = await run_agent("What is machine learning?")
        
        # MLflow logs experiment metadata
        mlflow.log_param("user_input", "What is machine learning?")
        mlflow.log_text(result.final_output, "output.txt")
        
        # Link traces between systems
        langfuse_context.update_current_trace(
            metadata={"mlflow_run_id": run.info.run_id}
        )
        
        langfuse_context.flush()

asyncio.run(main())
```

**Why not `mlflow.openai.autolog()`?** It doesn't support the async OpenAI Agents SDK and causes duplicate key errors due to race conditions.

### MLflow for Model Tracking

```python
import mlflow
from sklearn.ensemble import RandomForestClassifier

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-ml-experiment")

with mlflow.start_run():
    # Train model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    # Log parameters and metrics
    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", 0.95)
    
    # Log model to registry
    mlflow.sklearn.log_model(model, "model")
```

## License

See LICENSE file for details.
