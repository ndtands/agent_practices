import logging
from collections.abc import AsyncIterable
from typing import Any, Dict, List, Literal
from pydantic import BaseModel
from langchain_core.messages import AIMessage, AIMessageChunk
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from configs import azure_gpt4o_mini

# Configure logging
logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO)


class ResponseFormat(BaseModel):
    """Schema for structured agent responses."""
    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class WeatherAgent:
    """A specialized agent for retrieving and relaying weather forecast information using MCP tools.

    Attributes:
        model: The language model used for processing queries.
        mcp_tools (List[Any]): List of Model Context Protocol (MCP) tools for weather data retrieval.
        agent_runnable: The LangGraph agent instance for processing queries.
        memory: Checkpoint memory for maintaining conversation state.
    """

    SYSTEM_INSTRUCTION = """
    You are a specialized weather forecast assistant. Your primary function is to utilize the provided tools to retrieve and relay weather information in response to user queries. You must rely exclusively on these tools for data and refrain from inventing information. Ensure that all responses include the detailed output from the tools used and are formatted in Markdown.
    """

    RESPONSE_FORMAT_INSTRUCTION = (
        'Select status as "completed" if the request is fully addressed and no further input is needed. '
        'Select status as "input_required" if you need more information from the user or are asking a clarifying question. '
        'Select status as "error" if an error occurred or the request cannot be fulfilled.'
    )

    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']

    def __init__(self, mcp_tools: List[Any]):
        """Initialize the WeatherAgent with necessary dependencies.

        Args:
            mcp_tools: List of MCP tools for weather data retrieval.

        Raises:
            ValueError: If no MCP tools are provided.
        """
        if not mcp_tools:
            raise ValueError("No MCP tools provided to WeatherAgent")

        self.model = azure_gpt4o_mini
        self.mcp_tools = mcp_tools
        self.memory = MemorySaver()
        self.agent_runnable = create_react_agent(
            model=self.model,
            tools=self.mcp_tools,
            checkpointer=self.memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=(self.RESPONSE_FORMAT_INSTRUCTION, ResponseFormat),
        )
        # self.agent_runnable = self.agent_runnable.with_config(tags=["weather_agent"])

    async def ainvoke(self, query: str, session_id: str) -> Dict[str, Any]:
        """Process a weather query and return a structured response.

        Args:
            query: The user's weather-related query.
            session_id: Unique identifier for the session.

        Returns:
            A dictionary containing the response status, input requirement, and content.
        """
        logger.info(f"Processing query: '{query}' for session: '{session_id}'")
        try:
            config = {'configurable': {'thread_id': session_id}}
            langgraph_input = {'messages': [('user', query)]}
            await self.agent_runnable.ainvoke(langgraph_input, config)
            return self._extract_response(config)
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return self._format_error_response(f"Error processing query: {str(e)}")

    async def astream(self, query: str, session_id: str) -> AsyncIterable[Dict[str, Any]]:
        """Stream weather query responses as they are generated.

        Args:
            query: The user's weather-related query.
            session_id: Unique identifier for the session.

        Yields:
            Dictionaries containing partial or final response data.
        """
        logger.info(f"Streaming query: '{query}' for session: '{session_id}'")
        config = {'configurable': {'thread_id': session_id}}
        langgraph_input = {'messages': [('user', query)]}

        try:
            async for chunk in self.agent_runnable.astream_events(langgraph_input, config, version='v1'):
                response = self._process_stream_chunk(chunk)
                if response:
                    yield response

            yield self._extract_response(config)
        except Exception as e:
            logger.error(f"Error during streaming: {e}", exc_info=True)
            yield self._format_error_response(f"Streaming error: {str(e)}")

    def _extract_response(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the final response from the agent's state.

        Args:
            config: Configuration dictionary with session details.

        Returns:
            A formatted response dictionary with status, input requirement, and content.
        """
        logger.debug(f"Extracting response for config: {config}")
        try:
            state = self.agent_runnable.get_state(config)
            state_values = getattr(state, 'values', None)
            if not state_values:
                logger.error("No state values found")
                return self._format_error_response("Agent state is unavailable")

            structured_response = (state_values.get('structured_response')
                                 if isinstance(state_values, dict)
                                 else getattr(state_values, 'structured_response', None))

            if structured_response and isinstance(structured_response, ResponseFormat):
                logger.info(f"Structured response: {structured_response}")
                return {
                    'is_task_complete': structured_response.status == 'completed',
                    'require_user_input': structured_response.status == 'input_required',
                    'content': structured_response.message,
                }

            return self._fallback_to_message_content(state_values)
        except Exception as e:
            logger.error(f"Error extracting state: {e}", exc_info=True)
            return self._format_error_response("Could not retrieve agent state")

    def _fallback_to_message_content(self, state_values: Any) -> Dict[str, Any]:
        """Fallback to extracting content from the last AI message if structured response is unavailable.

        Args:
            state_values: The agent's state values.

        Returns:
            A formatted response dictionary.
        """
        messages = (state_values.get('messages', [])
                   if isinstance(state_values, dict)
                   else getattr(state_values, 'messages', []))
        
        if messages and isinstance(messages[-1], AIMessage):
            content = messages[-1].content
            if isinstance(content, str) and content:
                logger.warning("Falling back to last AI message content")
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': content,
                }
            if isinstance(content, list):
                text_parts = [part['text'] for part in content
                             if isinstance(part, dict) and part.get('type') == 'text']
                if text_parts:
                    logger.warning("Falling back to concatenated text parts")
                    return {
                        'is_task_complete': True,
                        'require_user_input': False,
                        'content': '\n'.join(text_parts),
                    }

        logger.warning("No suitable response found in state")
        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': "Unable to process request due to unexpected response format. Please try again.",
        }

    def _process_stream_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any] | None:
        """Process a single stream chunk and return a response if applicable.

        Args:
            chunk: A chunk of streaming data from the agent.

        Returns:
            A response dictionary or None if no content should be yielded.
        """
        event_name = chunk.get('event')
        data = chunk.get('data', {})
        content = None

        if event_name == 'on_tool_start':
            content = f"Using tool: {data.get('name', 'a tool')}..."
        elif event_name == 'on_chat_model_stream':
            message_chunk = data.get('chunk')
            if isinstance(message_chunk, AIMessageChunk) and message_chunk.content:
                content = message_chunk.content

        return {
            'is_task_complete': False,
            'require_user_input': False,
            'content': content,
        } if content else None

    def _format_error_response(self, message: str) -> Dict[str, Any]:
        """Format an error response.

        Args:
            message: The error message to include.

        Returns:
            A formatted error response dictionary.
        """
        return {
            'is_task_complete': True,
            'require_user_input': False,
            'content': message,
        }