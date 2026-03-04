"""
Pattern Extractor for Colony.

Automatically extracts reusable patterns from successful task completions.
Analyzes conversation history, code changes, and task outcomes to identify
approaches that should be captured for future reuse.
"""

import re
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum


class PatternQuality(Enum):
    """Quality level of an extracted pattern."""
    EXCELLENT = 1.0    # High confidence, reusable approach
    GOOD = 0.75        # Likely reusable
    MODERATE = 0.5     # Possibly reusable
    LOW = 0.25         # Uncertain, needs review


@dataclass
class ExtractedPattern:
    """A pattern extracted from successful work."""
    name: str
    category: str
    trigger_keywords: List[str]
    approach: Dict
    lessons_learned: List[str]
    quality: PatternQuality
    source_task_id: str
    source_agent_id: str
    extracted_at: str
    confidence_score: float

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_pattern_dict(self) -> Dict:
        """Convert to format compatible with Pattern class."""
        return {
            "pattern_id": "",
            "name": self.name,
            "category": self.category,
            "trigger_keywords": self.trigger_keywords,
            "approach": self.approach,
            "lessons_learned": self.lessons_learned,
            "usage_count": 0,
            "success_rate": self.confidence_score,
            "created_at": self.extracted_at,
            "last_used": ""
        }


@dataclass
class ExtractionContext:
    """Context for pattern extraction."""
    task_id: str
    task_description: str
    agent_id: str
    outcome: str  # SUCCESS, FAILURE, PARTIAL
    quality_score: float
    messages: List[Dict]
    duration_ms: int
    timestamp: str


