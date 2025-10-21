#!/usr/bin/env python3
"""
MLOps Stack Service Validation Script

This script validates that all services in the MLOps stack are running correctly
and can communicate with each other.
"""

import os
import sys
import time
import requests
import psycopg2
from urllib3.exceptions import InsecureRequestWarning
import argparse
from dotenv import load_dotenv

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

def check_service_health(name, url, timeout=30):
    """Check if a service is healthy by making an HTTP request"""
    print(f"🔍 Checking {name} at {url}...")
    
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            print(f"✅ {name} is healthy")
            return True
        else:
            print(f"⚠️  {name} returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {name} is not accessible: {e}")
        return False

def check_postgres(name, host, port, user, password, database):
    """Check PostgreSQL connection"""
    print(f"🔍 Checking {name} PostgreSQL at {host}:{port}...")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=10
        )
        conn.close()
        print(f"✅ {name} PostgreSQL is accessible")
        return True
    except psycopg2.Error as e:
        print(f"❌ {name} PostgreSQL connection failed: {e}")
        return False

def check_minio(name, url, access_key, secret_key):
    """Check MinIO S3 API"""
    print(f"🔍 Checking {name} MinIO at {url}...")
    
    try:
        # Try to access the health endpoint
        health_url = f"{url}/minio/health/live"
        response = requests.get(health_url, timeout=10)
        if response.status_code == 200:
            print(f"✅ {name} MinIO is healthy")
            return True
        else:
            print(f"⚠️  {name} MinIO health check returned {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {name} MinIO is not accessible: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Validate MLOps Stack services")
    parser.add_argument("--wait", "-w", type=int, default=0, 
                       help="Wait time in seconds before starting validation")
    args = parser.parse_args()
    
    # Load .env file first
    load_dotenv()
    
    if args.wait > 0:
        print(f"⏳ Waiting {args.wait} seconds before validation...")
        time.sleep(args.wait)
    
    print("🚀 MLOps Stack Service Validation")
    print("=" * 50)
    
    # Load environment variables from .env file (now they should be loaded)
    mlflow_postgres_user = os.getenv("MLFLOW_POSTGRES_USER", "mlflow")
    mlflow_postgres_password = os.getenv("MLFLOW_POSTGRES_PASSWORD", "mlflow123")
    mlflow_postgres_db = os.getenv("MLFLOW_POSTGRES_DB", "mlflow")
    
    mlflow_auth_user = os.getenv("MLFLOW_POSTGRES_AUTH_USER", "mlflow_auth")
    mlflow_auth_password = os.getenv("MLFLOW_POSTGRES_AUTH_PASSWORD", "mlflow_auth123")
    mlflow_auth_db = os.getenv("MLFLOW_POSTGRES_AUTH_DB", "mlflow_auth")
    
    langfuse_postgres_user = os.getenv("LANGFUSE_POSTGRES_USER", "langfuse")
    langfuse_postgres_password = os.getenv("LANGFUSE_POSTGRES_PASSWORD", "change_me_langfuse_password")
    langfuse_postgres_db = os.getenv("LANGFUSE_POSTGRES_DB", "langfuse")
    
    mlflow_minio_user = os.getenv("MLFLOW_MINIO_ROOT_USER", "minio")
    mlflow_minio_password = os.getenv("MLFLOW_MINIO_ROOT_PASSWORD", "minio123")
    
    langfuse_minio_user = os.getenv("MINIO_ROOT_USER", "langfuse_minio")
    langfuse_minio_password = os.getenv("MINIO_ROOT_PASSWORD", "change_me_minio_password")
    
    results = []
    
    # MLflow Services
    print("\\n📊 MLflow Services")
    print("-" * 30)
    results.append(check_postgres("MLflow", "localhost", 5434, 
                                 mlflow_postgres_user, mlflow_postgres_password, mlflow_postgres_db))
    results.append(check_postgres("MLflow Auth", "localhost", 5433, 
                                 mlflow_auth_user, mlflow_auth_password, mlflow_auth_db))
    results.append(check_minio("MLflow", "http://localhost:9002", 
                              mlflow_minio_user, mlflow_minio_password))
    results.append(check_service_health("MLflow Server", "http://localhost:5000/health"))
    
    # Langfuse Services
    print("\\n🔍 Langfuse Services")
    print("-" * 30)
    results.append(check_postgres("Langfuse", "localhost", 5435,
                                 langfuse_postgres_user, langfuse_postgres_password, langfuse_postgres_db))
    results.append(check_minio("Langfuse", "http://localhost:9090",
                              langfuse_minio_user, langfuse_minio_password))
    results.append(check_service_health("Langfuse ClickHouse", "http://localhost:8123/ping"))
    results.append(check_service_health("Langfuse Web", "http://localhost:3000/api/public/health"))
    
    # Summary
    print("\\n📋 Validation Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} services are healthy!")
        print("\\n🚀 Your MLOps stack is ready to use:")
        print("   • MLflow: http://localhost:5000")
        print("   • Langfuse: http://localhost:3000")
        print("   • MLflow MinIO Console: http://localhost:9003")
        print("   • Langfuse MinIO Console: http://localhost:9091")
        return 0
    else:
        print(f"❌ {total - passed} out of {total} services failed validation")
        print("\\n🔧 Troubleshooting:")
        print("   • Check docker-compose logs: docker-compose logs -f")
        print("   • Verify .env configuration matches .env.example")
        print("   • Ensure all containers are running: docker-compose ps")
        print("   • Wait longer for services to start up (especially on first run)")
        return 1

if __name__ == "__main__":
    sys.exit(main())