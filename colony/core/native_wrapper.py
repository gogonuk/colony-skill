"""
Native Team Wrapper for Colony.

Integrates with Claude Code's native teams API.
Provides context injection and team state management.
"""

from pathlib import Path
from typing import List, Dict, Optional, Any
import json
from datetime import datetime


class NativeTeamWrapper:
    """
    Wrapper for native Claude Code teams.

    This class doesn't create teams directly (that's done via the Task tool),
    but it provides utilities for:
    - Building Colony context for teams
    - Reading team state and configurations
    - Formatting team prompts with injected context
    """

    # Default team types with their configurations
    TEAM_TEMPLATES = {
        "code-review": {
            "name": "Code Review Team",
            "description": "Reviews code for security, style, and test coverage",
            "default_agents": ["code-reviewer", "security-analyst", "test-coverage"],
            "context_template": """
You are a code review team with access to Colony's pattern library.

RELEVANT PATTERNS:
{patterns}

RELEVANT MEMORY:
{memory}

Focus on:
1. Security vulnerabilities
2. Code style and consistency
3. Test coverage gaps
4. Performance considerations
5. Documentation completeness
"""
        },
        "security": {
            "name": "Security Audit Team",
            "description": "Performs comprehensive security audits",
            "default_agents": ["security-analyst", "penetration-tester", "auditor"],
            "context_template": """
You are a security audit team with access to Colony's pattern library.

RELEVANT PATTERNS:
{patterns}

RELEVANT MEMORY:
{memory}

Focus on:
1. OWASP Top 10 vulnerabilities
2. Input validation issues
3. Authentication/authorization flaws
4. Dependency vulnerabilities
5. Security best practices
"""
        },
        "refactor": {
            "name": "Refactoring Team",
            "description": "Plans and executes code refactoring",
            "default_agents": ["architect", "code-reviewer", "developer"],
            "context_template": """
You are a refactoring team with access to Colony's pattern library.

RELEVANT PATTERNS:
{patterns}

RELEVANT MEMORY:
{memory}

Focus on:
1. Code duplication reduction
2. Improving maintainability
3. Design pattern application
4. API consistency
5. Breaking changes minimization
"""
        }
    }

    def __init__(self, teams_path: Optional[Path] = None, tasks_path: Optional[Path] = None):
        """
        Initialize the native team wrapper.

        Args:
            teams_path: Path to Claude Code teams directory
            tasks_path: Path to Claude Code tasks directory
        """
        self.teams_path = teams_path or Path.home() / ".claude" / "teams"
        self.tasks_path = tasks_path or Path.home() / ".claude" / "tasks"

    def get_team_types(self) -> List[str]:
        """
        Get available team type templates.

        Returns:
            List of team type names
        """
        return list(self.TEAM_TEMPLATES.keys())

    def get_team_template(self, team_type: str) -> Optional[Dict]:
        """
        Get configuration template for a team type.

        Args:
            team_type: Type of team (code-review, security, refactor)

        Returns:
            Template dict or None if not found
        """
        return self.TEAM_TEMPLATES.get(team_type)

    def build_team_prompt(
        self,
        task: str,
        team_type: str,
        patterns: Optional[List[Dict]] = None,
        memory_chunks: Optional[List[Dict]] = None
    ) -> str:
        """
        Build a team creation prompt with Colony context injected.

        Args:
            task: The task description for the team
            team_type: Type of team to create
            patterns: List of relevant patterns from pattern library
            memory_chunks: List of relevant memory chunks

        Returns:
            Formatted prompt string for team creation
        """
        template = self.TEAM_TEMPLATES.get(team_type)
        if not template:
            template = {
                "context_template": """
RELEVANT PATTERNS:
{patterns}

RELEVANT MEMORY:
{memory}

Complete the task efficiently.
"""
            }

        # Format patterns section
        patterns_text = ""
        if patterns:
            for i, pattern in enumerate(patterns[:3], 1):
                patterns_text += f"\n{i}. {pattern.get('name', 'Unnamed')}\n"
                approach = pattern.get('approach', {})
                steps = approach.get('steps', [])
                if steps:
                    patterns_text += f"   Steps: {steps[0]}\n"
                lessons = pattern.get('lessons_learned', [])
                if lessons:
                    patterns_text += f"   Key lesson: {lessons[0]}\n"
        else:
            patterns_text = "No relevant patterns found."

        # Format memory section
        memory_text = ""
        if memory_chunks:
            for i, chunk in enumerate(memory_chunks[:2], 1):
                metadata = chunk.get('metadata', {})
                memory_text += f"\n{i}. {metadata.get('summary', 'No summary')}\n"
                keywords = metadata.get('keywords', [])
                if keywords:
                    memory_text += f"   Keywords: {', '.join(keywords[:5])}\n"
        else:
            memory_text = "No relevant memory found."

        # Build the final prompt
        context = template["context_template"].format(
            patterns=patterns_text,
            memory=memory_text
        )

        prompt = f"""Create a {team_type} team for: {task}

{context}

Use the native TeamCreate API to coordinate the team.
Track task completions for reputation scoring.
"""

        return prompt

    def get_team_status(self, team_name: str) -> Dict[str, Any]:
        """
        Get current status of a team.

        Args:
            team_name: Name/ID of the team

        Returns:
            Team status dict with keys: exists, config, state, etc.
        """
        result = {
            "exists": False,
            "team_name": team_name,
            "config": {},
            "state": "unknown"
        }

        config_file = self.teams_path / team_name / "config.json"
        if config_file.exists():
            result["exists"] = True
            try:
                result["config"] = json.loads(config_file.read_text())
                result["state"] = result["config"].get("state", "unknown")
            except (json.JSONDecodeError, IOError):
                pass

        return result

    def get_all_teams(self) -> List[Dict[str, Any]]:
        """
        Get status of all teams.

        Returns:
            List of team status dicts
        """
        teams = []

        if not self.teams_path.exists():
            return teams

        for team_dir in self.teams_path.iterdir():
            if not team_dir.is_dir():
                continue

            team_name = team_dir.name
            status = self.get_team_status(team_name)
            if status["exists"]:
                teams.append(status)

        return teams

    def get_team_tasks(self, team_name: str) -> List[Dict]:
        """
        Get tasks associated with a team.

        Args:
            team_name: Name of the team

        Returns:
            List of task dicts
        """
        tasks_file = self.tasks_path / team_name / "tasks.json"
        if tasks_file.exists():
            try:
                data = json.loads(tasks_file.read_text())
                return data.get("tasks", [])
            except (json.JSONDecodeError, IOError):
                pass
        return []

    def format_team_summary(self, team_status: Dict) -> str:
        """
        Format a human-readable team summary.

        Args:
            team_status: Team status dict from get_team_status()

        Returns:
            Formatted summary string
        """
        if not team_status["exists"]:
            return f"Team '{team_status['team_name']}' does not exist."

        config = team_status["config"]
        lines = [
            f"Team: {team_status['team_name']}",
            f"State: {team_status['state']}",
        ]

        if "description" in config:
            lines.append(f"Description: {config['description']}")

        if "agents" in config:
            agents = config["agents"]
            if isinstance(agents, list):
                lines.append(f"Agents: {', '.join(str(a) for a in agents)}")

        if "created_at" in config:
            lines.append(f"Created: {config['created_at']}")

        return "\n".join(lines)

    def create_custom_template(
        self,
        name: str,
        description: str,
        context_template: str,
        default_agents: Optional[List[str]] = None
    ) -> Dict:
        """
        Create a custom team type template.

        Args:
            name: Name of the team type
            description: Description of what the team does
            context_template: Context template string (use {patterns} and {memory} placeholders)
            default_agents: List of default agent types

        Returns:
            Created template dict
        """
        template = {
            "name": name,
            "description": description,
            "context_template": context_template,
            "default_agents": default_agents or []
        }

        # Store in a custom templates file
        custom_templates_file = self.teams_path / ".custom_templates.json"
        custom_templates = {}
        if custom_templates_file.exists():
            try:
                custom_templates = json.loads(custom_templates_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass

        custom_templates[name] = template
        custom_templates_file.write_text(json.dumps(custom_templates, indent=2))

        return template

    def get_available_templates(self) -> Dict[str, Dict]:
        """
        Get all available team templates (built-in + custom).

        Returns:
            Dict mapping template names to template configs
        """
        templates = dict(self.TEAM_TEMPLATES)

        # Load custom templates
        custom_templates_file = self.teams_path / ".custom_templates.json"
        if custom_templates_file.exists():
            try:
                custom_templates = json.loads(custom_templates_file.read_text())
                templates.update(custom_templates)
            except (json.JSONDecodeError, IOError):
                pass

        return templates


# CLI helper for testing
def main():
    """Simple CLI for testing native team wrapper."""
    import argparse

    parser = argparse.ArgumentParser(description="Colony Native Team Wrapper")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List teams command
    subparsers.add_parser("list-teams", help="List all native teams")

    # Get team status command
    status_parser = subparsers.add_parser("status", help="Get team status")
    status_parser.add_argument("--team", required=True, help="Team name")

    # Build prompt command
    prompt_parser = subparsers.add_parser("build-prompt", help="Build team prompt with context")
    prompt_parser.add_argument("--task", required=True, help="Task description")
    prompt_parser.add_argument("--type", default="code-review", help="Team type")

    args = parser.parse_args()

    wrapper = NativeTeamWrapper()

    if args.command == "list-teams":
        teams = wrapper.get_all_teams()
        print(f"\n📋 Found {len(teams)} teams:\n")
        for team in teams:
            print(f"  {wrapper.format_team_summary(team)}\n")

    elif args.command == "status":
        status = wrapper.get_team_status(args.team)
        print(f"\n{wrapper.format_team_summary(status)}\n")

    elif args.command == "build-prompt":
        prompt = wrapper.build_team_prompt(args.task, args.type)
        print(f"\n{prompt}\n")


if __name__ == "__main__":
    main()
