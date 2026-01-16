"""Workflow orchestration service for dynamic workflow execution."""

import json
import logging
from typing import Any, Dict, List, Optional

from agent_framework import Executor, WorkflowBuilder, WorkflowContext, handler
from agent_framework.azure import AzureOpenAIResponsesClient
from agent_framework.observability import get_tracer
from azure.identity import AzureCliCredential
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.span import format_trace_id
from typing_extensions import Never

from src.config import (
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_ENDPOINT,
)
from src.models.schemas import (
    AgentExecutorConfig,
    FunctionExecutorConfig,
    WorkflowDefinition,
)
from src.services.agent_service import AVAILABLE_TOOLS
from src.tools import execute_command
from src.utils.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


def _instrument_agent_output(
    result: Any,
    agent_name: str,
    tracer: Any,
    parent_span: Any,
) -> None:
    """
    Instrument agent output messages with granular spans for better visualization.

    Creates spans for:
    - Message parsing
    - Tool calls identification
    - Response content analysis

    Args:
        result: Agent run result object
        agent_name: Name of the agent
        tracer: OpenTelemetry tracer
        parent_span: Parent span context
    """
    try:
        # Try to extract messages from result
        messages = None
        tool_calls = []
        response_text = None

        # Check if result has messages attribute
        if hasattr(result, "messages"):
            messages = result.messages
        elif hasattr(result, "text"):
            response_text = result.text

        # Create span for message parsing
        with tracer.start_as_current_span(
            "gen_ai.message.parse",
            kind=SpanKind.INTERNAL,
            attributes={
                "gen_ai.agent.name": agent_name,
                "gen_ai.operation.name": "parse_messages",
            },
        ) as parse_span:
            if messages:
                try:
                    # Parse messages if it's a string
                    if isinstance(messages, str):
                        messages = json.loads(messages)

                    # Extract tool calls from messages
                    for msg in messages if isinstance(messages, list) else [messages]:
                        if isinstance(msg, dict):
                            # Check for tool calls in message
                            if "parts" in msg:
                                for part in msg.get("parts", []):
                                    if isinstance(part, dict):
                                        # Tool call part
                                        if part.get("type") == "tool_call":
                                            tool_call_id = part.get("id", "unknown")
                                            tool_name = part.get("name", "unknown")
                                            tool_args = part.get("arguments", {})

                                            tool_calls.append(
                                                {
                                                    "id": tool_call_id,
                                                    "name": tool_name,
                                                    "arguments": tool_args,
                                                }
                                            )

                                            # Create dedicated span for each tool call
                                            with tracer.start_as_current_span(
                                                f"gen_ai.tool_call.{tool_name}",
                                                kind=SpanKind.INTERNAL,
                                                attributes={
                                                    "gen_ai.agent.name": agent_name,
                                                    "gen_ai.tool_call.id": tool_call_id,
                                                    "gen_ai.tool_call.name": tool_name,
                                                    "gen_ai.tool_call.arguments": (
                                                        json.dumps(tool_args)
                                                        if tool_args
                                                        else ""
                                                    ),
                                                },
                                            ) as tool_call_span:
                                                logger.info(
                                                    f"[TOOL CALL] Agent '{agent_name}' → "
                                                    f"Tool: {tool_name} | ID: {tool_call_id}"
                                                )

                                                # Log tool call details
                                                if tool_args:
                                                    logger.debug(
                                                        f"[TOOL CALL ARGS] {tool_name}: {json.dumps(tool_args, indent=2)}"
                                                    )

                                        # Text response part
                                        elif part.get("type") == "text":
                                            text_content = part.get("content", "")
                                            if text_content:
                                                response_text = text_content
                                                parse_span.set_attribute(
                                                    "gen_ai.response.text_length",
                                                    len(text_content),
                                                )
                                                logger.debug(
                                                    f"[AI RESPONSE] Agent '{agent_name}' text response: "
                                                    f"{len(text_content)} chars"
                                                )

                            # Direct text content
                            elif "content" in msg:
                                response_text = msg.get("content", "")

                    # Set attributes on parse span
                    parse_span.set_attribute(
                        "gen_ai.message.tool_calls_count",
                        len(tool_calls),
                    )
                    parse_span.set_attribute(
                        "gen_ai.message.has_text_response",
                        bool(response_text),
                    )

                    if tool_calls:
                        tool_names = [tc["name"] for tc in tool_calls]
                        parse_span.set_attribute(
                            "gen_ai.message.tool_names",
                            ",".join(tool_names),
                        )
                        logger.info(
                            f"[MESSAGE PARSE] Agent '{agent_name}' → "
                            f"Found {len(tool_calls)} tool call(s): {', '.join(tool_names)}"
                        )

                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    logger.warning(
                        f"[MESSAGE PARSE] Failed to parse messages for '{agent_name}': {e}"
                    )
                    parse_span.set_attribute("gen_ai.message.parse_error", str(e))

            # If we have response text, create a span for content analysis
            if response_text:
                with tracer.start_as_current_span(
                    "gen_ai.response.analyze",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        "gen_ai.agent.name": agent_name,
                        "gen_ai.response.length": len(response_text),
                        "gen_ai.response.has_json": "{" in response_text
                        and "}" in response_text,
                    },
                ) as analyze_span:
                    # Try to detect if response contains JSON
                    try:
                        # Check if response starts with JSON
                        if response_text.strip().startswith("{"):
                            json_data = json.loads(response_text)
                            analyze_span.set_attribute(
                                "gen_ai.response.is_valid_json",
                                True,
                            )
                            analyze_span.set_attribute(
                                "gen_ai.response.json_keys",
                                (
                                    ",".join(json_data.keys())
                                    if isinstance(json_data, dict)
                                    else ""
                                ),
                            )
                            logger.debug(
                                f"[RESPONSE ANALYZE] Agent '{agent_name}' → "
                                f"Valid JSON with keys: {list(json_data.keys()) if isinstance(json_data, dict) else 'N/A'}"
                            )
                    except json.JSONDecodeError:
                        analyze_span.set_attribute(
                            "gen_ai.response.is_valid_json", False
                        )
                        logger.debug(
                            f"[RESPONSE ANALYZE] Agent '{agent_name}' → "
                            f"Text response (not JSON): {len(response_text)} chars"
                        )

    except Exception as e:
        logger.warning(
            f"[INSTRUMENTATION] Failed to instrument agent output for '{agent_name}': {e}",
            exc_info=True,
        )


