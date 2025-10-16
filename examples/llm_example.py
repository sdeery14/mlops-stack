import mlflow
import asyncio
import os
from agents import Agent, Runner
from langfuse import get_client, observe
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from dotenv import load_dotenv
load_dotenv()

# Initialize Langfuse client
langfuse = get_client()

# Verify Langfuse connection
if langfuse.auth_check():
    print("Langfuse client is authenticated and ready!")
else:
    print("Authentication failed. Please check your credentials and host.")

# Instrument OpenAI Agents with OpenInference
OpenAIAgentsInstrumentor().instrument()

# Setup MLflow
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-experiment")

async def run_agent(user_input: str):
    """Run the agent with the given user input."""
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )
    result = await Runner.run(agent, user_input)
    return result

@observe
async def main():
    with mlflow.start_run() as run:
        user_input = "What is machine learning?"
        
        # Run agent - Langfuse automatically captures detailed traces via OpenInference instrumentation
        result = await run_agent(user_input)
        
        # MLflow logs experiment metadata
        mlflow.log_param("user_input", user_input)
        mlflow.log_text(result.final_output, "output.txt")
        mlflow.log_param("mlflow_run_id", run.info.run_id)
        
        print(f"Agent response: {result.final_output}")
        print(f"MLflow run ID: {run.info.run_id}")

        langfuse.update_current_trace(
            input=user_input,
            output=result.final_output,
            user_id="user_123",
            session_id="session_abc",
            tags=["agent", "my-trace"],
            metadata={"email": "user@langfuse.com"},
            version="1.0.0"
    )
        
        # Flush Langfuse to ensure all traces are sent
        langfuse.flush()

if __name__ == "__main__":
    asyncio.run(main())