"""
Pattern Library for Colony.

Stores and retrieves reusable successful approaches.
Patterns are organized by category and can be searched by keywords.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import json
import uuid


@dataclass
class Pattern:
    """A reusable successful approach."""
    pattern_id: str
    name: str
    category: str  # security, code_review, debugging, refactoring, etc.
    trigger_keywords: List[str]
    approach: Dict  # steps, tools, focus_areas
    lessons_learned: List[str]
    usage_count: int = 0
    success_rate: float = 1.0
    created_at: str = ""
    last_used: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        # Handle datetime fields
        if isinstance(self.created_at, datetime):
            d["created_at"] = self.created_at.isoformat()
        if isinstance(self.last_used, datetime):
            d["last_used"] = self.last_used.isoformat()
        return d


class PatternLibrary:
    """Manages the pattern library."""

    # Common categories
    CATEGORIES = [
        "security",
        "code_review",
        "debugging",
        "refactoring",
        "testing",
        "documentation",
        "optimization",
        "migration",
    ]

    # Common words to filter out during keyword extraction
    STOP_WORDS = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "and", "or", "but", "for", "with", "from", "this", "that", "these",
        "those", "have", "has", "had", "do", "does", "did", "will", "would",
        "could", "should", "may", "might", "must", "shall", "can", "need",
        "into", "onto", "upon", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "each",
        "few", "more", "most", "other", "some", "such", "no", "nor", "not",
        "only", "own", "same", "so", "than", "too", "very", "just", "also"
    }

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the pattern library.

        Args:
            storage_path: Path to store patterns. Defaults to ~/.colony/patterns/
        """
        self.storage_path = Path(storage_path or "~/.colony/patterns").expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create category directories
        for category in self.CATEGORIES:
            (self.storage_path / category).mkdir(exist_ok=True)

    def save_pattern(self, pattern: Pattern) -> str:
        """
        Save a pattern to the library.

        Args:
            pattern: Pattern to save

        Returns:
            Path to the saved pattern file
        """
        # Ensure category directory exists
        category_dir = self.storage_path / pattern.category
        category_dir.mkdir(exist_ok=True)

        # Generate ID if not provided
        if not pattern.pattern_id:
            pattern.pattern_id = f"{pattern.category}_{uuid.uuid4().hex[:8]}"

        # Save pattern
        file_path = category_dir / f"{pattern.pattern_id}.json"
        file_path.write_text(json.dumps(pattern.to_dict(), indent=2))

        return str(file_path)

    def get_pattern(self, pattern_id: str, category: Optional[str] = None) -> Optional[Pattern]:
        """
        Get a specific pattern by ID.

        Args:
            pattern_id: ID of the pattern to retrieve
            category: Category to search in (optional, searches all if not provided)

        Returns:
            Pattern or None if not found
        """
        if category:
            search_paths = [self.storage_path / category]
        else:
            search_paths = [self.storage_path / cat for cat in self.CATEGORIES]

        for search_path in search_paths:
            file_path = search_path / f"{pattern_id}.json"
            if file_path.exists():
                try:
                    data = json.loads(file_path.read_text())
                    return Pattern(**data)
                except (json.JSONDecodeError, TypeError):
                    continue
        return None

    def find_relevant(
        self,
        task_description: str,
        category: Optional[str] = None,
        limit: int = 3
    ) -> List[tuple[Pattern, float]]:
        """
        Find patterns relevant to a task description.

        Args:
            task_description: Description of the task
            category: Filter by category (optional)
            limit: Maximum number of patterns to return

        Returns:
            List of (Pattern, relevance_score) tuples, sorted by relevance
        """
        task_keywords = self._extract_keywords(task_description)
        relevant = []

        # Determine search directories
        if category:
            search_dirs = [self.storage_path / category]
        else:
            search_dirs = [self.storage_path / cat for cat in self.CATEGORIES]

        # Search for patterns
        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file in search_dir.glob("*.json"):
                try:
                    pattern_data = json.loads(file.read_text())
                    pattern = Pattern(**pattern_data)

                    # Calculate relevance
                    relevance = self._calculate_relevance(task_keywords, pattern.trigger_keywords)

                    if relevance > 0.3:
                        relevant.append((pattern, relevance))
                except (json.JSONDecodeError, TypeError):
                    continue

        # Sort by relevance * success_rate and usage_count
        relevant.sort(
            key=lambda x: (x[1] * x[0].success_rate) + (x[0].usage_count * 0.01),
            reverse=True
        )

        return relevant[:limit]

    def list_patterns(self, category: Optional[str] = None) -> List[Dict]:
        """
        List all patterns.

        Args:
            category: Filter by category (optional)

        Returns:
            List of pattern metadata dicts
        """
        patterns = []

        if category:
            search_dirs = [self.storage_path / category]
        else:
            search_dirs = [self.storage_path / cat for cat in self.CATEGORIES]

        for search_dir in search_dirs:
            if not search_dir.exists():
                continue

            for file in search_dir.glob("*.json"):
                try:
                    data = json.loads(file.read_text())
                    # Return lightweight metadata
                    patterns.append({
                        "pattern_id": data["pattern_id"],
                        "name": data["name"],
                        "category": data["category"],
                        "usage_count": data["usage_count"],
                        "success_rate": data["success_rate"]
                    })
                except (json.JSONDecodeError, KeyError):
                    continue

        return patterns

    def update_usage(self, pattern_id: str, success: bool = True) -> Optional[Pattern]:
        """
        Update pattern usage statistics.

        Args:
            pattern_id: ID of the pattern to update
            success: Whether the pattern was used successfully

        Returns:
            Updated Pattern or None if not found
        """
        pattern = self.get_pattern(pattern_id)
        if not pattern:
            return None

        # Update usage count
        pattern.usage_count += 1

        # Update success rate using moving average
        alpha = 0.3  # Weight for new samples
        new_value = 1.0 if success else 0.0
        pattern.success_rate = (alpha * new_value) + ((1 - alpha) * pattern.success_rate)

        # Update last used timestamp
        pattern.last_used = datetime.now().isoformat()

        # Save updated pattern
        self.save_pattern(pattern)

        return pattern

    def create_pattern(
        self,
        name: str,
        category: str,
        trigger_keywords: List[str],
        approach: Dict,
        lessons_learned: List[str]
    ) -> Pattern:
        """
        Create a new pattern.

        Args:
            name: Human-readable pattern name
            category: Pattern category
            trigger_keywords: Keywords that should trigger this pattern
            approach: Dictionary with 'steps', 'tools', 'focus_areas'
            lessons_learned: List of lessons learned from using this pattern

        Returns:
            Created Pattern
        """
        pattern = Pattern(
            pattern_id="",  # Will be generated in save_pattern
            name=name,
            category=category,
            trigger_keywords=trigger_keywords,
            approach=approach,
            lessons_learned=lessons_learned
        )
        self.save_pattern(pattern)
        return pattern

    def delete_pattern(self, pattern_id: str, category: Optional[str] = None) -> bool:
        """
        Delete a pattern from the library.

        Args:
            pattern_id: ID of the pattern to delete
            category: Category of the pattern (helps locate it faster)

        Returns:
            True if deleted, False if not found
        """
        if category:
            file_path = self.storage_path / category / f"{pattern_id}.json"
        else:
            # Search all categories
            for cat in self.CATEGORIES:
                file_path = self.storage_path / cat / f"{pattern_id}.json"
                if file_path.exists():
                    file_path.unlink()
                    return True
            return False

        if file_path.exists():
            file_path.unlink()
            return True
        return False

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.

        Filters out common stop words and short words.
        """
        # Convert to lowercase and split
        words = text.lower().split()

        # Filter out stop words and short words
        keywords = [w.strip(".,!?;:\"'()[]{}") for w in words
                   if w.strip(".,!?;:\"'()[]{}") not in self.STOP_WORDS
                   and len(w.strip(".,!?;:\"'()[]{}")) > 3]

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)

        return result

    def _calculate_relevance(self, task_keywords: List[str], pattern_keywords: List[str]) -> float:
        """
        Calculate relevance using Jaccard similarity.

        Jaccard similarity = |intersection| / |union|
        """
        if not pattern_keywords:
            return 0.0

        task_set = set(kw.lower() for kw in task_keywords)
        pattern_set = set(kw.lower() for kw in pattern_keywords)

        intersection = len(task_set & pattern_set)
        union = len(task_set | pattern_set)

        return intersection / union if union > 0 else 0.0


# CLI helper for testing
def main():
    """Simple CLI for testing pattern library."""
    import argparse

    parser = argparse.ArgumentParser(description="Colony Pattern Library")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new pattern")
    create_parser.add_argument("--name", required=True, help="Pattern name")
    create_parser.add_argument("--category", required=True, choices=PatternLibrary.CATEGORIES)
    create_parser.add_argument("--keywords", nargs="+", required=True, help="Trigger keywords")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search for patterns")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--category", help="Filter by category")
    search_parser.add_argument("--limit", type=int, default=3, help="Number of results")

    # List command
    list_parser = subparsers.add_parser("list", help="List all patterns")
    list_parser.add_argument("--category", help="Filter by category")

    args = parser.parse_args()

    library = PatternLibrary()

    if args.command == "create":
        pattern = library.create_pattern(
            name=args.name,
            category=args.category,
            trigger_keywords=args.keywords,
            approach={"steps": ["Example step"], "tools": [], "focus_areas": []},
            lessons_learned=["Example lesson"]
        )
        print(f"✅ Created pattern: {pattern.pattern_id}")

    elif args.command == "search":
        results = library.find_relevant(args.query, category=args.category, limit=args.limit)
        print(f"\n🔍 Found {len(results)} relevant patterns:\n")
        for pattern, relevance in results:
            print(f"  {pattern.name} ({pattern.category}) - Relevance: {relevance:.2f}")

    elif args.command == "list":
        patterns = library.list_patterns(category=args.category)
        print(f"\n📚 {len(patterns)} patterns:\n")
        for p in patterns:
            print(f"  {p['name']} ({p['category']}) - Used {p['usage_count']}x - {p['success_rate']:.0%} success")


if __name__ == "__main__":
    main()
