# MLOps Stack

Local development environment for **MLflow 3.4.0** (model tracking) and **Langfuse v3** (LLM observability).

> **Note**: The Langfuse configuration follows the [official docker-compose.yml structure](https://github.com/langfuse/langfuse/blob/main/docker-compose.yml) for best practices and compatibility.

## Why Two Services?

This stack uses **Langfuse for tracing** and **MLflow for model management** because each excels at different tasks:

**Langfuse** - LLM Observability & Tracing:
- ✅ **Native async support**: Designed for modern async agent workflows (OpenAI Agents SDK, LangGraph, etc.)
- ✅ **Rich LLM traces**: Captures nested spans, function calls, streaming responses, and token usage automatically
- ✅ **No race conditions**: Handles concurrent agent executions without duplicate key errors
- ✅ **Built-in evaluations**: Supports human feedback, automated scoring, and A/B testing
- ✅ **Cost tracking**: Automatic token counting and cost calculation per trace

**MLflow** - Experiment Tracking & Model Registry:
- ✅ **Model versioning**: Complete model lifecycle management and registry
- ✅ **Artifact storage**: Centralized storage for models, plots, and datasets
- ✅ **Experiment comparison**: Compare runs across different model architectures
- ✅ **Production deployment**: Model serving and deployment integrations
- ✅ **Industry standard**: Widely adopted with extensive integrations

**In practice**: Use Langfuse's `@observe` decorator for detailed LLM traces, and MLflow's `start_run()` for experiment metadata and model artifacts. This gives you the best of both worlds without the limitations of `mlflow.openai.autolog()` (which doesn't support async agents).

## Quick Reference

| Service | URL | Default Credentials |
|---------|-----|---------------------|
| MLflow | http://localhost:5000 | `admin` / (from `.env`) |
| Langfuse | http://localhost:3000 | Create account on first visit |
| MinIO Console | http://localhost:9001 | (from `.env`) |

## Prerequisites

- Docker Desktop (min: 4 CPU cores, 8GB RAM, 20GB disk)
- OpenSSL (for generating security keys)
- Poetry (optional, for running tests)

## Quick Start

**1. Clone the repository:**

```bash
git clone https://github.com/sdeery14/mlops-stack.git
cd mlops-stack
```

**2. Copy the environment template:**

```bash
cp .env.example .env
```

**3. Generate security keys and update `.env`:**

```bash
# Generate NEXTAUTH_SECRET and SALT (run twice for two different keys)
openssl rand -base64 32

# Generate ENCRYPTION_KEY (run once, must be 64 hex characters)
openssl rand -hex 32
```

Edit `.env` and replace:
- `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` with generated keys
- Database passwords (Postgres, ClickHouse, MinIO)
- MLflow admin credentials

**4. Start services:**

```bash
docker-compose up -d
```

*First startup takes 2-3 minutes for database migrations. Watch progress: `docker-compose logs -f langfuse-web`*

**5. Access the UIs** using the URLs in the Quick Reference table above.

**6. Stop services:**

```bash
docker-compose down              # Keep data
docker-compose down -v           # Remove all data
```

## What's Included

**MLflow** (2 containers):
- MLflow Server (port 5000) - Experiment tracking UI/API
- PostgreSQL - Backend store for experiments/runs

**Langfuse** (7 containers - production architecture):
- Web Server (port 3000) - UI and API
- Worker - Async event processing
- PostgreSQL - Transactional data (users, projects, configs)
- ClickHouse - Analytics database (traces, observations)
- Redis - Cache and job queue
- MinIO (ports 9000, 9001) - S3-compatible object storage
- MinIO Client - One-time bucket setup

All services run on a shared Docker network (`mlops-network`). Data persists in Docker volumes.

## Testing

```bash
poetry install
poetry run pytest tests/test_stack.py -v
```

## Security Notes

⚠️ **Important**: 
- Never commit `.env` files with real credentials to version control
- Change all default passwords before using in production
- Use strong, unique passwords for each service
- For production: use managed databases, cloud storage, SSL/TLS, and secret management services

## Common Issues

| Issue | Solution |
|-------|----------|
| **Langfuse won't start** | Check `ENCRYPTION_KEY` is exactly 64 hex chars. Verify services: `docker-compose ps` |
| **Slow startup** | Normal on first run (2-3 min for migrations). Watch: `docker-compose logs -f langfuse-web` |
| **Port conflicts** | Change `MLFLOW_PORT` or `LANGFUSE_PORT` in `.env` |
| **Out of memory** | ClickHouse needs 2GB RAM. Increase Docker Desktop resources |

**Debugging**: `docker-compose logs -f [service-name]` | **Check health**: `docker-compose ps`

## Useful Commands

```bash
# View logs
docker-compose logs -f                              # All services
docker-compose logs -f langfuse-web langfuse-worker # Specific services

# Restart services
docker-compose restart mlflow
docker-compose restart langfuse-web

# Stop and remove
docker-compose stop           # Keep data
docker-compose down -v        # Remove all data

# Rebuild
docker-compose build --no-cache
```

## Usage Examples

### Langfuse for Tracing (Recommended for OpenAI Agents SDK)

```python
import mlflow
import asyncio
from agents import Agent, Runner
from langfuse.decorators import observe, langfuse_context

# Setup
mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-experiment")

@observe()  # Langfuse handles async agent tracing automatically
async def run_agent(user_input: str):
    agent = Agent(
        name="Assistant",
        instructions="You are a helpful assistant.",
    )
    result = await Runner.run(agent, user_input)
    return result

async def main():
    with mlflow.start_run() as run:
        # Langfuse captures detailed traces
        result = await run_agent("What is machine learning?")
        
        # MLflow logs experiment metadata
        mlflow.log_param("user_input", "What is machine learning?")
        mlflow.log_text(result.final_output, "output.txt")
        
        # Link traces between systems
        langfuse_context.update_current_trace(
            metadata={"mlflow_run_id": run.info.run_id}
        )
        
        langfuse_context.flush()

asyncio.run(main())
```

**Why not `mlflow.openai.autolog()`?** It doesn't support the async OpenAI Agents SDK and causes duplicate key errors due to race conditions.

### MLflow for Model Tracking

```python
import mlflow
from sklearn.ensemble import RandomForestClassifier

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("my-ml-experiment")

with mlflow.start_run():
    # Train model
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    # Log parameters and metrics
    mlflow.log_param("n_estimators", 100)
    mlflow.log_metric("accuracy", 0.95)
    
    # Log model to registry
    mlflow.sklearn.log_model(model, "model")
```

## MLflow ResponsesAgent Integration with OpenAI Agents SDK

### Overview

When integrating the OpenAI Agents SDK with MLflow's ResponsesAgent, it's crucial to properly convert between the two frameworks' output formats. This section explains how to correctly return OpenAI agents model output for MLflow.

### Key Concepts

**OpenAI Agents SDK** returns a `RunResult` object with:
- `final_output`: The final text/structured output from the agent
- `new_items`: List of `RunItem` objects (messages, tool calls, tool outputs, reasoning)
- `to_input_list()`: Conversation history (for constructing next turn input, NOT for output)

**MLflow ResponsesAgent** expects:
- Structured output items created via helper methods
- Only agent outputs (not user inputs)
- Proper item types: text, function_call, function_call_output, reasoning

### Item Type Mapping

| OpenAI Agents Type | MLflow Helper Method | Purpose |
|-------------------|---------------------|---------|
| `MessageOutputItem` | `create_text_output_item()` | Agent text responses |
| `ToolCallItem` | `create_function_call_item()` | Tool/function calls |
| `ToolCallOutputItem` | `create_function_call_output_item()` | Tool execution results |
| `ReasoningItem` | `create_reasoning_item()` | Model reasoning steps |

### Correct Implementation

#### Non-Streaming Predict Method

```python
from agents import Agent, Runner
from agents.items import MessageOutputItem, ToolCallItem, ToolCallOutputItem, ReasoningItem
import mlflow
from mlflow.entities.span import SpanType
from mlflow.pyfunc import ResponsesAgent
from mlflow.types.responses import ResponsesAgentRequest, ResponsesAgentResponse
import uuid

class SimpleResponsesAgent(ResponsesAgent):
    def __init__(self, model: str):
        self.agent = Agent(
            name="Assistant", 
            instructions="You are a helpful assistant", 
            model=model
        )

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        # Extract user input
        user_input = request.input[0].content if request.input else ""
        
        # Run OpenAI agent
        result = Runner.run_sync(self.agent, user_input)
        
        # Convert to MLflow output items
        output_items = []
        
        for item in result.new_items:
            if isinstance(item.raw_item, MessageOutputItem):
                # Extract text from message
                message = item.raw_item
                text_content = ""
                if hasattr(message, 'content') and message.content:
                    for content_item in message.content:
                        if hasattr(content_item, 'text'):
                            text_content += content_item.text
                
                output_items.append(
                    self.create_text_output_item(
                        text=text_content or str(result.final_output),
                        id=str(uuid.uuid4())
                    )
                )
            elif isinstance(item.raw_item, ToolCallItem):
                tool_call = item.raw_item
                output_items.append(
                    self.create_function_call_item(
                        id=str(uuid.uuid4()),
                        call_id=tool_call.call_id,
                        name=tool_call.name,
                        arguments=tool_call.arguments
                    )
                )
            elif isinstance(item.raw_item, ToolCallOutputItem):
                tool_output = item.raw_item
                output_items.append(
                    self.create_function_call_output_item(
                        call_id=tool_output.call_id,
                        output=str(tool_output.output)
                    )
                )
        
        # Fallback to final_output if no items
        if not output_items:
            output_items.append(
                self.create_text_output_item(
                    text=str(result.final_output),
                    id=str(uuid.uuid4())
                )
            )
        
        return ResponsesAgentResponse(
            output=output_items,
            custom_outputs=request.custom_inputs
        )
```

#### Streaming Predict Method

```python
import asyncio
from typing import Generator
from mlflow.types.responses import ResponsesAgentStreamEvent

class SimpleResponsesAgent(ResponsesAgent):
    @mlflow.trace(span_type=SpanType.AGENT)
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        user_input = request.input[0].content if request.input else ""
        text_item_id = str(uuid.uuid4())
        accumulated_text = ""
        
        async def async_stream():
            nonlocal accumulated_text
            result = await Runner.run_streamed(self.agent, user_input)
            
            async for event in result.stream_events():
                if event.type == "raw_response_event":
                    if hasattr(event, 'data') and hasattr(event.data, 'delta'):
                        delta = event.data.delta
                        accumulated_text += delta
                        
                        # Yield text delta
                        yield ResponsesAgentStreamEvent(
                            **self.create_text_delta(
                                delta=delta,
                                item_id=text_item_id
                            )
                        )
            
            # Yield final done event
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(
                    text=accumulated_text,
                    id=text_item_id
                )
            )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for event in loop.run_until_complete(self._collect_events(async_stream())):
                yield event
        finally:
            loop.close()
    
    async def _collect_events(self, async_gen):
        events = []
        async for event in async_gen:
            events.append(event)
        return events
```

### Common Mistakes to Avoid

❌ **Don't return raw conversation history**
```python
# WRONG - to_input_list() is for next turn input, not output
return ResponsesAgentResponse(output=result.to_input_list())
```

❌ **Don't filter conversation for output**
```python
# WRONG - this includes user messages and wrong format
output = [msg for msg in conversation if msg.get("role") != "user"]
```

❌ **Don't return raw dictionaries**
```python
# WRONG - bypasses MLflow's structured validation
output = [{"type": "message", "content": text}]
```

### Best Practices

✅ **Always use MLflow helper methods** - They ensure proper schema validation
✅ **Process `new_items` from RunResult** - These contain only agent outputs
✅ **Use `final_output` as fallback** - For simple text-only responses
✅ **Add MLflow tracing** - Use `@mlflow.trace()` decorator for observability
✅ **Generate unique IDs** - Use `uuid.uuid4()` for all item IDs

### Testing Your Agent

```python
import mlflow

# Test before logging
agent = SimpleResponsesAgent(model="gpt-4o")
response = agent.predict({
    "input": [{"role": "user", "content": "Hello"}],
    "context": {"conversation_id": "123"}
})
print(response)

# Log to MLflow
with mlflow.start_run():
    logged_agent = mlflow.pyfunc.log_model(
        python_model="examples/mlflow_agent.py",
        name="openai_agents_mlflow",
    )

# Load and test
loaded = mlflow.pyfunc.load_model(logged_agent.model_uri)
result = loaded.predict({
    "input": [{"role": "user", "content": "What is 2+2?"}],
    "context": {"conversation_id": "456"}
})
```

### Reference Documentation

- **MLflow ResponsesAgent**: https://mlflow.org/docs/latest/genai/serving/responses-agent/
- **OpenAI Agents Results**: https://openai.github.io/openai-agents-python/results/
- **MLflow API Reference**: https://mlflow.org/docs/latest/api_reference/python_api/mlflow.pyfunc.html

## License

See LICENSE file for details.
