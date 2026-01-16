"""Agent service for handling agent operations."""

import logging
from typing import Optional

from agent_framework import HostedCodeInterpreterTool
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.observability import get_tracer
from azure.identity import AzureCliCredential
from opentelemetry.trace import SpanKind
from opentelemetry.trace.span import format_trace_id

from src.config import (
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_ENDPOINT,
)
from src.tools import execute_command
from src.utils.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

# Mapping of available tools
AVAILABLE_TOOLS = {
    "execute_command": execute_command,
    "code_interpreter": HostedCodeInterpreterTool(),
}


class AgentService:
    """Service for managing agent operations."""

    def __init__(self):
        """Initialize the agent service."""
        self.endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.credential = AzureCliCredential()
        self.client = None
        self._agent_cache = {}

    def _get_client(self) -> AzureOpenAIResponsesClient:
        """Get or create the Azure OpenAI client."""
        if self.client is None:
            self.client = AzureOpenAIResponsesClient(
                endpoint=self.endpoint,
                api_version=AZURE_OPENAI_API_VERSION,
                deployment_name=AZURE_OPENAI_DEPLOYMENT_NAME,
                credential=self.credential,
            )
        return self.client

    def _resolve_tools(self):
        """
        Return all registered tools.

        Returns:
            List of all available tool functions
        """
        return list(AVAILABLE_TOOLS.values())

    def _get_agent(
        self,
        name: str = "agent",
        instructions: str = "You are a helpful assistant.",
        agent_id: str = "agent",
    ):
        """
        Get or create an agent with the specified configuration.
        All registered tools are always available.

        Args:
            name: The name of the agent
            instructions: The instructions for the agent
            agent_id: The ID of the agent

        Returns:
            The agent instance
        """
        cache_key = (name, instructions, agent_id)

        if cache_key not in self._agent_cache:
            client = self._get_client()
            tools = self._resolve_tools()

            self._agent_cache[cache_key] = client.create_agent(
                name=name,
                instructions=instructions,
                id=agent_id,
                tools=tools,
            )
            logger.info(
                f"Created agent '{name}' (id: {agent_id}) with {len(tools)} tools"
            )

        return self._agent_cache[cache_key]

    async def run(
        self,
        message: str,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        agent_id: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Run the agent with a message and optional configuration.
        All registered tools are always available.

        Args:
            message: The message to send to the agent.
            name: The name of the agent (default: "agent")
            instructions: The instructions for the agent (default: "You are a helpful assistant.")
            agent_id: The ID of the agent (default: "agent")

        Returns:
            Tuple of (response_text, trace_id)
        """
        with get_tracer().start_as_current_span(
            "Chat Agent", kind=SpanKind.CLIENT
        ) as span:
            trace_id = format_trace_id(span.get_span_context().trace_id)
            logger.info(f"Trace ID: {trace_id}")

            agent = self._get_agent(
                name=name or "agent",
                instructions=instructions or "You are a helpful assistant.",
                agent_id=agent_id or "agent",
            )
            
            # Apply rate limiting before API call
            rate_limiter = get_rate_limiter()
            await rate_limiter.wait_if_needed()
            
            result = await agent.run(message)
            response_text = result.text or "OK"

            return response_text, trace_id
