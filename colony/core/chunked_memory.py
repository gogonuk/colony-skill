"""
Chunked Memory for Colony.

Stores and retrieves conversation chunks using RLM for summarization.
Provides fallback to simple fixed-size chunking if RLM is unavailable.
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import List, Dict, Optional, Union
import json
import subprocess
from datetime import datetime


@dataclass
class MemoryChunk:
    """A single chunk of conversation memory."""
    chunk_id: str
    team_id: str
    messages_range: List[int]  # [start, end]
    summary: str
    keywords: List[str]
    timestamp: str
    content: Optional[str] = None  # Optional full content

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        d = asdict(self)
        if self.content is None:
            d.pop('content', None)
        return d


class ChunkedMemory:
    """
    Manages chunked conversation memory.

    Uses RLM (Recursive Language Model) for intelligent chunking and
    summarization, with fallback to simple fixed-size chunking.
    """

    # Default chunk size for fallback mode
    DEFAULT_CHUNK_SIZE = 50

    # Relevance threshold for memory retrieval
    RELEVANCE_THRESHOLD = 0.3

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

    def __init__(self, storage_path: Optional[str] = None, use_rlm: bool = True):
        """
        Initialize the chunked memory manager.

        Args:
            storage_path: Path to store memory data. Defaults to ~/.colony/memory/
            use_rlm: Whether to use RLM for chunking. If True, will attempt to
                    use RLM and fall back to simple chunking if unavailable.
        """
        self.storage_path = Path(storage_path or "~/.colony/memory").expanduser()
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.use_rlm = use_rlm
        self._rlm_available = None  # Cached check

    def store_conversation(
        self,
        team_id: str,
        messages: List[Dict],
        chunk_size: Optional[int] = None
    ) -> str:
        """
        Store conversation in chunks.

        Args:
            team_id: ID of the team this conversation belongs to
            messages: List of message dictionaries
            chunk_size: Override default chunk size (for fallback mode)

        Returns:
            Path to the stored chunks directory
        """
        team_dir = self.storage_path / "conversations" / team_id
        team_dir.mkdir(parents=True, exist_ok=True)

        # Try RLM first if enabled
        if self.use_rlm and self._check_rlm_available():
            chunks_metadata = self._store_with_rlm(team_dir, messages)
        else:
            chunks_metadata = self._store_simple(team_dir, messages, chunk_size)

        # Save index
        index_file = team_dir / "index.json"
        index_data = {
            "team_id": team_id,
            "total_messages": len(messages),
            "total_chunks": len(chunks_metadata),
            "last_updated": datetime.now().isoformat(),
            "chunks": chunks_metadata
        }
        index_file.write_text(json.dumps(index_data, indent=2))

        return str(team_dir)

    def retrieve_relevant(
        self,
        task_description: str,
        team_id: Optional[str] = None,
        limit: int = 3,
        chunked: bool = True
    ) -> Union['MemoryChunkedResult', List[Dict]]:
        """
        Retrieve relevant memory chunks using keyword matching.

        Args:
            task_description: Description of the current task
            team_id: Optional filter for specific team
            limit: Maximum number of chunks to return (for non-chunked mode)
            chunked: If True, return ChunkedResult; if False, return raw list

        Returns:
            MemoryChunkedResult (if chunked=True) or
            List of dicts with keys: metadata, relevance, team_id, content (if chunked=False)
        """
        from .chunked_result import MemoryChunkedResult, TierConfig

        if chunked:
            # Create chunked result with lazy loading
            def loader(min_relevance: float, max_items: int) -> List[tuple[Dict, float]]:
                return self._retrieve_relevant_raw(
                    task_description,
                    team_id,
                    min_relevance=min_relevance,
                    limit=max_items
                )

            return MemoryChunkedResult(
                query=task_description,
                loader=loader,
                config=TierConfig(
                    critical_limit=2,
                    relevant_limit=5,
                    context_limit=10,
                    all_limit=50,
                    critical_min_relevance=0.7,
                    relevant_min_relevance=0.4,
                    context_min_relevance=self.RELEVANCE_THRESHOLD
                )
            )
        else:
            # Legacy behavior: return raw list
            return self._retrieve_relevant_raw(task_description, team_id, limit=limit)

    def _retrieve_relevant_raw(
        self,
        task_description: str,
        team_id: Optional[str] = None,
        min_relevance: float = 0.0,
        limit: int = 50
    ) -> List[Dict]:
        """
        Raw memory retrieval without chunking.

        Args:
            task_description: Description of the current task
            team_id: Optional filter for specific team
            min_relevance: Minimum relevance threshold (default: uses RELEVANCE_THRESHOLD)
            limit: Maximum number of chunks to return

        Returns:
            List of dicts with keys: metadata, relevance, team_id, content
        """
        task_keywords = self._extract_keywords(task_description)
        relevant = []
        threshold = max(min_relevance, self.RELEVANCE_THRESHOLD)

        # Determine search directories
        if team_id:
            search_dirs = [self.storage_path / "conversations" / team_id]
        else:
            search_dirs = list((self.storage_path / "conversations").iterdir())

        for team_dir in search_dirs:
            if not team_dir.is_dir():
                continue

            index_file = team_dir / "index.json"
            if not index_file.exists():
                continue

            try:
                index = json.loads(index_file.read_text())

                for chunk_metadata in index.get("chunks", []):
                    chunk_keywords = chunk_metadata.get("keywords", [])
                    relevance = self._calculate_relevance(task_keywords, chunk_keywords)

                    if relevance >= threshold:
                        # Try to load the chunk content
                        chunk_file = team_dir / f"{chunk_metadata['chunk_id']}.json"
                        content = None
                        if chunk_file.exists():
                            try:
                                chunk_data = json.loads(chunk_file.read_text())
                                content = chunk_data.get("content", chunk_data.get("summary", ""))
                            except (json.JSONDecodeError, IOError):
                                content = chunk_metadata.get("summary", "")

                        relevant.append({
                            "metadata": chunk_metadata,
                            "relevance": relevance,
                            "team_id": index["team_id"],
                            "content": content or chunk_metadata.get("summary", "")
                        })
            except (json.JSONDecodeError, KeyError, IOError):
                continue

        # Sort by relevance and limit
        relevant.sort(key=lambda x: x["relevance"], reverse=True)
        return relevant[:limit]

    def get_conversation_summary(self, team_id: str) -> Optional[Dict]:
        """
        Get summary of a team's conversation.

        Args:
            team_id: ID of the team

        Returns:
            Summary dict with keys: team_id, total_messages, total_chunks, chunks
        """
        index_file = self.storage_path / "conversations" / team_id / "index.json"
        if index_file.exists():
            try:
                return json.loads(index_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass
        return None

    def list_teams(self) -> List[str]:
        """
        List all team IDs that have stored conversations.

        Returns:
            List of team IDs
        """
        teams = []
        conversations_dir = self.storage_path / "conversations"
        if conversations_dir.exists():
            for team_dir in conversations_dir.iterdir():
                if team_dir.is_dir() and (team_dir / "index.json").exists():
                    teams.append(team_dir.name)
        return teams

    def delete_conversation(self, team_id: str) -> bool:
        """
        Delete all stored conversation data for a team.

        Args:
            team_id: ID of the team

        Returns:
            True if deleted, False if not found
        """
        team_dir = self.storage_path / "conversations" / team_id
        if team_dir.exists():
            import shutil
            shutil.rmtree(team_dir)
            return True
        return False

    def _check_rlm_available(self) -> bool:
        """Check if RLM is available (cached result)."""
        if self._rlm_available is not None:
            return self._rlm_available

        # Check if RLM skill exists
        rlm_skill_path = Path.home() / ".claude" / "skills" / "rlm"
        if rlm_skill_path.exists():
            # Try to run RLM to verify it works
            try:
                result = subprocess.run(
                    ["python3", "-c", "import sys; sys.path.insert(0, str(rlm_skill_path)); import rlm"],
                    capture_output=True,
                    timeout=5
                )
                self._rlm_available = result.returncode == 0
                return self._rlm_available
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        self._rlm_available = False
        return False

    def _store_with_rlm(self, team_dir: Path, messages: List[Dict]) -> List[Dict]:
        """Store conversation using RLM for chunking and summarization."""
        # Save messages to temporary file for RLM
        temp_file = team_dir / "_raw_messages.jsonl"
        with open(temp_file, 'w') as f:
            for msg in messages:
                f.write(json.dumps(msg) + '\n')

        rlm_workspace = team_dir / "_rlm_workspace"
        chunks_metadata = []

        # Pre-compute RLM path for f-string
        rlm_path = Path.home() / ".claude" / "skills" / "rlm"

        try:
            # Run RLM with semantic chunking and summarization
            result = subprocess.run([
                "python3", "-c",
                f"""
