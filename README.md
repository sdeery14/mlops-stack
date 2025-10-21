# MLOps Stack

A production-ready local development environment for ML experimentation and LLM observability.

**What's included:**
- 🔬 **MLflow 3.4.0** - Model tracking, registry, and artifact storage with authentication
- 🔍 **Langfuse v3** - LLM observability and tracing

See [docs/SERVICES.md](docs/SERVICES.md) for complete docker service details, ports, and configuration.

---

## Setup

### Prerequisites

- **Docker Desktop** (minimum: 4 CPU cores, 8GB RAM, 20GB disk)
- **Python**
- **Poetry**

### 1. Clone the repo

```bash
git clone https://github.com/sdeery14/mlops-stack.git
cd mlops-stack
```

### 2. Deploy the stack

The deployment script will: 
- Auto-generate secure passwords
- Run Docker Compose services
- Validate deployment

```bash
poetry install
poetry run python scripts/deploy_stack.py
```
First startup takes 2-3 minutes for database migrations.

### 3. Validate Services

```bash
# Check all containers are running
docker-compose ps

# Validate all services are healthy
poetry run python scripts/validate_services.py

# Run test suite
poetry run pytest tests/ -v
```
Access services:
- **MLflow**: http://localhost:5000 (login with generated credentials)
- **Langfuse**: http://localhost:3000 (create account on first visit)
- **MinIO Consoles**: http://localhost:9003 (MLflow), http://localhost:9091 (Langfuse)

> 🔐 **Auto-generated Credentials**: When using the automated setup, MLflow admin credentials are displayed after deployment and saved in your `.env` file.

---

## Usage

### User Management

**MLflow** uses authentication. Create users for team members and automations:

```bash
# List users
poetry run python scripts/manage_mlflow_users.py list-users

# Create user
poetry run python scripts/manage_mlflow_users.py create-user --username alice --password secure_pass

# Grant experiment permission
poetry run python scripts/manage_mlflow_users.py grant-exp --experiment-id 1 --username alice --permission EDIT
```

**Langfuse** manages users through the web UI (http://localhost:3000). Create an account, then invite team members via Settings → Members.

### Project Organization

Use consistent naming to keep experiments and traces organized across projects:

**MLflow Experiments:**
```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("project-name/experiment-type")

# Examples:
# "sentiment-model/training"
# "sentiment-model/hyperparameter-tuning"
# "chatbot-v2/rag-evaluation"
```

**Langfuse Projects:**

Create a project per application in the Langfuse UI. Use API keys to connect:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)

# Tag traces with metadata for filtering
langfuse.trace(name="chat", metadata={"env": "dev", "version": "v2"})
```

**Recommended patterns:**
- Single developer: One MLflow experiment per project, one Langfuse project per application
- Small team: Shared experiments with per-user branches (`alice/feature-x`), shared Langfuse projects

### Python SDK Configuration

**MLflow:**
```python
import mlflow
import os

os.environ['MLFLOW_TRACKING_URI'] = 'http://localhost:5000'
os.environ['MLFLOW_TRACKING_USERNAME'] = 'your-username'
os.environ['MLFLOW_TRACKING_PASSWORD'] = 'your-password'

mlflow.set_experiment("my-project/training")
```

**Langfuse:**
```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key="pk-lf-...",      # From Langfuse UI → Settings → API Keys
    secret_key="sk-lf-...",
    host="http://localhost:3000"
)
```

---


