import logging

from agent_framework.exceptions import ServiceResponseException
from fastapi import APIRouter, HTTPException
from openai import RateLimitError

from src.models import MessageRequest, MessageResponse
from src.services import AgentService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/agent",
    response_model=MessageResponse,
    summary="Custom Agent",
    description="""
    Este endpoint interage com o Custom Agent para processar mensagens e executar tarefas.
    
    O agent possui acesso a ferramentas para executar comandos CLI e código Python,
    permitindo operações como manipulação de arquivos, git, análise de dados, etc.
    """,
)
async def agent_endpoint(request: MessageRequest) -> MessageResponse:
    logger.info("Starting request processing for /custom-architect endpoint.")

    if not request.message:
        logger.warning("Request missing 'message' field")
        raise HTTPException(status_code=400, detail="Missing 'message' field")

    try:
        service = AgentService()
        logger.info("AgentService instance created.")

        response_text, trace_id = await service.run(
            message=request.message,
            name=request.name,
            instructions=request.instructions,
            agent_id=request.id,
        )
        logger.info("Agent executed successfully. Trace ID: %s", trace_id)

        return MessageResponse(response=response_text, trace_id=trace_id)

    except (RateLimitError, ServiceResponseException) as e:
        error_msg = str(e)
        if "429" in error_msg or "RateLimitError" in error_msg or "Too Many Requests" in error_msg:
            logger.warning("Rate limit exceeded: %s", error_msg)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again in a few moments.",
            )
        logger.exception("Service response error.")
        raise HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable: {str(e)}",
        )
    except Exception as e:
        logger.exception("Agent processing failed.")
        raise HTTPException(
            status_code=500, detail=f"Agent processing failed: {str(e)}"
        )