class DynamicWorkflowService:
    """Service for creating and executing dynamic workflows."""

    def __init__(self):
        """Initialize the workflow service."""
        self.endpoint = AZURE_OPENAI_ENDPOINT.rstrip("/")
        self.credential = AzureCliCredential()
        self.client = None
        self._agent_cache = {}
        self._workflow_cache = {}

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

    def _resolve_tools(self, tool_names: Optional[List[str]] = None):
        """
        Resolve tools by name.

        Args:
            tool_names: List of tool names to resolve. If None, returns all tools.

        Returns:
            List of tool functions
        """
        if tool_names is None:
            return list(AVAILABLE_TOOLS.values())

        tools = []
        for tool_name in tool_names:
            if tool_name in AVAILABLE_TOOLS:
                tools.append(AVAILABLE_TOOLS[tool_name])
            else:
                logger.warning(f"Tool '{tool_name}' not found, skipping")
        return tools

    def _create_agent_executor(self, config: AgentExecutorConfig) -> "AgentExecutor":
        """Create an agent executor from configuration."""
        # Use agent_name consistently - this will be used in spans
        agent_name = config.agent_name or config.name
        return AgentExecutor(
            name=config.name,
            agent_name=agent_name,
            agent_id=agent_name,  # Use agent_name as id for consistency in spans
            instructions=config.instructions or "You are a helpful assistant.",
            tools=self._resolve_tools(config.tools),
            client=self._get_client(),
        )

    def _create_function_executor(
        self, config: FunctionExecutorConfig
    ) -> "FunctionExecutor":
        """Create a function executor from configuration."""
        return FunctionExecutor(
            name=config.name,
            function_name=config.function_name,
            parameters=config.parameters or {},
        )

    def _evaluate_condition(self, condition: Dict[str, Any], message: Any) -> bool:
        """
        Evaluate a condition against a message.

        Args:
            condition: Condition configuration with 'field', 'operator', 'value'
            message: Message to evaluate

        Returns:
            True if condition is met, False otherwise
        """
        field = condition.get("field")
        operator = condition.get("operator")
        value = condition.get("value")

        # Get field value from message
        if isinstance(message, dict):
            field_value = message.get(field)
        elif hasattr(message, field):
            field_value = getattr(message, field)
        else:
            return False

        # Evaluate condition
        if operator == "equals":
            return field_value == value
        elif operator == "contains":
            return value in str(field_value)
        elif operator == "starts_with":
            return str(field_value).startswith(str(value))
        elif operator == "ends_with":
            return str(field_value).endswith(str(value))
        elif operator == "greater_than":
            return float(field_value) > float(value)
        elif operator == "less_than":
            return float(field_value) < float(value)
        else:
            logger.warning(f"Unknown operator: {operator}")
            return False

    async def build_and_execute_workflow(
        self,
        workflow_def: WorkflowDefinition,
        input_message: str,
        streaming: bool = False,
    ) -> tuple[str, str, List[Dict[str, Any]]]:
        """
        Build and execute a workflow from a definition.

        Args:
            workflow_def: Workflow definition
            input_message: Input message to start the workflow
            streaming: Whether to stream execution events

        Returns:
            Tuple of (output_text, trace_id, execution_steps)
        """
        tracer = get_tracer()
        with tracer.start_as_current_span(
            f"workflow.{workflow_def.name}",
            kind=SpanKind.SERVER,
            attributes={
                "workflow.name": workflow_def.name,
                "workflow.type": workflow_def.workflow_type,
                "workflow.executor_count": len(workflow_def.executors),
                "workflow.edge_count": len(workflow_def.edges),
                "workflow.start_executor": workflow_def.start_executor,
            },
        ) as workflow_span:
            trace_id = format_trace_id(workflow_span.get_span_context().trace_id)
            logger.info(
                f"[WORKFLOW START] '{workflow_def.name}' | Trace ID: {trace_id} | "
                f"Executors: {len(workflow_def.executors)} | Edges: {len(workflow_def.edges)}"
            )

            execution_steps = []

            try:
                # Create executors
                with tracer.start_as_current_span(
                    "workflow.build.executors",
                    kind=SpanKind.INTERNAL,
                    attributes={"workflow.name": workflow_def.name},
                ) as build_span:
                    executors_map = {}
                    for executor_config in workflow_def.executors:
                        with tracer.start_as_current_span(
                            f"workflow.executor.create.{executor_config.name}",
                            kind=SpanKind.INTERNAL,
                            attributes={
                                "executor.name": executor_config.name,
                                "executor.type": executor_config.type,
                            },
                        ) as executor_span:
                            logger.info(
                                f"[EXECUTOR CREATE] '{executor_config.name}' "
                                f"(type: {executor_config.type})"
                            )

                            if isinstance(executor_config, AgentExecutorConfig):
                                executor = self._create_agent_executor(executor_config)
                                executor_span.set_attribute(
                                    "executor.agent_name",
                                    executor_config.agent_name or executor_config.name,
                                )
                                executor_span.set_attribute(
                                    "executor.tools_count",
                                    len(executor_config.tools or []),
                                )
                            elif isinstance(executor_config, FunctionExecutorConfig):
                                executor = self._create_function_executor(
                                    executor_config
                                )
                                executor_span.set_attribute(
                                    "executor.function_name",
                                    executor_config.function_name,
                                )
                            else:
                                logger.error(
                                    f"[EXECUTOR ERROR] Unknown executor type: {type(executor_config)}"
                                )
                                executor_span.set_status(
                                    Status(StatusCode.ERROR, "Unknown executor type")
                                )
                                continue

                            executors_map[executor_config.name] = executor
                            execution_steps.append(
                                {
                                    "step": "executor_created",
                                    "executor": executor_config.name,
                                    "type": executor_config.type,
                                }
                            )
                            logger.info(
                                f"[EXECUTOR CREATED] '{executor_config.name}' ✓"
                            )

                # Build workflow
                with tracer.start_as_current_span(
                    "workflow.build.graph",
                    kind=SpanKind.INTERNAL,
                    attributes={"workflow.name": workflow_def.name},
                ) as graph_span:
                    logger.info(f"[WORKFLOW BUILD] Building graph structure")
                    builder = WorkflowBuilder()

                    # Register executors with factory functions
                    executor_factories = {}
                    for executor_config in workflow_def.executors:
                        executor = executors_map.get(executor_config.name)
                        if executor:
                            executor_factories[executor_config.name] = (
                                lambda e=executor: e
                            )
                            builder.register_executor(
                                executor_factories[executor_config.name],
                                name=executor_config.name,
                            )
                            logger.debug(
                                f"[WORKFLOW BUILD] Registered executor: {executor_config.name}"
                            )

                    # Set start executor
                    if workflow_def.start_executor not in executors_map:
                        error_msg = (
                            f"Start executor '{workflow_def.start_executor}' not found"
                        )
                        logger.error(f"[WORKFLOW ERROR] {error_msg}")
                        graph_span.set_status(Status(StatusCode.ERROR, error_msg))
                        raise ValueError(error_msg)

                    builder.set_start_executor(workflow_def.start_executor)
                    logger.info(
                        f"[WORKFLOW BUILD] Start executor: {workflow_def.start_executor}"
                    )

                    # Add edges
                    edges_added = 0
                    for edge_config in workflow_def.edges:
                        if edge_config.from_executor not in executors_map:
                            logger.warning(
                                f"[WORKFLOW BUILD] Edge from '{edge_config.from_executor}' skipped - executor not found"
                            )
                            continue
                        if edge_config.to_executor not in executors_map:
                            logger.warning(
                                f"[WORKFLOW BUILD] Edge to '{edge_config.to_executor}' skipped - executor not found"
                            )
                            continue

                        if edge_config.edge_type == "direct":
                            builder.add_edge(
                                edge_config.from_executor, edge_config.to_executor
                            )
                        elif (
                            edge_config.edge_type == "conditional"
                            and edge_config.condition
                        ):
                            builder.add_edge(
                                edge_config.from_executor, edge_config.to_executor
                            )
                        else:
                            builder.add_edge(
                                edge_config.from_executor, edge_config.to_executor
                            )

                        edges_added += 1
                        logger.debug(
                            f"[WORKFLOW BUILD] Edge: {edge_config.from_executor} → {edge_config.to_executor} ({edge_config.edge_type})"
                        )
                        execution_steps.append(
                            {
                                "step": "edge_added",
                                "from": edge_config.from_executor,
                                "to": edge_config.to_executor,
                                "type": edge_config.edge_type,
                            }
                        )

                    graph_span.set_attribute("workflow.edges_added", edges_added)
                    logger.info(f"[WORKFLOW BUILD] Added {edges_added} edges")

                # Build workflow
                with tracer.start_as_current_span(
                    "workflow.build.finalize",
                    kind=SpanKind.INTERNAL,
                ) as finalize_span:
                    workflow = builder.build()
                    execution_steps.append(
                        {"step": "workflow_built", "status": "success"}
                    )
                    logger.info(f"[WORKFLOW BUILD] Workflow built successfully ✓")

                # Execute workflow
                with tracer.start_as_current_span(
                    "workflow.execute",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        "workflow.name": workflow_def.name,
                        "workflow.streaming": streaming,
                        "workflow.input_length": len(input_message),
                    },
                ) as execute_span:
                    logger.info(
                        f"[WORKFLOW EXECUTE] Starting execution | "
                        f"Input length: {len(input_message)} chars | Streaming: {streaming}"
                    )
                    execution_steps.append({"step": "workflow_execution_started"})

                    if streaming:
                        # Streaming execution
                        output_parts = []
                        event_count = 0
                        async for event in workflow.run_streaming(input_message):
                            event_count += 1
                            event_type = type(event).__name__
                            logger.debug(
                                f"[WORKFLOW EVENT] {event_type} (event #{event_count})"
                            )
                            execution_steps.append(
                                {
                                    "step": "workflow_event",
                                    "event_type": event_type,
                                    "event_number": event_count,
                                }
                            )
                            if hasattr(event, "text"):
                                output_parts.append(event.text)
                            elif hasattr(event, "get_outputs"):
                                outputs = event.get_outputs()
                                if outputs:
                                    output_parts.extend([str(o) for o in outputs])
                        output_text = " ".join(output_parts) if output_parts else ""
                        execute_span.set_attribute("workflow.events_count", event_count)
                    else:
                        # Non-streaming execution
                        logger.info(
                            f"[WORKFLOW EXECUTE] Running workflow (non-streaming)"
                        )
                        result = await workflow.run(input_message)
                        outputs = (
                            result.get_outputs()
                            if hasattr(result, "get_outputs")
                            else []
                        )
                        output_text = (
                            " ".join([str(o) for o in outputs])
                            if outputs
                            else str(result)
                        )

                    execute_span.set_attribute(
                        "workflow.output_length", len(output_text)
                    )
                    execution_steps.append(
                        {
                            "step": "workflow_execution_completed",
                            "status": "success",
                            "output_length": len(output_text),
                        }
                    )

                    logger.info(
                        f"[WORKFLOW SUCCESS] '{workflow_def.name}' completed | "
                        f"Output: {len(output_text)} chars | Trace ID: {trace_id}"
                    )
                    workflow_span.set_attribute("workflow.status", "success")
                    workflow_span.set_attribute(
                        "workflow.output_length", len(output_text)
                    )

                    return output_text, trace_id, execution_steps

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"[WORKFLOW ERROR] '{workflow_def.name}' failed: {error_msg} | "
                    f"Trace ID: {trace_id}",
                    exc_info=True,
                )
                workflow_span.set_status(Status(StatusCode.ERROR, error_msg))
                workflow_span.set_attribute("workflow.status", "error")
                workflow_span.set_attribute("workflow.error", error_msg)
                execution_steps.append(
                    {
                        "step": "workflow_execution_failed",
                        "error": error_msg,
                        "error_type": type(e).__name__,
                    }
                )
                raise


