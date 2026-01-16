"""CLI execution tool for the agent."""

import os
import re
import subprocess
from typing import Annotated

from pydantic import Field


def _inject_github_token(command: str) -> str:
    """Inject GitHub token into git commands that need authentication."""
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        return command

    # For git push - configure remote URL with token
    if "git push" in command:
        # First, get current remote URL and update it
        return f"""
        REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "");
        if [[ "$REMOTE_URL" == *"github.com"* ]] && [[ "$REMOTE_URL" != *"{github_token}"* ]]; then
            NEW_URL=$(echo "$REMOTE_URL" | sed "s|https://github.com|https://{github_token}@github.com|g" | sed "s|https://[^@]*@github.com|https://{github_token}@github.com|g");
            git remote set-url origin "$NEW_URL" 2>/dev/null;
        fi;
        {command}
        """

    # For git clone - inject token in URL
    if "git clone" in command and "github.com" in command:
        # Replace https://github.com with https://TOKEN@github.com
        command = re.sub(
            r"https://github\.com", f"https://{github_token}@github.com", command
        )
        return command

    return command


def execute_command(
    command: Annotated[
        str,
        Field(
            description="Command to execute (e.g., 'ls -la', 'git clone ...', 'rm -rf ...')"
        ),
    ],
    working_directory: Annotated[
        str,
        Field(
            description="Working directory to execute the command in (default: current directory)"
        ),
    ] = ".",
) -> str:
    """
    Execute a shell command and return the output.

    Automatically handles GitHub authentication for git commands.
    This tool can execute any CLI command including:
    - File operations: ls, rm, mkdir, cat, echo, etc.
    - Git operations: git clone, git add, git commit, git push, etc.
    - Any other shell command

    Returns the stdout output or error message.
    """
    try:
        # Inject GitHub token for git commands
        command = _inject_github_token(command)

        result = subprocess.run(
            command,
            shell=True,
            cwd=working_directory,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
            check=False,  # Don't raise on non-zero exit
        )

        output = result.stdout.strip() if result.stdout else ""
        error = result.stderr.strip() if result.stderr else ""

        if result.returncode != 0:
            return f"Command failed (exit code {result.returncode}):\n{error}\n{output}"

        return output if output else "Command executed successfully"

    except subprocess.TimeoutExpired:
        return "Command timed out after 5 minutes"
    except Exception as e:
        return f"Error executing command: {str(e)}"
