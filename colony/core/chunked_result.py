"""
Chunked Result Container for Colony.

Provides lazy-loading, tiered access to search results.
Enables progressive loading of patterns and memory chunks.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Generic, TypeVar, Callable, Any, Set
from enum import Enum
import hashlib


T = TypeVar('T')


class RelevanceTier(Enum):
    """Relevance tiers for chunked results."""
    CRITICAL = "critical"   # High relevance, must-have context
    RELEVANT = "relevant"   # Medium relevance, nice-to-have
    CONTEXT = "context"     # Low relevance, background info
    ALL = "all"             # Everything available


@dataclass
class TierConfig:
    """Configuration for relevance tiers."""
    critical_limit: int = 2      # Max critical items to return
    relevant_limit: int = 5      # Max relevant items to return
    context_limit: int = 10      # Max context items to return
    all_limit: int = 50          # Max total items to return

    # Relevance thresholds
    critical_min_relevance: float = 0.7
    relevant_min_relevance: float = 0.4
    context_min_relevance: float = 0.2

    def get_limit_for_tier(self, tier: RelevanceTier) -> int:
        """Get the limit for a specific tier."""
        return {
            RelevanceTier.CRITICAL: self.critical_limit,
            RelevanceTier.RELEVANT: self.relevant_limit,
            RelevanceTier.CONTEXT: self.context_limit,
            RelevanceTier.ALL: self.all_limit,
        }.get(tier, self.all_limit)

    def get_min_relevance_for_tier(self, tier: RelevanceTier) -> float:
        """Get minimum relevance score for a tier."""
        return {
            RelevanceTier.CRITICAL: self.critical_min_relevance,
            RelevanceTier.RELEVANT: self.relevant_min_relevance,
            RelevanceTier.CONTEXT: self.context_min_relevance,
            RelevanceTier.ALL: 0.0,
        }.get(tier, 0.0)


@dataclass
class ChunkedItem(Generic[T]):
    """A single item in chunked results with metadata."""
    item: T
    relevance: float
    tier: RelevanceTier
    loaded: bool = True

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "item": self.item if not isinstance(self.item, dict) else self.item,
            "relevance": self.relevance,
            "tier": self.tier.value
        }


class ChunkedResult(Generic[T]):
    """
    Lazy-loading container for chunked search results.

    Provides tiered access to results with progressive loading.
    Only loads what's needed, when it's needed.

    Example:
        results = library.find_relevant("fix sql injection")

        # Get only critical items (fast, minimal loading)
        critical = results.critical()

        # Get critical + relevant (more, but still limited)
        relevant = results.relevant()

        # Get everything (expensive, complete)
        all_results = results.all()

        # Get a compact summary
        summary = results.summary()
    """

    # Default tier configuration
    DEFAULT_CONFIG = TierConfig(
        critical_limit=2,
        relevant_limit=5,
        context_limit=10,
        all_limit=50,
        critical_min_relevance=0.7,
        relevant_min_relevance=0.4,
        context_min_relevance=0.2
    )

    def __init__(
        self,
        query: str,
        loader: Callable[[float, int], List[tuple[T, float]]],
        config: Optional[TierConfig] = None,
        item_formatter: Optional[Callable[[T], str]] = None
    ):
        """
        Initialize chunked results.

        Args:
            query: The search query (for summary/debugging)
            loader: Function that loads results given (min_relevance, limit)
                    Returns: List of (item, relevance_score) tuples
            config: Tier configuration (uses DEFAULT_CONFIG if None)
            item_formatter: Optional function to format items for summary
        """
        self.query = query
        self._loader = loader
        self.config = config or self.DEFAULT_CONFIG
        self._item_formatter = item_formatter or self._default_formatter

        # Lazy-loaded state
        self._loaded_tiers = set()
        self._all_items: List[ChunkedItem[T]] = []
        self._by_tier: Dict[RelevanceTier, List[ChunkedItem[T]]] = {
            tier: [] for tier in RelevanceTier
        }
        self._loaded_item_hashes: Set[str] = set()  # Track loaded items by content hash
        self._total_available = None
        self._fully_loaded = False

    def _default_formatter(self, item: T) -> str:
        """Default item formatter for summaries."""
        if isinstance(item, dict):
            name = item.get("name", item.get("pattern_id", item.get("chunk_id", "Unknown")))
            return str(name)
        return str(item)[:50]

    def _get_item_hash(self, item: T) -> str:
        """
        Generate a unique hash for an item for deduplication.

        Uses content-based hashing to handle different object instances
        with the same content.

        Args:
            item: The item to hash

        Returns:
            Hex string hash of the item content
        """
        # For dict items, hash the JSON representation
        if isinstance(item, dict):
            # Get a unique identifier if available
            if "pattern_id" in item:
                return f"pattern:{item['pattern_id']}"
            elif "chunk_id" in item:
                return f"chunk:{item['chunk_id']}"
            else:
                # Fall back to JSON hashing
                import json
                return hashlib.md5(
                    json.dumps(item, sort_keys=True).encode()
                ).hexdigest()

        # For objects with unique attributes
        if hasattr(item, 'pattern_id'):
            return f"pattern:{item.pattern_id}"
        if hasattr(item, 'chunk_id'):
            return f"chunk:{item.chunk_id}"

        # For other items, hash the string representation
        return hashlib.md5(str(item).encode()).hexdigest()

    def _load_tier(self, tier: RelevanceTier) -> None:
        """Load items for a specific tier if not already loaded."""
        if tier in self._loaded_tiers:
            return

        min_relevance = self.config.get_min_relevance_for_tier(tier)
        limit = self.config.get_limit_for_tier(tier)

        # Load from source
        raw_results = self._loader(min_relevance, limit)

        # Convert to ChunkedItems and assign tiers
        for item, relevance in raw_results:
            # Create a unique hash for deduplication
            item_hash = self._get_item_hash(item)
            if item_hash in self._loaded_item_hashes:
                continue

            chunked_item = ChunkedItem(
                item=item,
                relevance=relevance,
                tier=self._assign_tier(relevance)
            )
            self._all_items.append(chunked_item)
            self._by_tier[chunked_item.tier].append(chunked_item)
            self._loaded_item_hashes.add(item_hash)

        self._loaded_tiers.add(tier)

    def _assign_tier(self, relevance: float) -> RelevanceTier:
        """Assign a tier based on relevance score."""
        if relevance >= self.config.critical_min_relevance:
            return RelevanceTier.CRITICAL
        elif relevance >= self.config.relevant_min_relevance:
            return RelevanceTier.RELEVANT
        elif relevance >= self.config.context_min_relevance:
            return RelevanceTier.CONTEXT
        else:
            return RelevanceTier.ALL

    def _load_all(self) -> None:
        """Load all available results."""
        if self._fully_loaded:
            return

        # Load the highest tier (ALL tier)
        min_relevance = 0.0
        limit = self.config.all_limit

        raw_results = self._loader(min_relevance, limit)
        self._total_available = len(raw_results)

        # Convert to ChunkedItems and clear existing
        self._all_items = []
        self._by_tier = {tier: [] for tier in RelevanceTier}
        self._loaded_item_hashes = set()

        for item, relevance in raw_results:
            # Create a unique hash for deduplication
            item_hash = self._get_item_hash(item)
            if item_hash in self._loaded_item_hashes:
                continue

            chunked_item = ChunkedItem(
                item=item,
                relevance=relevance,
                tier=self._assign_tier(relevance)
            )
            self._all_items.append(chunked_item)
            self._by_tier[chunked_item.tier].append(chunked_item)
            self._loaded_item_hashes.add(item_hash)

        self._fully_loaded = True
        self._loaded_tiers.update(set(RelevanceTier))

    def critical(self) -> List[T]:
        """
        Get only critical (high relevance) items.

        Fast path: Returns only the most relevant results.
        Use this when you need must-have context quickly.

        Returns:
            List of items with relevance >= 0.7 (default)
        """
        self._load_tier(RelevanceTier.CRITICAL)
        return [item.item for item in self._by_tier[RelevanceTier.CRITICAL]]

    def relevant(self) -> List[T]:
        """
        Get critical + relevant items.

        Balanced path: Returns high and medium relevance results.
        Use this for most queries where you need good coverage.

        Returns:
            List of items with relevance >= 0.4 (default)
        """
        self._load_tier(RelevanceTier.CRITICAL)
        self._load_tier(RelevanceTier.RELEVANT)

        critical = self._by_tier[RelevanceTier.CRITICAL]
        relevant = self._by_tier[RelevanceTier.RELEVANT]

        return [item.item for item in (critical + relevant)]

    def context(self) -> List[T]:
        """
        Get critical + relevant + context items.

        Expanded path: Returns high, medium, and low relevance results.
        Use this when you need broader context.

        Returns:
            List of items with relevance >= 0.2 (default)
        """
        self._load_tier(RelevanceTier.CRITICAL)
        self._load_tier(RelevanceTier.RELEVANT)
        self._load_tier(RelevanceTier.CONTEXT)

        all_tiers = [
            self._by_tier[RelevanceTier.CRITICAL],
            self._by_tier[RelevanceTier.RELEVANT],
            self._by_tier[RelevanceTier.CONTEXT]
        ]

        return [item.item for item in sum(all_tiers, [])]

    def all(self) -> List[T]:
        """
        Get all available items.

        Complete path: Returns everything, regardless of relevance.
        Use this when you need exhaustive results.

        Note: This may be expensive for large datasets.

        Returns:
            All available items
        """
        self._load_all()
        return [item.item for item in self._all_items]

    def summary(self) -> str:
        """
        Get a compact summary of results.

        Returns a formatted string with:
        - Query information
        - Tier counts
        - Top items by tier

        Returns:
            Formatted summary string
        """
        # Ensure we have some data
        if not self._loaded_tiers:
            self._load_tier(RelevanceTier.CRITICAL)

        lines = [
            f"Query: {self.query}",
            f"Results found: {self.total_count()}",
            ""
        ]

        # Show breakdown by tier
        if self._fully_loaded or self._loaded_tiers:
            for tier in [RelevanceTier.CRITICAL, RelevanceTier.RELEVANT, RelevanceTier.CONTEXT]:
                items = self._by_tier.get(tier, [])
                if items:
                    tier_name = tier.value.upper()
                    lines.append(f"[{tier_name}] {len(items)} items")
                    for item in items[:3]:  # Show top 3 per tier
                        formatted = self._item_formatter(item.item)
                        lines.append(f"  - {formatted} (relevance: {item.relevance:.2f})")

        return "\n".join(lines)

    def total_count(self) -> int:
        """
        Get total count of all available items.

        Note: This may trigger a full load if not already loaded.
        For faster counts, use estimate_count().

        Returns:
            Total number of items available
        """
        if not self._fully_loaded:
            self._load_all()
        return len(self._all_items)

    def estimate_count(self) -> int:
        """
        Estimate total count without full load.

        Returns count of currently loaded items.

        Returns:
            Estimated count (may be less than total)
        """
        return len(self._all_items)

    def count_by_tier(self, tier: RelevanceTier) -> int:
        """
        Get count of items in a specific tier.

        Args:
            tier: The tier to count

        Returns:
            Number of items in the tier
        """
        self._load_tier(tier)
        return len(self._by_tier.get(tier, []))

    def get_tier_limits(self) -> TierConfig:
        """Get the tier configuration."""
        return self.config

    def has_more(self, tier: RelevanceTier = RelevanceTier.RELEVANT) -> bool:
        """
        Check if there are more items available in a tier.

        Args:
            tier: The tier to check (default: RELEVANT)

        Returns:
            True if more items are available beyond current limit
        """
        self._load_tier(tier)
        current_count = len(self._by_tier.get(tier, []))
        limit = self.config.get_limit_for_tier(tier)

        # If we hit the limit, there might be more
        return current_count >= limit

    def to_dict(self) -> Dict:
        """
        Convert to dictionary for JSON serialization.

        Returns:
            Dict with query, config, and tier breakdown
        """
        return {
            "query": self.query,
            "total_count": self.estimate_count(),
            "fully_loaded": self._fully_loaded,
            "loaded_tiers": [t.value for t in self._loaded_tiers],
            "config": {
                "critical_limit": self.config.critical_limit,
                "relevant_limit": self.config.relevant_limit,
                "context_limit": self.config.context_limit,
            },
            "tiers": {
                tier.value: {
                    "count": len(self._by_tier.get(tier, [])),
                    "limit": self.config.get_limit_for_tier(tier)
                }
                for tier in RelevanceTier
            }
        }

    def __len__(self) -> int:
        """Get count of currently loaded items."""
        return len(self._all_items)

    def __repr__(self) -> str:
        return f"ChunkedResult(query='{self.query}', loaded={len(self._all_items)})"


class PatternChunkedResult(ChunkedResult):
    """Specialized ChunkedResult for patterns."""

    def __init__(self, query: str, loader: Callable, config: Optional[TierConfig] = None):
        super().__init__(
            query=query,
            loader=loader,
            config=config,
            item_formatter=self._format_pattern
        )

    def _format_pattern(self, pattern: Any) -> str:
        """Format a pattern for display."""
        if isinstance(pattern, dict):
            name = pattern.get("name", "Unknown")
            category = pattern.get("category", "")
            return f"{name} ({category})" if category else name
        return str(pattern)[:50]


class MemoryChunkedResult(ChunkedResult):
    """Specialized ChunkedResult for memory chunks."""

    def __init__(self, query: str, loader: Callable, config: Optional[TierConfig] = None):
        super().__init__(
            query=query,
            loader=loader,
            config=config,
            item_formatter=self._format_memory
        )

    def _format_memory(self, memory: Any) -> str:
        """Format a memory chunk for display."""
        if isinstance(memory, dict):
            metadata = memory.get("metadata", {})
            chunk_id = metadata.get("chunk_id", "Unknown")
            summary = metadata.get("summary", "")[:30]
            return f"{chunk_id}: {summary}..."
        return str(memory)[:50]


def main():
    """CLI for testing chunked results."""
    import argparse

    parser = argparse.ArgumentParser(description="Colony Chunked Result Test")
    parser.add_argument("--test", action="store_true", help="Run test")
    args = parser.parse_args()

    if args.test:
        print("\n🧪 ChunkedResult Test\n")

        # Create a mock loader
        def mock_loader(min_relevance: float, limit: int) -> List[tuple]:
            items = [
                ("High Relevance Item 1", 0.95),
                ("High Relevance Item 2", 0.85),
                ("High Relevance Item 3", 0.75),
                ("Medium Relevance Item 1", 0.55),
                ("Medium Relevance Item 2", 0.45),
                ("Low Relevance Item 1", 0.35),
                ("Low Relevance Item 2", 0.25),
                ("Very Low Relevance Item 1", 0.15),
            ]
            # Filter and limit
            filtered = [(i, r) for i, r in items if r >= min_relevance]
            return filtered[:limit]

        # Test ChunkedResult
        result = ChunkedResult(
            query="test query",
            loader=mock_loader,
            config=TierConfig(
                critical_limit=2,
                relevant_limit=4,
                context_limit=6
            )
        )

        print("📊 Critical items:")
        for item in result.critical():
            print(f"  - {item}")
        print()

        print("📊 Relevant items:")
        for item in result.relevant():
            print(f"  - {item}")
        print()

        print("📊 Summary:")
        print(result.summary())
        print()

        print("📊 Dict representation:")
        import json
        print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