class AgentExecutor(Executor):
    """Executor that wraps an AI agent."""

    def __init__(
        self,
        name: str,
        agent_name: str,
        agent_id: str,
        instructions: str,
        tools: List,
        client: AzureOpenAIResponsesClient,
    ):
        """Initialize the agent executor."""
        super().__init__(id=name)
        self.agent_name = agent_name
        self.agent_id = agent_id
        self.instructions = instructions
        self.tools = tools
        self.client = client
        self._agent = None

    def _get_agent(self):
        """Get or create the agent."""
        if self._agent is None:
            # Use agent_name for both name and id to ensure consistency
            # The framework uses the 'name' parameter for gen_ai.agent.name attribute
            self._agent = self.client.create_agent(
                name=self.agent_name,
                instructions=self.instructions,
                id=self.agent_name,  # Use agent_name as id for consistency
                tools=self.tools,
            )
        return self._agent

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        """Handle incoming message and process with agent."""
        tracer = get_tracer()
        # Create executor span - this will be the parent for all operations
        with tracer.start_as_current_span(
            f"executor.agent.{self.agent_name}",
            kind=SpanKind.INTERNAL,
            attributes={
                "executor.name": self.agent_name,
                "executor.id": self.agent_id,
                "executor.type": "agent",
                "executor.input_length": len(message),
            },
        ) as executor_span:
            logger.info(
                f"[EXECUTOR START] Agent '{self.agent_name}' | "
                f"Input: {len(message)} chars"
            )

            try:
                agent = self._get_agent()

                # Apply rate limiting before API call
                # This span will be a child of executor_span (created in context)
                with tracer.start_as_current_span(
                    "rate_limit.wait",
                    kind=SpanKind.INTERNAL,
                    attributes={
                        "executor.name": self.agent_name,
                        "rate_limit.executor": self.agent_name,
                        "rate_limit.min_interval": get_rate_limiter().min_interval,
                    },
                ) as rate_limit_span:
                    rate_limiter = get_rate_limiter()
                    await rate_limiter.wait_if_needed()
                    logger.debug(f"[RATE LIMIT] '{self.agent_name}' ready to proceed")

                # Execute agent - the framework will automatically create
                # gen_ai.invoke_agent, chat, and execute_tool spans as children
                # These will be automatically nested under executor_span
                logger.info(f"[AGENT RUN] '{self.agent_name}' calling OpenAI API")
                result = await agent.run(message)
                response_text = (
                    result.text if hasattr(result, "text") else str(result) or "OK"
                )

                # Instrument agent output with granular spans for better visualization
                _instrument_agent_output(
                    result=result,
                    agent_name=self.agent_name,
                    tracer=tracer,
                    parent_span=executor_span,
                )

                logger.info(
                    f"[AGENT SUCCESS] '{self.agent_name}' | "
                    f"Response: {len(response_text)} chars"
                )

                executor_span.set_attribute(
                    "executor.output_length", len(response_text)
                )
                executor_span.set_attribute("executor.status", "success")
                await ctx.send_message(response_text)
                logger.info(f"[EXECUTOR SUCCESS] Agent '{self.agent_name}' ✓")

            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(
                    f"[EXECUTOR ERROR] Agent '{self.agent_name}' failed: {error_msg}",
                    exc_info=True,
                )
                executor_span.set_status(Status(StatusCode.ERROR, error_msg))
                executor_span.set_attribute("executor.status", "error")
                executor_span.set_attribute("executor.error", error_msg)
                executor_span.set_attribute("executor.error_type", error_type)

                # Re-raise to let workflow handle it
                raise


