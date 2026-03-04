"""
Command Parser for Colony skill.

Centralized command routing and argument parsing for all Colony commands.
This module provides the entry point for the skill invocation.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import json


class CommandParser:
    """
    Parse and route Colony commands.

    Supports commands documented in SKILL.md:
    - deploy: Create team with Colony context
    - reputation: View agent reputations
    - patterns: Manage pattern library
    - memory: Manage conversation memory
    - dashboard: Launch monitoring dashboard
    - status: Colony status
    """

    def __init__(self):
        """Initialize the command parser."""
        self.storage_path = Path.home() / ".colony"

    def parse(self, args: str) -> Tuple[str, Dict[str, Any]]:
        """
        Parse command arguments.

        Args:
            args: Raw argument string from skill invocation

        Returns:
            Tuple of (command_name, parsed_arguments)

        Raises:
            ValueError: If command syntax is invalid
        """
        if not args or args.strip() == "":
            return ("status", {})

        # Tokenize while respecting quoted strings
        tokens = self._tokenize(args)
        if not tokens:
            return ("status", {})

        command = tokens[0].lower()
        parsed = {}

        if command == "deploy":
            parsed = self._parse_deploy(tokens[1:])
        elif command == "reputation":
            parsed = self._parse_reputation(tokens[1:])
        elif command == "patterns":
            parsed = self._parse_patterns(tokens[1:])
        elif command == "memory":
            parsed = self._parse_memory(tokens[1:])
        elif command == "dashboard":
            parsed = self._parse_dashboard(tokens[1:])
        elif command == "status":
            parsed = self._parse_status(tokens[1:])
        else:
            raise ValueError(f"Unknown command: {command}")

        return (command, parsed)

    def _tokenize(self, args: str) -> List[str]:
        """
        Tokenize argument string, respecting quoted values.

        Examples:
            "deploy --team code-review --task 'Review code'" ->
            ["deploy", "--team", "code-review", "--task", "Review code"]
        """
        tokens = []
        current = ""
        in_quotes = False
        quote_char = None

        for char in args:
            if char in ('"', "'") and (not in_quotes or quote_char == char):
                in_quotes = not in_quotes
                quote_char = char if in_quotes else None
            elif char.isspace() and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return tokens

    def _parse_deploy(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parse deploy command.

        Syntax: deploy --team <type> --task "<description>" [options]
        Options: --target <path>, --patterns <category>
        """
        result = {
            "team_type": None,
            "task": None,
            "target": None,
            "patterns": None
        }

        i = 0
        while i < len(tokens):
            if tokens[i] == "--team" and i + 1 < len(tokens):
                result["team_type"] = tokens[i + 1]
                i += 2
            elif tokens[i] == "--task" and i + 1 < len(tokens):
                result["task"] = tokens[i + 1]
                i += 2
            elif tokens[i] == "--target" and i + 1 < len(tokens):
                result["target"] = tokens[i + 1]
                i += 2
            elif tokens[i] == "--patterns" and i + 1 < len(tokens):
                result["patterns"] = tokens[i + 1]
                i += 2
            else:
                i += 1

        # Validate required fields
        if not result["team_type"]:
            raise ValueError("deploy requires --team <type>")
        if not result["task"]:
            raise ValueError("deploy requires --task <description>")

        return result

    def _parse_reputation(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parse reputation command.

        Syntax: reputation [--agent <id>] [--top N]
        """
        result = {
            "agent_id": None,
            "top": None
        }

        i = 0
        while i < len(tokens):
            if tokens[i] == "--agent" and i + 1 < len(tokens):
                result["agent_id"] = tokens[i + 1]
                i += 2
            elif tokens[i] == "--top" and i + 1 < len(tokens):
                try:
                    result["top"] = int(tokens[i + 1])
                    i += 2
                except ValueError:
                    raise ValueError(f"--top requires a number, got '{tokens[i + 1]}'")
            else:
                i += 1

        return result

    def _parse_patterns(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parse patterns command.

        Syntax: patterns list [--category <cat>]
                patterns search <query>
                patterns create --name <name> --category <cat> --keywords <k1 k2...>
        """
        if not tokens:
            raise ValueError("patterns requires a subcommand: list, search, or create")

        subcommand = tokens[0].lower()
        result = {
            "subcommand": subcommand,
            "category": None,
            "query": None,
            "name": None,
            "keywords": None,
            "approach": None,
            "lessons": None
        }

        if subcommand == "list":
            i = 1
            while i < len(tokens):
                if tokens[i] == "--category" and i + 1 < len(tokens):
                    result["category"] = tokens[i + 1]
                    i += 2
                else:
                    i += 1

        elif subcommand == "search":
            if len(tokens) < 2:
                raise ValueError("patterns search requires a query")
            result["query"] = tokens[1]
            i = 2
            while i < len(tokens):
                if tokens[i] == "--category" and i + 1 < len(tokens):
                    result["category"] = tokens[i + 1]
                    i += 2
                else:
                    i += 1

        elif subcommand == "create":
            i = 1
            while i < len(tokens):
                if tokens[i] == "--name" and i + 1 < len(tokens):
                    result["name"] = tokens[i + 1]
                    i += 2
                elif tokens[i] == "--category" and i + 1 < len(tokens):
                    result["category"] = tokens[i + 1]
                    i += 2
                elif tokens[i] == "--keywords" and i + 1 < len(tokens):
                    # Collect all remaining tokens as keywords until next flag
                    keywords = []
                    i += 1
                    while i < len(tokens) and not tokens[i].startswith("--"):
                        keywords.append(tokens[i])
                        i += 1
                    result["keywords"] = keywords
                elif tokens[i] == "--approach" and i + 1 < len(tokens):
                    result["approach"] = tokens[i + 1]
                    i += 2
                elif tokens[i] == "--lessons" and i + 1 < len(tokens):
                    result["lessons"] = tokens[i + 1]
                    i += 2
                else:
                    i += 1

            # Validate required fields
            if not result["name"]:
                raise ValueError("patterns create requires --name")
            if not result["category"]:
                raise ValueError("patterns create requires --category")
            if not result["keywords"]:
                raise ValueError("patterns create requires --keywords")

        else:
            raise ValueError(f"Unknown patterns subcommand: {subcommand}")

        return result

    def _parse_memory(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parse memory command.

        Syntax: memory store --team <id> --messages <file>
                memory search <query> [--team <id>]
        """
        if not tokens:
            raise ValueError("memory requires a subcommand: store or search")

        subcommand = tokens[0].lower()
        result = {
            "subcommand": subcommand,
            "team_id": None,
            "messages_file": None,
            "query": None
        }

        if subcommand == "store":
            i = 1
            while i < len(tokens):
                if tokens[i] == "--team" and i + 1 < len(tokens):
                    result["team_id"] = tokens[i + 1]
                    i += 2
                elif tokens[i] == "--messages" and i + 1 < len(tokens):
                    result["messages_file"] = tokens[i + 1]
                    i += 2
                else:
                    i += 1

            # Validate required fields
            if not result["team_id"]:
                raise ValueError("memory store requires --team <id>")
            if not result["messages_file"]:
                raise ValueError("memory store requires --messages <file>")

        elif subcommand == "search":
            if len(tokens) < 2:
                raise ValueError("memory search requires a query")
            result["query"] = tokens[1]
            i = 2
            while i < len(tokens):
                if tokens[i] == "--team" and i + 1 < len(tokens):
                    result["team_id"] = tokens[i + 1]
                    i += 2
                else:
                    i += 1

        else:
            raise ValueError(f"Unknown memory subcommand: {subcommand}")

        return result

    def _parse_dashboard(self, tokens: List[str]) -> Dict[str, Any]:
        """
        Parse dashboard command.

        Syntax: dashboard [--port 5001]
        """
        result = {"port": 5001}

        i = 0
        while i < len(tokens):
            if tokens[i] == "--port" and i + 1 < len(tokens):
                try:
                    result["port"] = int(tokens[i + 1])
                    i += 2
                except ValueError:
                    raise ValueError(f"--port requires a number, got '{tokens[i + 1]}'")
            else:
                i += 1

        return result

    def _parse_status(self, tokens: List[str]) -> Dict[str, Any]:
        """Parse status command (no arguments)."""
        return {}

    def format_help(self) -> str:
        """Return formatted help text."""
        return """
Colony Commands:

  /colony deploy --team <type> --task "<desc>" [options]
      Create a team with Colony context
      --team <type>     Team type: code-review, security, refactor
      --task <desc>     Task description
      --target <path>   Target directory (optional)
      --patterns <cat>  Force pattern category (optional)

  /colony reputation [--agent <id>] [--top N]
      View agent reputations
      --agent <id>  Specific agent ID
      --top N       Show top N agents (default: 5)

  /colony patterns list [--category <cat>]
  /colony patterns search <query>
  /colony patterns create --name <name> --category <cat> --keywords <k1 k2...>
      Manage pattern library

  /colony memory store --team <id> --messages <file>
  /colony memory search <query> [--team <id>]
      Manage conversation memory

  /colony dashboard [--port 5001]
      Launch monitoring dashboard

  /colony status
      Show Colony status and statistics
"""

    def validate_team_type(self, team_type: str) -> bool:
        """Validate team type against known templates."""
        from .native_wrapper import NativeTeamWrapper
        wrapper = NativeTeamWrapper()
        return team_type in wrapper.get_team_types()

    def validate_pattern_category(self, category: str) -> bool:
        """Validate pattern category."""
        from .pattern_library import PatternLibrary
        return category in PatternLibrary.CATEGORIES


class CommandRouter:
    """
    Route parsed commands to appropriate handlers.

    This class coordinates between the command parser and the
    various Colony components (reputation, patterns, memory, etc.).
    """

    def __init__(self):
        """Initialize the command router."""
        self.parser = CommandParser()
        self._reputation_tracker = None
        self._pattern_library = None
        self._chunked_memory = None
        self._team_wrapper = None

    @property
    def reputation_tracker(self):
        """Lazy load reputation tracker."""
        if self._reputation_tracker is None:
            from .reputation_tracker import ReputationTracker
            self._reputation_tracker = ReputationTracker()
        return self._reputation_tracker

    @property
    def pattern_library(self):
        """Lazy load pattern library."""
        if self._pattern_library is None:
            from .pattern_library import PatternLibrary
            self._pattern_library = PatternLibrary()
        return self._pattern_library

    @property
    def chunked_memory(self):
        """Lazy load chunked memory."""
        if self._chunked_memory is None:
            from .chunked_memory import ChunkedMemory
            self._chunked_memory = ChunkedMemory()
        return self._chunked_memory

    @property
    def team_wrapper(self):
        """Lazy load team wrapper."""
        if self._team_wrapper is None:
            from .native_wrapper import NativeTeamWrapper
            self._team_wrapper = NativeTeamWrapper()
        return self._team_wrapper

    def route(self, args: str) -> Dict[str, Any]:
        """
        Route command to appropriate handler.

        Args:
            args: Raw argument string from skill invocation

        Returns:
            Dict with keys: success, message, data
        """
        try:
            command, parsed = self.parser.parse(args)
            return self._execute(command, parsed)
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "help": self.parser.format_help()
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    def _execute(self, command: str, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command with parsed arguments."""
        if command == "deploy":
            return self._execute_deploy(parsed)
        elif command == "reputation":
            return self._execute_reputation(parsed)
        elif command == "patterns":
            return self._execute_patterns(parsed)
        elif command == "memory":
            return self._execute_memory(parsed)
        elif command == "dashboard":
            return self._execute_dashboard(parsed)
        elif command == "status":
            return self._execute_status(parsed)
        else:
            return {
                "success": False,
                "error": f"Unknown command: {command}"
            }

    def _execute_deploy(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deploy command."""
        team_type = parsed["team_type"]
        task = parsed["task"]

        # Validate team type
        if not self.parser.validate_team_type(team_type):
            available = self.team_wrapper.get_team_types()
            return {
                "success": False,
                "error": f"Unknown team type: {team_type}. Available: {', '.join(available)}"
            }

        # Find relevant patterns (using ChunkedResult)
        category = parsed.get("patterns") or self._infer_category(task, team_type)
        patterns_result = self.pattern_library.find_relevant(task, category=category)

        # Find relevant memory (using ChunkedResult)
        memory_result = self.chunked_memory.retrieve_relevant(task)

        # Extract patterns and memory from ChunkedResult
        # Use critical() for must-have context, relevant() for broader coverage
        patterns_data = None
        memory_data = None

        if hasattr(patterns_result, 'critical'):
            # ChunkedResult interface
            from .chunked_result import ChunkedResult
            # Use relevant() to get both critical and relevant patterns
            relevant_patterns = patterns_result.relevant()
            patterns_data = [p.to_dict() if hasattr(p, 'to_dict') else p for p in relevant_patterns]
            patterns_count = patterns_result.estimate_count()
        else:
            # Legacy list interface: List[tuple[Pattern, float]]
            patterns_data = [p[0].to_dict() for p in patterns_result] if patterns_result else None
            patterns_count = len(patterns_result) if patterns_result else 0

        if hasattr(memory_result, 'critical'):
            # ChunkedResult interface
            critical_memory = memory_result.critical()
            memory_data = critical_memory
            memory_count = memory_result.estimate_count()
        else:
            # Legacy list interface
            memory_data = memory_result
            memory_count = len(memory_result) if memory_result else 0

        # Build team prompt with context
        prompt = self.team_wrapper.build_team_prompt(
            task=task,
            team_type=team_type,
            patterns=patterns_data,
            memory_chunks=memory_data
        )

        return {
            "success": True,
            "message": f"Deployed {team_type} team for: {task}",
            "data": {
                "team_type": team_type,
                "task": task,
                "target": parsed.get("target"),
                "patterns_found": patterns_count,
                "memory_chunks": memory_count,
                "prompt": prompt
            }
        }

    def _execute_reputation(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute reputation command."""
        agent_id = parsed.get("agent_id")
        top = parsed.get("top")

        if agent_id:
            reputation = self.reputation_tracker.get_reputation(agent_id)
            if reputation:
                return {
                    "success": True,
                    "message": f"Reputation for {agent_id}",
                    "data": reputation.to_dict()
                }
            else:
                return {
                    "success": False,
                    "error": f"Agent '{agent_id}' not found"
                }
        else:
            agents = self.reputation_tracker.get_top_agents(top or 5)
            return {
                "success": True,
                "message": f"Top {len(agents)} agents",
                "data": {"agents": agents}
            }

    def _execute_patterns(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute patterns command."""
        subcommand = parsed["subcommand"]

        if subcommand == "list":
            patterns = self.pattern_library.list_patterns(category=parsed.get("category"))
            return {
                "success": True,
                "message": f"Found {len(patterns)} patterns",
                "data": {"patterns": patterns}
            }

        elif subcommand == "search":
            results = self.pattern_library.find_relevant(
                parsed["query"],
                category=parsed.get("category")
            )

            # Handle ChunkedResult or legacy list
            if hasattr(results, 'critical'):
                # ChunkedResult interface - show tiered summary
                return {
                    "success": True,
                    "message": results.summary(),
                    "data": {
                        "query": parsed["query"],
                        "chunked": True,
                        "summary": results.to_dict(),
                        "critical": [p.to_dict() if hasattr(p, 'to_dict') else p for p in results.critical()],
                        "relevant": [p.to_dict() if hasattr(p, 'to_dict') else p for p in results.relevant()],
                    }
                }
            else:
                # Legacy list interface: List[tuple[Pattern, float]]
                return {
                    "success": True,
                    "message": f"Found {len(results)} relevant patterns",
                    "data": {
                        "query": parsed["query"],
                        "chunked": False,
                        "results": [(p[0].to_dict(), p[1]) for p in results]
                    }
                }

        elif subcommand == "create":
            pattern = self.pattern_library.create_pattern(
                name=parsed["name"],
                category=parsed["category"],
                trigger_keywords=parsed["keywords"],
                approach=json.loads(parsed.get("approach", "{}")),
                lessons_learned=json.loads(parsed.get("lessons", "[]"))
            )
            return {
                "success": True,
                "message": f"Created pattern: {pattern.pattern_id}",
                "data": pattern.to_dict()
            }

    def _execute_memory(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute memory command."""
        subcommand = parsed["subcommand"]

        if subcommand == "store":
            import json as json_module
            messages_file = Path(parsed["messages_file"])
            if not messages_file.exists():
                return {
                    "success": False,
                    "error": f"Messages file not found: {messages_file}"
                }

            with open(messages_file) as f:
                messages = json_module.load(f)

            path = self.chunked_memory.store_conversation(
                team_id=parsed["team_id"],
                messages=messages
            )
            return {
                "success": True,
                "message": f"Stored {len(messages)} messages for team {parsed['team_id']}",
                "data": {"path": path}
            }

        elif subcommand == "search":
            results = self.chunked_memory.retrieve_relevant(
                parsed["query"],
                team_id=parsed.get("team_id")
            )

            # Handle ChunkedResult or legacy list
            if hasattr(results, 'critical'):
                # ChunkedResult interface - show tiered summary
                return {
                    "success": True,
                    "message": results.summary(),
                    "data": {
                        "query": parsed["query"],
                        "chunked": True,
                        "summary": results.to_dict(),
                        "critical": results.critical(),
                        "relevant": results.relevant(),
                    }
                }
            else:
                # Legacy list interface
                return {
                    "success": True,
                    "message": f"Found {len(results)} relevant memory chunks",
                    "data": {
                        "query": parsed["query"],
                        "chunked": False,
                        "results": results
                    }
                }

    def _execute_dashboard(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute dashboard command."""
        port = parsed.get("port", 5001)

        # Check if Flask is available
        try:
            import flask
        except ImportError:
            return {
                "success": False,
                "error": "Flask not installed. Install with: pip install flask"
            }

        # Check if dashboard module exists
        dashboard_path = Path(__file__).parent.parent / "dashboard" / "app.py"
        if not dashboard_path.exists():
            return {
                "success": False,
                "error": "Dashboard module not found. Run: pip install flask"
            }

        return {
            "success": True,
            "message": f"Dashboard starting on port {port}",
            "data": {"port": port, "url": f"http://localhost:{port}"}
        }

    def _execute_status(self, parsed: Dict[str, Any]) -> Dict[str, Any]:
        """Execute status command."""
        # Collect statistics
        agents = self.reputation_tracker.get_all_agents()
        patterns = self.pattern_library.list_patterns()
        teams = self.chunked_memory.list_teams()
        native_teams = self.team_wrapper.get_all_teams()

        # Count by tier
        tier_counts = {}
        for agent in agents:
            tier = agent.get("tier", "UNKNOWN")
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        return {
            "success": True,
            "message": "Colony status",
            "data": {
                "total_agents": len(agents),
                "total_patterns": len(patterns),
                "total_teams_with_memory": len(teams),
                "active_native_teams": len(native_teams),
                "tier_distribution": tier_counts
            }
        }

    def _infer_category(self, task: str, team_type: str) -> Optional[str]:
        """Infer pattern category from task and team type."""
        task_lower = task.lower()

        if team_type == "security" or "security" in task_lower:
            return "security"
        elif team_type == "code-review" or "review" in task_lower:
            return "code_review"
        elif team_type == "refactor" or "refactor" in task_lower:
            return "refactoring"
        elif "test" in task_lower:
            return "testing"
        elif "debug" in task_lower or "fix" in task_lower:
            return "debugging"
        elif "optimize" in task_lower or "performance" in task_lower:
            return "optimization"

        return None


def main():
    """CLI entry point for testing."""
    import sys

    if len(sys.argv) < 2:
        print(CommandParser().format_help())
        return

    args = " ".join(sys.argv[1:])
    router = CommandRouter()
    result = router.route(args)

    if result.get("success"):
        print(f"✅ {result.get('message')}")
        if "data" in result:
            print(json.dumps(result["data"], indent=2))
    else:
        print(f"❌ {result.get('error')}")
        if "help" in result:
            print(result["help"])


if __name__ == "__main__":
    main()
