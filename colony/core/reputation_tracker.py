"""
Reputation Tracker for Colony.

Tracks agent performance with a 5-tier reputation system:
UNKNOWN → NOVICE → CONTRIBUTOR → EXPERT → ELITE

Adapted from Colony Alpha's reputation system.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json


@dataclass
class TaskEvent:
    """Record of a single task completion."""
    agent_id: str
    task_id: str
    outcome: str  # SUCCESS/FAILURE/PARTIAL
    timestamp: str
    quality_score: float  # 0.0 to 1.0
    duration_ms: int


@dataclass
class AgentReputation:
    """Reputation data for a single agent."""
    agent_id: str
    total_tasks: int = 0
    successful_tasks: int = 0
    reputation_score: float = 0.0
    tier: str = "UNKNOWN"
    recent_events: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


class ReputationTracker:
    """Tracks and manages agent reputations."""

    # Tier thresholds
    TIERS = {
        "UNKNOWN": (0, 0.4, 3),    # min_tasks, min_score, min_task_count
        "NOVICE": (3, 0.4, 0),
        "CONTRIBUTOR": (0, 0.6, 0),
        "EXPERT": (0, 0.8, 0),
        "ELITE": (0, 1.0, 0),
    }

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the reputation tracker.

        Args:
            storage_path: Path to store reputation data. Defaults to ~/.colony/reputation/
        """
        self.storage_path = Path(storage_path or "~/.colony/reputation").expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def record_completion(
        self,
        agent_id: str,
        task_id: str,
        quality_score: float,
        outcome: str = "SUCCESS",
        duration_ms: int = 0
    ) -> AgentReputation:
        """
        Record a task completion and update reputation.

        Args:
            agent_id: ID of the agent that completed the task
            task_id: ID of the completed task
            quality_score: Quality score from 0.0 to 1.0
            outcome: Task outcome - SUCCESS, FAILURE, or PARTIAL
            duration_ms: Task duration in milliseconds

        Returns:
            Updated AgentReputation
        """
        reputation = self._load_reputation(agent_id)

        reputation.total_tasks += 1
        if outcome == "SUCCESS":
            reputation.successful_tasks += 1

        # Calculate composite score
        reputation.reputation_score = self._calculate_score(reputation, quality_score)
        reputation.tier = self._calculate_tier(reputation)

        # Add to recent events (keep last 10)
        event = {
            "task_id": task_id,
            "outcome": outcome,
            "timestamp": datetime.now().isoformat(),
            "quality_score": quality_score
        }
        reputation.recent_events.append(json.dumps(event))
        if len(reputation.recent_events) > 10:
            reputation.recent_events.pop(0)

        self._save_reputation(agent_id, reputation)
        return reputation

    def get_reputation(self, agent_id: str) -> Optional[AgentReputation]:
        """
        Get reputation data for a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            AgentReputation or None if agent not found
        """
        reputation = self._load_reputation(agent_id)
        if reputation.total_tasks == 0 and agent_id not in self._list_stored_agents():
            return None
        return reputation

    def get_top_agents(self, limit: int = 5) -> List[Dict]:
        """
        Get top agents by reputation score.

        Args:
            limit: Maximum number of agents to return

        Returns:
            List of agent reputation dicts, sorted by score
        """
        agents = []
        for file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                agents.append(data)
            except (json.JSONDecodeError, IOError):
                continue

        agents.sort(key=lambda x: x.get("reputation_score", 0.0), reverse=True)
        return agents[:limit]

    def get_all_agents(self) -> List[Dict]:
        """
        Get all agents with reputation data.

        Returns:
            List of all agent reputation dicts
        """
        agents = []
        for file in self.storage_path.glob("*.json"):
            try:
                data = json.loads(file.read_text())
                agents.append(data)
            except (json.JSONDecodeError, IOError):
                continue
        return agents

    def _calculate_score(self, reputation: AgentReputation, quality_score: float) -> float:
        """
        Calculate composite reputation score.

        Formula: 60% success rate + 40% quality average
        """
        success_rate = reputation.successful_tasks / max(reputation.total_tasks, 1)

        # Simple moving average for quality (uses current score as proxy)
        # In a full implementation, we'd track all quality scores
        current_quality_avg = quality_score

        return (success_rate * 0.6) + (current_quality_avg * 0.4)

    def _calculate_tier(self, reputation: AgentReputation) -> str:
        """
        Calculate reputation tier based on score and task count.

        Tiers:
        - UNKNOWN: < 3 tasks completed
        - NOVICE: score < 0.4
        - CONTRIBUTOR: score < 0.6
        - EXPERT: score < 0.8
        - ELITE: score >= 0.8
        """
        score = reputation.reputation_score
        tasks = reputation.total_tasks

        if tasks < 3:
            return "UNKNOWN"
        elif score < 0.4:
            return "NOVICE"
        elif score < 0.6:
            return "CONTRIBUTOR"
        elif score < 0.8:
            return "EXPERT"
        else:
            return "ELITE"

    def _load_reputation(self, agent_id: str) -> AgentReputation:
        """Load agent reputation from storage."""
        file_path = self.storage_path / f"{agent_id}.json"
        if file_path.exists():
            try:
                data = json.loads(file_path.read_text())
                return AgentReputation(**data)
            except (json.JSONDecodeError, TypeError):
                return AgentReputation(agent_id=agent_id)
        return AgentReputation(agent_id=agent_id)

    def _save_reputation(self, agent_id: str, reputation: AgentReputation):
        """Save agent reputation to storage."""
        file_path = self.storage_path / f"{agent_id}.json"
        file_path.write_text(json.dumps(reputation.to_dict(), indent=2))

    def _list_stored_agents(self) -> List[str]:
        """List all agent IDs that have stored reputation data."""
        agents = []
        for file in self.storage_path.glob("*.json"):
            agents.append(file.stem)
        return agents


