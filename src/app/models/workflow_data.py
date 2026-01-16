"""Structured data models for workflow executors."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProjectContext(BaseModel):
    """Project context information."""

    repository_url: str = Field(..., description="Repository URL")
    local_path: str = Field(..., description="Local path to the repository")
    default_branch: str = Field(..., description="Default branch name")
    current_commit: str = Field(..., description="Current commit SHA")


class AnalysisSummary(BaseModel):
    """Codebase analysis summary."""

    project_purpose: str = Field(..., description="Project purpose based on evidence")
    how_to_run: str = Field(..., description="How to run the project")
    directory_structure: str = Field(..., description="Directory structure")
    key_modules: str = Field(..., description="Key modules and files")
    execution_flow: str = Field(..., description="Execution flow")
    tooling_dependencies: str = Field(..., description="Tooling and dependencies")
    observations: str = Field(..., description="Objective observations")


class ArchitecturePlan(BaseModel):
    """Architecture refactoring plan."""

    target_overview: str = Field(..., description="Target architecture overview")
    proposed_repo_tree: str = Field(..., description="Proposed repository tree")
    module_responsibilities: str = Field(..., description="Module responsibilities")
    public_entry_points: str = Field(..., description="Public entry points")
    config_strategy: str = Field(..., description="Configuration strategy")
    testing_strategy: str = Field(..., description="Testing strategy")
    migration_plan: str = Field(..., description="Step-by-step migration plan")
    risks_assumptions: str = Field(..., description="Risks and assumptions")


class RefactorResult(BaseModel):
    """Refactoring implementation result."""

    branch_name: str = Field(..., description="Feature branch name")
    commit_shas: List[str] = Field(..., description="List of commit SHAs")
    summary: str = Field(..., description="Summary of structural changes")
    pushed: bool = Field(default=False, description="Whether branch was pushed to remote")


class TestReport(BaseModel):
    """Test execution report."""

    status: str = Field(..., description="Test status (passed/failed/error)")
    commands_executed: List[str] = Field(..., description="Commands that were executed")
    results: str = Field(..., description="Test results output")
    fix_commits: Optional[List[str]] = Field(
        default=None, description="Commits made to fix issues"
    )


class PullRequestMetadata(BaseModel):
    """Pull request metadata."""

    url: Optional[str] = Field(default=None, description="PR URL or identifier")
    source_branch: str = Field(..., description="Source branch name")
    target_branch: str = Field(..., description="Target branch name")
    status: str = Field(..., description="PR status")


class WorkflowData(BaseModel):
    """Complete workflow data structure."""

    project_context: Optional[ProjectContext] = None
    analysis_summary: Optional[AnalysisSummary] = None
    architecture_plan: Optional[ArchitecturePlan] = None
    refactor_result: Optional[RefactorResult] = None
    test_report: Optional[TestReport] = None
    pull_request: Optional[PullRequestMetadata] = None
    raw_text: Optional[str] = Field(
        default=None, description="Raw text output for backward compatibility"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_text(cls, text: str) -> "WorkflowData":
        """Create from raw text (for backward compatibility)."""
        return cls(raw_text=text)
