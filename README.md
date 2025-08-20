# 🏈 FantasyAgent - Multi-Platform Draft Assistant

**AI-powered fantasy football draft assistant supporting Sleeper and Yahoo leagues**

[![Multi-Agent AI](https://img.shields.io/badge/AI-Claude%204%20Sonnet-blue.svg)](https://github.com/adamrubinsky/FantasyAgent)
[![Platforms](https://img.shields.io/badge/Platforms-Sleeper%20%7C%20Yahoo-purple.svg)]()
[![API Status](https://img.shields.io/badge/APIs-Sleeper%20%2B%20FantasyPros-brightgreen.svg)]()
[![Performance](https://img.shields.io/badge/Sleeper-15s%20|%20Yahoo-<3s-green.svg)]()

---

## 🎯 Project Overview

A unified fantasy football draft assistant supporting **multiple platforms and league types**. Powered by CrewAI (Sleeper) and LangGraph (Yahoo) multi-agent systems with Claude AI integration.

### 📅 Development Phases

| Phase | Dates | Platform | Draft Type | Status |
|-------|-------|----------|------------|--------|
| **Phase 1** | Aug 5-14 | Sleeper | Snake (SUPERFLEX) | ✅ Completed (Live draft success!) |
| **Phase 2** | Aug 14-19 | Yahoo | Snake (Full PPR) | 🔄 Current Phase |
| **Phase 3** | Aug 20-24 | Sleeper | Auction ($200) | 📅 Upcoming |

### 🎮 Supported Platforms & Leagues

#### Sleeper (Production Ready ✅)
- **Snake Draft**: 12-team, Half-PPR, SUPERFLEX position
  - Status: Successfully used in live draft (Aug 12)
  - Framework: CrewAI with 4 specialized agents
  - Response Time: 15 seconds
- **Auction Draft**: 12-team, Half-PPR, $200 budget
  - Status: Scheduled for Aug 24
  - Framework: CrewAI with value optimization

#### Yahoo (In Development 🔄)
- **Snake Draft**: 10-team, Full PPR, 6PT passing TDs
  - Status: Ready for testing (Aug 19)
  - Framework: LangGraph for <3s response
  - Features: Return yards scoring (25 yards/point)

### ✨ Key Features
- 🎨 **Unified Interface** with platform detection
- 🤖 **Dual AI Systems**: CrewAI (Sleeper) + LangGraph (Yahoo)
- 🏈 **11,389 unified player IDs** across all platforms
- 📊 **Real-time draft monitoring** with WebSocket support
- 🎯 **Proactive recommendations** at 6, 3, and 0 picks ahead
- 📈 **Keeper value scoring** with graduated blending
- 🔄 **MCP Integration** for FantasyPros data
- 🌐 **Web interface** at http://localhost:3001 (unified)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Sleeper/Yahoo account with league access
- Anthropic API key (for Claude)
- FantasyPros MCP server configured

### Installation

```bash
# Clone the repository
git clone https://github.com/adamrubinsky/FantasyAgent.git
cd FantasyAgent

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env.local
```

### Configuration

Edit `.env.local` with your credentials:
```env
# Sleeper (no auth needed, just username)
SLEEPER_USERNAME=your-username
SLEEPER_LEAGUE_ID=your-league-id

# Anthropic Claude API (required)
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Yahoo (for OAuth)
YAHOO_CLIENT_ID=your-client-id
YAHOO_CLIENT_SECRET=your-client-secret
```

### Running the Assistant

```bash
# Start unified server (recommended)
python3 unified_server.py
# Access at: http://localhost:3001

# Or use development server for testing
python3 dev_server.py
# Access at: http://localhost:3000
```

---

## 🏗️ System Architecture

### Directory Structure (Phase 2 Day 4 - Reorganized)

```
FantasyAgent/
├── 🚀 Core Entry Points
│   ├── unified_server.py       # Main unified server
│   ├── dev_server.py           # Development server
│   └── main.py                 # CLI entry point
│
├── 📂 platforms/               # Platform-specific code
│   ├── sleeper/                # Sleeper (PRODUCTION)
│   │   └── agents/             # CrewAI agents
│   │       └── draft_crew.py   # 4-agent system
│   ├── yahoo/                  # Yahoo (DEVELOPMENT)
│   │   └── agents/             # LangGraph agents
│   │       └── yahoo_snake_agent.py  # Snake draft only
│   └── shared/                 # Shared utilities
│
├── 📂 core/                    # Core functionality
│   ├── official_fantasypros.py # MCP integration
│   ├── rankings_manager.py     # Caching (30-min TTL)
│   └── draft_monitor.py        # Real-time tracking
│
├── 📂 tests/                   # All test files
│   └── yahoo/                  # Yahoo-specific tests
│
├── 📂 data/                    # Data and mappings
│   └── unified_player_mapping.json # 11,389 players
│
└── 📂 archive/                 # Old code (archived)
```

### Data Flow Architecture

```
User Request
    ↓
unified_server.py (Platform Detection)
    ↓
┌─────────────┴─────────────┐
│                           │
Sleeper Platform      Yahoo Platform
    ↓                       ↓
CrewAI Agents         LangGraph Agents
(15s response)        (<3s response)
    ↓                       ↓
└─────────────┬─────────────┘
              ↓
       MCP Integration
              ↓
      FantasyPros API
              ↓
         Response
```

---

## 📊 Key Components

### 1. Unified Player Mapping System
- **11,389 players** mapped across all platforms
- Solves ID mismatch issues (Sleeper '4984' ↔ FantasyPros '17298')
- Enables robust cross-platform filtering

### 2. Platform-Specific Agents

#### Sleeper Agent (`platforms/sleeper/agents/draft_crew.py`)
```python
# 4 specialized CrewAI agents:
1. Value Analyst - Identifies best value picks
2. Position Strategist - Manages roster balance
3. Risk Assessor - Evaluates player risks
4. Final Recommender - Synthesizes recommendations
```

#### Yahoo Agent (`platforms/yahoo/agents/yahoo_snake_agent.py`)
```python
# LangGraph state machine for <3s response:
- Parallel analysis execution
- Smart conditional routing
- Haiku for speed, Sonnet for synthesis
- Full PPR + Return yards adjustments
```

### 3. Proactive Recommendations
- **6 picks ahead**: Initial analysis
- **3 picks ahead**: Refined recommendations
- **0 picks (your turn)**: 5-second instant analysis
- Shows reasoning and alternatives

---

## 🎮 Usage Guide

### Starting a Draft Session

1. **Start server**: `python3 unified_server.py`
2. **Open browser**: http://localhost:3001
3. **Select platform**: Sleeper or Yahoo
4. **Enter draft ID**: Your draft room ID
5. **Get recommendations**: Real-time AI assistance

### Example Questions
- "Who should I draft next?"
- "Compare Josh Allen vs Lamar Jackson"
- "What RBs are available?"
- "Should I reach for my watchlist player?"
- "What's my roster weakness?"

---

## 📈 Performance Metrics

| Metric | Sleeper | Yahoo |
|--------|---------|-------|
| Response Time | 15 seconds (achieved) | <3 seconds (target) |
| API Latency | <500ms | <1s |
| Cache Hit Rate | >90% | >90% |
| Player Database | 11,389 unified IDs | Same |
| Accuracy | Production tested ✅ | In testing 🔄 |

---

## 🔧 Recent Updates (Phase 2 Day 4 - Aug 18)

### ✅ Completed Today
1. **Project Reorganization**: Complete file structure cleanup
2. **Import Path Fixes**: All using `platforms/` structure now
3. **Context Fix**: CrewAI now receives full draft data (draft_picks, available_players)
4. **Documentation**: Updated PROJECT_STRUCTURE.md, ARCHITECTURE.md
5. **Archive**: Old files moved to archive folders

### 🔄 Current Focus (Phase 2)
- Yahoo Snake draft preparation for Aug 19
- Testing <3s response times with LangGraph
- Full PPR + return yards scoring adjustments

---

## 📅 Upcoming Drafts

| Date | Platform | Type | League | Key Settings |
|------|----------|------|--------|--------------|
| **Aug 19** | Yahoo | Snake | League 2 | 10-team, Full PPR, 6PT Pass TD, Return yards |
| **Aug 24** | Sleeper | Auction | League 3 | 12-team, Half PPR, $200 budget, NO KICKER |

---

## 🗺️ Development Roadmap

### Phase 1 (Aug 5-14) - Sleeper Snake ✅
- [x] CrewAI integration
- [x] SUPERFLEX rankings (OP position)
- [x] Real-time draft monitoring
- [x] Proactive recommendations
- [x] **Live draft success!** (Aug 12)

### Phase 2 (Aug 14-19) - Yahoo Snake 🔄
- [x] LangGraph agent implementation
- [x] OAuth integration
- [x] Full PPR adjustments
- [ ] Return yards scoring (25 yards/point)
- [ ] Live mock draft testing
- [ ] <3s response verification

### Phase 3 (Aug 20-24) - Sleeper Auction 📅
- [ ] Auction value calculations
- [ ] Budget management logic
- [ ] Stars & Scrubs strategy (70% on 3-4 elite)
- [ ] Real-time bidding recommendations
- [ ] No kicker position handling

---

## 📚 Documentation

- [Project Structure](PROJECT_STRUCTURE.md) - Detailed file organization
- [Architecture](docs/ARCHITECTURE.md) - System design
- [Action Log](action_log.md) - Development history
- [Claude Instructions](CLAUDE.md) - AI assistant guidelines
- [League Settings](docs/league_settings.md) - Specific league configurations

---

## ⚠️ Important Notes

### Development Guidelines
- **DO NOT MODIFY** `platforms/sleeper/agents/` - production system
- Keep Sleeper and Yahoo systems **isolated**
- Yahoo requires **<3s response** for 90-second draft clock
- Use `unified_server.py` for all testing
- All new development uses `platforms/` structure

### Critical Context Passing
The unified server MUST pass full draft context to agents:
```python
context["draft_picks"] = status.get("draftPicks", [])
context["available_players"] = status.get("availablePlayers", [])
context["recent_picks"] = status.get("recentPicks", [])
```

---

## 🤝 Contributing

This project is actively maintained for the 2025 fantasy season. Issues and PRs welcome!

### Testing Requirements
1. Run comprehensive test suites before commits
2. Monitor response times (Yahoo <3s requirement)
3. Test with mock drafts before live drafts
4. Verify league-specific adjustments work

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **CrewAI** - Multi-agent orchestration for Sleeper
- **LangGraph** - High-performance state machines for Yahoo
- **Anthropic** - Claude AI models
- **Sleeper & Yahoo** - Fantasy platforms and APIs
- **FantasyPros** - Rankings and projections via MCP

---

*Built with 🤖 by Adam Rubinsky | Phase 2 Day 4 - August 18, 2025*