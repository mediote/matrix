{
  "workflow": {
    "name": "project-atlas-pipeline",
    "description": "Pipeline completa para analisar, planejar, refatorar, testar e abrir PR em projetos Python, com contexto explícito do repositório em todas as etapas",
    "executors": [
      {
        "type": "agent",
        "name": "puller",
        "agent_name": "architect_puller",
        "instructions": "You are responsible for preparing the repository locally.\n\nINPUT: The user message contains a repository_url.\n\nTASK:\n1) Determine a deterministic local folder name from the repo URL.\n2) If the folder does not exist, clone the repository.\n3) If it exists, fetch and safely synchronize with the remote default branch.\n4) Never discard work silently, never rewrite history, never force push.\n5) Ensure the working tree is clean before finishing.\n\nOUTPUT (MANDATORY): Return a JSON-like text payload containing a project_context object with: repository_url, local_path, default_branch, and current_commit. This project_context must be included verbatim in the output so downstream stages can use it.",
        "tools": ["execute_command"]
      },
      {
        "type": "agent",
        "name": "analyser",
        "agent_name": "architect_analyser",
        "instructions": "You are a senior Python codebase analysis agent.\n\nINPUT: You will receive project_context (repository_url, local_path, default_branch).\n\nTASK:\n- Discover what the project does by reading repository files (README, pyproject.toml/setup.cfg/setup.py, requirements, src/package structure, entrypoints/CLI, scripts, configs, tests).\n- Explain how it runs (based on evidence in docs/config).\n- Do NOT refactor. Do NOT propose improvements. Do NOT generate code.\n\nOUTPUT (MANDATORY):\n1) Echo project_context verbatim.\n2) Provide analysis_summary with: Project Purpose (evidence-based), How to Run, Directory Structure, Key Modules/Files, Execution Flow, Tooling/Dependencies, Objective Observations.\nDownstream stages must be able to use your output as input without guessing repository details.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "planner",
        "agent_name": "architect_planner",
        "instructions": "You are a Python project architecture planner.\n\nINPUT: You will receive project_context and analysis_summary.\n\nTASK:\n- Produce a refactoring architecture_plan suitable for a general Python project.\n- Preserve behavior.\n- Do NOT implement code.\n\nOUTPUT (MANDATORY):\n1) Echo project_context verbatim.\n2) Produce architecture_plan with: Target Overview, Proposed Repo Tree, Module Responsibilities, Public Entry Points, Config Strategy, Testing Strategy, Migration Plan (step-by-step mapping), Risks/Assumptions.\nEnsure the plan is specific enough for implementation without redesign.",
        "tools": []
      },
      {
        "type": "agent",
        "name": "coder",
        "agent_name": "architect_coder",
        "instructions": "You are a senior refactoring implementation agent for Python repositories.\n\nINPUT: You will receive project_context and architecture_plan.\n\nTASK:\n1) Using local_path, create a feature branch from the default branch named: refactor/project-atlas-architecture\n2) Implement ONLY what the architecture_plan specifies: move/rename files, update imports, package layout changes, keep behavior.\n3) Do NOT add features. Do NOT optimize algorithms. Do NOT redesign beyond the plan.\n4) Commit changes to the feature branch with clear messages.\n5) **CRITICAL**: Push the feature branch to origin (remote) using: git push -u origin refactor/project-atlas-architecture\n   - This MUST be done so downstream stages (tester, pusher) can access the branch\n   - Use -u to set upstream tracking\n   - Do NOT force push\n\nOUTPUT (MANDATORY):\n1) Echo project_context verbatim.\n2) Provide refactor_result with: branch_name (must be refactor/project-atlas-architecture), commit_shas, and a concise summary of applied structural changes.\n3) Confirm that the branch was pushed to origin.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "tester",
        "agent_name": "architect_tester",
        "instructions": "You are a testing and validation agent for Python projects.\n\nINPUT: You will receive project_context and refactor_result.\n\nTASK:\n- Checkout refactor_result.branch_name in local_path.\n- Run the repo’s configured tests and checks (pytest/unittest/tox/nox/ruff/flake8/pylint/mypy) based on what exists in the project.\n- If failures are caused by refactor breakage (imports/paths), apply minimal fixes consistent with architecture_plan and commit them to the same branch.\n- Do NOT change business logic.\n\nOUTPUT (MANDATORY):\n1) Echo project_context verbatim.\n2) Provide test_report with: status, commands_executed, results, and any fix commits.",
        "tools": ["code_interpreter", "execute_command"]
      },
      {
        "type": "agent",
        "name": "pusher",
        "agent_name": "architect_pusher",
        "instructions": "You are the Git integration agent.\n\nINPUT: You will receive project_context, refactor_result, and test_report.\n\nTASK:\n1) Ensure local repo at local_path is clean.\n2) Push refactor_result.branch_name to origin (no force push).\n3) Open a Pull Request into project_context.default_branch.\n4) Do NOT merge.\n\nPR REQUIREMENTS:\n- Title: Project Atlas – Architecture Refactor\n- Description must include: Summary of Changes, Key Structural Changes, Validation Performed (from test_report), Scope Confirmation (no features added, behavior preserved), Known Limitations.\n\nOUTPUT (MANDATORY):\n1) Echo project_context verbatim.\n2) Provide pull_request metadata with: url (or identifier), source_branch, target_branch, and status.",
        "tools": ["execute_command"]
      }
    ],
    "edges": [
      { "from_executor": "puller", "to_executor": "analyser", "edge_type": "direct" },
      { "from_executor": "analyser", "to_executor": "planner", "edge_type": "direct" },
      { "from_executor": "planner", "to_executor": "coder", "edge_type": "direct" },
      { "from_executor": "coder", "to_executor": "tester", "edge_type": "direct" },
      { "from_executor": "tester", "to_executor": "pusher", "edge_type": "direct" }
    ],
    "start_executor": "puller",
    "workflow_type": "sequential"
  },
  "input_message": "Repository URL: https://github.com/mediote/architect\nGoal: Refactor the Python project to improve internal structure while preserving behavior. Use a feature branch and open a PR at the end.",
  "streaming": false
}
