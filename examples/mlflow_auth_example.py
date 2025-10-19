"""
MLflow Authentication Example

This script demonstrates how to use MLflow with authentication enabled.
Run this after setting up MLflow authentication.
"""

import os
import mlflow
from mlflow import MlflowClient
from mlflow.server import get_app_client


def setup_authentication():
    """Configure authentication credentials"""
    print("🔐 Setting up authentication...")
    
    # Option 1: Environment variables (recommended)
    os.environ['MLFLOW_TRACKING_USERNAME'] = 'admin'
    os.environ['MLFLOW_TRACKING_PASSWORD'] = 'change_me_on_first_login_123!'
    
    # Set tracking URI
    tracking_uri = "http://localhost:5000"
    mlflow.set_tracking_uri(tracking_uri)
    
    return tracking_uri


def create_users(tracking_uri):
    """Create example users"""
    print("\n👥 Creating users...")
    
    auth_client = get_app_client("basic-auth", tracking_uri=tracking_uri)
    
    try:
        # Create data scientist user
        auth_client.create_user(username="data_scientist", password="ds_password123")
        print("✅ Created user: data_scientist")
    except Exception as e:
        print(f"⚠️  User 'data_scientist' may already exist: {e}")
    
    try:
        # Create analyst user
        auth_client.create_user(username="analyst", password="analyst_password123")
        print("✅ Created user: analyst")
    except Exception as e:
        print(f"⚠️  User 'analyst' may already exist: {e}")


def create_experiment_with_permissions(tracking_uri):
    """Create an experiment and grant permissions"""
    print("\n📊 Creating experiment with permissions...")
    
    client = MlflowClient(tracking_uri=tracking_uri)
    auth_client = get_app_client("basic-auth", tracking_uri=tracking_uri)
    
    # Create experiment (admin gets MANAGE automatically)
    try:
        experiment_id = client.create_experiment(name="ml_project_demo")
        print(f"✅ Created experiment: ml_project_demo (ID: {experiment_id})")
    except Exception as e:
        print(f"⚠️  Experiment may already exist: {e}")
        experiment = client.get_experiment_by_name("ml_project_demo")
        experiment_id = experiment.experiment_id
        print(f"ℹ️  Using existing experiment (ID: {experiment_id})")
    
    # Grant EDIT permission to data_scientist
    try:
        auth_client.create_experiment_permission(
            experiment_id=experiment_id,
            username="data_scientist",
            permission="EDIT"
        )
        print("✅ Granted EDIT permission to data_scientist")
    except Exception as e:
        print(f"⚠️  Permission may already exist: {e}")
    
    # Grant READ permission to analyst
    try:
        auth_client.create_experiment_permission(
            experiment_id=experiment_id,
            username="analyst",
            permission="READ"
        )
        print("✅ Granted READ permission to analyst")
    except Exception as e:
        print(f"⚠️  Permission may already exist: {e}")
    
    return experiment_id


def log_sample_runs(experiment_id):
    """Log sample ML runs"""
    print("\n📝 Logging sample runs...")
    
    # Set experiment
    mlflow.set_experiment(experiment_id=experiment_id)
    
    # Run 1: Random Forest
    with mlflow.start_run(run_name="random_forest_baseline"):
        mlflow.log_param("model_type", "random_forest")
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("max_depth", 10)
        
        mlflow.log_metric("accuracy", 0.92)
        mlflow.log_metric("precision", 0.89)
        mlflow.log_metric("recall", 0.91)
        mlflow.log_metric("f1_score", 0.90)
        
        print("✅ Logged Random Forest run")
    
    # Run 2: XGBoost
    with mlflow.start_run(run_name="xgboost_tuned"):
        mlflow.log_param("model_type", "xgboost")
        mlflow.log_param("learning_rate", 0.01)
        mlflow.log_param("max_depth", 8)
        mlflow.log_param("n_estimators", 200)
        
        mlflow.log_metric("accuracy", 0.94)
        mlflow.log_metric("precision", 0.93)
        mlflow.log_metric("recall", 0.92)
        mlflow.log_metric("f1_score", 0.925)
        
        print("✅ Logged XGBoost run")


