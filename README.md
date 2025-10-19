# MLOps Stack

A production-ready local development environment for ML experimentation and LLM observability.

**What's included:**
- 🔬 **MLflow 3.4.0** - Model tracking, registry, and artifact storage with authentication
- 🔍 **Langfuse v3** - LLM observability and tracing
- 🔐 **Full authentication** - Python-based user management with permissions
- 📦 **Complete stack** - PostgreSQL, MinIO, ClickHouse, Redis - all configured and ready

---

## 📋 Table of Contents

- [Quick Reference](#quick-reference)
- [Why Two Services?](#why-two-services)
- [Quick Start](#quick-start)
- [MLflow Authentication](#mlflow-authentication)
- [User Management](#user-management)
- [Usage Examples](#usage-examples)
- [What's Included](#whats-included)
- [Troubleshooting](#troubleshooting)
- [Production Deployment](#production-deployment)
- [Contributing](#contributing)

---

## Quick Reference

**Service URLs:**

| Service | URL | Credentials |
|---------|-----|-------------|
| MLflow | http://localhost:5000 | `admin` / `change_me_on_first_login_123!` ⚠️ |
| Langfuse | http://localhost:3000 | Create account on first visit |
| MinIO Console | http://localhost:9001 | See `.env` file |

> ⚠️ **IMPORTANT**: Change the default MLflow admin password immediately after first login (see [Initial Setup](#6-set-up-mlflow-authentication-important))

---

## Why Two Services?

This stack combines **Langfuse** and **MLflow** because they excel at different but complementary tasks:

### 🔍 Langfuse - LLM Observability

**Best for:** Real-time tracing of LLM agent interactions

- Native async support for modern agent workflows
- Rich traces with nested spans, function calls, and token usage
- No race conditions in concurrent executions
- Built-in evaluations and cost tracking
- Automatic token counting per trace

### 🔬 MLflow - ML Lifecycle Management

**Best for:** Experiment tracking and model versioning

- Complete model lifecycle management and registry
- Centralized artifact storage (models, plots, datasets)
- Experiment comparison across different architectures
- Production deployment and serving integrations
- Built-in authentication and permissions system
- Industry standard with extensive integrations

### 💡 Best Practice

Use **Langfuse's `@observe` decorator** for detailed LLM traces, and **MLflow's `start_run()`** for experiment metadata and model artifacts. This gives you the best of both worlds without the limitations of `mlflow.openai.autolog()` (which doesn't support async agents).

---

## Quick Start

### Prerequisites

- **Docker Desktop** (minimum: 4 CPU cores, 8GB RAM, 20GB disk)
- **OpenSSL** (for generating security keys)
- **Poetry** (optional, for running tests and management scripts)

### 1. Clone and Setup

### 1. Clone and Setup

```bash
git clone https://github.com/sdeery14/mlops-stack.git
cd mlops-stack
cp .env.example .env
```

### 2. Generate Security Keys

```bash
# Generate keys (run openssl commands below)
openssl rand -base64 32  # For NEXTAUTH_SECRET
openssl rand -base64 32  # For SALT
openssl rand -hex 32     # For ENCRYPTION_KEY (must be 64 hex chars)
openssl rand -base64 32  # For MLFLOW_FLASK_SERVER_SECRET_KEY
```

**Edit `.env` and replace:**
- `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` with generated Langfuse keys
- `MLFLOW_FLASK_SERVER_SECRET_KEY` with generated MLflow key
- Database passwords (Postgres, ClickHouse, MinIO)
- `MLFLOW_ADMIN_USERNAME` and `MLFLOW_ADMIN_PASSWORD`

> 🔒 **Security Note**: The `mlflow_auth_config.ini` file is auto-generated at runtime from environment variables. No credentials are stored in version control.

### 3. Start Services

```bash
docker-compose up -d
```

**First startup takes 2-3 minutes** for database migrations. Monitor progress:

```bash
docker-compose logs -f langfuse-web mlflow-server
```

### 4. Access Services

- **MLflow**: http://localhost:5000 (login required)
- **Langfuse**: http://localhost:3000 (create account on first visit)
- **MinIO**: http://localhost:9001 (optional)

### 5. Verify Services

```bash
# Check all containers are running
docker-compose ps

# Optional: Run test suite
poetry install
poetry run pytest tests/ -v
```

### 6. Set Up MLflow Authentication (IMPORTANT!)

**Run the interactive setup script** to change the default admin password:

```bash
poetry run python scripts/setup_mlflow_auth.py
```

This script will:
1. Authenticate with default credentials from `.env`
2. Prompt you to set a new secure admin password
3. Optionally create initial team members
4. Display all users

⚠️ **CRITICAL**: Update `.env` with your new admin password after running this script!

### 7. Stop Services

```bash
docker-compose down      # Stop and keep data
docker-compose down -v   # Stop and remove all data
```

---

## MLflow Authentication

### Architecture Overview

MLflow authentication uses **Flask-based HTTP Basic Auth** with PostgreSQL storage for users and permissions.

```
┌─────────────────────────────────────────┐
│         MLflow Server (Flask)           │
│  ✓ Basic HTTP Authentication            │
│  ✓ User Management API                  │
│  ✓ Permission System (READ/EDIT/MANAGE) │
│  ✓ CSRF Protection                      │
└────────────┬────────────────────────────┘
             │
             ├──────┬──────────────────────┐
             ▼      ▼                      ▼
     ┌───────────┐ ┌─────────────┐ ┌─────────────┐
     │PostgreSQL │ │   MinIO     │ │PostgreSQL   │
     │(Tracking) │ │(Artifacts)  │ │(Auth Data)  │
     │  :5432    │ │:9000/:9001  │ │   :5433     │
     └───────────┘ └─────────────┘ └─────────────┘
```

**Key Components:**
- **Server**: Gunicorn with Flask (MLflow 3.4.0)
- **Auth Method**: HTTP Basic Authentication
- **Storage**: Separate PostgreSQL database for auth data
- **Password Hashing**: Werkzeug security (PBKDF2)
- **Config**: Runtime-generated from environment variables

### How Admin User is Created

The admin user is **automatically created** by MLflow on first startup:

1. Container startup runs `envsubst` to generate `mlflow_auth_config.ini` from template
2. MLflow reads the config file and loads admin credentials
3. If no admin exists in the database, creates one from config
4. Logs confirmation: `"Created admin user 'admin'"` (or silent if already exists)

> 💡 **Note**: Admin is only created once. To change credentials, use the Python management scripts.

### Permissions System

MLflow uses a three-level permission model for experiments and models:

| Permission | Read | Edit | Delete | Manage Permissions |
|------------|------|------|--------|-------------------|
| **READ** | ✅ | ❌ | ❌ | ❌ |
| **EDIT** | ✅ | ✅ | ❌ | ❌ |
| **MANAGE** | ✅ | ✅ | ✅ | ✅ |

**Default**: New resources get `READ` permission for all users (configurable in `mlflow_auth_config.ini`)

---

## User Management

### Management Scripts

#### `setup_mlflow_auth.py` - Initial Setup

**When to use:** Run ONCE after first deployment

```bash
poetry run python scripts/setup_mlflow_auth.py
```

**What it does:**
- Changes the default admin password
- Creates initial team users
- Sets up admin privileges

#### `manage_mlflow_users.py` - Daily Operations

**When to use:** Anytime you need to manage users or permissions

**Available commands:**
- `create-user` - Add new users
- `delete-user` - Remove users
- `list-users` - Show all users
- `change-password` - Update passwords
- `promote-user` - Grant admin privileges
- `demote-user` - Revoke admin privileges
- `grant-exp` - Grant experiment permissions
- `revoke-exp` - Revoke experiment permissions
- `grant-model` - Grant model permissions
- `revoke-model` - Revoke model permissions

### Common Tasks

#### List All Users

```bash
poetry run python scripts/manage_mlflow_users.py list-users
```

**Output:**
```
📋 MLflow Users:
------------------------------------------------------------
👑 ADMIN | admin (ID: 1)
👤 USER  | alice (ID: 2)
👤 USER  | bob (ID: 3)
------------------------------------------------------------
Total users: 3
```

#### Create a New User

```bash
poetry run python scripts/manage_mlflow_users.py create-user \
  --username alice \
  --password "alice_secure_pass"
```

#### Change Password

```bash
poetry run python scripts/manage_mlflow_users.py change-password \
  --new-password "your_super_secure_password_123!"
```

**Don't forget to update `.env`:**
```bash
MLFLOW_ADMIN_PASSWORD=your_super_secure_password_123!
```

#### Grant Permissions

```bash
# Experiment permissions
poetry run python scripts/manage_mlflow_users.py grant-exp \
  --experiment-id 1 \
  --username alice \
  --permission EDIT

# Model permissions
poetry run python scripts/manage_mlflow_users.py grant-model \
  --model-name my-classifier \
  --username alice \
  --permission MANAGE
```

#### Revoke Permissions

```bash
# Revoke experiment permission
poetry run python scripts/manage_mlflow_users.py revoke-exp \
  --experiment-id 1 \
  --username alice

# Revoke model permission
poetry run python scripts/manage_mlflow_users.py revoke-model \
  --model-name my-classifier \
  --username alice
```

### Programmatic Usage

```python
from scripts.manage_mlflow_users import MLflowUserManager
import os

# Initialize and authenticate
manager = MLflowUserManager(tracking_uri="http://localhost:5000")
manager.authenticate(
    os.getenv("MLFLOW_ADMIN_USERNAME", "admin"),
    os.getenv("MLFLOW_ADMIN_PASSWORD")
)

# Create users
manager.create_user("data_scientist", "secure_pass_123")
manager.create_user("ml_engineer", "another_pass_456")

# Grant permissions
manager.grant_experiment_permission(
    experiment_id="1",
    username="data_scientist",
    permission="EDIT"
)

manager.grant_model_permission(
    model_name="production-model",
    username="data_scientist",
    permission="MANAGE"
)

# List users
manager.list_users()
```

---

## Usage Examples

### Example 1: LLM Agent with Dual Logging

Log **traces to Langfuse** (detailed LLM interactions) and **experiment metadata to MLflow** (model versions, parameters).

```python
import asyncio
import os
from openai import AsyncOpenAI
from langfuse.decorators import observe, langfuse_context
import mlflow

# Configure clients
client = AsyncOpenAI()
os.environ['MLFLOW_TRACKING_USERNAME'] = 'admin'
os.environ['MLFLOW_TRACKING_PASSWORD'] = 'your_password'
mlflow.set_tracking_uri("http://localhost:5000")

@observe()  # Langfuse automatically captures all nested LLM calls
async def research_agent(topic: str):
    """Agent that researches a topic using multiple LLM calls."""
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"Research {topic}"}],
    )
    return response.choices[0].message.content

async def main():
    # MLflow: Track experiment parameters and results
    with mlflow.start_run(run_name="research-experiment"):
        mlflow.log_param("model", "gpt-4")
        mlflow.log_param("topic", "quantum computing")
        
        result = await research_agent("quantum computing")
        
        mlflow.log_metric("response_length", len(result))
        mlflow.log_text(result, "research_output.txt")
        
        # Link to Langfuse trace
        trace_url = langfuse_context.get_current_trace_url()
        mlflow.log_param("langfuse_trace", trace_url)

asyncio.run(main())
```

> 💡 **Why not `mlflow.openai.autolog()`?** It doesn't support async OpenAI Agents SDK and causes race condition errors.

### Example 2: Model Training with Artifact Storage

```python
import mlflow
import mlflow.sklearn
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
import os

# Authenticate
os.environ['MLFLOW_TRACKING_USERNAME'] = 'data_scientist'
os.environ['MLFLOW_TRACKING_PASSWORD'] = 'secure_password123'
mlflow.set_tracking_uri("http://localhost:5000")

# Load data
X, y = load_iris(return_X_y=True)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Start MLflow run
with mlflow.start_run():
    # Log parameters
    mlflow.log_param("n_estimators", 100)
    mlflow.log_param("max_depth", 5)
    
    # Train model
    model = RandomForestClassifier(n_estimators=100, max_depth=5)
    model.fit(X_train, y_train)
    
    # Log metrics
    score = model.score(X_test, y_test)
    mlflow.log_metric("accuracy", score)
    
    # Log model (automatically stored in MinIO)
    mlflow.sklearn.log_model(model, "model")
```

### Example 3: Langfuse Prompt Management

```python
from langfuse import Langfuse
from openai import OpenAI

langfuse = Langfuse()
client = OpenAI()

# Get versioned prompt from Langfuse
prompt = langfuse.get_prompt("research-prompt", version=2)

# Use in production
response = client.chat.completions.create(
    model="gpt-4",
    messages=prompt.compile(topic="AI safety")
)
```

---

## What's Included

### MLflow Stack (5 containers)

| Container | Purpose | Port(s) |
|-----------|---------|---------|
| `mlflow-server` | Tracking server UI/API | 5000 |
| `mlflow-postgres` | Experiment/run data | 5432 |
| `mlflow-postgres-auth` | User/permission data | 5433 |
| `mlflow-minio` | S3-compatible artifact storage | 9000, 9001 |
| `mlflow-create-bucket` | One-time bucket setup | - |

### Langfuse Stack (7 containers)

| Container | Purpose | Port(s) |
|-----------|---------|---------|
| `langfuse-web` | Web UI and API | 3000 |
| `langfuse-worker` | Async event processing | - |
| `langfuse-postgres` | Transactional data | 5432 |
| `langfuse-clickhouse` | Analytics database | 9000, 8123 |
| `langfuse-redis` | Cache and job queue | 6379 |
| `langfuse-minio` | Object storage | 9000, 9001 |
| `langfuse-init-minio` | Bucket initialization | - |

**All services** run on shared Docker networks with persistent volumes for data retention.

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| **Langfuse won't start** | Verify `ENCRYPTION_KEY` is exactly 64 hex characters. Check: `docker-compose ps` |
| **Slow first startup** | Normal (2-3 min for migrations). Monitor: `docker-compose logs -f langfuse-web` |
| **Port conflicts** | Change `MLFLOW_PORT` or `LANGFUSE_PORT` in `.env` |
| **Out of memory** | ClickHouse needs 2GB RAM. Increase Docker Desktop memory allocation |
| **Unauthorized errors** | Verify credentials in `.env` match current admin password |

### MLflow Authentication Issues

**Problem:** `Unauthorized` when accessing MLflow

**Solution:**
```bash
# Verify credentials in .env
cat .env | grep MLFLOW_ADMIN

# Verify admin user exists
poetry run python scripts/manage_mlflow_users.py list-users

# If needed, change password
poetry run python scripts/setup_mlflow_auth.py
```

### Database Migration Errors

**Problem:** Alembic revision mismatch or migration failures

**Solution:**
```bash
docker-compose down -v  # Remove all data
docker-compose up -d    # Fresh start with new migrations
```

### Server Startup Problems

**Problem:** Container crashes or authentication not working

**Solution:**
```bash
# Check logs
docker-compose logs mlflow-server

# Verify auth database
docker exec -it mlflow-postgres-auth psql -U mlflow_auth -d mlflow_auth -c "\dt"

# Inspect generated config
docker exec mlflow-server cat /mlflow/mlflow_auth_config.ini

# Full reset if needed
docker-compose down -v
docker-compose up -d
```

### Useful Commands

```bash
# View logs
docker-compose logs -f                            # All services
docker-compose logs -f mlflow-server langfuse-web # Specific services

# Restart services
docker-compose restart mlflow-server
docker-compose restart langfuse-web langfuse-worker

# Check health
docker-compose ps
docker stats

# Access containers
docker exec -it mlflow-server /bin/bash
docker exec -it mlflow-postgres psql -U mlflow

# Stop and cleanup
docker-compose stop      # Keep data
docker-compose down      # Remove containers, keep data
docker-compose down -v   # Remove everything including data

# Rebuild
docker-compose up -d --build        # Rebuild and restart
docker-compose build --no-cache     # Clean rebuild
```

---

## Production Deployment

⚠️ **This stack is configured for local development** - default credentials are documented and NOT production-safe.

### Production Checklist

#### 1. Change All Default Passwords

- ✅ MLflow admin: `MLFLOW_ADMIN_PASSWORD`
- ✅ PostgreSQL passwords (all instances)
- ✅ MinIO credentials
- ✅ ClickHouse password
- ✅ Redis password (if exposed)

#### 2. Generate New Security Keys

```bash
openssl rand -base64 32  # MLFLOW_FLASK_SERVER_SECRET_KEY
openssl rand -base64 32  # NEXTAUTH_SECRET
openssl rand -base64 32  # SALT
openssl rand -hex 32     # ENCRYPTION_KEY (must be 64 hex chars)
```

#### 3. Use Managed Services

Replace local containers with production services:

- **PostgreSQL** → RDS, Cloud SQL, Azure Database
- **Object Storage** → S3, GCS, Azure Blob Storage
- **Redis** → ElastiCache, Cloud Memorystore
- **ClickHouse** → ClickHouse Cloud, managed hosting

#### 4. Enable SSL/TLS

- Use HTTPS for all web traffic
- Enable SSL for database connections
- Use TLS for Redis connections
- Secure artifact storage URLs

#### 5. Network Security

- Don't expose databases to public internet
- Use VPCs and security groups
- Implement network policies
- Configure firewall rules
- Use private subnets for databases

#### 6. Authentication & Authorization

- Use strong, unique passwords (20+ characters)
- Implement SSO/SAML if possible
- Enable MFA where supported
- Follow principle of least privilege
- Rotate credentials regularly (every 90 days)

#### 7. Monitoring & Auditing

- Enable access logs on all services
- Monitor for suspicious activity
- Set up alerts for failed auth attempts
- Regular security audits
- Track user management operations

### Security Best Practices

| Practice | Implementation |
|----------|----------------|
| **Password Strength** | Min 20 chars, mixed case, numbers, symbols |
| **Credential Storage** | Use secret managers (AWS Secrets Manager, Vault) |
| **Access Control** | READ by default, EDIT/MANAGE only when needed |
| **Audit Trail** | Enable logging on all services |
| **Version Control** | Never commit `.env` or credentials |
| **Rotation** | Change passwords every 90 days |
| **SSL/TLS** | HTTPS and encrypted connections everywhere |

### File Security Status

| File | Status | Why |
|------|--------|-----|
| `.env` | ⛔ **Never commit** | Contains all secrets |
| `mlflow_auth_config.ini` | ⛔ **Never commit** | Generated at runtime with credentials |
| `mlflow_auth_config.ini.template` | ✅ **Safe to commit** | Only contains placeholders |
| `.env.example` | ✅ **Safe to commit** | Template with dummy values |

### MLflow Version Notes

| Version | Status | Notes |
|---------|--------|-------|
| **3.4.0** | ✅ **Recommended** | Stable auth with Gunicorn/Flask |
| **3.5.0+** | ❌ **Broken Auth** | Switched to Uvicorn/FastAPI, auth not compatible |

**Why 3.4.0?** MLflow 3.5.0+ switched from Gunicorn (Flask) to Uvicorn (FastAPI), breaking the Flask-based authentication module. This stack uses 3.4.0 until FastAPI auth support is fixed.

---

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Resources

- **Issues**: [GitHub Issues](https://github.com/sdeery14/mlops-stack/issues)
- **MLflow Docs**: https://mlflow.org/docs/latest/auth/index.html
- **Langfuse Docs**: https://langfuse.com/docs
- **OWASP Security**: https://owasp.org/

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for modern MLOps workflows**

Ready for production use with comprehensive authentication, user management, and best practices! 🚀
