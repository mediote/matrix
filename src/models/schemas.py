"""Pydantic schemas for API requests and responses."""

from typing import Optional

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
