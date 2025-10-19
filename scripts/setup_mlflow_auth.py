"""
Initial MLflow Setup Script

Run this script ONCE after starting MLflow for the first time to:
1. Change the default admin password
2. Create initial team users
3. Set up basic permissions

Usage:
    python scripts/setup_mlflow_auth.py
"""

import os
import sys
from manage_mlflow_users import MLflowUserManager


def main():
    """Initial setup workflow."""
    print("\n" + "="*60)
    print("🔐 MLflow Initial Authentication Setup")
    print("="*60 + "\n")
    
    # Get credentials from environment or prompt
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    admin_username = os.getenv("MLFLOW_ADMIN_USERNAME", "admin")
    default_password = os.getenv("MLFLOW_ADMIN_PASSWORD", "change_me_on_first_login_123!")
    
    print(f"📍 MLflow Server: {tracking_uri}")
    print(f"👤 Admin Username: {admin_username}")
    print(f"🔑 Current Password: {'*' * len(default_password)}\n")
    
    # Initialize manager
    manager = MLflowUserManager(tracking_uri=tracking_uri)
    
    try:
        # Step 1: Authenticate with default credentials
        print("Step 1: Authenticating with default credentials...")
        manager.authenticate(admin_username, default_password)
        
        # Step 2: Change admin password
        print("\nStep 2: Change admin password")
        print("-" * 60)
        new_password = input("Enter new admin password (min 8 chars): ").strip()
        
        if len(new_password) < 8:
            print("❌ Password must be at least 8 characters")
            sys.exit(1)
            
        confirm_password = input("Confirm new admin password: ").strip()
        
        if new_password != confirm_password:
            print("❌ Passwords don't match")
            sys.exit(1)
            
        manager.change_admin_password(new_password)
        
        # Re-authenticate with new password
        print("\n🔄 Re-authenticating with new password...")
        manager.authenticate(admin_username, new_password)
        
        # Step 3: Create initial users (optional)
        print("\nStep 3: Create initial users (optional)")
        print("-" * 60)
        create_users = input("Create initial team users? (y/n): ").strip().lower()
        
        if create_users == 'y':
            users_to_create = []
            
            while True:
                username = input("\nUsername (or 'done' to finish): ").strip()
                if username.lower() == 'done':
                    break
                    
                password = input(f"Password for {username}: ").strip()
                is_admin = input(f"Make {username} an admin? (y/n): ").strip().lower() == 'y'
                
                users_to_create.append({
                    'username': username,
                    'password': password,
                    'is_admin': is_admin
                })
            
            # Create users
            for user in users_to_create:
                manager.create_user(user['username'], user['password'])
                if user['is_admin']:
                    manager.promote_user(user['username'])
        
        # Step 4: Summary
        print("\n" + "="*60)
        print("✅ Setup Complete!")
        print("="*60)
        print("\n📋 Current Users:")
        manager.list_users()
        
        print("\n⚠️  IMPORTANT: Update your .env file:")
        print(f"   MLFLOW_ADMIN_PASSWORD={new_password}")
        print("\n💡 Next steps:")
        print("   - Use scripts/manage_mlflow_users.py for user management")
        print("   - Grant experiment/model permissions as needed")
        print("   - See README.md for detailed usage examples\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