import sys
import json
sys.path.insert(0, '{rlm_path}')

# Import and use RLM
from rlm import RLMProcessor

messages = []
with open('{temp_file}', 'r') as f:
    for line in f:
        messages.append(json.loads(line))

processor = RLMProcessor()
chunks = processor.process_chunks(
    messages,
    chunk_size=50,
    strategy='semantic',
    summarize=True
)

print(json.dumps(chunks))
"""
            ], capture_output=True, text=True, timeout=300)

            if result.returncode == 0:
                chunks_data = json.loads(result.stdout)
            else:
                # RLM failed, fall back to simple
                return self._store_simple(team_dir, messages)

            # Store chunks
            for i, chunk_data in enumerate(chunks_data):
                chunk_id = f"chunk_{i + 1:03d}"

                chunk = MemoryChunk(
                    chunk_id=chunk_id,
                    team_id=team_dir.name,
                    messages_range=chunk_data.get('range', [0, 0]),
                    summary=chunk_data.get('summary', ''),
                    keywords=self._extract_keywords(chunk_data.get('summary', '')),
                    timestamp=datetime.now().isoformat(),
                    content=chunk_data.get('content', '')
                )

                # Save chunk
                chunk_file = team_dir / f"{chunk_id}.json"
                chunk_file.write_text(json.dumps(chunk.to_dict(), indent=2))

                chunks_metadata.append(chunk.to_dict())

        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError, Exception) as e:
            # RLM unavailable or failed, fall back to simple
            return self._store_simple(team_dir, messages)

        finally:
            # Cleanup temp file
            temp_file.unlink(missing_ok=True)

        return chunks_metadata

    def _store_simple(
        self,
        team_dir: Path,
        messages: List[Dict],
        chunk_size: Optional[int] = None
    ) -> List[Dict]:
        """Store conversation using simple fixed-size chunking."""
        chunk_size = chunk_size or self.DEFAULT_CHUNK_SIZE
        chunks_metadata = []

        for i in range(0, len(messages), chunk_size):
            chunk_messages = messages[i:i + chunk_size]
            chunk_id = f"chunk_{i // chunk_size + 1:03d}"

            # Simple summary: first and last message preview
            first_content = self._get_message_content(chunk_messages[0])[:100] if chunk_messages else ''
            last_content = self._get_message_content(chunk_messages[-1])[:100] if chunk_messages else ''

            summary = f"[{len(chunk_messages)} messages] "
            if first_content:
                summary += f"Start: {first_content}... "
            if last_content:
                summary += f"End: {last_content}..."

            chunk = {
                "chunk_id": chunk_id,
                "team_id": team_dir.name,
                "messages_range": [i, min(i + chunk_size, len(messages))],
                "summary": summary,
                "keywords": self._extract_keywords_from_messages(chunk_messages),
                "timestamp": datetime.now().isoformat()
            }

            # Save chunk
            chunk_file = team_dir / f"{chunk_id}.json"
            chunk_file.write_text(json.dumps({
                **chunk,
                "content": chunk_messages
            }, indent=2))

            chunks_metadata.append(chunk)

        return chunks_metadata

    def _get_message_content(self, message: Dict) -> str:
        """Extract content from a message dict."""
        # Try common content keys
        for key in ['content', 'text', 'message', 'body']:
            if key in message:
                return str(message[key])
        return ''

    def _extract_keywords_from_messages(self, messages: List[Dict]) -> List[str]:
        """Extract keywords from a list of messages."""
        all_text = []
        for msg in messages:
            content = self._get_message_content(msg)
            all_text.append(content)
        return self._extract_keywords(' '.join(all_text))

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.

        Filters out stop words and short words.
        """
        # Convert to lowercase and split
        words = str(text).lower().split()

        # Filter out stop words and short words, clean punctuation
        keywords = []
        for w in words:
            w_clean = w.strip(".,!?;:\"'()[]{}")
            if w_clean not in self.STOP_WORDS and len(w_clean) > 3:
                keywords.append(w_clean)

        # Remove duplicates while preserving order
        seen = set()
        result = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                result.append(kw)

        return result

    def _calculate_relevance(self, task_keywords: List[str], chunk_keywords: List[str]) -> float:
        """
        Calculate relevance using Jaccard similarity.

        Jaccard similarity = |intersection| / |union|
        """
        if not chunk_keywords:
            return 0.0

        task_set = set(kw.lower() for kw in task_keywords)
        chunk_set = set(kw.lower() for kw in chunk_keywords)

        intersection = len(task_set & chunk_set)
        union = len(task_set | chunk_set)

        return intersection / union if union > 0 else 0.0


