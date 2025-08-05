# 🏈 Fantasy Football Draft Assistant

**AI-powered real-time draft recommendations for SUPERFLEX leagues**

[![Draft Ready](https://img.shields.io/badge/Draft%20Ready-August%2014%202025-green.svg)](https://github.com/adamrubinsky/FantasyAgent)
[![League Type](https://img.shields.io/badge/League-SUPERFLEX-blue.svg)]()
[![API Status](https://img.shields.io/badge/Sleeper%20API-Connected-brightgreen.svg)]()

---

## 🎯 Project Overview

Building an AI-powered fantasy football draft assistant that provides **real-time recommendations within the critical 90-second pick window** for my **August 14th, 2025 SUPERFLEX draft** on Sleeper platform.

### Key Features (Planned)
- ⚡ **<2 second response time** when your pick arrives
- 🏈 **SUPERFLEX league optimized** (QBs are much more valuable!)
- 🤖 **Multi-agent AI system** using CrewAI + Claude
- 📊 **Real-time draft monitoring** with 3-5 second polling
- 📈 **Live rankings integration** from FantasyPros
- 🎯 **Pre-computation engine** starts analysis 3 picks before your turn

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Your Sleeper username and league ID

### Installation & Testing
```bash
# Clone the repository
git clone https://github.com/adamrubinsky/FantasyAgent.git
cd FantasyAgent

# Install dependencies
pip3 install --user python-dotenv aiohttp click rich

# Set up environment
cp .env.example .env
# Edit .env with your Sleeper username and league ID

# Test connection with your league
python3 main.py test

# View your league details
python3 main.py league

# See available QBs (critical for SUPERFLEX!)
python3 main.py available -p QB -l 10
```

---

## 📊 Current Status (Day 1 Complete)

### ✅ What's Working Right Now
- **Sleeper API Integration**: Connected to test league successfully
- **Player Database**: 11,388 NFL players cached locally
- **Position Filtering**: QB/RB/WR/TE filtering works perfectly
- **SUPERFLEX Detection**: Automatically detects league format (QBs rank 2-4!)
- **Real-time Data**: Can see available players and current draft state
- **CLI Interface**: Multiple commands for testing and data exploration

### 🔄 In Development (Day 2-9)
- Draft monitoring with real-time pick detection
- AI agent system with CrewAI
- Claude integration for natural language analysis
- FantasyPros rankings integration
- Pre-computation engine
- Performance optimization

---

## 🏗️ Architecture

```
fantasy-draft-assistant/
├── agents/          # CrewAI multi-agent system
├── api/            # External API clients (Sleeper, Yahoo, FantasyPros)
├── core/           # Draft monitoring & recommendation engine  
├── data/           # Player cache & rankings storage
├── tests/          # Unit tests
└── main.py         # CLI interface
```

**Tech Stack**: Python 3.10+ • CrewAI • Claude AI • aiohttp • Click

---

## 🎲 Example League Details

**League**: [Your League Name]  
**Teams**: 12  
**Format**: SUPERFLEX + Half PPR  
**Draft**: Snake, August 2025  
**Draft Status**: Pre-draft

### 🚨 SUPERFLEX Impact
In SUPERFLEX leagues, you can start a QB in your FLEX position, making QBs **dramatically** more valuable:
- Josh Allen: Rank #2 overall
- Lamar Jackson: Rank #3 overall  
- Jayden Daniels: Rank #4 overall

**Strategy**: Draft QBs much earlier than standard leagues!

---

## 📋 Development Timeline

### ✅ Day 1 (Aug 5) - COMPLETED
- [x] Project setup & structure
- [x] Sleeper API client with caching
- [x] CLI interface with position filtering
- [x] Connection to actual league
- [x] Comprehensive documentation

### 🔄 Day 2 (Aug 6) - IN PROGRESS
- [ ] Real-time draft monitoring
- [ ] Pick detection & state management
- [ ] Enhanced CLI for live drafts

### 📅 Upcoming Days
- **Day 3**: FantasyPros rankings integration
- **Day 4**: Claude AI integration  
- **Weekend**: Multi-agent system & testing
- **Final**: Polish & draft day preparation

---

## 💻 Usage Examples

### Basic Commands
```bash
# Test API connections
python3 main.py test

# View league information
python3 main.py league

# See all available players (top 20)
python3 main.py available -l 20

# Filter by position (essential for SUPERFLEX)
python3 main.py available -p QB -l 10    # Top 10 QBs
python3 main.py available -p RB -l 15    # Top 15 RBs
python3 main.py available -p WR -l 20    # Top 20 WRs
```

### Sample Output
```
Available Players (QB)
┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┓
┃ Rank  ┃ Player               ┃ Pos    ┃ Team  ┃ Experience ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━┩
│ 2     │ Josh Allen           │ QB     │ BUF   │ 7y         │
│ 3     │ Lamar Jackson        │ QB     │ BAL   │ 7y         │
│ 4     │ Jayden Daniels       │ QB     │ WAS   │ 1y         │
```

---

## 📚 Documentation

- **[OVERVIEW.md](OVERVIEW.md)**: Complete project architecture & file explanations
- **[ACTION_LOG.md](ACTION_LOG.md)**: Daily development progress & discoveries
- **Code Comments**: Verbose explanations throughout codebase

---

## 🤝 Contributing

This is a personal project for my August 14th draft, but feel free to:
- 🐛 Report bugs or issues
- 💡 Suggest features or improvements  
- 📖 Improve documentation
- 🔧 Submit pull requests

---

## 📜 License

MIT License - feel free to adapt for your own fantasy drafts!

---

## 🎯 Success Metrics

- [ ] Recommendations delivered in <2 seconds
- [ ] Successfully complete August 14th draft
- [ ] Zero timeouts on any pick
- [ ] Draft grade improvement vs. previous seasons
- [ ] Build foundation for future seasons

---

**Built with ❤️ and Claude Code for the 2025 fantasy football season**