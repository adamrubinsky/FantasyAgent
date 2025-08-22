# 🏈 FantasyAgent - AI-Powered Fantasy Football Draft Assistant

**Real-time draft assistance for Sleeper leagues with AI-powered recommendations**

[![Platform](https://img.shields.io/badge/Platform-Sleeper-purple.svg)](https://sleeper.app)
[![AI](https://img.shields.io/badge/AI-Claude%204%20Sonnet-blue.svg)](https://anthropic.com)
[![Framework](https://img.shields.io/badge/Framework-CrewAI-orange.svg)](https://crewai.com)
[![Tech](https://img.shields.io/badge/Tech-Python%20%7C%20FastAPI%20%7C%20Vue.js-red.svg)](https://github.com/adamrubinsky/FantasyAgent)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-green.svg)](https://github.com/adamrubinsky/FantasyAgent)

---

## 🎯 What is FantasyAgent?

FantasyAgent is an AI-powered draft assistant that provides real-time recommendations during your fantasy football drafts. It monitors your draft room, analyzes available players, and suggests optimal picks based on your league's specific scoring settings and your roster needs.

### ✅ Supported League Types

#### Production Ready
- **Sleeper Snake Drafts** (Half-PPR, SUPERFLEX)
  - Successfully used in multiple live drafts
  - 15-second response time with detailed analysis
  - Proactive recommendations at 6, 3, and 0 picks ahead

- **Sleeper Auction Drafts** (Half-PPR, $200 budget)
  - Real-time bid recommendations with max bid calculations
  - VBD-based auction values with market price analysis
  - Budget-aware adjustments based on remaining roster spots
  - 3-second update frequency for fast-paced bidding

#### In Development
- **Yahoo Snake Drafts** - Framework complete, awaiting live testing
- **Yahoo Auction Drafts** - Planned for future release

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Sleeper account with active draft
- Anthropic API key for Claude AI

### Installation

```bash
# Clone the repository
git clone https://github.com/adamrubinsky/FantasyAgent.git
cd FantasyAgent

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env.local
```

### Configuration

Edit `.env.local` with your settings:
```env
# Required: Your Anthropic API key
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here

# Optional: Default Sleeper username
SLEEPER_USERNAME=your-username
```

### Starting the Assistant

```bash
# Start the server
python3 unified_server.py

# Open in browser
# Navigate to: http://localhost:3001
```

---

## 📖 How to Use

### For Snake Drafts

1. **Start a Mock or Real Draft** in Sleeper
2. **Open FantasyAgent** at http://localhost:3001
3. **Select "Sleeper Snake"** from the platform dropdown
4. **Enter your Draft ID** (found in Sleeper draft URL)
5. **Enter your Team Name** or username
6. **Connect** and receive real-time recommendations

The assistant will:
- Show who's on the clock
- Display recent picks
- Provide recommendations when you're within 6 picks
- Give detailed analysis when it's your turn

### For Auction Drafts

1. **Start an Auction Draft** in Sleeper
2. **Select "Sleeper Auction"** in FantasyAgent
3. **Enter Draft ID** and **Slot Number** (e.g., "2" for Team 2)
4. **Connect** to receive bidding recommendations

The assistant provides:
- **Max Bid**: Maximum you should bid based on value and budget
- **Market Value**: Expected auction price
- **Budget Status**: Your remaining budget and roster needs
- **Proactive Analysis**: Updates every 3 seconds during nominations

---

## 🎮 Features

### Real-Time Draft Monitoring
- Tracks all picks as they happen
- Shows who's currently on the clock
- Displays your roster and recent picks
- Updates available players automatically

### AI-Powered Recommendations
- **Value Analysis**: Identifies best value picks based on ADP
- **Position Strategy**: Manages roster construction and balance
- **Risk Assessment**: Evaluates injury history and consistency
- **Synthesized Recommendations**: Top 3 picks with reasoning

### Auction-Specific Features
- **VBD Calculations**: Value-based drafting for accurate pricing
- **Budget Management**: Tracks spending and suggests allocation
- **Market Analysis**: Compares your max bid to expected prices
- **Quick Updates**: 3-second refresh for fast-paced bidding

### League Customization
- Supports SUPERFLEX positions
- Handles Half-PPR and Full-PPR scoring
- Adapts to roster requirements (2RB, 3WR, FLEX, etc.)
- Works with standard and custom scoring settings

---

## 🏗️ Technical Architecture

### Core Components

```
FantasyAgent/
├── unified_server.py           # Main server (port 3001)
├── templates/unified.html      # Web interface
├── core/
│   ├── draft_monitor.py        # Real-time draft tracking
│   └── sleeper_player_cache.py # Player ID resolution
├── platforms/sleeper/
│   └── agents/
│       ├── draft_crew.py       # Snake draft AI agents
│       └── sleeper_auction_crew_fast.py # Auction AI (<3s)
└── data/
    └── fantasypros_rankings_*.json # Rankings data
```

### AI Agent System

**Snake Draft** uses 4 specialized CrewAI agents:
1. **Value Analyst** - Identifies value picks vs ADP
2. **Position Strategist** - Manages roster balance
3. **Risk Assessor** - Evaluates player reliability
4. **Final Recommender** - Synthesizes final picks

**Auction Draft** uses optimized single-pass analysis:
- Parallel value calculations
- Position-based pricing tiers
- Budget-aware adjustments
- Rank-based fallbacks when data unavailable

---

## 📊 Performance

| Feature | Snake Draft | Auction Draft |
|---------|------------|---------------|
| Response Time | 15 seconds | 3 seconds |
| Update Frequency | On demand | Every 3 seconds |
| Recommendation Depth | Full analysis | Quick bid advice |
| Budget Tracking | N/A | Real-time |
| Platform Support | Sleeper ✅ | Sleeper ✅ |

---

## 🛠️ Troubleshooting

### Common Issues

**"Can't connect to draft"**
- Verify draft ID is correct (check Sleeper URL)
- Ensure draft has started (not just created)
- Confirm you're a participant in the draft

**"Team not found"**
- For auction: Use slot number (e.g., "2" for Team 2)
- For snake: Use exact team name or username
- Check spelling and capitalization

**"No recommendations showing"**
- Recommendations appear 6 picks before your turn
- Check that draft is active and not paused
- Verify connection status in UI

**"Values seem incorrect"**
- Rankings update weekly from FantasyPros
- Auction values use VBD calculations
- Custom scoring may affect player values

---

## 📅 Development Status

### Recently Completed (August 2024)
- ✅ Sleeper snake draft support with live testing
- ✅ Full auction draft implementation with VBD
- ✅ Real-time bid recommendations
- ✅ Budget-aware max bid calculations
- ✅ 3-second auction update frequency
- ✅ Player cache system for ID resolution

### Upcoming Features
- 🔄 Yahoo platform support (snake and auction)
- 🔄 ESPN platform integration
- 🔄 Dynasty league rookie draft support
- 🔄 Keeper league value optimization
- 🔄 Trade analyzer for season-long leagues

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test thoroughly with mock drafts
4. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Check response times
python3 tests/performance_test.py
```

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙏 Acknowledgments

- **Sleeper** - Fantasy platform and API
- **FantasyPros** - Rankings and projections
- **Anthropic** - Claude AI models
- **CrewAI** - Multi-agent orchestration framework

---

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/adamrubinsky/FantasyAgent/issues)
- **Discussions**: [GitHub Discussions](https://github.com/adamrubinsky/FantasyAgent/discussions)

---

*Built with 🤖 by Adam Rubinsky | Version 1.0.0 - August 2024*