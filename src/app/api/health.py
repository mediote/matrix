from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get(
    "/health",
    summary="Verificação de Saúde do Serviço",
    description="""
    Retorna o status operacional da API. Útil para monitoramento e probes de readiness.
    """,
)
def health():
    """
    Health check endpoint to verify that the API is running.

    Returns:
        JSONResponse: Response with status.
    """
    return JSONResponse(status_code=200, content={"status": "UP"})
