---
name: colony
description: Enhance native Claude Code teams with reputation tracking, pattern library, and visual monitoring
argument-hint: <command> [options]
user-invocable: true
allowed-tools: TaskCreate, TaskUpdate, TeamCreate, SendMessage, Bash, Skill
context: fork
agent: general-purpose
---

# Colony - Native Team Enhancement

Add memory and learning to Claude Code's native teams.

Colony enhances (doesn't replace) native teams by adding:
- **Reputation tracking** - Know which agents excel at specific tasks
- **Pattern library** - Reuse successful approaches across sessions
- **Chunked memory** - Retrieve relevant conversation history
- **Visual monitoring** - Dashboard to observe team activity

## Quick Start

```bash
# Deploy a team with Colony context
/colony deploy --team code-review --target ./src

# Check reputation scores
/colony reputation

# View dashboard
/colony dashboard

# List patterns
/colony patterns list
```

## Commands

### deploy - Create team with Colony context

```bash
/colony deploy --team <type> --task "<description>" [options]
```

Creates a native team with relevant patterns and memory injected.

**Team types:**
- `code-review` - Security, style, and test coverage review
- `security` - Security vulnerability scan
- `refactor` - Code refactoring

**Options:**
- `--target <path>` - Target directory for the team to work on
- `--patterns` - Force specific pattern category

**Example:**
```bash
/colony deploy --team code-review --task "Review auth module for security issues" --target ./src/auth
```

### reputation - View agent reputations

```bash
/colony reputation [--agent <id>] [--top N]
```

Shows reputation scores and tiers.

**Tiers:** UNKNOWN → NOVICE → CONTRIBUTOR → EXPERT → ELITE

**Examples:**
```bash
/colony reputation              # Show all agents
/colony reputation --top 5      # Top 5 agents
/colony reputation --agent agent-123  # Specific agent
```

### patterns - Manage pattern library

```bash
/colony patterns list [--category <cat>]
/colony patterns search <query>
/colony patterns create --name <name> --category <cat> --keywords <k1 k2...>
```

**Pattern categories:** security, code_review, debugging, refactoring, testing, documentation, optimization, migration

**Examples:**
```bash
/colony patterns list                    # List all patterns
/colony patterns list --category security  # Security patterns only
/colony patterns search "sql injection"    # Find relevant patterns
```

### memory - Manage conversation memory

```bash
/colony memory store --team <id> --messages <file>
/colony memory search <query>
```

Stores and retrieves chunked conversation history using RLM integration.

### dashboard - Launch monitoring dashboard

```bash
/colony dashboard [--port 5001]
```

Opens web UI at http://localhost:5001 with:
- Agent reputation leaderboard
- Pattern library browser
- Active team status
- Memory chunk viewer

### status - Colony status

```bash
/colony status
```

Shows Colony state and statistics:
- Total agents tracked
- Total patterns stored
- Total memory chunks
- Active teams

## What Gets Stored

```
~/.colony/
├── reputation/     # Agent reputation JSON files
├── patterns/       # Reusable patterns by category
├── memory/         # Chunked conversation history
└── dashboard.db    # Dashboard state (optional)
```

## How It Works

```
1. You invoke: /colony deploy --team code-review --task "Review auth module"
2. Colony searches pattern library for relevant approaches
3. Colony retrieves relevant memory chunks from past sessions
4. Colony creates native team with context injected into the prompt
5. Team works using native Claude Code infrastructure
6. Colony updates agent reputations based on task results
7. Colony extracts new patterns from excellent work (automatic)
```

## Integration with Native Teams

Colony ENHANCES native teams, doesn't replace them:

| Feature | Native Teams | Colony Adds |
|---------|--------------|-------------|
| Team creation | TeamCreate API | Context injection |
| Agent coordination | Built-in | Reputation-based selection |
| Task history | Session-only | Persistent patterns + memory |
| Monitoring | CLI only | Visual dashboard |
| Learning | No | Pattern extraction + reputation |

## Examples

### Code Review with Colony

```bash
/colony deploy --team code-review --task "Review payment processing for security" --target ./src/payment
```

Colony will:
1. Find patterns related to payment security, input validation
2. Retrieve memory from previous security reviews
3. Create team with this context pre-loaded
4. Track which agents found the most issues
5. Store successful approaches as patterns

### Security Audit

```bash
/colony deploy --team security --task "Audit entire codebase for OWASP Top 10"
```

### Refactoring

```bash
/colony deploy --team refactor --task "Extract validation logic into shared module" --target ./src
```

## Permissions

Colony requires these tools:
- `TaskCreate` - Create native teams
- `TeamCreate` - Team management
- `Bash` - Run RLM for memory chunking
- `Skill` - Invoke RLM skill

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Skill not found | Run `./install.sh` from colony-skill directory |
| Reputation not updating | Check `~/.colony/reputation/` exists and is writable |
| Patterns not found | Check `~/.colony/patterns/` exists |
| Dashboard won't start | Ensure Flask is installed: `pip install flask` |
| RLM errors | Ensure RLM skill is installed in `~/.claude/skills/rlm/` |

## Version

Colony v0.1.0 - Initial release with core components:
- ReputationTracker (5-tier system)
- PatternLibrary (keyword search)
- NativeTeamWrapper (context injection)
- ChunkedMemory (RLM integration)

## Dependencies

| Dependency | Purpose | Required |
|------------|---------|----------|
| RLM skill | Chunking, summarization | Yes (with fallback) |
| Native teams API | Team creation | Yes |
| Flask | Dashboard | Optional |