class FunctionExecutor(Executor):
    """Executor that executes a custom function."""

    def __init__(self, name: str, function_name: str, parameters: Dict[str, Any]):
        """Initialize the function executor."""
        super().__init__(id=name)
        self.function_name = function_name
        self.parameters = parameters

    @handler
    async def handle(self, message: str, ctx: WorkflowContext[str]) -> None:
        """Handle incoming message and execute function."""
        # Map of available functions
        available_functions = {
            "execute_command": execute_command,
            # Add more functions here as needed
        }

        if self.function_name not in available_functions:
            error_msg = f"Function '{self.function_name}' not found"
            logger.error(error_msg)
            await ctx.send_message(f"Error: {error_msg}")
            return

        try:
            func = available_functions[self.function_name]
            # Merge message content with parameters
            params = self.parameters.copy()
            params["input"] = message

            # Execute function
            if self.function_name == "execute_command":
                command = params.get("command", params.get("input", ""))
                result = func(
                    command=command,
                    working_directory=params.get("working_directory", "."),
                )
            else:
                result = func(**params)

            await ctx.send_message(str(result))
        except Exception as e:
            error_msg = f"Error executing function '{self.function_name}': {str(e)}"
            logger.exception(error_msg)
            await ctx.send_message(f"Error: {error_msg}")
