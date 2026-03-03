# Colony - Native Team Enhancement for Claude Code

Add memory and learning to Claude Code's native teams.

## Overview

Colony enhances (doesn't replace) native Claude Code teams by adding:

- **Reputation Tracking** - Know which agents excel at specific tasks (5-tier system)
- **Pattern Library** - Reuse successful approaches across sessions
- **Chunked Memory** - Retrieve relevant conversation history (RLM integration)
- **Visual Monitoring** - Dashboard to observe team activity

## Quick Start

```bash
# Install the skill
cd ~/dev_projects/colony-skill
./install.sh

# Use with Claude Code
/colony status
/colony deploy --team code-review --task "Review auth module"
```

## Commands

| Command | Description |
|---------|-------------|
| `/colony status` | Show Colony status and statistics |
| `/colony reputation` | View agent reputations and tiers |
| `/colony patterns list` | Browse pattern library |
| `/colony patterns search <query>` | Find relevant patterns |
| `/colony deploy --team <type> --task "<desc>"` | Create team with Colony context |
| `/colony memory search <query>` | Search conversation memory |
| `/colony dashboard` | Launch monitoring dashboard |

## Team Types

- `code-review` - Security, style, and test coverage review
- `security` - Security vulnerability scan
- `refactor` - Code refactoring

## Storage

Colony stores data in `~/.colony/`:

```
~/.colony/
├── reputation/     # Agent reputation JSON files
├── patterns/       # Reusable patterns by category
├── memory/         # Chunked conversation history
└── dashboard.db    # Dashboard state (optional)
```

## Architecture

```
colony/
├── core/
│   ├── reputation_tracker.py    # 5-tier reputation system
│   ├── pattern_library.py       # Pattern storage & search
│   ├── chunked_memory.py        # RLM-based memory chunking
│   └── native_wrapper.py        # Native team integration
├── SKILL.md                      # Claude Code skill definition
└── scripts/                      # Utility scripts
```

## Components

### ReputationTracker
- 5-tier system: UNKNOWN → NOVICE → CONTRIBUTOR → EXPERT → ELITE
- Composite scoring: 60% success rate + 40% quality
- Tracks task completion history

### PatternLibrary
- Keyword-based search using Jaccard similarity
- Pattern categories: security, code_review, debugging, refactoring, etc.
- Usage tracking and success rate calculation

### ChunkedMemory
- RLM integration for semantic chunking (optional)
- Fallback to fixed-size chunking
- Keyword-based memory retrieval

### NativeTeamWrapper
- Pre-built team templates (code-review, security, refactor)
- Context injection for patterns and memory
- Reads native team state from `~/.claude/teams/`

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| RLM skill | Chunking, summarization | Optional (with fallback) |
| Native teams API | Team creation | Yes |
| Flask | Dashboard | Optional |

## Development

```bash
# Test components
python3 colony/core/reputation_tracker.py list
python3 colony/core/pattern_library.py list
python3 colony/core/chunked_memory.py test

# Run all tests
bash run_tests.sh
```

## Backup & Restore

```bash
# Backup
./backup.sh

# Restore
tar -xzf ~/colony-backup/colony-YYYYMMDD_HHMMSS.tar.gz -C /
```

## Version

Colony v0.1.0 - Initial release

## License

MIT

## Contributing

Contributions welcome! Please read the contributing guidelines before submitting PRs.