class PatternExtractor:
    """
    Extracts patterns from successful task completions.

    Analysis dimensions:
    1. Task characteristics (what was done)
    2. Approach taken (how it was done)
    3. Tools used (what helped)
    4. Lessons learned (what insights emerged)
    """

    # Pattern categories with their trigger words
    CATEGORY_KEYWORDS = {
        "security": [
            "vulnerability", "security", "injection", "xss", "csrf", "auth",
            "authorization", "encryption", "hash", "credential", "attack",
            "mitigation", "owasp", "validation", "sanitization"
        ],
        "code_review": [
            "review", "refactor", "style", "lint", "quality", "standard",
            "convention", "naming", "complexity", "maintainability"
        ],
        "debugging": [
            "debug", "fix", "bug", "error", "issue", "crash", "exception",
            "trace", "log", "diagnose", "troubleshoot"
        ],
        "testing": [
            "test", "spec", "coverage", "mock", "stub", "assertion",
            "unit test", "integration", "e2e", "pytest", "jest"
        ],
        "refactoring": [
            "refactor", "extract", "simplify", "consolidate", "modularize",
            "design pattern", "restructure", "reorganize"
        ],
        "optimization": [
            "optimize", "performance", "cache", "efficient", "speed",
            "latency", "throughput", "bottleneck", "profiling"
        ],
        "documentation": [
            "document", "docstring", "readme", "api doc", "guide",
            "tutorial", "comment", "clarify"
        ],
        "migration": [
            "migrate", "upgrade", "convert", "transition", "port",
            "legacy", "modernize", "compatibility"
        ]
    }

    # Common tool names to detect
    TOOL_PATTERNS = [
        r"\b(grep|ripgrep|rg|ag)\b",
        r"\b(git|github|gitlab)\b",
        r"\b(python|node|npm|pip|yarn)\b",
        r"\b(docker|kubernetes|k8s)\b",
        r"\b(terraform|ansible|puppet)\b",
        r"\b(webpack|vite|rollup)\b",
        r"\b(jest|pytest|unittest)\b",
        r"\b(eslint|prettier|black)\b",
        r"\b(curl|wget|httpie)\b",
        r"\b(redis|postgres|mysql|mongodb)\b"
    ]

    # Step transition words that indicate approach
    STEP_INDICATORS = [
        "first", "then", "next", "after", "finally", "step",
        "approach", "strategy", "method", "process"
    ]

    # Lesson indicator phrases
    LESSON_INDICATORS = [
        "learned", "lesson", "insight", "key takeaway", "important",
        "critical", "essential", "note that", "remember"
    ]

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the pattern extractor.

        Args:
            storage_path: Path to store extracted patterns for review.
                         Defaults to ~/.colony/extracted_patterns/
        """
        self.storage_path = Path(storage_path or "~/.colony/extracted_patterns").expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Store extraction history
        self.history_file = self.storage_path / "extraction_history.json"
        self._history = self._load_history()

    def extract_from_task(
        self,
        context: ExtractionContext,
        min_quality: PatternQuality = PatternQuality.GOOD
    ) -> Optional[ExtractedPattern]:
        """
        Extract a pattern from a completed task.

        Args:
            context: Extraction context with task details
            min_quality: Minimum quality threshold for extraction

        Returns:
            ExtractedPattern if extraction successful, None otherwise
        """
        # Only extract from successful tasks
        if context.outcome != "SUCCESS" or context.quality_score < 0.7:
            return None

        # Analyze the task
        category = self._classify_category(context.task_description, context.messages)
        keywords = self._extract_keywords(context)
        approach = self._extract_approach(context)
        lessons = self._extract_lessons(context)

        if not approach["steps"]:
            # No clear approach detected
            return None

        # Generate pattern name
        name = self._generate_name(context.task_description, category)

        # Calculate quality and confidence
        quality = self._assess_quality(context, approach, lessons)
        confidence = self._calculate_confidence(context, quality)

        if quality.value < min_quality.value:
            return None

        pattern = ExtractedPattern(
            name=name,
            category=category,
            trigger_keywords=keywords,
            approach=approach,
            lessons_learned=lessons,
            quality=quality,
            source_task_id=context.task_id,
            source_agent_id=context.agent_id,
            extracted_at=datetime.now().isoformat(),
            confidence_score=confidence
        )

        # Save for review
        self._save_for_review(pattern)

        return pattern

    def extract_batch(
        self,
        contexts: List[ExtractionContext],
        min_quality: PatternQuality = PatternQuality.GOOD
    ) -> List[ExtractedPattern]:
        """
        Extract patterns from multiple tasks.

        Args:
            contexts: List of extraction contexts
            min_quality: Minimum quality threshold

        Returns:
            List of successfully extracted patterns
        """
        patterns = []
        for context in contexts:
            try:
                pattern = self.extract_from_task(context, min_quality)
                if pattern:
                    patterns.append(pattern)
            except Exception:
                # Continue with other tasks on error
                continue

        return patterns

    def auto_commit_pattern(self, pattern: ExtractedPattern) -> bool:
        """
        Automatically commit an excellent-quality pattern to the library.

        Args:
            pattern: The pattern to commit

        Returns:
            True if committed successfully
        """
        if pattern.quality != PatternQuality.EXCELLENT:
            return False

        from .pattern_library import PatternLibrary
        library = PatternLibrary()

        library.create_pattern(
            name=pattern.name,
            category=pattern.category,
            trigger_keywords=pattern.trigger_keywords,
            approach=pattern.approach,
            lessons_learned=pattern.lessons_learned
        )

        # Record in history
        self._record_commit(pattern)
        return True

    def _classify_category(self, task_description: str, messages: List[Dict]) -> str:
        """Classify task into pattern category."""
        text = task_description.lower()

        # Score each category
        scores = {}
        for category, keywords in self.CATEGORY_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[category] = score

        # Also check message content
        for msg in messages:
            content = self._get_message_content(msg).lower()
            for category, keywords in self.CATEGORY_KEYWORDS.items():
                scores[category] = scores.get(category, 0) + sum(
                    1 for kw in keywords if kw in content
                )

        # Return highest scoring category
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]

        return "code_review"  # Default fallback

    def _extract_keywords(self, context: ExtractionContext) -> List[str]:
        """Extract trigger keywords from context."""
        keywords = set()

        # From task description
        task_words = self._tokenize(context.task_description)
        keywords.update(self._filter_keywords(task_words))

        # From messages
        for msg in context.messages:
            content = self._get_message_content(msg)
            words = self._tokenize(content)
            keywords.update(self._filter_keywords(words))

        # Add category-specific keywords
        category = self._classify_category(context.task_description, context.messages)
        category_kws = [
            kw for kw in self.CATEGORY_KEYWORDS.get(category, [])
            if kw.lower() in context.task_description.lower()
        ]
        keywords.update(category_kws)

        return list(keywords)[:15]  # Limit to 15 most relevant

    def _extract_approach(self, context: ExtractionContext) -> Dict:
        """Extract the approach taken from messages."""
        approach = {
            "steps": [],
            "tools": [],
            "focus_areas": []
        }

        # Analyze messages for steps
        for i, msg in enumerate(context.messages):
            content = self._get_message_content(msg)
            lines = content.split("\n")

            for line in lines:
                line_lower = line.lower().strip()

                # Detect numbered steps
                step_match = re.match(r"^(\d+[\.)]\s*|[-\*]\s*)(.+)", line.strip())
                if step_match:
                    step_text = step_match.group(2)
                    if len(step_text) > 10:  # Ignore very short items
                        approach["steps"].append(step_text.strip())

                # Detect tool usage
                for tool_pattern in self.TOOL_PATTERNS:
                    if re.search(tool_pattern, line_lower):
                        tool_name = re.search(tool_pattern, line_lower).group(0)
                        if tool_name not in approach["tools"]:
                            approach["tools"].append(tool_name)

                # Detect focus areas from common phrases
                for indicator in self.STEP_INDICATORS:
                    if indicator in line_lower and len(line.strip()) > 20:
                        if line.strip() not in approach["steps"]:
                            approach["steps"].append(line.strip())

        # Deduplicate and limit
        approach["steps"] = list(dict.fromkeys(approach["steps"]))[:5]
        approach["tools"] = list(set(approach["tools"]))[:5]

        # Infer focus areas from steps and tools
        if "security" in context.task_description.lower():
            approach["focus_areas"].append("security")
        if "performance" in context.task_description.lower():
            approach["focus_areas"].append("performance")
        if "test" in context.task_description.lower():
            approach["focus_areas"].append("testing")

        return approach

    def _extract_lessons(self, context: ExtractionContext) -> List[str]:
        """Extract lessons learned from messages."""
        lessons = []

        for msg in context.messages:
            content = self._get_message_content(msg)

            # Look for lesson indicator phrases
            for indicator in self.LESSON_INDICATORS:
                if indicator.lower() in content.lower():
                    # Extract sentences containing the indicator
                    sentences = re.split(r"[.!?]+", content)
                    for sentence in sentences:
                        if indicator.lower() in sentence.lower():
                            cleaned = sentence.strip()
                            if len(cleaned) > 15 and len(cleaned) < 200:
                                if cleaned not in lessons:
                                    lessons.append(cleaned)

        # Also check task outcome for implicit lessons
        if context.quality_score >= 0.9:
            lessons.append(f"High-quality outcome achieved ({context.quality_score:.0%})")

        return lessons[:3]  # Limit to top 3 lessons

    def _assess_quality(
        self,
        context: ExtractionContext,
        approach: Dict,
        lessons: List[str]
    ) -> PatternQuality:
        """Assess the quality of the extracted pattern."""
        score = 0

        # High-quality outcome
        if context.quality_score >= 0.95:
            score += 3
        elif context.quality_score >= 0.85:
            score += 2
        elif context.quality_score >= 0.7:
            score += 1

        # Clear approach structure
        if len(approach["steps"]) >= 3:
            score += 2
        elif len(approach["steps"]) >= 2:
            score += 1

        # Tools identified
        if approach["tools"]:
            score += 1

        # Lessons learned
        if len(lessons) >= 2:
            score += 1
        elif len(lessons) >= 1:
            score += 0.5

        # Message depth (enough context)
        if len(context.messages) >= 5:
            score += 1

        # Map score to quality
        if score >= 7:
            return PatternQuality.EXCELLENT
        elif score >= 5:
            return PatternQuality.GOOD
        elif score >= 3:
            return PatternQuality.MODERATE
        else:
            return PatternQuality.LOW

    def _calculate_confidence(self, context: ExtractionContext, quality: PatternQuality) -> float:
        """Calculate confidence score for the pattern."""
        base_confidence = quality.value

        # Adjust based on agent reputation (if available)
        from .reputation_tracker import ReputationTracker
        tracker = ReputationTracker()
        reputation = tracker.get_reputation(context.agent_id)

        if reputation:
            # Boost confidence for high-tier agents
            tier_multiplier = {
                "ELITE": 1.2,
                "EXPERT": 1.1,
                "CONTRIBUTOR": 1.0,
                "NOVICE": 0.9,
                "UNKNOWN": 0.8
            }
            multiplier = tier_multiplier.get(reputation.tier, 1.0)
            base_confidence = min(1.0, base_confidence * multiplier)

        return round(base_confidence, 2)

    def _generate_name(self, task_description: str, category: str) -> str:
        """Generate a descriptive pattern name."""
        # Remove common prefixes
        desc = task_description.lower()
        for prefix in ["implement", "create", "add", "fix", "update"]:
            if desc.startswith(prefix):
                desc = desc[len(prefix):].strip()

        # Capitalize first letters
        name = " ".join(w.capitalize() for w in desc.split()[:5])

        # Add category prefix if not already clear
        if category not in name.lower():
            category_name = category.replace("_", " ").capitalize()
            name = f"{category_name}: {name}"

        return name

    def _get_message_content(self, message: Dict) -> str:
        """Extract content from a message dict."""
        for key in ["content", "text", "message", "body"]:
            if key in message:
                return str(message[key])
        return ""

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into words."""
        # Remove punctuation and split
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        return cleaned.split()

    def _filter_keywords(self, words: List[str]) -> Set[str]:
        """Filter meaningful keywords from word list."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "for", "with", "from",
            "this", "that", "have", "has", "had", "will", "would", "could",
            "should", "into", "over", "under", "after", "before", "when",
            "where", "how", "what", "which", "their", "there", "were", "been"
        }

        filtered = set()
        for word in words:
            if len(word) > 3 and word not in stop_words:
                filtered.add(word)

        return filtered

    def _save_for_review(self, pattern: ExtractedPattern):
        """Save extracted pattern for human review."""
        # Create file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{pattern.category}_{timestamp}.json"
        filepath = self.storage_path / filename

        # Convert to dict with quality as string for JSON serialization
        data = pattern.to_dict()
        data["quality"] = pattern.quality.name  # Convert enum to string
        filepath.write_text(json.dumps(data, indent=2))

    def _load_history(self) -> Dict:
        """Load extraction history."""
        if self.history_file.exists():
            try:
                return json.loads(self.history_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return {"committed": [], "extracted": []}

    def _record_commit(self, pattern: ExtractedPattern):
        """Record pattern commit in history."""
        self._history["committed"].append({
            "name": pattern.name,
            "category": pattern.category,
            "source_task": pattern.source_task_id,
            "timestamp": datetime.now().isoformat()
        })
        self.history_file.write_text(json.dumps(self._history, indent=2))

    def list_pending_review(self) -> List[Dict]:
        """List patterns awaiting review."""
        pending = []
        for file in self.storage_path.glob("*.json"):
            if file.name == "extraction_history.json":
                continue

            try:
                data = json.loads(file.read_text())
                # Convert quality string back to enum for proper display
                if "quality" in data and isinstance(data["quality"], str):
                    try:
                        data["quality"] = PatternQuality[data["quality"]].name
                    except KeyError:
                        pass
                pending.append(data)
            except (json.JSONDecodeError, IOError):
                continue

        return sorted(pending, key=lambda x: x.get("extracted_at", ""), reverse=True)

    def approve_pattern(self, filename: str) -> bool:
        """
        Approve a pending pattern and add to library.

        Args:
            filename: Name of the pending pattern file

        Returns:
            True if approved successfully
        """
        filepath = self.storage_path / filename
        if not filepath.exists():
            return False

        try:
            data = json.loads(filepath.read_text())
            # Convert quality string back to enum
            if "quality" in data and isinstance(data["quality"], str):
                data["quality"] = PatternQuality[data["quality"]]
            pattern = ExtractedPattern(**data)

            from .pattern_library import PatternLibrary
            library = PatternLibrary()

            library.create_pattern(
                name=pattern.name,
                category=pattern.category,
                trigger_keywords=pattern.trigger_keywords,
                approach=pattern.approach,
                lessons_learned=pattern.lessons_learned
            )

            # Remove from pending and record
            filepath.unlink()
            self._record_commit(pattern)
            return True

        except (json.JSONDecodeError, TypeError, IOError):
            return False

    def reject_pattern(self, filename: str) -> bool:
        """Reject a pending pattern."""
        filepath = self.storage_path / filename
        if filepath.exists():
            filepath.unlink()
            return True
        return False


def main():
    """CLI for testing pattern extraction."""
    import argparse

    parser = argparse.ArgumentParser(description="Colony Pattern Extractor")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List pending command
    subparsers.add_parser("list", help="List pending patterns")

    # Approve command
    approve_parser = subparsers.add_parser("approve", help="Approve a pattern")
    approve_parser.add_argument("filename", help="Pattern file to approve")

    # Reject command
    reject_parser = subparsers.add_parser("reject", help="Reject a pattern")
    reject_parser.add_argument("filename", help="Pattern file to reject")

    # Auto-commit command
    subparsers.add_parser("auto-commit", help="Auto-commit excellent patterns")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run extraction test")
    test_parser.add_argument("--task", default="Fix SQL injection in login form",
                           help="Test task description")

    args = parser.parse_args()

    extractor = PatternExtractor()

    if args.command == "list":
        pending = extractor.list_pending_review()
        print(f"\n📋 Pending patterns: {len(pending)}\n")
        for p in pending:
            print(f"  {p['name']} ({p['category']})")
            print(f"    Quality: {p['quality']}")
            print(f"    From: {p['source_task_id']}\n")

    elif args.command == "approve":
        if extractor.approve_pattern(args.filename):
            print(f"✅ Approved and committed: {args.filename}")
        else:
            print(f"❌ Failed to approve: {args.filename}")

    elif args.command == "reject":
        if extractor.reject_pattern(args.filename):
            print(f"🗑️ Rejected: {args.filename}")
        else:
            print(f"❌ Failed to reject: {args.filename}")

    elif args.command == "auto-commit":
        pending = extractor.list_pending_review()
        committed = 0
        for p in pending:
            pattern = ExtractedPattern(**p)
            if extractor.auto_commit_pattern(pattern):
                committed += 1
        print(f"✅ Auto-committed {committed} excellent patterns")

    elif args.command == "test":
        # Create test context
        context = ExtractionContext(
            task_id="test-001",
            task_description=args.task,
            agent_id="test-agent",
            outcome="SUCCESS",
            quality_score=0.95,
            messages=[
                {"role": "user", "content": "We need to fix the SQL injection vulnerability"},
                {"role": "assistant", "content": "I'll use parameterized queries to prevent injection"},
                {"role": "user", "content": "Great, also add input validation"},
                {"role": "assistant", "content": "Adding validation for all user inputs"},
                {"role": "assistant", "content": "The fix is complete with: 1) Parameterized queries 2) Input validation 3) Output encoding"},
            ],
            duration_ms=5000,
            timestamp=datetime.now().isoformat()
        )

        pattern = extractor.extract_from_task(context)
        if pattern:
            print(f"\n✅ Extracted pattern:\n")
            print(f"  Name: {pattern.name}")
            print(f"  Category: {pattern.category}")
            print(f"  Quality: {pattern.quality}")
            print(f"  Steps: {pattern.approach['steps']}")
            print(f"  Keywords: {pattern.trigger_keywords[:5]}")
            print(f"  Lessons: {pattern.lessons_learned}")
        else:
            print("\n❌ No pattern extracted")

        # Show pending
        pending = extractor.list_pending_review()
        print(f"\n📋 Pending patterns: {len(pending)}")


if __name__ == "__main__":
    main()
