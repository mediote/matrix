"""Tool for visualizing workflows as Mermaid diagrams."""

from typing import Dict, List, Optional

from src.models.schemas import WorkflowDefinition


def workflow_to_mermaid(workflow_def: WorkflowDefinition) -> str:
    """
    Convert a workflow definition to a Mermaid diagram.

    Args:
        workflow_def: Workflow definition

    Returns:
        Mermaid diagram as string
    """
    mermaid_lines = ["graph TD"]
    
    # Add nodes with labels
    for executor in workflow_def.executors:
        node_id = executor.name.replace(" ", "_").replace("-", "_").replace(".", "_")
        node_label = executor.name
        
        # Add executor type to label
        if hasattr(executor, "type"):
            executor_type = executor.type
            if executor_type == "agent":
                node_label = f"🤖 {node_label}"
            elif executor_type == "function":
                node_label = f"⚙️ {node_label}"
        
        # Add tools info for agents
        if hasattr(executor, "tools") and executor.tools:
            tools_str = ", ".join(executor.tools[:3])  # Limit to 3 tools
            if len(executor.tools) > 3:
                tools_str += "..."
            node_label += f"<br/><small>{tools_str}</small>"
        
        # Escape quotes in label for Mermaid
        node_label_escaped = node_label.replace('"', '&quot;')
        mermaid_lines.append(f'    {node_id}["{node_label_escaped}"]')
    
    # Add edges
    for edge in workflow_def.edges:
        from_id = edge.from_executor.replace(" ", "_").replace("-", "_").replace(".", "_")
        to_id = edge.to_executor.replace(" ", "_").replace("-", "_").replace(".", "_")
        
        edge_style = "-->"
        if edge.edge_type == "conditional":
            edge_style = "-.->"
        elif edge.edge_type == "fan_out":
            edge_style = "==>"
        elif edge.edge_type == "fan_in":
            edge_style = "==>"
        
        # Add condition label if present
        label = ""
        if edge.condition:
            condition = edge.condition
            condition_str = f"{condition.field} {condition.operator} {condition.value}"
            condition_escaped = condition_str.replace('"', '&quot;')
            label = f'|"{condition_escaped}"|'
        
        mermaid_lines.append(f"    {from_id} {edge_style}{label} {to_id}")
    
    # Highlight start executor
    start_id = workflow_def.start_executor.replace(" ", "_").replace("-", "_").replace(".", "_")
    mermaid_lines.append(f"    style {start_id} fill:#90EE90,stroke:#333,stroke-width:3px")
    
    return "\n".join(mermaid_lines)


def workflow_to_mermaid_file(workflow_def: WorkflowDefinition, output_path: str) -> None:
    """
    Save workflow as Mermaid diagram to file.

    Args:
        workflow_def: Workflow definition
        output_path: Path to save the Mermaid file
    """
    mermaid_diagram = workflow_to_mermaid(workflow_def)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(mermaid_diagram)


def workflow_json_to_mermaid(workflow_json: Dict) -> str:
    """
    Convert workflow JSON to Mermaid diagram.

    Args:
        workflow_json: Workflow definition as dictionary

    Returns:
        Mermaid diagram as string
    """
    # Parse workflow from dict
    workflow_def = WorkflowDefinition(**workflow_json)
    return workflow_to_mermaid(workflow_def)