def test_user_access(tracking_uri, experiment_id):
    """Test access with different user credentials"""
    print("\n🔍 Testing user access...")
    
    # Test data_scientist (EDIT permission)
    print("\n📌 Testing data_scientist access (EDIT permission)...")
    os.environ['MLFLOW_TRACKING_USERNAME'] = 'data_scientist'
    os.environ['MLFLOW_TRACKING_PASSWORD'] = 'ds_password123'
    
    try:
        mlflow.set_experiment(experiment_id=experiment_id)
        with mlflow.start_run(run_name="data_scientist_test_run"):
            mlflow.log_param("user", "data_scientist")
            mlflow.log_metric("test_metric", 0.5)
        print("✅ data_scientist can log runs (EDIT permission working)")
    except Exception as e:
        print(f"❌ data_scientist access failed: {e}")
    
    # Test analyst (READ permission)
    print("\n📌 Testing analyst access (READ permission)...")
    os.environ['MLFLOW_TRACKING_USERNAME'] = 'analyst'
    os.environ['MLFLOW_TRACKING_PASSWORD'] = 'analyst_password123'
    
    client = MlflowClient(tracking_uri=tracking_uri)
    try:
        experiment = client.get_experiment(experiment_id)
        runs = client.search_runs(experiment_ids=[experiment_id])
        print(f"✅ analyst can read experiment: {experiment.name}")
        print(f"✅ analyst can view {len(runs)} runs")
    except Exception as e:
        print(f"❌ analyst read access failed: {e}")
    
    try:
        mlflow.set_experiment(experiment_id=experiment_id)
        with mlflow.start_run(run_name="analyst_test_run"):
            mlflow.log_param("user", "analyst")
        print("❌ analyst should NOT be able to log runs (READ only)")
    except Exception as e:
        print(f"✅ analyst correctly denied EDIT access: {type(e).__name__}")


def view_permissions(tracking_uri, experiment_id):
    """View experiment permissions"""
    print("\n🔐 Current experiment permissions:")
    
    # Switch back to admin
    os.environ['MLFLOW_TRACKING_USERNAME'] = 'admin'
    os.environ['MLFLOW_TRACKING_PASSWORD'] = 'change_me_on_first_login_123!'
    
    auth_client = get_app_client("basic-auth", tracking_uri=tracking_uri)
    
    try:
        permissions = auth_client.get_experiment_permission(experiment_id=experiment_id)
        print("\nExperiment Permissions:")
        print("=" * 60)
        for perm in permissions.experiment_permissions:
            print(f"  User: {perm.user_name:20} | Permission: {perm.permission}")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Could not retrieve permissions: {e}")


def main():
    """Main execution"""
    print("=" * 70)
    print("🚀 MLflow Authentication Demo")
    print("=" * 70)
    
    try:
        # Setup
        tracking_uri = setup_authentication()
        
        # Create users
        create_users(tracking_uri)
        
        # Create experiment and set permissions
        experiment_id = create_experiment_with_permissions(tracking_uri)
        
        # Log sample runs as admin
        log_sample_runs(experiment_id)
        
        # Test user access
        test_user_access(tracking_uri, experiment_id)
        
        # View permissions
        view_permissions(tracking_uri, experiment_id)
        
        print("\n" + "=" * 70)
        print("✅ Demo completed successfully!")
        print("=" * 70)
        print("\n📌 Next Steps:")
        print("   1. Visit http://localhost:5000 to see the UI")
        print("   2. Try logging in with different users:")
        print("      - admin / change_me_on_first_login_123!")
        print("      - data_scientist / ds_password123")
        print("      - analyst / analyst_password123")
        print("   3. Change the admin password (see MLFLOW_AUTH_GUIDE.md)")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Troubleshooting:")
        print("   - Ensure MLflow is running: docker compose ps")
        print("   - Check logs: docker compose logs mlflow")
        print("   - Verify authentication is enabled")


if __name__ == "__main__":
    main()
