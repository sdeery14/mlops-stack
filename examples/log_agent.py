import mlflow

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("example-openai-agents-sdk-with-tool-calling")

with mlflow.start_run():
    logged_agent_info = mlflow.pyfunc.log_model(
        python_model="examples/mlflow_agent.py",  # path to the file defining the class
        name="openai_agents_tool_calling",
    )

print("Model logged to:", logged_agent_info.model_uri)
