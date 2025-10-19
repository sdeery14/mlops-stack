"""
MLflow User Management Script

This script helps you manage MLflow users, permissions, and authentication
after the MLflow server is running with Basic Auth enabled.

Usage:
    python scripts/manage_mlflow_users.py --help
"""

import os
import sys
import argparse
from typing import Optional, List
from mlflow.server import get_app_client


class MLflowUserManager:
    """Manage MLflow users and permissions."""
    
    def __init__(self, tracking_uri: str = "http://localhost:5000"):
        """
        Initialize the user manager.
        
        Args:
            tracking_uri: MLflow tracking server URI
        """
        self.tracking_uri = tracking_uri
        self.client = None
        
    def authenticate(self, username: str, password: str):
        """
        Authenticate with MLflow server.
        
        Args:
            username: Admin username
            password: Admin password
        """
        os.environ['MLFLOW_TRACKING_USERNAME'] = username
        os.environ['MLFLOW_TRACKING_PASSWORD'] = password
        self.client = get_app_client("basic-auth", tracking_uri=self.tracking_uri)
        print(f"✅ Authenticated as '{username}'")
        
    def change_admin_password(self, new_password: str):
        """
        Change the admin password (run this immediately after first startup!).
        
        Args:
            new_password: New secure password
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        self.client.update_user_password(
            username=os.environ['MLFLOW_TRACKING_USERNAME'],
            password=new_password
        )
        print(f"✅ Admin password updated successfully")
        print(f"⚠️  Update your .env file with: MLFLOW_ADMIN_PASSWORD={new_password}")
        
    def create_user(self, username: str, password: str):
        """
        Create a new user.
        
        Args:
            username: New username
            password: User password
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.create_user(username=username, password=password)
            print(f"✅ User '{username}' created successfully")
        except Exception as e:
            print(f"❌ Error creating user: {e}")
            
    def delete_user(self, username: str):
        """
        Delete a user.
        
        Args:
            username: Username to delete
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.delete_user(username=username)
            print(f"✅ User '{username}' deleted successfully")
        except Exception as e:
            print(f"❌ Error deleting user: {e}")
            
    def promote_user(self, username: str):
        """
        Promote a user to admin.
        
        Args:
            username: Username to promote
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.update_user_admin(username=username, is_admin=True)
            print(f"✅ User '{username}' promoted to admin")
        except Exception as e:
            print(f"❌ Error promoting user: {e}")
            
    def demote_user(self, username: str):
        """
        Demote an admin user to regular user.
        
        Args:
            username: Username to demote
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.update_user_admin(username=username, is_admin=False)
            print(f"✅ User '{username}' demoted to regular user")
        except Exception as e:
            print(f"❌ Error demoting user: {e}")
            
    def list_users(self):
        """List all users."""
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            # Get all users by calling without username parameter
            users = self.client.get_user()
            print("\n📋 MLflow Users:")
            print("-" * 60)
            if isinstance(users, list):
                for user in users:
                    admin_badge = "👑 ADMIN" if user.is_admin else "👤 USER"
                    print(f"{admin_badge} | {user.username} (ID: {user.id})")
                print("-" * 60)
                print(f"Total users: {len(users)}\n")
            else:
                # Single user returned
                admin_badge = "👑 ADMIN" if users.is_admin else "👤 USER"
                print(f"{admin_badge} | {users.username} (ID: {users.id})")
                print("-" * 60)
                print("Total users: 1\n")
        except TypeError as e:
            # Handle API change - try getting users differently
            print(f"⚠️  Note: Using alternative method to list users")
            try:
                # Try to get admin user as baseline
                admin_user = self.client.get_user(username=os.environ.get('MLFLOW_TRACKING_USERNAME', 'admin'))
                print("\n📋 MLflow Users:")
                print("-" * 60)
                admin_badge = "👑 ADMIN" if admin_user.is_admin else "👤 USER"
                print(f"{admin_badge} | {admin_user.username} (ID: {admin_user.id})")
                print("-" * 60)
                print("ℹ️  List all users API may require MLflow 3.5.0+\n")
            except Exception as inner_e:
                print(f"❌ Error: {inner_e}")
        except Exception as e:
            print(f"❌ Error listing users: {e}")
            
    def grant_experiment_permission(self, experiment_id: str, username: str, 
                                   permission: str = "READ"):
        """
        Grant experiment permission to a user.
        
        Args:
            experiment_id: Experiment ID
            username: Username
            permission: Permission level (READ, EDIT, MANAGE)
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        valid_permissions = ["READ", "EDIT", "MANAGE"]
        if permission not in valid_permissions:
            raise ValueError(f"Permission must be one of: {valid_permissions}")
            
        try:
            self.client.create_experiment_permission(
                experiment_id=experiment_id,
                username=username,
                permission=permission
            )
            print(f"✅ Granted {permission} permission on experiment {experiment_id} to '{username}'")
        except Exception as e:
            print(f"❌ Error granting permission: {e}")
            
    def grant_model_permission(self, model_name: str, username: str, 
                              permission: str = "READ"):
        """
        Grant registered model permission to a user.
        
        Args:
            model_name: Registered model name
            username: Username
            permission: Permission level (READ, EDIT, MANAGE)
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        valid_permissions = ["READ", "EDIT", "MANAGE"]
        if permission not in valid_permissions:
            raise ValueError(f"Permission must be one of: {valid_permissions}")
            
        try:
            self.client.create_registered_model_permission(
                name=model_name,
                username=username,
                permission=permission
            )
            print(f"✅ Granted {permission} permission on model '{model_name}' to '{username}'")
        except Exception as e:
            print(f"❌ Error granting permission: {e}")
            
    def revoke_experiment_permission(self, experiment_id: str, username: str):
        """
        Revoke experiment permission from a user.
        
        Args:
            experiment_id: Experiment ID
            username: Username
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.delete_experiment_permission(
                experiment_id=experiment_id,
                username=username
            )
            print(f"✅ Revoked experiment {experiment_id} permission from '{username}'")
        except Exception as e:
            print(f"❌ Error revoking permission: {e}")
            
    def revoke_model_permission(self, model_name: str, username: str):
        """
        Revoke registered model permission from a user.
        
        Args:
            model_name: Registered model name
            username: Username
        """
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")
            
        try:
            self.client.delete_registered_model_permission(
                name=model_name,
                username=username
            )
            print(f"✅ Revoked model '{model_name}' permission from '{username}'")
        except Exception as e:
            print(f"❌ Error revoking permission: {e}")


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Manage MLflow users and permissions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Change admin password (DO THIS FIRST!)
  python scripts/manage_mlflow_users.py change-password --new-password "secure_pass_123"
  
  # Create a new user
  python scripts/manage_mlflow_users.py create-user --username alice --password alice_pass
  
  # List all users
  python scripts/manage_mlflow_users.py list-users
  
  # Promote user to admin
  python scripts/manage_mlflow_users.py promote-user --username alice
  
  # Grant experiment permission
  python scripts/manage_mlflow_users.py grant-exp --experiment-id 1 --username alice --permission EDIT
  
  # Grant model permission
  python scripts/manage_mlflow_users.py grant-model --model-name my-model --username alice --permission MANAGE
        """
    )
    
    parser.add_argument(
        "--uri",
        default="http://localhost:5000",
        help="MLflow tracking URI (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--admin-username",
        default=os.getenv("MLFLOW_ADMIN_USERNAME", "admin"),
        help="Admin username (default: from MLFLOW_ADMIN_USERNAME or 'admin')"
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("MLFLOW_ADMIN_PASSWORD"),
        help="Admin password (default: from MLFLOW_ADMIN_PASSWORD)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Change password
    change_pass = subparsers.add_parser("change-password", help="Change admin password")
    change_pass.add_argument("--new-password", required=True, help="New password")
    
    # Create user
    create_user = subparsers.add_parser("create-user", help="Create a new user")
    create_user.add_argument("--username", required=True, help="New username")
    create_user.add_argument("--password", required=True, help="User password")
    
    # Delete user
    delete_user = subparsers.add_parser("delete-user", help="Delete a user")
    delete_user.add_argument("--username", required=True, help="Username to delete")
    
    # List users
    subparsers.add_parser("list-users", help="List all users")
    
    # Promote user
    promote = subparsers.add_parser("promote-user", help="Promote user to admin")
    promote.add_argument("--username", required=True, help="Username to promote")
    
    # Demote user
    demote = subparsers.add_parser("demote-user", help="Demote admin to user")
    demote.add_argument("--username", required=True, help="Username to demote")
    
    # Grant experiment permission
    grant_exp = subparsers.add_parser("grant-exp", help="Grant experiment permission")
    grant_exp.add_argument("--experiment-id", required=True, help="Experiment ID")
    grant_exp.add_argument("--username", required=True, help="Username")
    grant_exp.add_argument("--permission", default="READ", 
                          choices=["READ", "EDIT", "MANAGE"], help="Permission level")
    
    # Grant model permission
    grant_model = subparsers.add_parser("grant-model", help="Grant model permission")
    grant_model.add_argument("--model-name", required=True, help="Model name")
    grant_model.add_argument("--username", required=True, help="Username")
    grant_model.add_argument("--permission", default="READ",
                            choices=["READ", "EDIT", "MANAGE"], help="Permission level")
    
    # Revoke experiment permission
    revoke_exp = subparsers.add_parser("revoke-exp", help="Revoke experiment permission")
    revoke_exp.add_argument("--experiment-id", required=True, help="Experiment ID")
    revoke_exp.add_argument("--username", required=True, help="Username")
    
    # Revoke model permission
    revoke_model = subparsers.add_parser("revoke-model", help="Revoke model permission")
    revoke_model.add_argument("--model-name", required=True, help="Model name")
    revoke_model.add_argument("--username", required=True, help="Username")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if not args.admin_password:
        print("❌ Error: Admin password required.")
        print("   Set MLFLOW_ADMIN_PASSWORD environment variable or use --admin-password")
        sys.exit(1)
    
    # Initialize manager
    manager = MLflowUserManager(tracking_uri=args.uri)
    
    try:
        manager.authenticate(args.admin_username, args.admin_password)
        
        # Execute command
        if args.command == "change-password":
            manager.change_admin_password(args.new_password)
        elif args.command == "create-user":
            manager.create_user(args.username, args.password)
        elif args.command == "delete-user":
            manager.delete_user(args.username)
        elif args.command == "list-users":
            manager.list_users()
        elif args.command == "promote-user":
            manager.promote_user(args.username)
        elif args.command == "demote-user":
            manager.demote_user(args.username)
        elif args.command == "grant-exp":
            manager.grant_experiment_permission(
                args.experiment_id, args.username, args.permission
            )
        elif args.command == "grant-model":
            manager.grant_model_permission(
                args.model_name, args.username, args.permission
            )
        elif args.command == "revoke-exp":
            manager.revoke_experiment_permission(args.experiment_id, args.username)
        elif args.command == "revoke-model":
            manager.revoke_model_permission(args.model_name, args.username)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
