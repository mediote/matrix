"""Workflow orchestration routes."""

import logging

from agent_framework.exceptions import ServiceResponseException
from fastapi import APIRouter, HTTPException
from openai import RateLimitError

from src.models.schemas import WorkflowRequest, WorkflowResponse
from src.services.workflow_service import DynamicWorkflowService
from src.utils.rate_limiter import record_rate_limit_error

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post(
    "/workflow",
    response_model=WorkflowResponse,
    summary="Execute Dynamic Workflow",
    description="""
    Este endpoint permite criar e executar workflows dinâmicos usando o Microsoft Agent Framework.
    
    Você pode definir workflows com múltiplos executores (agentes ou funções) conectados por edges,
    suportando diferentes padrões de execução:
    - **Sequencial**: Executores executam em sequência
    - **Paralelo**: Múltiplos executores executam simultaneamente (fan-out/fan-in)
    - **Condicional**: Roteamento baseado em condições
    - **Dinâmico**: Workflows que se adaptam baseado no contexto
    
    **Tipos de Executores:**
    - `agent`: Agentes de IA com acesso a ferramentas
    - `function`: Funções customizadas (ex: execute_command)
    
    **Tipos de Edges:**
    - `direct`: Conexão direta entre executores
    - `conditional`: Roteamento condicional baseado em condições
    - `fan_out`: Distribui mensagens para múltiplos executores
    - `fan_in`: Combina resultados de múltiplos executores
    """,
)
async def execute_workflow(request: WorkflowRequest) -> WorkflowResponse:
    """
    Execute a dynamic workflow.

    Example workflow definition:
    ```json
    {
      "workflow": {
        "name": "data-processing",
        "description": "Process data through multiple agents",
        "executors": [
          {
            "type": "agent",
            "name": "analyzer",
            "agent_name": "data-analyzer",
            "instructions": "Analyze the input data",
            "tools": ["code_interpreter"]
          },
          {
            "type": "agent",
            "name": "formatter",
            "agent_name": "data-formatter",
            "instructions": "Format the analyzed data"
          }
        ],
        "edges": [
          {
            "from_executor": "analyzer",
            "to_executor": "formatter",
            "edge_type": "direct"
          }
        ],
        "start_executor": "analyzer",
        "workflow_type": "sequential"
      },
      "input_message": "Analyze this data: [1, 2, 3, 4, 5]",
      "streaming": false
    }
    ```
    """
    logger.info(f"Starting workflow execution: {request.workflow.name}")

    if not request.workflow.executors:
        logger.warning("Workflow has no executors")
        raise HTTPException(
            status_code=400, detail="Workflow must have at least one executor"
        )

    if not request.workflow.start_executor:
        logger.warning("Workflow has no start executor")
        raise HTTPException(
            status_code=400, detail="Workflow must specify a start executor"
        )

    # Validate start executor exists
    executor_names = [e.name for e in request.workflow.executors]
    if request.workflow.start_executor not in executor_names:
        raise HTTPException(
            status_code=400,
            detail=f"Start executor '{request.workflow.start_executor}' not found in executors",
        )

    try:
        service = DynamicWorkflowService()
        logger.info("DynamicWorkflowService instance created")

        output, trace_id, execution_steps = await service.build_and_execute_workflow(
            workflow_def=request.workflow,
            input_message=request.input_message,
            streaming=request.streaming,
        )

        logger.info(
            f"Workflow '{request.workflow.name}' executed successfully. "
            f"Trace ID: {trace_id}"
        )

        return WorkflowResponse(
            output=output,
            trace_id=trace_id,
            execution_steps=execution_steps,
            workflow_id=request.workflow.name,
        )

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except (RateLimitError, ServiceResponseException) as e:
        error_msg = str(e)
        if "429" in error_msg or "RateLimitError" in error_msg or "Too Many Requests" in error_msg:
            record_rate_limit_error()  # Record for adaptive rate limiting
            logger.warning("Rate limit exceeded: %s", error_msg)
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again in a few moments.",
            )
        logger.exception("Service response error")
        raise HTTPException(
            status_code=503,
            detail=f"Service temporarily unavailable: {str(e)}",
        )
    except Exception as e:
        logger.exception(f"Workflow execution failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Workflow execution failed: {str(e)}"
        )
