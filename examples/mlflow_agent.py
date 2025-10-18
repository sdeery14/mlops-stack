import asyncio
import os
import uuid
from typing import Generator

import mlflow
from mlflow.entities.span import SpanType
from mlflow.models import set_model
from mlflow.pyfunc.model import ResponsesAgent
from mlflow.types.responses import (
    ResponsesAgentRequest,
    ResponsesAgentResponse,
    ResponsesAgentStreamEvent,
)
from agents import Agent, Runner
from agents.items import (
    MessageOutputItem,
    ToolCallItem,
    ToolCallOutputItem,
    ReasoningItem,
)


class SimpleResponsesAgent(ResponsesAgent):
    def __init__(self, model: str):
        self.model = model
        self.agent = Agent(
            name="Assistant", 
            instructions="You are a helpful assistant", 
            model=self.model
        )

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict(self, request: ResponsesAgentRequest) -> ResponsesAgentResponse:
        """
        Run the agent and return structured MLflow ResponsesAgentResponse.
        Uses the OpenAI Agents SDK and converts results to MLflow format.
        """
        # Extract the user message content from the request
        user_input = request.input[0].content if request.input else ""
        
        # Run the OpenAI agent synchronously
        result = Runner.run_sync(self.agent, user_input)
        
        # Convert OpenAI agent results to MLflow output items
        output_items = []
        
        # Process new_items from the agent result
        for item in result.new_items:
            if isinstance(item.raw_item, MessageOutputItem):
                # Convert message output to MLflow format
                message = item.raw_item
                text_content = ""
                
                # Extract text from content array
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
                # Convert tool call to MLflow format
                tool_call = item.raw_item
                output_items.append(
                    self.create_function_call_item(
                        id=str(uuid.uuid4()),
                        call_id=tool_call.call_id if hasattr(tool_call, 'call_id') else str(uuid.uuid4()),
                        name=tool_call.name if hasattr(tool_call, 'name') else "unknown",
                        arguments=tool_call.arguments if hasattr(tool_call, 'arguments') else "{}"
                    )
                )
            elif isinstance(item.raw_item, ToolCallOutputItem):
                # Convert tool output to MLflow format
                tool_output = item.raw_item
                output_items.append(
                    self.create_function_call_output_item(
                        call_id=tool_output.call_id if hasattr(tool_output, 'call_id') else str(uuid.uuid4()),
                        output=str(tool_output.output if hasattr(tool_output, 'output') else "")
                    )
                )
            elif isinstance(item.raw_item, ReasoningItem):
                # Convert reasoning to MLflow format
                reasoning = item.raw_item
                output_items.append(
                    self.create_reasoning_item(
                        reasoning=reasoning.content if hasattr(reasoning, 'content') else str(reasoning),
                        id=str(uuid.uuid4())
                    )
                )
        
        # If no items were created, use final_output as fallback
        if not output_items:
            output_items.append(
                self.create_text_output_item(
                    text=str(result.final_output),
                    id=str(uuid.uuid4())
                )
            )
        
        return ResponsesAgentResponse(
            output=output_items,
            custom_outputs=request.custom_inputs  # Pass through custom inputs
        )

    @mlflow.trace(span_type=SpanType.AGENT)
    def predict_stream(
        self, request: ResponsesAgentRequest
    ) -> Generator[ResponsesAgentStreamEvent, None, None]:
        """
        Stream responses from the agent in real-time.
        Converts OpenAI Agents streaming events to MLflow ResponsesAgentStreamEvent format.
        """
        # Extract the user message content from the request
        user_input = request.input[0].content if request.input else ""
        
        # Create a unique item_id for text streaming
        text_item_id = str(uuid.uuid4())
        accumulated_text = ""
        
        async def async_stream():
            """Helper to run async streaming."""
            nonlocal accumulated_text
            
            result = await Runner.run_streamed(self.agent, user_input)
            
            async for event in result.stream_events():
                # Handle different event types from OpenAI Agents
                if event.type == "raw_response_event":
                    # Check if it's a text delta event
                    if hasattr(event, 'data') and hasattr(event.data, 'delta'):
                        delta = event.data.delta
                        accumulated_text += delta
                        
                        # Yield text delta using MLflow's helper method
                        yield ResponsesAgentStreamEvent(
                            **self.create_text_delta(
                                delta=delta,
                                item_id=text_item_id
                            )
                        )
            
            # After streaming completes, yield the final done event
            yield ResponsesAgentStreamEvent(
                type="response.output_item.done",
                item=self.create_text_output_item(
                    text=accumulated_text or str((await result).final_output),
                    id=text_item_id
                )
            )
        
        # Run the async streaming in a sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Collect and yield all events
            for event in loop.run_until_complete(self._collect_events(async_stream())):
                yield event
        finally:
            loop.close()
    
    async def _collect_events(self, async_gen):
        """Helper to collect async generator events."""
        events = []
        async for event in async_gen:
            events.append(event)
        return events


mlflow.openai.autolog()
agent = SimpleResponsesAgent(model="gpt-4o")
set_model(agent)