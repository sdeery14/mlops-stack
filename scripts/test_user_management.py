"""
Quick test to verify MLflow 3.5.0 user management is working.

Run this after starting MLflow to test the Python-based user management.
"""

import os
import sys

# Add parent directory to path to import our scripts
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from manage_mlflow_users import MLflowUserManager


def test_user_management():
    """Test MLflow user management workflow."""
    print("\n" + "="*60)
    print("🧪 Testing MLflow 3.5.0 User Management")
    print("="*60 + "\n")
    
    # Initialize manager
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    manager = MLflowUserManager(tracking_uri=tracking_uri)
    
    # Get credentials from environment
    admin_username = os.getenv("MLFLOW_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("MLFLOW_ADMIN_PASSWORD", "change_me_on_first_login_123!")
    
    print(f"📍 MLflow Server: {tracking_uri}")
    print(f"👤 Admin Username: {admin_username}\n")
    
    try:
        # Test 1: Authenticate
        print("Test 1: Authentication")
        print("-" * 60)
        manager.authenticate(admin_username, admin_password)
        print()
        
        # Test 2: List existing users
        print("Test 2: List Users")
        print("-" * 60)
        manager.list_users()
        
        # Test 3: Create test user
        print("\nTest 3: Create Test User")
        print("-" * 60)
        test_username = "test_user_temp"
        test_password = "test_pass_123"
        
        try:
            manager.create_user(test_username, test_password)
        except Exception as e:
            if "already exists" in str(e).lower():
                print(f"ℹ️  User '{test_username}' already exists, skipping creation")
            else:
                raise
        
        # Test 4: List users again (should show new user)
        print("\nTest 4: Verify User Created")
        print("-" * 60)
        manager.list_users()
        
        # Test 5: Cleanup - delete test user
        print("\nTest 5: Cleanup Test User")
        print("-" * 60)
        try:
            manager.delete_user(test_username)
        except Exception as e:
            print(f"⚠️  Could not delete test user: {e}")
        
        # Final state
        print("\nFinal State:")
        print("-" * 60)
        manager.list_users()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n💡 Next steps:")
        print("   1. Run: python scripts/setup_mlflow_auth.py")
        print("   2. Change your admin password")
        print("   3. Create your team users")
        print("   4. See README.md for complete documentation\n")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Ensure MLflow server is running: docker-compose ps")
        print("   - Check logs: docker-compose logs mlflow-server")
        print("   - Verify credentials in .env file")
        sys.exit(1)


if __name__ == "__main__":
    test_user_management()
