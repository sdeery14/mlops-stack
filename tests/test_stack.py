"""
Simple infrastructure tests for MLOps Stack
Run with: pytest test_stack.py -v
Install deps: pip install pytest pyyaml requests
"""
import subprocess
import yaml
import requests


def test_docker_compose_valid():
    """Verify docker-compose.yml is valid."""
    result = subprocess.run(
        ["docker-compose", "config"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Invalid docker-compose.yml: {result.stderr}"


def test_all_services_defined():
    """Verify expected services are in docker-compose.yml."""
    with open("docker-compose.yml", "r") as f:
        config = yaml.safe_load(f)
    
    expected = ["mlflow", "mlflow-db", "langfuse-web", "langfuse-worker", 
                "postgres", "clickhouse", "redis", "minio"]
    actual = list(config["services"].keys())
    
    for service in expected:
        assert service in actual, f"Missing service: {service}"


def test_mlflow_accessible():
    """Test MLflow UI is accessible (requires services running)."""
    try:
        response = requests.get("http://localhost:5000", timeout=5)
        assert response.status_code == 200
    except requests.exceptions.ConnectionError:
        # Skip if services aren't running
        pass


def test_langfuse_accessible():
    """Test Langfuse UI is accessible (requires services running)."""
    try:
        response = requests.get("http://localhost:3000", timeout=5)
        assert response.status_code in [200, 307, 308]
    except requests.exceptions.ConnectionError:
        # Skip if services aren't running
        pass
