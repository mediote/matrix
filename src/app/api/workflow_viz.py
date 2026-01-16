"""Route for workflow visualization."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.models.schemas import WorkflowDefinition
from src.tools.workflow_viz import workflow_to_mermaid

router = APIRouter()
logger = logging.getLogger(__name__)


class WorkflowVizRequest(BaseModel):
    """Request for workflow visualization."""

    workflow: WorkflowDefinition


class WorkflowVizResponse(BaseModel):
    """Response with Mermaid diagram."""

    mermaid_diagram: str
    html_preview: str


@router.post(
    "/workflow/viz",
    response_model=WorkflowVizResponse,
    summary="Visualize Workflow",
    description="""
    Gera uma visualização Mermaid do workflow fornecido.
    
    O diagrama pode ser visualizado em:
    - VS Code com extensão Mermaid Preview
    - GitHub/GitLab (renderiza automaticamente)
    - Mermaid Live Editor: https://mermaid.live
    - Qualquer ferramenta que suporte Mermaid
    """,
)
async def visualize_workflow(request: WorkflowVizRequest) -> WorkflowVizResponse:
    """Generate Mermaid diagram from workflow definition."""
    try:
        mermaid_diagram = workflow_to_mermaid(request.workflow)
        
        # Generate HTML preview
        workflow_name = request.workflow.name.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
        workflow_desc = (
            request.workflow.description.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;')
            if request.workflow.description
            else ""
        )
        
        html_preview = f"""<!DOCTYPE html>
<html>
<head>
    <title>Workflow: {workflow_name}</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
    </script>
</head>
<body>
    <h1>{workflow_name}</h1>
    {f'<p>{workflow_desc}</p>' if workflow_desc else ''}
    <div class="mermaid">
{mermaid_diagram}
    </div>
</body>
</html>"""
        
        return WorkflowVizResponse(
            mermaid_diagram=mermaid_diagram,
            html_preview=html_preview.strip()
        )
    except Exception as e:
        logger.exception(f"Error generating workflow visualization: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate visualization: {str(e)}"
        )
