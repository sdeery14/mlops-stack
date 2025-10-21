#!/usr/bin/env python3
"""
MLOps Stack Deployment Helper

This script helps deploy the MLOps stack with proper validation and setup.
"""

import os
import sys
import subprocess
import time
import shutil
import secrets
import string
from pathlib import Path

# Fix encoding for Windows PowerShell to support emojis
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Import validation script
from validate_services import main as validate_services_main

def run_command(cmd, description, check=True):
    """Run a shell command with description"""
    print(f"🔄 {description}...")
    try:
        # On Windows, we need to handle encoding differently for subprocess
        # Setting encoding explicitly helps prevent hangs with docker-compose output
        result = subprocess.run(
            cmd, 
            shell=True, 
            check=check, 
            capture_output=True, 
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        if result.returncode == 0:
            print(f"✅ {description} completed")
            return True
        else:
            print(f"❌ {description} failed:")
            print(result.stderr)
            return False
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        return False

def generate_secure_password(length=16):
    """Generate a secure random password"""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_secret_key(length=64):
    """Generate a secure secret key"""
    return secrets.token_hex(length // 2)

def generate_salt():
    """Generate a secure salt"""
    return secrets.token_hex(16)

def create_env_from_template():
    """Create .env file from .env.example with secure generated values"""
    env_example_path = Path(".env.example")
    env_path = Path(".env")
    
    if not env_example_path.exists():
        print("❌ .env.example file not found")
        return False
    
    print("🔐 Generating secure .env file from template...")
    
    # Read the template
    with open(env_example_path, 'r') as f:
        lines = f.readlines()
    
    # Process each line to replace placeholder values
    processed_lines = []
    
    # Pre-generate passwords for specific database fields
    postgres_passwords = {
        'MLFLOW_POSTGRES_PASSWORD': generate_secure_password(20),
        'MLFLOW_POSTGRES_AUTH_PASSWORD': generate_secure_password(20),
        'LANGFUSE_POSTGRES_PASSWORD': generate_secure_password(20),
    }
    
    for line in lines:
        
        # Replace specific placeholder patterns
        replacements = {
            'change_me_with_a_secure_key': generate_secret_key(64),
            'change_me_on_first_login': generate_secure_password(20),
            'change_me_with_a_secure_secret': generate_secret_key(64),
            'change_me_with_a_secure_salt': generate_salt(),
            'change_me_with_64_char_hex_key_generate_via_openssl_rand_hex_32': generate_secret_key(64),
            'change_me_langfuse_password': generate_secure_password(20),
            'change_me_clickhouse_password': generate_secure_password(20),
            'change_me_minio_password': generate_secure_password(20),
            'change_me_redis_password': generate_secure_password(20),
        }
        
        for placeholder, secure_value in replacements.items():
            line = line.replace(placeholder, secure_value)
        
        # Replace PostgreSQL database passwords specifically (before other processing)
        # This ensures database passwords are always replaced with secure values
        if '=' in line and not line.strip().startswith('#'):
            postgres_password_replaced = False
            for db_password_key, new_password in postgres_passwords.items():
                if line.strip().startswith(f'{db_password_key}='):
                    # Extract just the key part before the =
                    key = line.split('=', 1)[0]
                    line = f"{key}={new_password}\n"
                    postgres_password_replaced = True
                    break
            
            # Skip further processing for this line if we replaced a postgres password
            if postgres_password_replaced:
                processed_lines.append(line)
                continue
        
        # Handle default values that appear as standalone values (not in variable substitutions)
        # Only replace if it's after an = sign and not inside ${}
        if '=' in line and not line.strip().startswith('#'):
            # Split on = to get the value part
            parts = line.split('=', 1)
            if len(parts) == 2:
                key = parts[0]
                value = parts[1].rstrip('\n')
                
                # Don't replace if the value contains variable substitution
                if '${' not in value:
                    # Replace common default values
                    value_replacements = {
                        'mysecret': generate_secret_key(32),
                        'mysalt': generate_salt(),
                        'miniosecret': generate_secure_password(20),
                        'myredissecret': generate_secure_password(20),
                        'clickhouse': generate_secure_password(20),
                        'postgres': generate_secure_password(20),
                    }
                    
                    for default_val, secure_val in value_replacements.items():
                        if value.strip() == default_val:
                            value = secure_val
                            break
                        elif value.strip() == f'-{default_val}':
                            value = f'-{secure_val}'
                            break
                
                line = f"{key}={value}\n"
        
        processed_lines.append(line)
    
    # Ensure MLflow admin credentials exist in the processed lines.
    # If the template didn't include them, append defaults. If they exist but are empty, replace with generated values.
    has_user = any(line.startswith('MLFLOW_ADMIN_USERNAME=') for line in processed_lines)
    has_pass = any(line.startswith('MLFLOW_ADMIN_PASSWORD=') for line in processed_lines)

    # If username missing, add a sensible default
    if not has_user:
        processed_lines.append('MLFLOW_ADMIN_USERNAME=admin\n')
    else:
        # If present but empty, set to 'admin'
        new_lines = []
        for line in processed_lines:
            if line.startswith('MLFLOW_ADMIN_USERNAME='):
                val = line.split('=', 1)[1].strip()
                if not val:
                    new_lines.append('MLFLOW_ADMIN_USERNAME=admin\n')
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        processed_lines = new_lines

    # If password missing, generate and add one. If present but empty, replace with generated password.
    if not has_pass:
        admin_pass = generate_secure_password(20)
        processed_lines.append(f'MLFLOW_ADMIN_PASSWORD={admin_pass}\n')
    else:
        new_lines = []
        for line in processed_lines:
            if line.startswith('MLFLOW_ADMIN_PASSWORD='):
                val = line.split('=', 1)[1].strip()
                if not val:
                    new_lines.append(f'MLFLOW_ADMIN_PASSWORD={generate_secure_password(20)}\n')
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        processed_lines = new_lines

    # Write the new .env file
    with open(env_path, 'w') as f:
        f.writelines(processed_lines)
    
    print("✅ Secure .env file generated successfully")
    print("🔑 Generated secure passwords and keys for all services")
    return True

def check_prerequisites():
    """Check if required tools are installed"""
    print("🔍 Checking prerequisites...")
    
    # Check Docker
    if not shutil.which("docker"):
        print("❌ Docker is not installed or not in PATH")
        return False
    
    # Check Docker Compose
    if not (shutil.which("docker-compose") or run_command("docker compose version", "Docker Compose check", False)):
        print("❌ Docker Compose is not available")
        return False
    
    # Check if Docker is running
    if not run_command("docker info", "Docker daemon check", False):
        print("❌ Docker daemon is not running")
        return False
    
    print("✅ All prerequisites are available")
    return True

def check_env_file():
    """Check if .env file exists and has required variables, or create it automatically"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    if not env_path.exists():
        if env_example_path.exists():
            # Automatically create .env with secure values
            return create_env_from_template()
        else:
            print("❌ Neither .env nor .env.example found")
            return False
    
    # Check for placeholder values that need to be changed
    # We check actual values, not just substrings to avoid false positives
    with open(env_path) as f:
        lines = f.readlines()
    
    # Specific placeholder patterns that should be replaced
    placeholder_patterns = [
        "change_me",
        "CHANGEME",
    ]
    
    found_placeholders = []
    for line in lines:
        if '=' in line and not line.strip().startswith('#'):
            # Extract the value part
            parts = line.split('=', 1)
            if len(parts) == 2:
                value = parts[1].strip()
                # Check if the value contains any placeholder pattern
                for pattern in placeholder_patterns:
                    if pattern in value:
                        found_placeholders.append(pattern)
                        break
    
    if found_placeholders:
        print("⚠️  Found placeholder values in .env file:")
        for placeholder in set(found_placeholders):
            print(f"   - {placeholder}")
        print("\n🔄 Regenerating .env file with secure values...")
        return create_env_from_template()
    
    print("✅ .env file looks good")
    return True

def deploy_stack():
    """Deploy the MLOps stack"""
    print("🚀 Deploying MLOps Stack...")
    
    if not run_command("docker-compose down -v", "Stopping any existing containers", False):
        print("ℹ️  No existing containers to stop")
    
    if not run_command("docker-compose pull", "Pulling latest images"):
        return False
    
    # For docker-compose up, don't capture output to avoid hanging on Windows
    print("🔄 Starting services...")
    result = subprocess.run("docker-compose up -d --build", shell=True)
    if result.returncode == 0:
        print("✅ Starting services completed")
    else:
        print("❌ Starting services failed")
        return False
    
    print("⏳ Waiting for services to start (60 seconds)...")
    time.sleep(60)
    
    return True

def validate_deployment():
    """Validate the deployment"""
    print("🔍 Validating deployment...")
    
    try:
        # Call the validation script's main function directly
        result = validate_services_main()
        if result != 0:
            print("❌ Service validation failed")
            print("💡 Try running: docker-compose logs -f")
            return False
        return True
    except Exception as e:
        print(f"❌ Service validation failed with error: {e}")
        print("💡 Try running: docker-compose logs -f")
        return False

def main():
    print("🏗️  MLOps Stack Deployment Helper")
    print("=" * 50)
    
    # Change to script directory
    script_dir = Path(__file__).parent.parent
    os.chdir(script_dir)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Check environment file
    if not check_env_file():
        print("\n❌ Failed to create or validate .env file")
        sys.exit(1)
    
    # Deploy stack
    if not deploy_stack():
        sys.exit(1)
    
    # Validate deployment
    if not validate_deployment():
        sys.exit(1)
    
    print("\\n🎉 MLOps Stack deployed successfully!")
    print("\\n🌐 Access your services:")
    print("   • MLflow: http://localhost:5000")
    print("   • Langfuse: http://localhost:3000")
    print("   • MLflow MinIO Console: http://localhost:9003")
    print("   • Langfuse MinIO Console: http://localhost:9091")
    
    # Show MLflow admin credentials if they were generated
    env_path = Path(".env")
    if env_path.exists():
        with open(env_path) as f:
            content = f.read()
            
        # Extract MLflow admin credentials
        admin_username = None
        admin_password = None
        for line in content.split('\n'):
            if line.startswith('MLFLOW_ADMIN_USERNAME='):
                admin_username = line.split('=', 1)[1]
            elif line.startswith('MLFLOW_ADMIN_PASSWORD='):
                admin_password = line.split('=', 1)[1]
        
        if admin_username and admin_password:
            print("\\n🔐 MLflow Admin Credentials:")
            print(f"   Username: {admin_username}")
            print(f"   Password: {admin_password}")
    
    print("\\n🔐 Next steps:")
    print("   1. Run: poetry run python scripts/setup_mlflow_auth.py")
    print("   2. Create your first Langfuse project at http://localhost:3000")
    print("   3. Check out the examples/ directory for usage samples")
    print("\\n💡 All passwords and secrets have been automatically generated and saved in .env")

if __name__ == "__main__":
    main()