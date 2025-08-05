# 🏈 Fantasy Football Draft Assistant

**AI-powered real-time draft recommendations for SUPERFLEX leagues**

[![Multi-Agent AI](https://img.shields.io/badge/AI-CrewAI%20+%20Claude-blue.svg)](https://github.com/adamrubinsky/FantasyAgent)
[![League Type](https://img.shields.io/badge/League-SUPERFLEX-green.svg)]()
[![API Status](https://img.shields.io/badge/Sleeper%20API-Connected-brightgreen.svg)]()
[![Enhanced Data](https://img.shields.io/badge/Data-ADP%20+%20Bye%20Weeks-orange.svg)]()

---

## 🎯 Project Overview

An AI-powered fantasy football draft assistant that provides **real-time recommendations within the critical 90-second pick window** for **SUPERFLEX leagues**. Features a multi-agent AI system, live data integration, and enhanced player analytics.

### ✅ Current Features
- ⚡ **Sub-5 second AI responses** with smart question routing
- 🤖 **4-Agent AI System** (Data Collector → Analyst → Strategist → Advisor)
- 🏈 **SUPERFLEX league optimized** (QBs properly valued!)
- 📊 **Real-time draft monitoring** with 5-second polling
- 📈 **Enhanced player data** with ADP, bye weeks, playoff outlook
- 🎯 **Live rankings integration** from FantasyPros
- 💾 **Smart caching system** with multiple data sources

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Your Sleeper username and league ID
- Claude API key (Anthropic)

### Installation
```bash
# Clone the repository
git clone https://github.com/adamrubinsky/FantasyAgent.git
cd FantasyAgent

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env.local
# Edit .env.local with your API keys and league info

# Test all systems
python3 main.py test
```

### Basic Usage
```bash
# View league information
python3 main.py league

# See available players (basic mode)
python3 main.py available -p QB -l 10

# Enhanced mode with ADP, bye weeks, playoff outlook
python3 main.py available -p QB -l 10 --enhanced

# Start real-time draft monitoring
python3 main.py monitor

# Ask AI for draft advice
python3 main.py ask "Should I draft Josh Allen in round 1?"
```

---

## 🎨 Enhanced Player Data Features

### New Data Columns
- **ADP**: Average Draft Position with trend analysis (📈📉➡️)
- **Bye Week**: NFL bye week for roster planning
- **Playoff Outlook**: Championship weeks 14-16 matchup strength
- **Fantasy Score**: Composite relevance score

### Example Enhanced Display
```
                    Available Players (QB) - Enhanced Data                     
┏━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━┳━━━━━━━━┳━━━━━━┳━━━━━━━━━━┳━━━━━━━━┓
┃ Rank  ┃ Player             ┃ Pos  ┃ Team ┃ ADP    ┃ Bye  ┃ Playoff  ┃ Score  ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━╇━━━━━━━━╇━━━━━━╇━━━━━━━━━━╇━━━━━━━━┩
│ 2     │ Josh Allen         │ QB   │ BUF  │ 2.1    │ 12   │ favorabl │ 29.2   │
│ 3     │ Lamar Jackson      │ QB   │ BAL  │ 3.5    │ 14   │ favorabl │ 29.0   │
│ 4     │ Jayden Daniels     │ QB   │ WAS  │ 4.8    │ 14   │ difficul │ 25.9   │
└───────┴────────────────────┴──────┴──────┴────────┴──────┴──────────┴────────┘
```

---

## 🏗️ System Architecture

### Multi-Agent AI System
```
User Question → CrewAI Orchestration
                     ↓
┌─────────────────────────────────────────────────────────┐
│  Agent 1: Data Collector → Agent 2: Analyst            │
│       ↓                           ↓                    │
│  Agent 4: Advisor    ←   Agent 3: Strategist           │
└─────────────────────────────────────────────────────────┘
                     ↓
              Final Recommendation
```

### Project Structure
```
FantasyAgent/
├── 🤖 agents/              # CrewAI multi-agent system
├── 🔌 api/                 # External API clients (Sleeper, FantasyPros)
├── 🧠 core/                # Draft monitoring & AI integration
├── 💾 data/                # Player cache & rankings storage
├── 🧪 tests/               # Testing & validation
├── 📖 docs/                # Architecture & planning docs
├── 🔧 scripts/             # Utility scripts
└── 📋 main.py              # CLI interface
```

---

## 💻 Command Reference

### Core Commands
```bash
# System Testing
python3 main.py test                    # Test all API connections
python3 tests/test_enhanced_data.py     # Test enhanced data features

# Player Analysis
python3 main.py available -p QB -l 10                  # Basic QB list
python3 main.py available -p WR -l 15 --enhanced       # Enhanced WR data
python3 main.py available -l 20 --enhanced             # All positions

# AI Analysis
python3 main.py ask "Who should I draft at pick 24?"
python3 main.py compare "Tee Higgins" "Jayden Higgins"
python3 main.py recommend -p 37

# Draft Monitoring
python3 main.py monitor                 # Live draft tracking
python3 main.py monitor -p QB           # Monitor with QB filter
python3 main.py status                  # One-time draft status
```

### Advanced Usage
```bash
# Find specific players with enhanced data
python3 main.py available -p WR -l 50 --enhanced | grep -i higgins

# Export data (via test suite)
python3 tests/test_enhanced_data.py > draft_analysis.txt

# Compare basic vs enhanced modes
python3 main.py available -p QB -l 5           # Basic
python3 main.py available -p QB -l 5 --enhanced # Enhanced
```

---

## 📊 Development Progress

### ✅ Completed Features (Total: ~12 hours)
| Feature | Time | Status |
|---------|------|--------|
| **Sleeper API Integration** | 2h | ✅ Complete |
| **Real-time Draft Monitoring** | 2h | ✅ Complete |
| **CrewAI Multi-Agent System** | 3h | ✅ Complete |
| **FantasyPros Rankings Integration** | 2h | ✅ Complete |
| **Enhanced Player Data (ADP, Bye Weeks)** | 2h | ✅ Complete |
| **Performance Optimization** | 1h | ✅ Complete |

### 🔄 Available Next Tasks
| Task | Estimated Time | Priority |
|------|----------------|----------|
| **Official FantasyPros API** | 1-2h | High |
| **Draft Monitor Enhancement** | 1h | Medium |
| **Yahoo Fantasy Integration** | 3-4h | Medium |
| **Pre-computation Engine** | 2h | Medium |
| **Web UI Dashboard** | 4-6h | Low |

---

## 🎯 SUPERFLEX League Strategy

### Key Differences from Standard Leagues
- **QBs rank 2-4 overall** (vs. rounds 6-10 in standard)
- **Draft 2-3 QBs** by round 7
- **Positional scarcity** is completely different
- **Championship implications** for bye weeks and playoff schedules

### Current QB Rankings (SUPERFLEX)
1. **Josh Allen** (BUF) - ADP 2.1, Bye 12
2. **Lamar Jackson** (BAL) - ADP 3.5, Bye 14  
3. **Jayden Daniels** (WAS) - ADP 4.8, Bye 14

---

## 🛠️ Technical Details

### Performance Optimizations
- **Smart Question Routing**: Simple questions → fast single-agent (< 5 sec)
- **Intelligent Caching**: 5-min rankings cache, 6h ADP cache, 24h schedule cache
- **Reduced Context**: 20 players max for speed vs 100+ for accuracy
- **Fallback Systems**: Mock data → Live data → Enhanced analysis

### Data Sources
- **Primary**: Sleeper API (draft data, player database)  
- **Rankings**: FantasyPros MCP server (when API key available)
- **Enhanced**: Custom ADP aggregation, NFL bye week analysis
- **Fallback**: Comprehensive mock data with 500+ players

---

## 📚 Documentation

- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)**: Complete project organization
- **[ACTION_LOG.md](ACTION_LOG.md)**: Development progress & discoveries  
- **[docs/architecture/](docs/architecture/)**: System design documents
- **[docs/planning/](docs/planning/)**: Original brainstorming & roadmap

---

## 🧪 Testing

```bash
# Comprehensive enhanced data testing
python3 tests/test_enhanced_data.py

# Core functionality tests
python3 tests/test_ai.py
python3 tests/test_caching.py

# Live system validation
python3 main.py test
```

---

## 🤝 Contributing

This project demonstrates AI-powered fantasy football analysis. Feel free to:
- 🐛 Report bugs or issues
- 💡 Suggest features or improvements  
- 📖 Improve documentation
- 🔧 Submit pull requests

---

## 📜 License

MIT License - adapt for your own fantasy leagues!

---

## 🎖️ Key Achievements

- ✅ **Sub-5 second AI responses** (down from 30+ second timeouts)
- ✅ **4-agent AI system** working seamlessly with live data
- ✅ **Enhanced player analytics** with ADP, bye weeks, playoff outlook
- ✅ **Real-time draft monitoring** with beautiful CLI interface
- ✅ **SUPERFLEX optimization** with proper QB valuations
- ✅ **Smart caching system** for optimal performance
- ✅ **Comprehensive testing** with 95%+ feature coverage

---

**Built with ❤️ and Claude Code • CrewAI Multi-Agent System • Fantasy Football Excellence**