# CLI helper for testing
def main():
    """Simple CLI for testing reputation tracker."""
    import argparse

    parser = argparse.ArgumentParser(description="Colony Reputation Tracker")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Record command
    record_parser = subparsers.add_parser("record", help="Record a task completion")
    record_parser.add_argument("--agent", required=True, help="Agent ID")
    record_parser.add_argument("--task", required=True, help="Task ID")
    record_parser.add_argument("--score", type=float, required=True, help="Quality score (0.0-1.0)")
    record_parser.add_argument("--outcome", default="SUCCESS", choices=["SUCCESS", "FAILURE", "PARTIAL"])

    # List command
    list_parser = subparsers.add_parser("list", help="List agent reputations")
    list_parser.add_argument("--top", type=int, default=10, help="Number of top agents to show")

    # Get command
    get_parser = subparsers.add_parser("get", help="Get specific agent reputation")
    get_parser.add_argument("--agent", required=True, help="Agent ID")

    args = parser.parse_args()

    tracker = ReputationTracker()

    if args.command == "record":
        reputation = tracker.record_completion(
            args.agent, args.task, args.score, args.outcome
        )
        print(f"✅ Recorded: {args.agent} → {reputation.tier} ({reputation.reputation_score:.2f})")

    elif args.command == "list":
        agents = tracker.get_top_agents(args.top)
        print(f"\n📊 Top {len(agents)} Agents:\n")
        for agent in agents:
            print(f"  {agent['agent_id']}: {agent['tier']} ({agent['reputation_score']:.2f}) - {agent['total_tasks']} tasks")

    elif args.command == "get":
        reputation = tracker.get_reputation(args.agent)
        if reputation:
            print(f"\n👤 {reputation.agent_id}\n")
            print(f"  Tier: {reputation.tier}")
            print(f"  Score: {reputation.reputation_score:.2f}")
            print(f"  Tasks: {reputation.total_tasks} ({reputation.successful_tasks} successful)")
        else:
            print(f"❌ Agent '{args.agent}' not found")


if __name__ == "__main__":
    main()