# CLI helper for testing
def main():
    """Simple CLI for testing chunked memory."""
    import argparse
    import shutil

    parser = argparse.ArgumentParser(description="Colony Chunked Memory")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Store command
    store_parser = subparsers.add_parser("store", help="Store conversation")
    store_parser.add_argument("--team", required=True, help="Team ID")
    store_parser.add_argument("--messages", required=True, help="JSON file with messages")

    # Search command
    search_parser = subparsers.add_parser("search", help="Search memory")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--team", help="Filter by team ID")
    search_parser.add_argument("--limit", type=int, default=3, help="Number of results")

    # List command
    list_parser = subparsers.add_parser("list", help="List teams with conversations")

    # Summary command
    summary_parser = subparsers.add_parser("summary", help="Get conversation summary")
    summary_parser.add_argument("--team", required=True, help="Team ID")

    # Test command
    test_parser = subparsers.add_parser("test", help="Run tests")
    test_parser.add_argument("--no-rlm", action="store_true", help="Disable RLM")

    args = parser.parse_args()

    memory = ChunkedMemory(use_rlm=not getattr(args, 'no_rlm', False))

    if args.command == "store":
        # Load messages from file
        with open(args.messages, 'r') as f:
            messages = json.loads(f.read())

        path = memory.store_conversation(args.team, messages)
        print(f"✅ Stored {len(messages)} messages for team {args.team}")
        print(f"   Location: {path}")

    elif args.command == "search":
        results = memory.retrieve_relevant(args.query, team_id=args.team, limit=args.limit)
        print(f"\n🔍 Found {len(results)} relevant chunks:\n")
        for result in results:
            metadata = result["metadata"]
            print(f"  {metadata['chunk_id']} (team: {result['team_id']})")
            print(f"    Relevance: {result['relevance']:.2f}")
            print(f"    Summary: {metadata['summary'][:100]}...")
            keywords = metadata.get('keywords', [])[:5]
            if keywords:
                print(f"    Keywords: {', '.join(keywords)}")
            print()

    elif args.command == "list":
        teams = memory.list_teams()
        print(f"\n📋 Teams with conversations: {len(teams)}\n")
        for team_id in teams:
            summary = memory.get_conversation_summary(team_id)
            if summary:
                print(f"  {team_id}:")
                print(f"    Messages: {summary['total_messages']}")
                print(f"    Chunks: {summary['total_chunks']}")

    elif args.command == "summary":
        summary = memory.get_conversation_summary(args.team)
        if summary:
            print(f"\n📊 Summary for team: {args.team}\n")
            print(f"  Total messages: {summary['total_messages']}")
            print(f"  Total chunks: {summary['total_chunks']}")
            print(f"  Last updated: {summary.get('last_updated', 'Unknown')}")
        else:
            print(f"❌ No conversation found for team: {args.team}")

    elif args.command == "test":
        print("\n🧪 Testing ChunkedMemory...\n")

        # Create test messages
        test_messages = [
            {"role": "user", "content": "We need to fix the SQL injection vulnerability in the login form"},
            {"role": "assistant", "content": "I'll review the authentication code for SQL injection issues"},
            {"role": "user", "content": "Also check the payment processing for security issues"},
            {"role": "assistant", "content": "I'll audit both the login and payment modules"},
        ] * 20  # 80 messages total

        # Store conversation
        team_id = "test-team"
        print(f"1️⃣ Storing {len(test_messages)} messages...")
        path = memory.store_conversation(team_id, test_messages)
        print(f"   ✅ Stored at: {path}")

        # Get summary
        print(f"\n2️⃣ Getting conversation summary...")
        summary = memory.get_conversation_summary(team_id)
        if summary:
            print(f"   ✅ {summary['total_messages']} messages in {summary['total_chunks']} chunks")

        # Search for relevant chunks
        print(f"\n3️⃣ Searching for 'SQL injection'...")
        results = memory.retrieve_relevant("SQL injection security vulnerability", team_id=team_id)
        print(f"   ✅ Found {len(results)} relevant chunks")
        for result in results[:2]:
            print(f"      - {result['metadata']['summary'][:60]}... (relevance: {result['relevance']:.2f})")

        # List teams
        print(f"\n4️⃣ Listing teams...")
        teams = memory.list_teams()
        print(f"   ✅ Found {len(teams)} team(s)")

        # Cleanup
        print(f"\n5️⃣ Cleaning up test data...")
        memory.delete_conversation(team_id)
        print(f"   ✅ Test data deleted")

        print("\n✅ All tests passed!")

        # Cleanup test directory
        test_dir = memory.storage_path / "conversations" / team_id
        shutil.rmtree(test_dir, ignore_errors=True)


if __name__ == "__main__":
    main()
