"""Pydantic schemas for API requests and responses."""

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class MessageRequest(BaseModel):
    """Request schema for agent messages."""

    message: str = Field(..., description="The message to send to the agent")
    name: Optional[str] = Field(
        default="custom-agent", description="The name of the agent"
    )
    id: Optional[str] = Field(default="agent", description="The ID of the agent")
    instructions: Optional[str] = Field(
        default="You are a helpful assistant.",
        description="The instructions for the agent",
    )


class MessageResponse(BaseModel):
    """Response schema for agent messages."""

    response: str
    trace_id: Optional[str] = None


# Workflow Orchestration Schemas
class AgentExecutorConfig(BaseModel):
    """Configuration for an agent executor."""

    type: str = Field(default="agent", description="Executor type: 'agent'")
    name: str = Field(..., description="Name of the executor")
    agent_name: Optional[str] = Field(default=None, description="Name of the agent")
    agent_id: Optional[str] = Field(default=None, description="ID of the agent")
    instructions: Optional[str] = Field(
        default="You are a helpful assistant.",
        description="Instructions for the agent",
    )
    tools: Optional[List[str]] = Field(
        default=None, description="List of tool names to enable for this agent"
    )


class FunctionExecutorConfig(BaseModel):
    """Configuration for a function executor."""

    type: str = Field(default="function", description="Executor type: 'function'")
    name: str = Field(..., description="Name of the executor")
    function_name: str = Field(..., description="Name of the function to execute")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Parameters to pass to the function"
    )


class EdgeCondition(BaseModel):
    """Condition for conditional edge routing."""

    field: str = Field(..., description="Field to check in the message")
    operator: str = Field(
        ...,
        description="Comparison operator: 'equals', 'contains', 'starts_with', 'ends_with', 'greater_than', 'less_than'",
    )
    value: Any = Field(..., description="Value to compare against")


class EdgeConfig(BaseModel):
    """Configuration for an edge between executors."""

    from_executor: str = Field(..., description="Source executor name")
    to_executor: str = Field(..., description="Target executor name")
    condition: Optional[EdgeCondition] = Field(
        default=None, description="Optional condition for conditional routing"
    )
    edge_type: str = Field(
        default="direct",
        description="Edge type: 'direct', 'conditional', 'fan_out', 'fan_in'",
    )


class WorkflowDefinition(BaseModel):
    """Dynamic workflow definition."""

    name: str = Field(..., description="Name of the workflow")
    description: Optional[str] = Field(
        default=None, description="Description of the workflow"
    )
    executors: List[Union[AgentExecutorConfig, FunctionExecutorConfig]] = Field(
        ..., description="List of executors in the workflow"
    )
    edges: List[EdgeConfig] = Field(..., description="List of edges connecting executors")
    start_executor: str = Field(..., description="Name of the starting executor")
    workflow_type: str = Field(
        default="sequential",
        description="Workflow type: 'sequential', 'parallel', 'conditional', 'dynamic'",
    )


class WorkflowRequest(BaseModel):
    """Request to execute a workflow."""

    workflow: WorkflowDefinition = Field(..., description="Workflow definition")
    input_message: str = Field(..., description="Input message to start the workflow")
    streaming: bool = Field(
        default=False, description="Whether to stream workflow execution events"
    )


class WorkflowResponse(BaseModel):
    """Response from workflow execution."""

    output: str = Field(..., description="Final output from the workflow")
    trace_id: Optional[str] = None
    execution_steps: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Steps executed in the workflow"
    )
    workflow_id: Optional[str] = Field(
        default=None, description="ID of the executed workflow"
    )
