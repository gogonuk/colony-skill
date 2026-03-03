#!/usr/bin/env python3
"""
Test script simulating /colony status command.
This tests all Colony components together.
"""

import sys
import os
from pathlib import Path

# Add the colony module to path
sys.path.insert(0, str(Path(__file__).parent))

from colony.core.reputation_tracker import ReputationTracker
from colony.core.pattern_library import PatternLibrary
from colony.core.native_wrapper import NativeTeamWrapper
from colony.core.chunked_memory import ChunkedMemory

def colony_status():
    """Simulate the /colony status command."""

    print("\n" + "="*50)
    print("📊 Colony Status")
    print("="*50)

    # Initialize components
    reputation_dir = Path.home() / ".colony" / "reputation"
    patterns_dir = Path.home() / ".colony" / "patterns"
    memory_dir = Path.home() / ".colony" / "memory"

    tracker = ReputationTracker(str(reputation_dir))
    library = PatternLibrary(str(patterns_dir))
    memory = ChunkedMemory(str(memory_dir))
    wrapper = NativeTeamWrapper()

    # Check reputation data
    print("\n📈 Reputation Tracking:")
    agents = tracker.get_all_agents()
    if agents:
        print(f"   Tracking {len(agents)} agent(s)")
        for agent in agents[:5]:
            print(f"   - {agent['agent_id']}: {agent['tier']} ({agent['reputation_score']:.2f})")
    else:
        print("   ℹ️  No agents tracked yet")

    # Check pattern library
    print("\n📚 Pattern Library:")
    patterns = library.list_patterns()
    if patterns:
        print(f"   {len(patterns)} pattern(s) stored")
        by_category = {}
        for p in patterns:
            cat = p['category']
            by_category[cat] = by_category.get(cat, 0) + 1
        for cat, count in by_category.items():
            print(f"   - {cat}: {count}")
    else:
        print("   ℹ️  No patterns stored yet")

    # Check memory
    print("\n🧠 Memory:")
    teams = memory.list_teams()
    if teams:
        print(f"   {len(teams)} conversation(s) stored")
        total_messages = 0
        total_chunks = 0
        for team_id in teams:
            summary = memory.get_conversation_summary(team_id)
            if summary:
                total_messages += summary['total_messages']
                total_chunks += summary['total_chunks']
        print(f"   - {total_messages} messages in {total_chunks} chunks")
    else:
        print("   ℹ️  No conversations stored yet")

    # Check native teams
    print("\n👥 Native Teams:")
    native_teams = wrapper.get_all_teams()
    if native_teams:
        print(f"   {len(native_teams)} active team(s)")
        for team in native_teams[:3]:
            print(f"   - {team['team_name']}: {team['state']}")
    else:
        print("   ℹ️  No active teams")

    # Storage info
    print("\n💾 Storage:")
    colony_dir = Path.home() / ".colony"
    if colony_dir.exists():
        size = sum(f.stat().st_size for f in colony_dir.rglob('*') if f.is_file())
        print(f"   Location: ~/.colony/")
        print(f"   Size: {size / 1024:.1f} KB")

    print("\n" + "="*50)
    print("Colony v0.1.0 - All systems operational")
    print("="*50 + "\n")

    return True


def colony_reputation():
    """Simulate /colony reputation command."""
    print("\n" + "="*50)
    print("📈 Agent Reputations")
    print("="*50)

    tracker = ReputationTracker()
    agents = tracker.get_top_agents(10)

    if not agents:
        print("\n   ℹ️  No agents tracked yet")
        print("   Use /colony deploy to create teams and track reputation")
        return True

    print(f"\n   Top {len(agents)} Agent(s):\n")
    for i, agent in enumerate(agents, 1):
        tier_icon = {
            "ELITE": "🌟",
            "EXPERT": "💎",
            "CONTRIBUTOR": "👷",
            "NOVICE": "🌱",
            "UNKNOWN": "❓"
        }.get(agent['tier'], "❓")

        print(f"   {i}. {tier_icon} {agent['agent_id']}")
        print(f"      Tier: {agent['tier']}")
        print(f"      Score: {agent['reputation_score']:.2f}")
        print(f"      Tasks: {agent['total_tasks']} ({agent['successful_tasks']} successful)")
        print()

    return True


def colony_patterns_list():
    """Simulate /colony patterns list command."""
    print("\n" + "="*50)
    print("📚 Pattern Library")
    print("="*50)

    library = PatternLibrary()
    patterns = library.list_patterns()

    if not patterns:
        print("\n   ℹ️  No patterns stored yet")
        print("   Patterns are automatically extracted from successful team work")
        return True

    # Group by category
    by_category = {}
    for p in patterns:
        cat = p['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(p)

    print(f"\n   {len(patterns)} pattern(s) found:\n")
    for category, cats_patterns in by_category.items():
        print(f"   📂 {category}:")
        for p in cats_patterns:
            print(f"      - {p['name']}")
            print(f"        Used {p['usage_count']}x, {p['success_rate']:.0%} success")
        print()

    return True


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Colony CLI Test")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Default - status
    subparsers.add_parser("status", help="Show Colony status")

    # Reputation
    subparsers.add_parser("reputation", help="Show agent reputations")

    # Patterns
    subparsers.add_parser("patterns", help="List patterns")

    args = parser.parse_args()

    if not args.command or args.command == "status":
        colony_status()
    elif args.command == "reputation":
        colony_reputation()
    elif args.command == "patterns":
        colony_patterns_list()
