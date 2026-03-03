<div align="center">

# 🐝 Colony

### Native Team Enhancement for Claude Code

*Add memory and learning to Claude Code's native teams*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-0.1.0-blue.svg)](https://github.com/gogonuk/colony-skill)
[![LOC](https://img.shields.io/badge/LOC-1,651-green.svg)](https://github.com/gogonuk/colony-skill)

---

**Colony enhances (doesn't replace) native Claude Code teams with:**

📈 **Reputation Tracking** — Know which agents excel at specific tasks (5-tier system)

📚 **Pattern Library** — Reuse successful approaches across sessions

🧠 **Chunked Memory** — Retrieve relevant conversation history (RLM integration)

📊 **Visual Monitoring** — Dashboard to observe team activity

---

[Quick Start](#-quick-start) • [Commands](#-commands) • [Examples](#-examples) • [Architecture](#-architecture)

</div>

---

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/gogonuk/colony-skill.git
cd colony-skill

# Run the installer
./install.sh
```

That's it! Colony is now installed and ready to use.

### Verify Installation

```bash
/colony status
```

You should see:

```
╔════════════════════════════════════════════════════════════╗
║                    📊 Colony Status                        ║
╠════════════════════════════════════════════════════════════╣
║  📈 Reputation: No agents tracked yet                      ║
║  📚 Patterns: No patterns stored yet                       ║
║  🧠 Memory: No conversations stored yet                   ║
║  💾 Storage: ~/.colony/                                   ║
╚════════════════════════════════════════════════════════════╝
```

---

## 📖 Commands

| Command | Description | Example |
|:--------|:------------|:---------|
| `status` | Show Colony status and statistics | `/colony status` |
| `reputation` | View agent reputations and tiers | `/colony reputation --top 5` |
| `patterns list` | Browse pattern library | `/colony patterns list --category security` |
| `patterns search <query>` | Find relevant patterns | `/colony patterns search "sql injection"` |
| `deploy --team <type> --task "<desc>"` | Create team with Colony context | `/colony deploy --team code-review --task "Review auth"` |
| `memory search <query>` | Search conversation memory | `/colony memory search "previous reviews"` |
| `dashboard` | Launch monitoring dashboard | `/colony dashboard --port 5001` |

---

## 🎯 Team Types

```
┌─────────────────┐
│  code-review    │  Security, style, and test coverage review
├─────────────────┤
│  security       │  Security vulnerability scan
├─────────────────┤
│  refactor       │  Code refactoring
└─────────────────┘
```

---

## 💡 Examples

### Example 1: Code Review with Colony

```bash
/colony deploy --team code-review --task "Review authentication module for SQL injection vulnerabilities"
```

**What Colony does:**

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Searching Pattern Library...                            │
│  ✓ Found: "SQL Injection Prevention"                       │
│  ✓ Found: "Authentication Security Review"                 │
│                                                             │
│  🔍 Searching Conversation Memory...                        │
│  ✓ Found: 2 relevant chunks from previous security reviews│
│                                                             │
│  👥 Building Team with Enhanced Context...                 │
│  ✓ Patterns injected into team prompt                      │
│  ✓ Memory chunks included for context                      │
│  ✓ Top agents recommended based on reputation              │
└─────────────────────────────────────────────────────────────┘
```

### Example 2: Security Audit

```bash
/colony deploy --team security --task "Audit payment processing for OWASP Top 10"
```

### Example 3: Check Agent Performance

```bash
/colony reputation
```

**Output:**

```
╔════════════════════════════════════════════════════════════╗
║                 📈 Agent Reputations                       ║
╠════════════════════════════════════════════════════════════╣
║                                                          ║
║  1. 🌟 security-analyst@auth-review                       ║
║     Tier: ELITE                                           ║
║     Score: 0.96                                           ║
║     Tasks: 12 (11 successful)                             ║
║                                                          ║
║  2. 💎 code-reviewer@payment-module                       ║
║     Tier: EXPERT                                          ║
║     Score: 0.82                                           ║
║     Tasks: 8 (7 successful)                               ║
║                                                          ║
╚════════════════════════════════════════════════════════════╝
```

---

## 🏗️ Architecture

```
╔═══════════════════════════════════════════════════════════════════════╗
║                            COLONY SKILL                                ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              ║
║  │   REPUTATION  │    │   PATTERN    │    │    MEMORY    │              ║
║  │   TRACKER     │    │   LIBRARY    │    │   CHUNKER    │              ║
║  │              │    │              │    │              │              ║
║  │  5-tier sys  │    │  Keyword srch│    │  RLM + fall  │              ║
║  │  276 LOC     │    │  409 LOC     │    │  560 LOC     │              ║
║  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘              ║
║         │                   │                   │                       ║
║         └───────────────────┼───────────────────┘                       ║
║                             │                                           ║
║                    ┌────────▼────────┐                                ║
║                    │ NATIVE WRAPPER  │                                ║
║                    │  403 LOC        │                                ║
║                    └────────┬────────┘                                ║
║                             │                                           ║
║                             ▼                                           ║
║              ┌────────────────────────────┐                           ║
║              │   NATIVE TEAM API          │                           ║
║              │   (TaskCreate, TeamCreate) │                           ║
║              └────────────────────────────┘                           ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════╣
║                        DATA STORAGE                                    ║
║                                                                         ║
║   ~/.colony/reputation/  →  Agent reputation JSON files                 ║
║   ~/.colony/patterns/    →  Pattern library by category                 ║
║   ~/.colony/memory/      →  Chunked conversation history                ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## 📊 Components

### ReputationTracker (276 LOC)

<div align="center">

```
UNKNOWN ──► NOVICE ──► CONTRIBUTOR ──► EXPERT ──► ELITE
   │            │           │             │          │
   ▼            ▼           ▼             ▼          ▼
 < 3 tasks   score < 0.4  score < 0.6  score < 0.8  score ≥ 0.8
```

</div>

**Features:**
- Composite scoring: 60% success rate + 40% quality
- Task history tracking (last 10 events)
- Top agents ranking

### PatternLibrary (409 LOC)

**Categories:**
- `security` — Security vulnerabilities and fixes
- `code_review` — Code review approaches
- `debugging` — Debugging strategies
- `refactoring` — Refactoring patterns
- `testing` — Testing approaches
- `documentation` — Documentation patterns
- `optimization` — Performance optimization
- `migration` — API/library migrations

**Features:**
- Jaccard similarity search
- Pattern usage tracking
- Success rate calculation

### ChunkedMemory (560 LOC)

**Features:**
- RLM integration for semantic chunking
- Fallback to fixed-size chunking
- Keyword-based memory retrieval
- Automatic index management

### NativeTeamWrapper (403 LOC)

**Features:**
- Pre-built team templates
- Context injection for patterns/memory
- Native team state reading
- Custom template creation

---

## 📂 Storage Structure

```
~/.colony/
├── reputation/              # Agent reputation data
│   ├── agent-1.json
│   └── agent-2.json
│
├── patterns/                # Pattern library
│   ├── security/
│   │   ├── sql-injection.json
│   │   └── auth-review.json
│   └── code_review/
│       └── checklist.json
│
└── memory/                  # Chunked conversations
    └── conversations/
        ├── team-a/
        │   ├── index.json
        │   ├── chunk_001.json
        │   └── chunk_002.json
        └── team-b/
            └── index.json
```

---

## 🔧 Backup & Restore

### Backup

```bash
cd ~/dev_projects/colony-skill
./backup.sh
```

Creates: `~/colony-backup/colony-YYYYMMDD_HHMMSS.tar.gz`

Keeps last 5 backups automatically.

### Restore

```bash
tar -xzf ~/colony-backup/colony-20260304_030827.tar.gz -C /
```

---

## 🎓 Tutorial: Using Colony

### Step 1: Check Status

```bash
/colony status
```

### Step 2: Deploy Your First Team

```bash
/colony deploy --team code-review --task "Review the login form for security issues"
```

### Step 3: View Results

```bash
/colony reputation
```

### Step 4: Search Patterns

```bash
/colony patterns search "security"
```

### Step 5: Search Memory

```bash
/colony memory search "login form"
```

---

## 📈 How Colony Works

```
┌─────────────────────────────────────────────────────────────────┐
│                     WORKFLOW                                    │
└─────────────────────────────────────────────────────────────────┘

1. YOU INVOKE COLONY
   │
   ├─► /colony deploy --team code-review --task "Review auth"
   │
2. COLONY PROCESSES
   │
   ├─► Searches pattern library for relevant approaches
   ├─► Retrieves relevant memory chunks from past sessions
   ├─► Identifies top agents based on reputation
   │
3. COLONY ENHANCES TEAM
   │
   ├─► Creates native team via TaskCreate
   ├─► Injects patterns and memory into team prompt
   ├─► Tracks agent IDs for reputation updates
   │
4. TEAM WORKS
   │
   ├─► Native team executes task with enhanced context
   │
5. COLONY LEARNS
   │
   ├─► Records task completion and quality
   ├─► Updates agent reputation scores
   └─► Extracts new patterns from excellent work
```

---

## 🔌 Dependencies

| Dependency | Purpose | Required |
|:-----------|:---------|:---------|
| **RLM skill** | Chunking, summarization | Optional (fallback included) |
| **Native teams API** | Team creation | Yes |
| **Flask** | Dashboard | Optional |

---

## 📊 Stats

<div align="center">

```
╔══════════════════════════════════════════════════════╗
║              COLONY v0.1.0                          ║
╠══════════════════════════════════════════════════════╣
║                                                     ║
║  📦 Core Components:     1,651 LOC                  ║
║  📄 Documentation:        352 LOC                   ║
║  🔧 Scripts:             189 LOC                   ║
║  ─────────────────────────────────                  ║
║  📊 Total:              2,192 LOC                   ║
║                                                     ║
║  🎯 Focus:            ~80% smaller than Alpha      ║
║  ⚡ Speed:            Focused, modular design      ║
║  🛠️  Maintenance:      Clean separation of concerns║
║                                                     ║
╚══════════════════════════════════════════════════════╝
```

</div>

---

## 🤝 Contributing

Contributions welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - see LICENSE file for details

---

## 🙏 Acknowledgments

- Built for Claude Code's native teams feature
- RLM skill for intelligent chunking
- Colony Alpha as inspiration

---

<div align="center">

**Made with ❤️ for the Claude Code community**

[GitHub](https://github.com/gogonuk/colony-skill) • [Issues](https://github.com/gogonuk/colony-skill/issues) • [Releases](https://github.com/gogonuk/colony-skill/releases)

</div>
