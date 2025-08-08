# 🏈 Fantasy Football Draft Assistant

**AI-powered real-time draft recommendations for SUPERFLEX leagues**

[![Multi-Agent AI](https://img.shields.io/badge/AI-Claude%204%20Sonnet-blue.svg)](https://github.com/adamrubinsky/FantasyAgent)
[![League Type](https://img.shields.io/badge/League-SUPERFLEX-green.svg)]()
[![API Status](https://img.shields.io/badge/APIs-Sleeper%20%2B%20FantasyPros-brightgreen.svg)]()
[![Performance](https://img.shields.io/badge/Response%20Time-15--20s-orange.svg)]()

---

## 🎯 Project Overview

An AI-powered fantasy football draft assistant that provides **real-time recommendations** for **SUPERFLEX leagues**. Built with CrewAI multi-agent system, Claude 4 Sonnet, and live data from Sleeper and FantasyPros APIs.

### ✨ Key Features
- ⚡ **15-20 second AI responses** with intelligent recommendations
- 🤖 **CrewAI Multi-Agent System** with Claude 4 Sonnet integration  
- 🏈 **TRUE SUPERFLEX rankings** using FantasyPros 'OP' position parameter
- 📊 **Real-time draft monitoring** with 5-second polling
- 🎯 **Proactive recommendations** at 6 and 3 picks before your turn
- 📈 **Cross-platform player mapping** for 11,389 players
- 🔄 **Smart caching system** with 4-hour TTL for API efficiency
- 🌐 **Web interface** at http://localhost:3000

### 🏆 Current Status
**PRODUCTION READY** as of August 8, 2025 - Successfully tested with mock drafts!

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Sleeper account with league access
- Anthropic API key (for Claude)
- FantasyPros API key (optional but recommended)

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

# FantasyPros API (recommended for SUPERFLEX rankings)
FANTASYPROS_API_KEY=your-fantasypros-key
```

### Running the Assistant

```bash
# Start the development server
python3 dev_server.py

# Access the web interface
# Open browser to: http://localhost:3000
```

---

## 🏗️ System Architecture

### Core Components

```
FantasyAgent/
├── agents/               # CrewAI multi-agent system
│   └── draft_crew.py    # Main AI orchestration (Claude 4 Sonnet)
├── api/                 # External API integrations
│   └── sleeper_client.py    # Sleeper draft monitoring
├── core/                # Business logic
│   ├── draft_monitor.py     # Real-time draft tracking
│   └── official_fantasypros.py  # SUPERFLEX rankings (OP position)
├── data/                # Cached data and mappings
│   └── player_id_mapping.json  # 11,389 cross-platform IDs
├── templates/           # Web interface
│   └── dev.html        # Main UI (real-time updates)
└── dev_server.py       # FastAPI backend server
```

### Data Flow
1. **Draft Monitoring** → Sleeper API (5-second polling)
2. **Rankings Fetch** → FantasyPros API with `position='OP'` for SUPERFLEX
3. **Player Filtering** → Cross-platform ID mapping + keeper detection
4. **AI Analysis** → CrewAI agents with Claude 4 Sonnet
5. **Recommendations** → Web UI with real-time updates

---

## 📊 Key Features Explained

### SUPERFLEX Rankings (Fixed!)
```python
# Uses FantasyPros 'OP' (Offensive Player) position for true SUPERFLEX values
params = {
    'position': 'OP',    # This is the key!
    'scoring': 'HALF',   # Half-PPR
    'type': 'DRAFT',     # Draft rankings
    'week': 0            # Season-long
}
# Result: Tyreek Hill at #47 (correct) vs #30 (standard)
```

### CrewAI Configuration
```python
# Critical: Set environment variable BEFORE importing
os.environ["ANTHROPIC_API_KEY"] = api_key

# Don't pass api_key parameter - causes auth errors!
llm = LLM(
    model="claude-sonnet-4-20250514",  # Claude 4 Sonnet
    temperature=0.7,
    max_tokens=4000
)
```

### Proactive Recommendations
- Triggers at **6 picks** before your turn (initial analysis)
- Updates at **3 picks** before your turn (final recommendations)
- Pre-computed and cached for instant delivery

---

## 🎮 Usage Guide

### Starting a Mock Draft

1. **Start the server**: `python3 dev_server.py`
2. **Open browser**: http://localhost:3000
3. **Connect to draft**: Enter your Sleeper draft ID
4. **Monitor in real-time**: See picks as they happen
5. **Get recommendations**: Ask questions in the chat

### Example Questions
- "Who should I draft with my next pick?"
- "Compare Josh Allen vs Lamar Jackson"
- "What positions should I target?"
- "Show me available RBs"

### Understanding Recommendations
The AI considers:
- Your current roster composition
- SUPERFLEX league scoring (QBs valued higher)
- Position scarcity (3 WR requirement)
- Bye week distribution
- Available players in your draft

---

## 🔧 Troubleshooting

### Common Issues

**Issue**: AI recommendations take too long (>30s)
- **Solution**: Already optimized to 15-20s in latest version

**Issue**: Wrong player rankings (QBs undervalued)
- **Solution**: Fixed with FantasyPros 'OP' position parameter

**Issue**: Drafted players still being recommended
- **Solution**: Fixed with enhanced keeper detection

**Issue**: CrewAI authentication errors
- **Solution**: Set ANTHROPIC_API_KEY env var before importing

---

## 📈 Performance Metrics

- **API Response Times**: 
  - Sleeper: <500ms
  - FantasyPros: <1s
- **AI Recommendations**: 15-20 seconds
- **Draft Monitoring**: 5-second intervals
- **Cache Hit Rate**: >90%
- **Player Database**: 11,389 mapped players

---

## 🗺️ Roadmap

### Completed (August 8, 2025)
- ✅ SUPERFLEX rankings fixed
- ✅ CrewAI/Claude 4 integration
- ✅ Mock draft testing
- ✅ Performance optimization
- ✅ Keeper filtering

### Future Enhancements
- [ ] AWS Bedrock deployment
- [ ] Yahoo Fantasy integration
- [ ] Voice notifications
- [ ] Historical pattern analysis
- [ ] Trade analyzer

---

## 📚 Documentation

- [System Architecture](docs/architecture/system_flow_diagram_v2.md)
- [API Integration Guide](docs/planning/brainstorming.md)
- [Development Log](docs/ACTION_LOG.md)
- [Project Structure](docs/PROJECT_STRUCTURE.md)

---

## 🤝 Contributing

This project is actively maintained for the 2025 fantasy season. Issues and PRs welcome!

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **CrewAI** - Multi-agent orchestration framework
- **Anthropic** - Claude 4 Sonnet AI model
- **Sleeper** - Fantasy platform and API
- **FantasyPros** - Rankings and projections data

---

*Built with 🤖 by Adam Rubinsky | Powered by Claude Code*